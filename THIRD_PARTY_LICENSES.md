# Drittanbieter-Software und Lizenzen

MediaHub-AI-Node verwendet Python-Pakete und Betriebssystemkomponenten. Alle Rechte verbleiben bei den jeweiligen Urhebern. Diese Übersicht ersetzt nicht die Unterlagen der konkret installierten Version.

## Direkte Python-Abhängigkeiten

| Komponente | Zweck | Lizenz | Lokaler Standard-Lizenztext |
|---|---|---|---|
| aiosqlite | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| annotated-doc | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| annotated-types | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| anyio | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| certifi | Python-Abhängigkeit | MPL-2.0 | `licenses/MPL-2.0.txt` |
| click | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| fastapi | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| greenlet | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| h11 | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| httpcore | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| httptools | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| httpx | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| idna | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| packaging | Python-Abhängigkeit | Apache-2.0 OR BSD-2-Clause | `licenses/Apache-2.0.txt`, `licenses/BSD-2-Clause.txt` |
| psutil | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| pydantic | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| pydantic-settings | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| pydantic_core | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| python-dotenv | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| PyYAML | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| setuptools | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| SQLAlchemy | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| starlette | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| typing-inspection | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| typing_extensions | Python-Abhängigkeit | PSF-2.0 | `licenses/PSF-2.0.txt` |
| uvicorn | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| uvloop | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| watchfiles | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| websockets | Python-Abhängigkeit | BSD-3-Clause | `licenses/BSD-3-Clause.txt` |
| wheel | Python-Abhängigkeit | MIT | `licenses/MIT.txt` |
| opencv-python-headless | Python-Abhängigkeit | Apache-2.0 | `licenses/Apache-2.0.txt` |
| ImageHash | Python-Abhängigkeit | BSD-2-Clause | `licenses/BSD-2-Clause.txt` |

## Betriebssystem- und Installationskomponenten

Der Installer verwendet auf Debian-basierten Systemen `apt` und installiert Python, venv, pip, curl, CA-Zertifikate und Git. Diese Pakete werden nicht im Repository gebündelt. Ihre jeweiligen Lizenzen und Copyright-Hinweise stellt die verwendete Debian-/Raspberry-Pi-OS-Distribution bereit.

Optionale Linux-/ARM-Werkzeuge und spätere AI-Node-Plugins müssen vor Aufnahme in Installer, Tool-Katalog oder Release zusätzlich mit Hersteller, Paketquelle, Version, Plattform und Lizenz dokumentiert werden.



## Windows Compute Node

Der getrennte Windows Compute Node kann zusätzliche Laufzeitkomponenten
bei Bedarf aus den offiziellen Herstellerquellen herunterladen. Diese
Komponenten werden nicht im Git-Repository gebündelt.

### Isolierte Python-Laufzeit

Für das lokale Speech-to-Text-Plugin wird derzeit Python 3.12.10
Embedded x64 für Windows verwendet.

- Komponente: CPython 3.12.10 Embedded Distribution
- Hersteller/Projekt: Python Software Foundation / Python
- Plattform: Windows x86-64
- Quelle: `python.org`
- Paket: `python-3.12.10-embed-amd64.zip`
- Lizenz: Python Software Foundation License
- Lokaler Standard-Lizenztext: `licenses/PSF-2.0.txt`

Der Download wird vom Compute Node nicht im Repository gespeichert.
Die erwartete SHA-256-Prüfsumme ist im Provisioning-Code fest
hinterlegt und wird vor Verwendung geprüft.

### pip-Bootstrap

Falls die isolierte Python-Laufzeit noch kein pip besitzt, darf
`get-pip.py` ausschließlich per HTTPS von `bootstrap.pypa.io/get-pip.py`
geladen werden. Die Bootstrap-Datei wird nicht im Repository gebündelt.

pip und die darüber installierten Pakete behalten ihre jeweiligen
Lizenzen und Copyright-Hinweise.

### Speech-to-Text

Das optionale Plugin `mediahub.speech_to_text` verwendet eine eigene,
isolierte Python-Laufzeit und installiert seine Runtime-Abhängigkeiten
bei Bedarf über pip.

Direkt deklarierte Runtime-Abhängigkeit:

| Komponente | Zweck | Lizenz |
|---|---|---|
| faster-whisper | Lokale Speech-to-Text-Ausführung | MIT |

`faster-whisper` und seine transitiven Abhängigkeiten werden nicht im
Git-Repository gebündelt. Vor einem Windows-Compute-Node-Release müssen
die tatsächlich installierten Versionen und deren vollständige
Lizenzinformationen durch die Windows-Release-Prüfung inventarisiert
und dokumentiert werden.

### GPU- und Windows-Systemwerkzeuge

Der Windows Compute Node kann vorhandene Betriebssystem- bzw.
Treiberwerkzeuge zur Hardwareerkennung verwenden, darunter PowerShell,
Windows CIM/WMI, DXDiag und bei vorhandener NVIDIA-GPU `nvidia-smi`.

Diese Werkzeuge werden nicht durch MediaHub gebündelt oder verteilt.
Sie stammen aus Windows beziehungsweise aus der installierten
Grafiktreiberumgebung.


## Release-Regel

Ein Release darf nur erstellt werden, wenn jede direkte Abhängigkeit aus `requirements.txt` in `licenses/dependency_licenses.json` erfasst ist, alle referenzierten Lizenztexte vorhanden sind und der gesamte `licenses/`-Ordner zusammen mit `THIRD_PARTY_LICENSES.md` im Release enthalten ist.
