# MediaHub-AI-Node – Entwicklungsstand

## Pausenstand

Stand: v0.8.16  
Status: stabiler Entwicklungszwischenstand

## Fertig

- Provider-System für mehrere KI-Backends
- Provider-Prioritäten und Fallback
- AI-Plugin-Engine
- Plugin-Manifeste und Plugin-Typen
- Plugin-Erkennung und Aktivierungsstatus
- schreibgeschützte Plugin-API
- geschützte Plugin-Installations-API
- Aktivieren und Deaktivieren über API
- Deinstallation mit Backup
- Plugin-Rollback über API
- SHA-256-Paketprüfung
- sichere ZIP-Pfadprüfung
- API-Token-Schutz
- Lizenzprüfung
- Python-Abhängigkeitsprüfung
- externe Tool-Prüfung
- Plugin-Abhängigkeitsprüfung
- bestätigungspflichtige Installationspläne
- Plan-ID und einmalige Bestätigung
- persistenter Plan-Speicher
- kontrollierte Ausführung geprüfter Python-Pakete
- automatisierte Tests

## Aktueller Teststand

- 79 Tests bestanden
- Ruff-Prüfung bestanden
- eine bekannte externe Starlette/httpx-Warnung

## Noch offen

- vollständige Plugin-Transaktionen
- automatisches Rollback nach fehlgeschlagenen Installationen
- kontrollierte Installation externer Systemtools
- automatische Installation abhängiger AI-Plugins
- dev_build.py
- Release-Vorbereitung
- Integration des AI-Plugin-Stores in MediaHub
- getrennte Reiter „MediaHub-Plugins“ und „AI-Plugins“ in MediaHub

## Fortsetzung

Beim nächsten Start zuerst ausführen:

```bash
source /opt/mediahub/venv/bin/activate
cd /opt/mediahub/ai-node
git pull --ff-only origin main
python -m pytest
python -m ruff check .
