from __future__ import annotations

from windows_compute_node.hardware.gpu_info import (
    _decode_dxdiag_bytes,
    _merge_dxdiag_memory,
    _merge_nvidia_memory,
    _normalize_vendor,
    _parse_dxdiag_gpu_memory,
    _parse_windows_gpu_payload,
    clear_gpu_cache,
)


def test_vendor_pci_ids():
    assert (
        _normalize_vendor(
            "",
            "GPU",
            r"PCI\VEN_10DE&DEV_0001",
        )
        == "NVIDIA"
    )

    assert (
        _normalize_vendor(
            "",
            "GPU",
            r"PCI\VEN_1002&DEV_0001",
        )
        == "AMD"
    )

    assert (
        _normalize_vendor(
            "",
            "GPU",
            r"PCI\VEN_8086&DEV_0001",
        )
        == "Intel"
    )


def test_corporation_is_not_ati():
    assert (
        _normalize_vendor(
            "Intel Corporation",
            "Intel Arc Graphics",
            "",
        )
        == "Intel"
    )


def test_amd_apu():
    result = _parse_windows_gpu_payload(
        [
            {
                "Name": "AMD Radeon(TM) Graphics",
                "AdapterCompatibility": (
                    "Advanced Micro Devices, Inc."
                ),
                "AdapterRAM": 536870912,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_1002&DEV_1638"
                ),
            }
        ],
        cpu_name=(
            "AMD Ryzen 9 5900HX "
            "with Radeon Graphics"
        ),
    )

    gpu = result[0]

    assert gpu["vendor"] == "AMD"
    assert gpu["integrated"] is True
    assert (
        gpu["device_class"]
        == "integrated_gpu"
    )


def test_amd_discrete_gpu():
    result = _parse_windows_gpu_payload(
        [
            {
                "Name": "AMD Radeon RX 7900 XTX",
                "AdapterCompatibility": "AMD",
                "AdapterRAM": 24 * 1024**3,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_1002&DEV_744C"
                ),
            }
        ],
        cpu_name="AMD Ryzen 9 7950X",
    )

    gpu = result[0]

    assert gpu["vendor"] == "AMD"
    assert gpu["integrated"] is False
    assert (
        gpu["device_class"]
        == "discrete_gpu"
    )


def test_intel_integrated_gpu():
    result = _parse_windows_gpu_payload(
        [
            {
                "Name": "Intel Iris Xe Graphics",
                "AdapterCompatibility": (
                    "Intel Corporation"
                ),
                "AdapterRAM": 1024**3,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_8086&DEV_0001"
                ),
            }
        ],
        cpu_name="Intel Core Test CPU",
    )

    gpu = result[0]

    assert gpu["vendor"] == "Intel"
    assert gpu["integrated"] is True


def test_intel_discrete_arc():
    result = _parse_windows_gpu_payload(
        [
            {
                "Name": "Intel Arc A770",
                "AdapterCompatibility": (
                    "Intel Corporation"
                ),
                "AdapterRAM": 16 * 1024**3,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_8086&DEV_56A0"
                ),
            }
        ],
        cpu_name="Intel Core Test CPU",
    )

    gpu = result[0]

    assert gpu["vendor"] == "Intel"
    assert gpu["integrated"] is False


def test_nvidia_discrete_gpu():
    result = _parse_windows_gpu_payload(
        [
            {
                "Name": "NVIDIA GeForce RTX 4060",
                "AdapterCompatibility": "NVIDIA",
                "AdapterRAM": 8 * 1024**3,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_10DE&DEV_0001"
                ),
            }
        ],
        cpu_name="Test CPU",
    )

    gpu = result[0]

    assert gpu["vendor"] == "NVIDIA"
    assert gpu["integrated"] is False


def test_hybrid_amd_apu_and_nvidia():
    result = _parse_windows_gpu_payload(
        [
            {
                "Name": "AMD Radeon(TM) Graphics",
                "AdapterCompatibility": (
                    "Advanced Micro Devices, Inc."
                ),
                "AdapterRAM": 536870912,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_1002&DEV_1638"
                ),
            },
            {
                "Name": (
                    "NVIDIA GeForce RTX 3070 "
                    "Laptop GPU"
                ),
                "AdapterCompatibility": "NVIDIA",
                "AdapterRAM": 8 * 1024**3,
                "DriverVersion": "1.0",
                "PNPDeviceID": (
                    r"PCI\VEN_10DE&DEV_249D"
                ),
            },
        ],
        cpu_name=(
            "AMD Ryzen 9 5900HX "
            "with Radeon Graphics"
        ),
    )

    assert len(result) == 2

    assert result[0]["vendor"] == "AMD"
    assert result[0]["integrated"] is True

    assert result[1]["vendor"] == "NVIDIA"
    assert result[1]["integrated"] is False


def test_nvidia_smi_overrides_truncated_wmi_vram():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": (
                    "NVIDIA GeForce RTX 3070 "
                    "Laptop GPU"
                ),
                "AdapterCompatibility": "NVIDIA",
                "AdapterRAM": 4293918720,
                "DriverVersion": "WMI",
                "PNPDeviceID": (
                    r"PCI\VEN_10DE&DEV_249D"
                ),
            }
        ],
        cpu_name="Test CPU",
    )

    assert devices[0]["memory_total_mb"] == 4095
    assert (
        devices[0]["memory_source"]
        == "wmi_adapter_ram"
    )

    result = _merge_nvidia_memory(
        devices,
        [
            {
                "index": 0,
                "name": (
                    "NVIDIA GeForce RTX 3070 "
                    "Laptop GPU"
                ),
                "memory_total_mb": 8192,
                "driver_version": "566.07",
                "vendor": "NVIDIA",
            }
        ],
    )

    gpu = result[0]

    assert gpu["memory_total_mb"] == 8192
    assert gpu["memory_dedicated_mb"] == 8192
    assert gpu["memory_source"] == "nvidia-smi"
    assert gpu["driver_version"] == "566.07"


def test_nvidia_merge_does_not_modify_amd_apu():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": "AMD Radeon(TM) Graphics",
                "AdapterCompatibility": (
                    "Advanced Micro Devices, Inc."
                ),
                "AdapterRAM": 536870912,
                "DriverVersion": "AMD",
                "PNPDeviceID": (
                    r"PCI\VEN_1002&DEV_1638"
                ),
            }
        ],
        cpu_name=(
            "AMD Ryzen 9 5900HX "
            "with Radeon Graphics"
        ),
    )

    result = _merge_nvidia_memory(
        devices,
        [
            {
                "index": 0,
                "name": "NVIDIA Test GPU",
                "memory_total_mb": 8192,
                "driver_version": "566.07",
                "vendor": "NVIDIA",
            }
        ],
    )

    gpu = result[0]

    assert gpu["vendor"] == "AMD"
    assert gpu["integrated"] is True
    assert gpu["memory_total_mb"] == 512
    assert gpu["memory_dedicated_mb"] == 512
    assert (
        gpu["memory_source"]
        == "wmi_adapter_ram"
    )


def test_nvidia_merge_falls_back_to_wmi_without_smi():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": "NVIDIA Test GPU",
                "AdapterCompatibility": "NVIDIA",
                "AdapterRAM": 4293918720,
                "DriverVersion": "WMI",
                "PNPDeviceID": (
                    r"PCI\VEN_10DE&DEV_0001"
                ),
            }
        ],
        cpu_name="Test CPU",
    )

    result = _merge_nvidia_memory(
        devices,
        [],
    )

    gpu = result[0]

    assert gpu["memory_total_mb"] == 4095
    assert gpu["memory_dedicated_mb"] == 4095
    assert (
        gpu["memory_source"]
        == "wmi_adapter_ram"
    )


DXDIAG_MEMORY_SAMPLE = """
Card name: AMD Radeon(TM) Graphics
Manufacturer: Advanced Micro Devices, Inc.
Device Key: Enum\\PCI\\VEN_1002&DEV_1638&SUBSYS_106C1043&REV_C4
Display Memory: 8389 MB
Dedicated Memory: 496 MB
Shared Memory: 7893 MB
Device ID: 0x1638
Card name: NVIDIA GeForce RTX 3070 Laptop GPU
Manufacturer: NVIDIA
Device Key: Enum\\PCI\\VEN_10DE&DEV_249D&SUBSYS_106C1043&REV_A1
Display Memory: 15913 MB
Dedicated Memory: 8020 MB
Shared Memory: 7893 MB
Device ID: 0x249D
"""


def test_parse_dxdiag_gpu_memory():
    devices = _parse_dxdiag_gpu_memory(
        DXDIAG_MEMORY_SAMPLE
    )

    assert len(devices) == 2

    amd = devices[0]
    nvidia = devices[1]

    assert amd["name"] == "AMD Radeon(TM) Graphics"
    assert amd["memory_dedicated_mb"] == 496
    assert amd["memory_shared_mb"] == 7893
    assert amd["memory_display_mb"] == 8389

    assert (
        nvidia["memory_dedicated_mb"]
        == 8020
    )
    assert nvidia["memory_shared_mb"] == 7893


def test_dxdiag_enriches_amd_apu_memory():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": "AMD Radeon(TM) Graphics",
                "AdapterCompatibility": (
                    "Advanced Micro Devices, Inc."
                ),
                "AdapterRAM": 536870912,
                "DriverVersion": "AMD",
                "PNPDeviceID": (
                    "PCI\\\\VEN_1002&DEV_1638"
                    "&SUBSYS_106C1043&REV_C4"
                ),
            }
        ],
        cpu_name=(
            "AMD Ryzen 9 5900HX "
            "with Radeon Graphics"
        ),
    )

    dxdiag = _parse_dxdiag_gpu_memory(
        DXDIAG_MEMORY_SAMPLE
    )

    result = _merge_dxdiag_memory(
        devices,
        dxdiag,
    )

    gpu = result[0]

    assert gpu["integrated"] is True
    assert gpu["device_class"] == "integrated_gpu"
    assert gpu["memory_total_mb"] == 496
    assert gpu["memory_dedicated_mb"] == 496
    assert gpu["memory_shared_mb"] == 7893
    assert gpu["memory_source"] == "dxdiag"


def test_dxdiag_does_not_replace_nvidia_smi_vram():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": (
                    "NVIDIA GeForce RTX 3070 "
                    "Laptop GPU"
                ),
                "AdapterCompatibility": "NVIDIA",
                "AdapterRAM": 4293918720,
                "DriverVersion": "WMI",
                "PNPDeviceID": (
                    "PCI\\\\VEN_10DE&DEV_249D"
                    "&SUBSYS_106C1043&REV_A1"
                ),
            }
        ],
        cpu_name="Test CPU",
    )

    devices = _merge_nvidia_memory(
        devices,
        [
            {
                "index": 0,
                "name": (
                    "NVIDIA GeForce RTX 3070 "
                    "Laptop GPU"
                ),
                "memory_total_mb": 8192,
                "driver_version": "566.07",
                "vendor": "NVIDIA",
            }
        ],
    )

    result = _merge_dxdiag_memory(
        devices,
        _parse_dxdiag_gpu_memory(
            DXDIAG_MEMORY_SAMPLE
        ),
    )

    gpu = result[0]

    assert gpu["memory_total_mb"] == 8192
    assert gpu["memory_dedicated_mb"] == 8020
    assert gpu["memory_shared_mb"] == 7893
    assert gpu["memory_source"] == "nvidia-smi"


def test_dxdiag_supports_large_amd_discrete_vram():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": "AMD Radeon RX Test",
                "AdapterCompatibility": "AMD",
                "AdapterRAM": 4293918720,
                "DriverVersion": "AMD",
                "PNPDeviceID": (
                    "PCI\\\\VEN_1002&DEV_TEST"
                ),
            }
        ],
        cpu_name="AMD Ryzen Test",
    )

    dxdiag = _parse_dxdiag_gpu_memory(
        """
Card name: AMD Radeon RX Test
Manufacturer: Advanced Micro Devices, Inc.
Device Key: Enum\\PCI\\VEN_1002&DEV_TEST
Display Memory: 32768 MB
Dedicated Memory: 24576 MB
Shared Memory: 8192 MB
"""
    )

    gpu = _merge_dxdiag_memory(
        devices,
        dxdiag,
    )[0]

    assert gpu["integrated"] is False
    assert gpu["memory_total_mb"] == 24576
    assert gpu["memory_dedicated_mb"] == 24576
    assert gpu["memory_shared_mb"] == 8192
    assert gpu["memory_source"] == "dxdiag"


def test_dxdiag_supports_large_intel_discrete_vram():
    devices = _parse_windows_gpu_payload(
        [
            {
                "Name": "Intel Arc Test",
                "AdapterCompatibility": "Intel",
                "AdapterRAM": 4293918720,
                "DriverVersion": "Intel",
                "PNPDeviceID": (
                    "PCI\\\\VEN_8086&DEV_TEST"
                ),
            }
        ],
        cpu_name="Intel Test CPU",
    )

    dxdiag = _parse_dxdiag_gpu_memory(
        """
Card name: Intel Arc Test
Manufacturer: Intel Corporation
Device Key: Enum\\PCI\\VEN_8086&DEV_TEST
Display Memory: 24576 MB
Dedicated Memory: 16384 MB
Shared Memory: 8192 MB
"""
    )

    gpu = _merge_dxdiag_memory(
        devices,
        dxdiag,
    )[0]

    assert gpu["integrated"] is False
    assert gpu["memory_total_mb"] == 16384
    assert gpu["memory_dedicated_mb"] == 16384
    assert gpu["memory_shared_mb"] == 8192
    assert gpu["memory_source"] == "dxdiag"


def test_decode_dxdiag_cp1252():
    text = """
Display Devices
Card name: AMD Radeon(TM) Graphics
Dedicated Memory: 496 MB
Shared Memory: 7893 MB
Gerät: vollständig
"""

    encoded = text.encode(
        "cp1252"
    )

    result = _decode_dxdiag_bytes(
        encoded
    )

    assert result is not None
    assert "Card name:" in result
    assert "Gerät" in result


def test_decode_dxdiag_rejects_unknown_content():
    assert (
        _decode_dxdiag_bytes(
            b"not a dxdiag display report"
        )
        is None
    )


def test_clear_gpu_cache_resets_discovery_state():
    import windows_compute_node.hardware.gpu_info as gpu_info

    gpu_info._WINDOWS_GPU_CACHE = [
        {
            "name": "Cached GPU",
        }
    ]

    gpu_info._DXDIAG_GPU_MEMORY_CACHE = [
        {
            "name": "Cached DXDiag GPU",
        }
    ]

    clear_gpu_cache()

    assert gpu_info._WINDOWS_GPU_CACHE is None
    assert gpu_info._DXDIAG_GPU_MEMORY_CACHE is None
