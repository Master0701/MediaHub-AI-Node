# MediaHub-AI-Node v0.8.28

## MediaHub-AI-Node v0.8.28

- Versionsanhebung fuer die Release-Vorbereitung; der Raspberry-Pi-Online-Installer bleibt unveraendert.

- Weiterentwicklung der gemeinsamen Plugin-Manifest- und Preflight-Prüfungen.
- Anpassungen der Plugin-Voraussetzungen für verwaltete Python-Laufzeiten.
- Verbesserte Prüfung der Plugin-Abhängigkeiten und Laufzeitumgebungen.
- Bestehende Raspberry-Pi-Online-Installation bleibt unverändert.

## Windows Compute Node v0.1.5

### Sichere Plugin-Installation

- Einführung eines zweistufigen Installationsverfahrens mit Installationsplan und ausdrücklicher Bestätigung.
- Neuer API-Endpunkt zur Erstellung eines Installationsplans.
- Bestätigung und Abbruch von Installationsplänen über eigene API-Endpunkte.
- SHA-256-Prüfung des Plugin-Pakets vor der Installation.
- Anzeige benötigter Python-Pakete und Plugin-Abhängigkeiten vor der Bestätigung.
- Direkte Plugin-Installation über den bisherigen API-Endpunkt wird mit HTTP 409 abgewiesen.
- Installationspläne sind zeitlich begrenzt und können nur einmal bestätigt werden.

### Python-Runtime und Plugin-Unterstützung

- Verbesserte Unterstützung verwalteter Python-Laufzeitumgebungen.
- Anpassungen der Runtime-Erkennung und Plugin-Ladefunktionen.
- Überarbeitung der Windows-Unterstützung für Speech-to-Text.
- Verbesserte Laufzeitprüfung für GLiNER.
- Eigenständige Plugins bleiben separat installierbar und werden nicht fest in den Compute Node integriert.

### Tests und Sicherheit

- 86 Windows-Compute-Node-Tests erfolgreich; 206 Gesamttests erfolgreich.
- Keine Tests übersprungen.
- Sicherheitsprüfungen für Installationsplan, SHA-256, Abbruch und einmalige Bestätigung erfolgreich.
- HTTP-Handler-Test bestätigt die Sperre direkter Plugin-Installationen.
- Keine echte Plugin-Installation während der Sicherheitstests.

## Release und Kompatibilität

- Windows Compute Node wird weiterhin als eigenständiges Windows-Paket bereitgestellt.
- Raspberry-Pi- und Windows-Installationswege bleiben getrennt.
- Bestehender Raspberry-Pi-Online-Installer wird nicht verändert.

### GLiNER-Modellverwaltung (in Entwicklung)
- Modellinstallation aus validierten Plugin-Manifestangaben statt fest eingebauter GLiNER-Modellquelle.
- GLiNER-Pflichtdateien an gliner_config.json und Modellgewichte angepasst.
- Lokaler Modellpfad und Offline-Ladetest vorbereitet; reale Windows-CPU- und CUDA-Installation mit echter Modellinferenz bestanden.

### Zentrale Plugin-Abhaengigkeitsverwaltung (in Entwicklung)

- Rekursive Aufloesung deklarierter Plugin-Abhaengigkeiten.
- Gemeinsamer Installationsplan fuer Hauptplugin und benoetigte Plugin-Abhaengigkeiten.
- Installation in der erforderlichen Abhaengigkeitsreihenfolge nach einer gemeinsamen Bestaetigung.
- Wiederverwendung bereits installierter, kompatibler Plugin-Abhaengigkeiten.
- Grundlage fuer die automatische Installation der Python Runtime vor GLiNER.
- Bestehende Windows-Compute-Node-Installations-API erweitert.
- Vollstaendiger Neuinstallationstest mit GLiNER auf CPU und CUDA bestanden.

### GLiNER-Nulltest Windows Compute Node v0.1.4 (historischer Test)

- Node-EXE aus frischer Kopie des aktuellen lokalen AI-Node-Repositories neu gebaut.
- Python-Runtime- und GLiNER-Plugin-Pakete aus frischer Kopie des lokalen Plugin-Repositories neu gebaut.
- Abhaengigkeitsgesteuerte Installation in separaten CPU- und CUDA-Nulltestumgebungen erfolgreich.
- Private Python 3.12.10, isolierte Pakete, torch 2.14.0+cpu und 2.14.0+cu126 nachgewiesen.
- Echte GLiNER-Inferenz in beiden Profilen bestanden; Testprozesse beendet.
- Python-Runtime selbst und Raspberry-Pi-Online-Installer unveraendert.
### SmolVLM2-Nullinstallation CPU/CUDA (29.10.2026)

- SmolVLM2-Installation mit verwalteter privater Python-Runtime und isolierten CPU-/CUDA-Profilen verbessert.
- CUDA-Auswahl und Laufzeitvalidierung im Windows-Compute-Node-Plugininstaller ergänzt; bestehende GLiNER-Installationslogik erhalten.
- CPU-Nullinstallation mit torch 2.14.0+cpu und CUDA-Nullinstallation mit torch 2.14.0+cu126 erfolgreich getestet.
- Echte SmolVLM2-Modellinferenz in beiden Profilen durchgeführt; Test-Node anschließend beendet.
- Änderungen aus der isolierten Testkopie gezielt in die Originalquellen übernommen; Raspberry-Pi-Online-Installer unverändert.

### Build-Pakete Windows Compute Node v0.1.5 (31.10.2026)

- Eigenständige Windows-EXE, portable ZIP und Inno-Setup-Installer erfolgreich lokal gebaut.
- SHA-256-Prüfsummen von portablem ZIP und Setup erfolgreich kontrolliert.
- Windows-Build bereinigt nur die eigenen Unterordner unter build/, dist/ und release/windows_compute_node/.
- Gemeinsamer GitHub-Release-Workflow baut Raspberry-Pi/Linux und Windows auf getrennten Runnern und führt ihre Artefakte erst zur Veröffentlichung zusammen.

### Abschließende lokale Release-Prüfung (01.11.2026)

- 86 Windows-Compute-Node-Tests erfolgreich.
- 206 Gesamttests unter lokalem Python 3.14 erfolgreich; keine Tests übersprungen.
- Ruff und Git-Diff-Prüfung erfolgreich.
- Verbliebene Referenzen auf die entfernten alten Speech-to-Text-Quellen geprüft.
- Neue Plugin-Abhängigkeitsverwaltung einschließlich dependency_plan.py für den Release berücksichtigt.
- GitHub-Testmatrix auf Python 3.11, 3.12, 3.13 und 3.14 erweitert.
- Raspberry-Pi-Online-Installer unverändert.
- GitHub-CI und veröffentlichte Release-Artefakte nach dem Push noch zu überprüfen.
