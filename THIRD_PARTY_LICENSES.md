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


### Windows Tray / GUI

#### pystray

- Verwendung: Windows-System-Tray des MediaHub Compute Node
- Paket: `pystray`
- Lizenz laut Paketmetadaten: GNU Lesser General Public License v3
- Original-Lizenzdateien:
  - `licenses/pystray-COPYING.txt`
  - `licenses/LGPL-3.0.txt`

#### Pillow

- Verwendung: Bild- und Icon-Verarbeitung für die Windows-Tray-Oberfläche
- Paket: `Pillow`
- Lizenz laut Paketmetadaten: MIT-CMU
- Pillow enthält bzw. verwendet zusätzlich Komponenten mit eigenen
  Lizenzbedingungen.
- Der vollständige mit dem installierten Pillow-Paket ausgelieferte
  Lizenztext einschließlich der Hinweise zu gebündelten Komponenten liegt
  unter:
  - `licenses/Pillow-LICENSE.txt`
### Windows Build- und Installer-Werkzeuge

#### PyInstaller

- Verwendung: Erstellung der eigenständigen Windows-EXE des MediaHub Compute Node
- Build-Werkzeug: `PyInstaller`
- Aktuell verwendete Version: `6.22.2`
- Lizenz: GPL-2.0-or-later mit PyInstaller Bootloader Exception
- PyInstaller wird als Build-Werkzeug verwendet und nicht als eigenständiges MediaHub-Programm weitergegeben.
- Die PyInstaller Bootloader Exception erlaubt die Verteilung der mit PyInstaller erzeugten Anwendung unter der Lizenz der Anwendung.

#### Inno Setup

- Verwendung: Erstellung des Windows-Setup-Pakets des MediaHub Compute Node
- Build-Werkzeug: `Inno Setup`
- Aktuell verwendete Version: `6.7.3`
- Inno Setup wird ausschließlich zum Erzeugen des Setup-Pakets verwendet und nicht mit MediaHub ausgeliefert.
- Für die verwendete Inno-Setup-Installation gelten die Lizenzbedingungen des Herstellers.
- Der derzeit verwendete Compiler meldet `Non-commercial use only`.
- Vor einer kommerziellen Nutzung oder kommerziellen Veröffentlichung muss daher eine dafür geeignete Inno-Setup-Lizenz vorhanden sein.

## Interaktions-KI: zusätzliche optionale Laufzeitkomponenten (Windows Compute Node)

| Komponente | Verwendung | Lizenz / Hinweis | Verteilung |
|---|---|---|---|
| llama.cpp / llama-server | lokale GGUF-Inferenz (CPU und CUDA) | MIT; maßgeblich sind Lizenz und Notices der tatsächlich eingesetzten Version | nicht als Bestandteil des Node-Quellcodes vorausgesetzt; lokale, geprüfte Archive |
| GGUF-Modell | lokale Sprachgenerierung | **modellabhängig**; Lizenz, Nutzungsbedingungen, Herkunft und eventuelle Einschränkungen für jedes konkrete Modell separat prüfen | nicht im Repository oder Plugin gebündelt |
| NVIDIA CUDA / Treiber und Runtime-Bibliotheken | optionale GPU-Beschleunigung | NVIDIA-Lizenzbedingungen der jeweils eingesetzten Komponenten; keine pauschale MIT-Lizenz | abhängig von vorhandener GPU und gewähltem Runtime-Paket |
| Python-Standardbibliothek (`ssl`, `http.server`, `hashlib`, `socket`) | HTTPS, Authentifizierung, Netzwerk und Prüfungen | Python Software Foundation License; zugrundeliegende OpenSSL-Komponenten nach ihrer jeweiligen Lizenz | über die verwendete Python-/EXE-Distribution |

Vor einem Release sind die **konkret gebündelten** Fremdkomponenten anhand der Build-Artefakte auf Original-Lizenztexte, NOTICE-Dateien und Weitergabebedingungen zu prüfen. Die MIT-Angabe für `llama.cpp` gilt nicht automatisch für Modelle, CUDA oder jedes fremde Binärpaket. Die vorhandene zentrale Lizenzsammlung bleibt bestehen.

## Windows Compute Node: optionale Interaktions-KI

Die Interaktions-KI v0.1.12 verwendet separat installierte llama.cpp-Runtime (MIT, https://github.com/ggml-org/llama.cpp), modellabhängig lizenzierte GGUF-Dateien und optional NVIDIA/CUDA mit gesonderten Lizenzbedingungen. Vor Verteilung von Runtime-Binärdateien sind die tatsächlich enthaltenen Lizenz- und Drittanbieterhinweise zu prüfen. Der Raspberry-Pi-Online-Installer bleibt unverändert.
