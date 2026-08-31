# MediaHub-AI-Node

**MediaHub-AI-Node** ist ein optionaler lokaler KI-, Wissens- und Medienanalyse-Knoten für Raspberry Pi und andere Linux-Systeme.

> **Projektstatus:** funktionsfähige Entwicklungsfassung
> **Primäre Zielplattform:** Raspberry Pi 5 mit Raspberry Pi OS 64-Bit
> **Getestete Basis:** Debian 13 „Trixie“, systemd und Python 3.13

## Rolle im MediaHub-System

Die interne MediaHub-KI bleibt die zentrale Orchestrierungs- und Entscheidungsinstanz. Der Raspberry-Pi-AI-Node ist nur ein optionaler zusätzlicher Ausführungsknoten. Ist er nicht vorhanden oder offline, übernimmt die interne MediaHub-KI die Aufgaben lokal, soweit die benötigten Werkzeuge verfügbar sind.

Nur die interne MediaHub-KI muss das Desktopprogramm selbst steuern. Analyse-, Provider-, OCR-, Audio-, Fingerprint- und ähnliche Funktionen sollen auf beiden Seiten möglichst gleich nutzbar sein.

## Getestete Plattform

- Raspberry Pi 5
- Raspberry Pi OS 64-Bit
- Debian 13 „Trixie“
- ARM64 / aarch64
- systemd
- Python 3.13
- SSD-Installation unter `/opt/mediahub`
- REST-API auf Port `8765`

Der Installer setzt derzeit ein Debian-basiertes System mit `apt` und `systemd` voraus. Andere Debian-13- und Ubuntu-Systeme können funktionieren, wurden aber noch nicht vollständig getestet.

## Installation

```bash
sudo ./install.sh
```

Der Installer verwendet einen frei wählbaren Linux-Benutzer, schlägt standardmäßig `mediahub` vor, erzeugt ein sicheres API-Token, richtet Verzeichnisse und Rechte ein, installiert den systemd-Dienst und prüft Health- sowie geschützten Plugin-Zugriff.

- [Raspberry Pi vorbereiten](docs/RASPBERRY_PI_SETUP.md)
- [Installation](docs/INSTALLATION.md)
- [systemd-Dienst](docs/SYSTEMD_SERVICE.md)
- [Deinstallation](docs/UNINSTALL.md)
- [Release-Checkliste](RELEASE_CHECKLIST.md)

## Automatische Installation durch MediaHub

Die vollständige automatische Installation aus MediaHub wird vorbereitet. MediaHub soll künftig bei Auswahl eines AI-Plugins prüfen, ob ein AI-Node vorhanden ist, bei Bedarf SSH-Daten abfragen, den Node installieren, das erzeugte Token übernehmen und danach das ausgewählte `.mhaiplugin` installieren.

Das SSH-Passwort wird nicht dauerhaft gespeichert.

## Werkzeug- und Abhängigkeitsverwaltung

MediaHub und AI-Node sollen eine gemeinsame Werkzeugverwaltung verwenden. Plugins melden benötigte Werkzeuge und Pakete an. Gemeinsam genutzte Werkzeuge werden referenzgezählt und erst entfernt, wenn kein Plugin sie mehr benötigt.

## Tests

```bash
python -m pytest
python -m ruff check .
python release.py
```

## Lizenz

MIT-Lizenz. Drittanbieter-Komponenten behalten ihre jeweiligen Lizenzen.

## Entwicklung unter Windows

Für Tests und den Release-Bau kann das Repository auch unter Windows verwendet
werden. `uvloop` ist nur für Linux und vergleichbare Unix-Systeme vorgesehen
und wird durch einen Plattformmarker unter Windows automatisch übersprungen.

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest==9.1.1 ruff
python -m pytest
python -m ruff check .
```

---

# MediaHub Compute Node für Windows

Zusätzlich zum Raspberry-Pi-/Linux-AI-Node enthält dieses Repository den
getrennten **MediaHub Compute Node für Windows**.

Der Windows Compute Node ist ein optionaler zusätzlicher Ausführungsknoten
für MediaHub. Er ersetzt weder die interne MediaHub-KI noch den bestehenden
Raspberry-Pi-AI-Node.

Der vorhandene Raspberry-Pi-Online-Installer bleibt vollständig getrennt
und wird durch den Windows-Build und Windows-Installer nicht verändert.

## Windows-Varianten

Für Windows werden zwei getrennte Varianten veröffentlicht:

### Windows Setup

Das Setup ist für eine normale und dauerhafte Windows-Installation
vorgesehen.

Es installiert den MediaHub Compute Node als Windows-Anwendung und bietet
unter anderem:

- Installation unter Windows x64
- Startmenü-Eintrag
- optionales Desktop-Symbol
- optionalen automatischen Start mit Windows
- Windows-Deinstallation
- getrennte persistente Daten
- Abfrage beim Deinstallieren, ob persistente Daten ebenfalls entfernt
  werden sollen

### Windows Portable

Die Portable-Version benötigt keine Installation.

ZIP-Datei entpacken und den MediaHub Compute Node direkt starten.

Sie eignet sich insbesondere für:

- Tests
- portable Nutzung
- Rechner, auf denen keine dauerhafte Installation gewünscht ist

Lokale Einstellungen, Pairing-Daten, API-Token, Logs, Modelle,
Runtime-Dateien und andere benutzerspezifische Daten werden nicht in den
veröffentlichten Portable-Paketen mitgeliefert.

## Windows-Port

Der Windows Compute Node verwendet standardmäßig:

`8766`

Der Raspberry-Pi-/Linux-AI-Node verwendet weiterhin:

`8765`

Dadurch können beide Knotentypen unabhängig voneinander betrieben werden.

## Windows-Funktionen

Der Windows Compute Node unterstützt bzw. bereitet unter anderem vor:

- eigenständige Windows-EXE
- Hardware- und Capability-Erkennung
- CPU-/GPU-Auswahl
- `.mhaiplugin`-Unterstützung
- authentifizierte Verbindung zu MediaHub
- Job-Warteschlange
- Health- und Statusinformationen
- Windows-Tray-Oberfläche
- lokale Speech-to-Text-Ausführung

## Speech-to-Text und isolierte Python-Runtime

Für lokale Speech-to-Text-Aufgaben kann der Windows Compute Node eine vom
Hauptprogramm getrennte Python-Runtime verwenden.

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
außerhalb des eingecheckten Quellbestands und sind nicht Bestandteil der
Release-Pakete.

## Hardwareerkennung unter Windows

Die Hardwareerkennung berücksichtigt CPU, dedizierte GPUs sowie
integrierte GPU/APU-Grafik.

Für die Erkennung können vorhandene Windows- und Treiberkomponenten
verwendet werden:

- Windows CIM/WMI
- DXDiag
- `nvidia-smi` bei NVIDIA-GPUs

GPU-Speicherwerte unterscheiden zwischen dediziertem und gemeinsam
verwendetem Speicher.

## Windows-Version

Der Windows Compute Node besitzt eine eigene Komponenten-Version.

Die Windows-Version muss deshalb nicht mit der Version des
Raspberry-Pi-/Linux-AI-Nodes übereinstimmen.

Ein gemeinsames GitHub-Release kann beispielsweise enthalten:

- MediaHub-AI-Node `v0.8.x`
- MediaHub Compute Node für Windows `v0.1.x`
