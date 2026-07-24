# Gemeinsamer MediaHub-Repository-Standard

Dieser Standard gilt für MediaHub, MediaHub_Plugins, MediaHub-AI-Node und zukünftige eigenständige MediaHub-Projekte.

## Pflichtdateien

- `README.md`
- `CHANGELOG.md`
- `LICENSE`
- `THIRD_PARTY_LICENSES.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `RELEASE_NOTES_PENDING.md` nur während der Vorbereitung eines Releases
- `docs/`
- `licenses/`
- `.github/workflows/`

## Release-Ablauf

1. Zentrale Versionsnummer aktualisieren.
2. `CHANGELOG.md` ergänzen.
3. `RELEASE_NOTES_PENDING.md` mit Änderungen, Installation und Downloads erstellen.
4. Tests, Ruff, Dokumentation und Lizenzdateien prüfen.
5. Release-ZIP und SHA-256-Datei bauen.
6. Änderungen nach `main` übertragen.
7. Passenden Versions-Tag erstellen und pushen.
8. GitHub Actions erstellt das Release und übernimmt den Text aus `RELEASE_NOTES_PENDING.md`.
9. Nach erfolgreicher Veröffentlichung wird die temporäre Notiz aus `main` entfernt.

## Installationswege

Jedes eigenständige Projekt dokumentiert mindestens:

- Installation über das fertige Release-ZIP
- direkte Installation über Git
- Update
- Deinstallation
- Backup und Wiederherstellung, sofern Daten dauerhaft gespeichert werden
