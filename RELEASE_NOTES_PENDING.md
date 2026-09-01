# MediaHub-AI-Node v0.8.20

## MediaHub-AI-Node 0.8.20

- Neuer gemeinsamer lokaler Release-Assistent für MediaHub-AI-Node und Windows Compute Node.
- Automatischer Build des Raspberry-Pi-/Linux-Release-Pakets inklusive SHA-256-Prüfsumme.
- Gemeinsame Prüfung aller Linux- und Windows-Release-Artefakte vor der Veröffentlichung.
- Schutz vor bereits gestagten Dateien und unbeabsichtigten Änderungen aus parallelen Entwicklungsfenstern.
- Fingerprint-Prüfung erkennt Änderungen an Release-Dateien während eines laufenden Release-Vorgangs.
- Release-Tags werden vor der Veröffentlichung erneut geprüft und bestehende historische Tags niemals verschoben oder ersetzt.
- Release-Prüfungen und Paketbau wurden für den lokalen Release-Workflow erweitert.
- Repository- und Lizenzhinweise wurden bereinigt und aktualisiert.

## Windows Compute Node 0.1.0

- Windows Compute Node bleibt in Version 0.1.0.
- Portable ZIP und SHA-256-Prüfsumme werden automatisch in den gemeinsamen Release-Ablauf aufgenommen.
- Windows-Setup und zugehörige SHA-256-Prüfsumme werden automatisch gebaut und geprüft.
- Windows- und Raspberry-Pi-/Linux-Artefakte werden gemeinsam im selben GitHub-Release veröffentlicht.
