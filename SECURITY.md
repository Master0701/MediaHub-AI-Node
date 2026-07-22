# Sicherheitsrichtlinie

## Unterstützte Versionen

Während der frühen Entwicklung wird nur der aktuelle Stand unterstützt.

## Sicherheitslücken melden

Sicherheitsprobleme bitte nicht als öffentliches GitHub-Issue veröffentlichen. Nutze stattdessen GitHubs private Security-Advisory-Funktion des Repositorys.

## Grundregeln

- Port 8765 nicht ungeprüft ins Internet weiterleiten.
- API-Tokens nie in Git speichern.
- `.env`, Schlüssel und lokale Datenbanken bleiben ausgeschlossen.
- Dienst möglichst mit einem unprivilegierten Benutzer ausführen.
- Cloud-Anbieter nur optional und bewusst aktivieren.
- Backups können sensible Metadaten enthalten und müssen geschützt gespeichert werden.
