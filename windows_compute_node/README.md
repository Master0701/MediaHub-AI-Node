# MediaHub Compute Node for Windows

Windows-specific frontend for the MediaHub AI/Compute Node.

## Goals

- standalone Windows executable
- reuse the existing MediaHub AI Node core
- hardware and capability discovery
- CPU/GPU worker selection
- `.mhaiplugin` support
- authenticated connection to MediaHub
- job queue and health reporting

## Important

The existing Raspberry Pi online installation remains separate and must not
be modified by the Windows Compute Node build or installer.


## Speech-to-Text und isolierte Python-Runtime

Der Windows Compute Node kann für lokale Speech-to-Text-Aufgaben eine
vom Hauptprogramm getrennte Python-Runtime verwenden.

Aktueller Runtime-Stand:

- Python 3.12.10 Embedded x64
- Download ausschließlich von `python.org`
- Integritätsprüfung über fest hinterlegte SHA-256-Prüfsumme
- pip-Bootstrap ausschließlich über HTTPS von `bootstrap.pypa.io`
- Speech-Engine: `faster-whisper`
- CPU- und GPU-Ausführung
- automatische Accelerator-Auswahl
- NVIDIA-CUDA-Nutzung nur bei geeigneter vorhandener Umgebung

Heruntergeladene Runtime-, Modell-, Cache- und Paketdateien liegen
außerhalb des eingecheckten Quellbestands und dürfen nicht Bestandteil
des Git-Repositories werden.

## Hardwareerkennung unter Windows

Die Hardwareerkennung berücksichtigt CPU, dedizierte GPUs sowie
integrierte GPU/APU-Grafik.

Für die Erkennung können vorhandene Windows- und Treiberkomponenten
verwendet werden:

- Windows CIM/WMI
- DXDiag
- `nvidia-smi` bei NVIDIA-GPUs

Ermittelte GPU-Speicherwerte unterscheiden zwischen dediziertem und
gemeinsam verwendetem Speicher. Die Hardwareerkennung wird während der
laufenden Node-Sitzung gecacht und kann explizit aktualisiert werden.
