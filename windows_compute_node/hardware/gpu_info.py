"""GPU discovery for the Windows Compute Node."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _run_nvidia_smi() -> str | None:
    executable = shutil.which("nvidia-smi")

    if not executable:
        return None

    command = [
        executable,
        "--query-gpu=index,name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def get_nvidia_gpus() -> list[dict[str, Any]]:
    output = _run_nvidia_smi()

    if not output:
        return []

    gpus: list[dict[str, Any]] = []

    for line in output.splitlines():
        parts = [
            item.strip()
            for item in line.split(",")
        ]

        if len(parts) != 4:
            continue

        index, name, memory_mb, driver = parts

        try:
            memory = int(memory_mb)
        except ValueError:
            memory = 0

        gpus.append(
            {
                "index": int(index),
                "name": name,
                "memory_total_mb": memory,
                "driver_version": driver,
                "vendor": "NVIDIA",
            }
        )

    return gpus


def _normalize_vendor(
    compatibility: str,
    name: str,
    pnp_device_id: str,
) -> str:
    """Normalize a Windows GPU vendor."""

    compatibility_lower = (
        compatibility.strip().lower()
    )
    name_lower = name.strip().lower()
    pnp_upper = pnp_device_id.upper()

    if (
        "VEN_10DE" in pnp_upper
        or "nvidia" in compatibility_lower
        or name_lower.startswith("nvidia ")
    ):
        return "NVIDIA"

    if (
        "VEN_1002" in pnp_upper
        or "advanced micro devices"
        in compatibility_lower
        or name_lower.startswith("amd ")
        or name_lower.startswith("ati ")
    ):
        return "AMD"

    if (
        "VEN_8086" in pnp_upper
        or "intel" in compatibility_lower
        or name_lower.startswith("intel ")
    ):
        return "Intel"

    return "Unknown"


def _backend_family(
    vendor: str,
) -> list[str]:
    if vendor == "NVIDIA":
        return [
            "cuda",
            "directml",
        ]

    if vendor == "AMD":
        return [
            "directml",
            "rocm",
        ]

    if vendor == "Intel":
        return [
            "openvino",
            "directml",
        ]

    return []


def _classify_integrated(
    *,
    vendor: str,
    name: str,
    adapter_ram: int,
    cpu_name: str,
) -> bool:
    """Best-effort integrated-GPU classification.

    This is classification only. It does not claim
    that a Speech backend can execute on the device.
    """

    name_lower = name.strip().lower()
    cpu_lower = cpu_name.strip().lower()

    if vendor == "Intel":
        integrated_markers = (
            "iris",
            "uhd graphics",
            "hd graphics",
            "intel(r) graphics",
        )

        if any(
            marker in name_lower
            for marker in integrated_markers
        ):
            return True

    if vendor == "AMD":
        # Ryzen APUs commonly expose a generic
        # "AMD Radeon(TM) Graphics" adapter.
        if (
            "ryzen" in cpu_lower
            and "radeon" in cpu_lower
            and (
                name_lower
                in {
                    "amd radeon(tm) graphics",
                    "amd radeon graphics",
                    "radeon graphics",
                }
                or adapter_ram <= 1024 * 1024 * 1024
            )
        ):
            return True

        apu_markers = (
            "radeon 610m",
            "radeon 660m",
            "radeon 680m",
            "radeon 740m",
            "radeon 760m",
            "radeon 780m",
            "radeon 8060s",
            "radeon 8050s",
        )

        if any(
            marker in name_lower
            for marker in apu_markers
        ):
            return True

    return False


def _parse_windows_gpu_payload(
    payload: list[dict[str, Any]],
    *,
    cpu_name: str = "",
) -> list[dict[str, Any]]:
    """Convert CIM GPU data to MediaHub accelerators."""

    devices: list[dict[str, Any]] = []

    for index, raw in enumerate(payload):
        name = str(
            raw.get("Name") or ""
        ).strip()

        compatibility = str(
            raw.get("AdapterCompatibility")
            or ""
        ).strip()

        pnp_device_id = str(
            raw.get("PNPDeviceID") or ""
        ).strip()

        driver = str(
            raw.get("DriverVersion") or ""
        ).strip()

        try:
            adapter_ram = int(
                raw.get("AdapterRAM") or 0
            )
        except (TypeError, ValueError):
            adapter_ram = 0

        if not name:
            continue

        vendor = _normalize_vendor(
            compatibility,
            name,
            pnp_device_id,
        )

        integrated = _classify_integrated(
            vendor=vendor,
            name=name,
            adapter_ram=adapter_ram,
            cpu_name=cpu_name,
        )

        devices.append(
            {
                "index": index,
                "kind": "gpu",
                "vendor": vendor,
                "name": name,
                "integrated": integrated,
                "device_class": (
                    "integrated_gpu"
                    if integrated
                    else "discrete_gpu"
                ),
                "memory_total_mb": (
                    adapter_ram
                    // (1024 * 1024)
                ),
                "memory_dedicated_mb": (
                    adapter_ram
                    // (1024 * 1024)
                ),
                "memory_source": "wmi_adapter_ram",
                "driver_version": driver,
                "pnp_device_id": pnp_device_id,
                "backend_family": (
                    _backend_family(vendor)
                ),
                "detected": True,
            }
        )

    return devices


_DXDIAG_GPU_MEMORY_CACHE: list[
    dict[str, Any]
] | None = None


def _decode_dxdiag_bytes(
    data: bytes,
) -> str | None:
    """Decode DXDiag text produced by different Windows locales."""

    for encoding in (
        "utf-8-sig",
        "cp1252",
    ):
        try:
            text = data.decode(
                encoding
            )
        except UnicodeError:
            continue

        if (
            "Card name:" in text
            or "Display Devices" in text
        ):
            return text

    return None


def _run_dxdiag_gpu_memory() -> list[dict[str, Any]]:
    """Run DXDiag once and parse GPU memory information."""

    executable = shutil.which(
        "dxdiag.exe"
    )

    if not executable:
        executable = shutil.which(
            "dxdiag"
        )

    if not executable:
        return []

    temp_path = (
        Path(tempfile.gettempdir())
        / "mediahub_compute_node_dxdiag.txt"
    )

    try:
        temp_path.unlink(
            missing_ok=True
        )
    except OSError:
        pass

    try:
        result = subprocess.run(
            [
                executable,
                "/t",
                str(temp_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return []

    if result.returncode != 0:
        return []

    if not temp_path.exists():
        return []

    try:
        data = temp_path.read_bytes()
    except OSError:
        return []
    finally:
        try:
            temp_path.unlink(
                missing_ok=True
            )
        except OSError:
            pass

    text = _decode_dxdiag_bytes(
        data
    )

    if text is None:
        return []

    return _parse_dxdiag_gpu_memory(
        text
    )


def get_dxdiag_gpu_memory() -> list[dict[str, Any]]:
    """Return cached DXDiag GPU memory information."""

    global _DXDIAG_GPU_MEMORY_CACHE

    if _DXDIAG_GPU_MEMORY_CACHE is None:
        _DXDIAG_GPU_MEMORY_CACHE = (
            _run_dxdiag_gpu_memory()
        )

    return [
        dict(item)
        for item in _DXDIAG_GPU_MEMORY_CACHE
    ]


def _parse_dxdiag_memory_mb(
    value: str | None,
) -> int | None:
    """Parse a DXDiag memory value such as '8020 MB'."""

    if not value:
        return None

    cleaned = str(value).strip()

    if not cleaned:
        return None

    number = cleaned.split()[0]

    try:
        return int(number)
    except (TypeError, ValueError):
        return None


def _parse_dxdiag_gpu_memory(
    text: str,
) -> list[dict[str, Any]]:
    """Parse GPU memory information from DXDiag text."""

    devices: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    wanted = {
        "Card name": "name",
        "Manufacturer": "manufacturer",
        "Device Key": "device_key",
        "Device ID": "device_id",
        "Display Memory": "memory_display_mb",
        "Dedicated Memory": "memory_dedicated_mb",
        "Shared Memory": "memory_shared_mb",
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or ":" not in line:
            continue

        key, value = line.split(
            ":",
            1,
        )

        key = key.strip()
        value = value.strip()

        if key == "Card name":
            if current:
                devices.append(current)

            current = {
                "name": value,
            }
            continue

        if current is None:
            continue

        target = wanted.get(key)

        if not target:
            continue

        if target.startswith("memory_"):
            current[target] = (
                _parse_dxdiag_memory_mb(
                    value
                )
            )
        else:
            current[target] = value

    if current:
        devices.append(current)

    return devices


def _merge_dxdiag_memory(
    devices: list[dict[str, Any]],
    dxdiag_devices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich Windows GPU devices with DXDiag memory data."""

    unused = list(dxdiag_devices)

    for device in devices:
        device_name = str(
            device.get("name") or ""
        ).strip().lower()

        pnp_id = str(
            device.get("pnp_device_id") or ""
        ).strip().lower()

        match = None

        # Prefer exact PNP / Device Key matching.
        for candidate in unused:
            device_key = str(
                candidate.get(
                    "device_key"
                )
                or ""
            ).strip().lower()

            if (
                pnp_id
                and device_key
                and (
                    pnp_id in device_key
                    or device_key.endswith(
                        pnp_id
                    )
                )
            ):
                match = candidate
                break

        # Names are normally identical between WMI and DXDiag.
        if match is None:
            for candidate in unused:
                candidate_name = str(
                    candidate.get(
                        "name"
                    )
                    or ""
                ).strip().lower()

                if (
                    device_name
                    and candidate_name
                    and device_name
                    == candidate_name
                ):
                    match = candidate
                    break

        if match is None:
            continue

        dedicated = match.get(
            "memory_dedicated_mb"
        )

        shared = match.get(
            "memory_shared_mb"
        )

        if (
            isinstance(dedicated, int)
            and dedicated >= 0
        ):
            device[
                "memory_dedicated_mb"
            ] = dedicated

            # Keep memory_total_mb compatible:
            # it means compute-relevant dedicated VRAM.
            #
            # NVIDIA may already have a better nvidia-smi
            # value. Do not replace it with DXDiag.
            if (
                device.get(
                    "memory_source"
                )
                != "nvidia-smi"
            ):
                device[
                    "memory_total_mb"
                ] = dedicated

                device[
                    "memory_source"
                ] = "dxdiag"

        if (
            isinstance(shared, int)
            and shared >= 0
        ):
            device[
                "memory_shared_mb"
            ] = shared

        unused.remove(match)

    return devices


def _merge_nvidia_memory(
    devices: list[dict[str, Any]],
    nvidia_gpus: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich Windows NVIDIA adapters with nvidia-smi data.

    Win32_VideoController.AdapterRAM is a UInt32 value and
    cannot reliably represent modern dedicated VRAM sizes
    above roughly 4 GiB. nvidia-smi is authoritative for
    NVIDIA dedicated memory when available.
    """

    unused = list(nvidia_gpus)

    for device in devices:
        if device.get("vendor") != "NVIDIA":
            continue

        device_name = str(
            device.get("name") or ""
        ).strip().lower()

        match = None

        for candidate in unused:
            candidate_name = str(
                candidate.get("name") or ""
            ).strip().lower()

            if (
                device_name
                and candidate_name
                and device_name == candidate_name
            ):
                match = candidate
                break

        # A system can contain a single NVIDIA adapter whose
        # naming differs slightly between CIM and nvidia-smi.
        if match is None and len(unused) == 1:
            match = unused[0]

        if match is None:
            continue

        try:
            memory_mb = int(
                match.get(
                    "memory_total_mb"
                )
                or 0
            )
        except (TypeError, ValueError):
            memory_mb = 0

        if memory_mb > 0:
            device["memory_total_mb"] = memory_mb
            device["memory_dedicated_mb"] = memory_mb
            device["memory_source"] = "nvidia-smi"

        smi_driver = str(
            match.get(
                "driver_version"
            )
            or ""
        ).strip()

        if smi_driver:
            device["driver_version"] = smi_driver

        unused.remove(match)

    return devices


def _run_powershell_json(
    script: str,
) -> Any:
    executable = (
        shutil.which("powershell.exe")
        or shutil.which("powershell")
    )

    if not executable:
        return None

    try:
        result = subprocess.run(
            [
                executable,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None

    if result.returncode != 0:
        return None

    output = result.stdout.strip()

    if not output:
        return None

    try:
        import json

        return json.loads(output)
    except (
        ValueError,
        TypeError,
    ):
        return None


_WINDOWS_GPU_CACHE: list[
    dict[str, Any]
] | None = None


def clear_gpu_cache() -> None:
    """Invalidate cached Windows GPU discovery data."""

    global _WINDOWS_GPU_CACHE
    global _DXDIAG_GPU_MEMORY_CACHE

    _WINDOWS_GPU_CACHE = None
    _DXDIAG_GPU_MEMORY_CACHE = None


def get_windows_gpus(
    *,
    refresh: bool = False,
) -> list[dict[str, Any]]:
    """Discover and cache Windows display adapters via CIM."""

    global _WINDOWS_GPU_CACHE

    if (
        not refresh
        and _WINDOWS_GPU_CACHE is not None
    ):
        return [
            dict(device)
            for device in _WINDOWS_GPU_CACHE
        ]

    if refresh:
        clear_gpu_cache()

    gpu_payload = _run_powershell_json(
        "Get-CimInstance Win32_VideoController "
        "| Select-Object "
        "Name,AdapterCompatibility,AdapterRAM,"
        "DriverVersion,PNPDeviceID "
        "| ConvertTo-Json -Compress"
    )

    if gpu_payload is None:
        return []

    if isinstance(gpu_payload, dict):
        gpu_payload = [gpu_payload]

    if not isinstance(gpu_payload, list):
        return []

    cpu_payload = _run_powershell_json(
        "Get-CimInstance Win32_Processor "
        "| Select-Object -First 1 Name "
        "| ConvertTo-Json -Compress"
    )

    cpu_name = ""

    if isinstance(cpu_payload, dict):
        cpu_name = str(
            cpu_payload.get("Name")
            or ""
        )

    devices = _parse_windows_gpu_payload(
        gpu_payload,
        cpu_name=cpu_name,
    )

    devices = _merge_dxdiag_memory(
        devices,
        get_dxdiag_gpu_memory(),
    )

    devices = _merge_nvidia_memory(
        devices,
        get_nvidia_gpus(),
    )

    _WINDOWS_GPU_CACHE = [
        dict(device)
        for device in devices
    ]

    return [
        dict(device)
        for device in _WINDOWS_GPU_CACHE
    ]
