# Changelog

## MediaHub-AI-Node v0.9.0 – Release-Vorbereitung (17.11.2026)

- Gemeinsame AI-Node-Version von v0.8.29 auf v0.9.0 angehoben.
- Windows Compute Node wird separat als v0.2.0 geführt; keine Änderung des Raspberry-Pi-Online-Installers.
- Gemeinsame Release-Notizen enthalten die Windows-Interaktions-KI-Erweiterungen.


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


## v0.8.25

- Plugin-Installationsverwaltung für GLiNER und SmolVLM2 verbessert.
- Strukturierte Tool- und Modellabhängigkeiten werden vollständig erkannt.
- Fehlende Runtimes und Modelle werden während der bestätigten Installation eingerichtet.
- Vorhandene Runtimes und Modelle werden wiederverwendet.
- Installation prüft Betriebsbereitschaft vor der Erfolgsmeldung.
- Rollback bei fehlgeschlagener Plugin-Aktivierung ergänzt.
- Regressionstests für Installation, Modellprüfung und Rollback ergänzt.
- Raspberry-Pi-Online-Installer und Windows-Speech-Runtime unverändert.

## v0.8.22

- Raspberry-Pi-AI-Node um Heartbeat-basierte MediaHub-Aktivitätserkennung erweitert.
- Automatischen Plugin-Ruhemodus nach 15 Minuten Inaktivität ergänzt.
- Automatisches Wiederaufwecken der Plugins bei neuer MediaHub-Aktivität ergänzt.
- Lokale, im Heimnetz erreichbare AI-Node-Statusseite unter `/status` ergänzt.
- Statusanzeige für Verbindung, letzte Aktivität, Jobs, Ruhemodus, Plattform und Plugins ergänzt.
- Gemeinsame Node-Activity- und Runtime-Grundlagen für AI Node und Windows Compute Node erweitert.
- Windows-Compute-Node-Plugin-, Worker- und Speech-Runtime weiter stabilisiert.

## v0.8.18

- Vollständige Drittanbieter-Lizenzverwaltung ergänzt.
- Direkte Python-Abhängigkeiten in `dependency_licenses.json` dokumentiert.
- Standard-Lizenztexte unter `licenses/` ergänzt.
- Automatische Lizenzprüfung in den Release-Prozess integriert.
- Release bricht bei fehlenden Lizenzinformationen ab.

## v0.8.17

- Windows-Entwicklungsinstallation korrigiert: `uvloop` wird unter Windows automatisch übersprungen.
- Provider-System und AI-Plugin-Engine weiter stabilisiert.
- Geschützte Plugin-API mit API-Token-Unterstützung ergänzt.
- `.mhaiplugin`-Pakete mit Pflichtdateien, Paketprüfung und Lizenzprüfung unterstützt.
- Installationspläne, Preflight-Prüfung, Bestätigung und kontrollierte Ausführung ergänzt.
- Persistenten Planspeicher und Plugin-Verwaltungsendpunkte erweitert.
- Laufzeitpfade konsequent auf `/opt/mediahub/ai-node` umgestellt.
- Installer für Debian 13 „Trixie“ und Raspberry Pi OS 64-Bit vervollständigt.
- Systemweiten Uninstaller mit vollständigem Test-Reset ergänzt.
- Health-Endpunkt um Pluginzahlen und Systemstatus erweitert.
- 79 automatisierte Tests erfolgreich ausgeführt.
- Zahlreiche Stabilitäts-, Token-, Pfad- und Installationskorrekturen.

Alle wesentlichen Änderungen an MediaHub-AI-Node werden in dieser Datei dokumentiert.

## [Unreleased]

### Hinzugefügt

- öffentliche Repository-Struktur
- MIT-Lizenz
- vollständige Dokumentationsstruktur
- GitHub-Actions für Tests, Release und Dokumentation
- Backup-, Restore- und Wartungsdokumentation
- `health_check.sh`
- Sicherheits- und Beitragsrichtlinien

## [0.7.1] - 2026-07-24

### Geändert

- Release-Paketbau korrigiert.
- GitHub-Releases erhalten vollständige Release-Beschreibungen.
- Installation über Release-ZIP und direkte Git-Installation dokumentiert.
- Versionsangaben vereinheitlicht.
- Gemeinsamen MediaHub-Repository-Standard ergänzt.
- Temporäre Release-Notizen werden nach erfolgreichem Release entfernt.

## [0.1.0] - 2026-07-22

### Funktionsfähiger Raspberry-Pi-Teststand

- systemd-Dienst
- REST-API auf Port 8765
- Health-Endpunkt
- Wissensdatenbank
- Titel-, Alias- und externe-ID-Erkennung
- Dublettenerkennung
- Merge-Service
- Importer
- Beziehungsimport
- Graphprüfung
- Backup- und Restore-Skripte
- automatischer Abschlusstest mit 5 von 5 bestandenen Prüfungen
