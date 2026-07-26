# MediaHub-AI-Node Release-Checkliste

## Repository
- [ ] Arbeitsverzeichnis sauber
- [ ] Version aktualisiert
- [ ] CHANGELOG und Release-Notizen aktuell
- [ ] Dokumentation aktuell
- [ ] Drittanbieter-Lizenzen geprüft

## Tests
- [ ] `python -m compileall app tests -q`
- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] `python release.py`
- [ ] Release-ZIP und SHA-256 geprüft

## Neuinstallation
- [ ] Raspberry Pi OS 64-Bit / Debian 13 „Trixie“ getestet
- [ ] Standardbenutzer `mediahub` getestet
- [ ] anderer vorhandener Benutzer getestet
- [ ] neuer Benutzer getestet
- [ ] `.env` und Modus `600` geprüft
- [ ] API-Token geprüft
- [ ] systemd-Dienst geprüft
- [ ] Health-Endpunkt geprüft
- [ ] geschützter Plugin-Endpunkt geprüft

## AI-Plugins
- [ ] `.mhaiplugin` akzeptiert
- [ ] SHA-256 geprüft
- [ ] Pflichtdateien geprüft
- [ ] Installationsplan geprüft
- [ ] Installation geprüft
- [ ] Aktivieren/Deaktivieren/Deinstallieren geprüft
- [ ] Backup und Rollback geprüft

## MediaHub
- [ ] Verbindung getestet
- [ ] Tokenübernahme getestet
- [ ] SSH-Passwort wird nicht gespeichert
- [ ] Fallback auf interne MediaHub-KI geprüft
- [ ] Aufgabenverteilung lokal/Pi geprüft

## Werkzeuge
- [ ] Werkzeugerkennung geprüft
- [ ] Nachinstallation geprüft
- [ ] Referenzzählung geprüft
- [ ] Entfernen ungenutzter Werkzeuge geprüft

## GitHub Release
- [ ] Commit und Tag gepusht
- [ ] Workflows grün
- [ ] Release-Beschreibung korrekt
- [ ] Installationshinweise sichtbar
- [ ] ZIP und SHA-256 vorhanden

## Deinstallation
- [ ] Systemweiter Uninstaller wurde installiert
- [ ] Normale Deinstallation getestet
- [ ] Datensicherung bei Deinstallation getestet
- [ ] `--purge --remove-venv --yes` getestet
- [ ] Dienstdatei und Drop-ins wurden entfernt
- [ ] Port 8765 ist nach Deinstallation frei
- [ ] Linux-Benutzer blieb erhalten
