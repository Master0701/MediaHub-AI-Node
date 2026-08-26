"""Windows entry point for the MediaHub Compute Node."""

from __future__ import annotations

from pathlib import Path

from windows_compute_node.config.node_identity import (
    NodeIdentity,
)
from windows_compute_node.config.settings import (
    NodeSettings,
)
from windows_compute_node.hardware.capabilities import (
    get_capabilities,
)
from windows_compute_node.service.api_server import (
    run_server,
)


def _runtime_dir() -> Path:
    return (
        Path.cwd()
        / "windows_compute_node"
        / "runtime"
    )


def main() -> int:
    runtime = _runtime_dir()

    identity = NodeIdentity(
        runtime / "node_identity.json"
    ).load_or_create()

    settings = NodeSettings(
        runtime / "settings.json"
    ).load()

    capabilities = get_capabilities()

    cpu = capabilities["cpu"]
    accelerators = capabilities[
        "accelerators"
    ]

    print("MediaHub Compute Node")
    print("=====================")

    print(
        f"Node-ID  : "
        f"{identity['node_id']}"
    )

    print(
        f"Name     : "
        f"{settings['node_name']}"
    )

    print(
        f"Adresse  : "
        f"{settings['listen_host']}:"
        f"{settings['listen_port']}"
    )

    print()

    print(
        f"Platform : "
        f"{capabilities['platform']} "
        f"{capabilities['machine']}"
    )

    print(
        f"CPU      : "
        f"{cpu['name']}"
    )

    print(
        f"Threads  : "
        f"{cpu['logical_threads']}"
    )

    print()

    print("Beschleuniger")

    if not accelerators:
        print(
            "  Keine unterstützten "
            "Beschleuniger erkannt."
        )
    else:
        for device in accelerators:
            kind = str(
                device.get("kind")
                or "unknown"
            ).upper()

            vendor = str(
                device.get("vendor")
                or "unknown"
            )

            name = str(
                device.get("name")
                or "unknown"
            )

            index = device.get("index")

            display_name = name

            if not name.upper().startswith(
                vendor.upper()
            ):
                display_name = (
                    f"{vendor} {name}"
                )

            print(
                f"  {kind} {index}: "
                f"{display_name}"
            )

            memory = device.get(
                "memory_total_mb"
            )

            if memory is not None:
                print(
                    f"    Speicher: "
                    f"{memory} MB"
                )

            driver = device.get(
                "driver_version"
            )

            if driver:
                print(
                    f"    Treiber : "
                    f"{driver}"
                )

            backends = (
                device.get(
                    "backend_family"
                )
                or []
            )

            if backends:
                print(
                    "    Backends: "
                    + ", ".join(
                        str(item)
                        for item in backends
                    )
                )

    print()

    execution = settings["execution"]

    print(
        "Standardmodus : "
        f"{execution['default_mode']}"
    )

    print(
        "CPU-Threads   : "
        f"{execution['cpu_threads']}"
    )

    print(
        "GPU-Auswahl   : "
        f"{execution['gpu_device']}"
    )

    print()

    print(
        "Verfügbare Modi: "
        + ", ".join(
            capabilities[
                "execution_modes"
            ]
        )
    )

    print()
    print("Starte Netzwerk-API ...")

    run_server(
        runtime_dir=runtime,
        host=str(
            settings["listen_host"]
        ),
        port=int(
            settings["listen_port"]
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
