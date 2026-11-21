# MediaHub-AI-Node v0.9.1

## MediaHub-AI-Node 0.9.1

- Gemeinsames Release mit aktualisiertem Windows Compute Node; der bestehende Raspberry-Pi-/Linux-Installer bleibt unveraendert.
- Kein neuer Funktionsumfang fuer den Raspberry-Pi-Knoten in dieser Version.

## Windows Compute Node 0.2.1

- Aktuelle Windows-Compute-Node-Version mit bestehender LAN-HTTPS-Unterstuetzung (Port 8769), Authentifizierung und Firewall-Statuspruefung.
- Windows-Setup und portables Paket werden mit dem vorhandenen Release-Assistenten neu gebaut und geprueft.
- Praxistest: Nach erneuter Installation ueber das Setup trat die zuvor wiederkehrende Firewall-Abfrage auf dem Windows-10-Server nicht mehr auf. Die genaue Ursache ist noch nicht abschliessend geklaert.
- Bestehende Windows-Installation, Runtime-Daten und der separate Raspberry-Pi-Installationsweg bleiben erhalten.

## Bisherige Entwicklung und Testnachweise (historisch)

## MediaHub-AI-Node v0.9.0
- Versionsanhebung fuer die Release-Vorbereitung; der Raspberry-Pi-Online-Installer bleibt unveraendert.

- Weiterentwicklung der gemeinsamen Plugin-Manifest- und Preflight-Prüfungen.
- Anpassungen der Plugin-Voraussetzungen für verwaltete Python-Laufzeiten.
- Verbesserte Prüfung der Plugin-Abhängigkeiten und Laufzeitumgebungen.
- Bestehende Raspberry-Pi-Online-Installation bleibt unverändert.

## Windows Compute Node v0.2.0

Die folgenden Abschnitte dokumentieren die Entwicklung seit den früheren Windows-Compute-Node-Versionen; historische Versions- und Testergebnisse bleiben als solche gekennzeichnet.

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
### GLiNER-Offline-Fix und sechs Nulltests (02.11.2026)

- GLiNER-Modellinstallation ueber das gemeinsame MediaHub-Tools-Release korrigiert.
- Tokenizer- und DeBERTa-Backbone-Konfiguration fuer den Betrieb ohne Hugging-Face-Modellcache lokal bereitgestellt.
- GLiNER-Modellpfade und Offline-Ladetest nach der Installation korrigiert.
- Gemeinsamer Nullinstallationstest mit sechs Varianten erfolgreich: GLiNER CPU/CUDA, SmolVLM2 CPU/CUDA und Speech-to-Text CPU/CUDA.
- Echte GLiNER-Texterkennung, SmolVLM2-Video-Inferenz und Speech-to-Text-API-Jobs im isolierten Test bestaetigt.
- Windows Compute Node von v0.1.5 auf v0.1.6 angehoben; Raspberry-Pi-Online-Installer unveraendert.

## Windows Compute Node v0.2.0 – Interaktions-KI und LAN-HTTPS (Release-Vorbereitung, 17.11.2026)

### Neue Funktionen seit Beginn der Interaktions-KI-Integration
- Windows Compute Node als separater, optionaler Ausführungsknoten für MediaHub; Raspberry-Pi-AI-Node und dessen Online-Installer bleiben unabhängig.
- Einbindung des separat installierbaren AI-Node-Plugins `mediahub.interaktions_ki` v0.1.12 über die bestätigte Plugin-Installationsplanung und die Node-API.
- Plugin-Web-Bridge mit lokalem HTTP-Zugriff unter `http://127.0.0.1:8768/` sowie automatischem LAN-HTTPS-Zugriff unter `https://<LAN-IP>:8769/`.
- LAN-IPv4-Ermittlung anhand der Standardroute; Konfigurationsmodi `auto`, `manual` und `disabled`; explizite Umgebungsvariablen bleiben als Overrides verfügbar.
- TLS-Zertifikat und Schlüssel werden bei fehlenden expliziten TLS-Dateipfaden durch die Node in ihrem eigenen Sicherheitsverzeichnis erzeugt bzw. verwaltet.
- HTTPS-Webzugriff nur nach lokaler Einrichtung von Zugangsdaten; Authentifizierung schützt die LAN-Oberfläche.
- Start und Ende der Web-Bridge in den Node-/Plugin-Lebenszyklus integriert; kontrolliertes Stoppen bei Node-Ende und Plugin-Reload.
- Lokaler llama.cpp/GGUF-Chat über CPU und CUDA mit getrennten Ausführungsprofilen und tatsächlichem Backend-Nachweis.
- Weiterverwendung der sicheren lokalen, SHA256-geprüften Installationskette für llama.cpp-Runtime und GGUF-Modell; kein ungefragter Cloud- oder Modell-Download.

### Verifizierte Nullinstallation am 17.11.2026
- Compute-Node-EXE v0.1.6 (Buildstand vor der Versionsanhebung), SHA256 `14C77FC342F5EB12FAC9612588054B1790767EFEE905D99A8691CEFD5513769F`.
- Interaktions-KI v0.1.12 über API-Installationsplan installiert und aktiviert.
- HTTP 8768: Status 200; HTTPS 8769: ohne Zugangsdaten 401, mit falschem Passwort 401, mit gültigen Zugangsdaten 200.
- Echte CPU-Chat-Inferenz bestanden (`owned_llama_process_cpu_mode_gpu_layers_0`).
- Echte CUDA-Chat-Inferenz bestanden (`llama_cpp_startup_log_offloaded_layers`).
- Ports 8766, 8767, 8768 und 8769 nach Testende freigegeben; vorhandene Windows-Firewallregel nicht verändert oder gelöscht; temporäre Test-Zugangsdaten entfernt.
- Gemeinsamer Nulltest v1.0.19 erfolgreich; v1.0.20 ergänzt die auswählbare Node-EXE und ist noch auf Windows erneut auszuführen.

### Release-Grenzen
- Die neue Versionsnummer v0.2.0 ist eine **Quellcode-/Release-Vorbereitung**, noch kein neu gebautes, installiertes oder veröffentlichtes v0.2.0-Paket.
- Vor GitHub-Veröffentlichung: Build und Installer mit v0.2.0, Lizenzprüfung, vollständige Tests, SHA256-Dateien und Release-Notizen über den bestehenden Release-Assistenten kontrollieren.
- Der Raspberry-Pi-Online-Installer bleibt unverändert; keine automatische Firewallregel-Veränderung.

