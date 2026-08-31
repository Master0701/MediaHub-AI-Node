# MediaHub-AI-Node Release-Checkliste

## Repository

- [ ] Arbeitsverzeichnis geprüft
- [ ] keine temporären Entwicklungs-/Debugdateien im Release
- [ ] AI-Node-Version aktualisiert
- [ ] Windows-Compute-Node-Version geprüft
- [ ] CHANGELOG und Release-Notizen aktuell
- [ ] Dokumentation aktuell
- [ ] Drittanbieter-Lizenzen vollständig geprüft
- [ ] keine lokalen Tokens, Pairing-Daten oder Secrets enthalten

## Raspberry Pi / Linux

- [ ] bestehender Pi-Online-Installer unverändert
- [ ] `python -m compileall app tests -q`
- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] `python release.py`
- [ ] Raspberry-Pi-/Linux-ZIP erstellt
- [ ] SHA-256 des ZIP geprüft
- [ ] Port 8765 geprüft

## Raspberry-Pi-Neuinstallation

- [ ] Raspberry Pi OS 64-Bit / Debian 13 „Trixie“ getestet
- [ ] Standardbenutzer `mediahub` getestet
- [ ] anderer vorhandener Benutzer getestet
- [ ] neuer Benutzer getestet
- [ ] `.env` und Modus `600` geprüft
- [ ] API-Token geprüft
- [ ] systemd-Dienst geprüft
- [ ] Health-Endpunkt geprüft
- [ ] geschützter Plugin-Endpunkt geprüft

## Windows Compute Node

- [ ] Windows-Version aus `windows_compute_node/version.py` geprüft
- [ ] Windows-Build mit Python 3.14 geprüft
- [ ] PyInstaller-Build erfolgreich
- [ ] Windows Setup erfolgreich gebaut
- [ ] Windows Portable erfolgreich gebaut
- [ ] Setup startet korrekt
- [ ] Portable-Version startet korrekt
- [ ] Port 8766 geprüft
- [ ] `/health` geprüft
- [ ] `/identity` geprüft
- [ ] Tray-Oberfläche geprüft
- [ ] Autostart-Option des Setups geprüft
- [ ] Windows-Deinstallation geprüft
- [ ] persistente Daten bleiben auf Wunsch erhalten
- [ ] persistente Daten können auf Wunsch gelöscht werden
- [ ] separater Restdaten-Eintrag erscheint nach "Daten behalten"
- [ ] Restdaten-Eintrag "MediaHub Compute Node - gespeicherte Daten entfernen" getestet
- [ ] späterer Restdaten-Cleanup entfernt ComputeNode-ProgramData vollständig
- [ ] Restdaten-Cleanup entfernt seinen eigenen Windows-Uninstall-Eintrag

## Windows-Release-Sicherheit

- [ ] Portable-ZIP enthält kein `api_token.json`
- [ ] Portable-ZIP enthält kein `node_identity.json`
- [ ] Portable-ZIP enthält keine lokalen `settings.json`
- [ ] Portable-ZIP enthält keine lokalen Logs
- [ ] Setup enthält keine lokalen Runtime-Daten
- [ ] Setup enthält LICENSE
- [ ] Setup enthält THIRD_PARTY_LICENSES.md
- [ ] Setup enthält erforderliche Lizenztexte
- [ ] Windows-Abhängigkeiten und Lizenzen vollständig inventarisiert

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
- [ ] Aufgabenverteilung lokal/Pi/Windows geprüft
- [ ] Capability Discovery vor Aufgabenvergabe geprüft
- [ ] nicht verfügbare Plugins/Tools werden nicht vorausgesetzt

## Werkzeuge

- [ ] Werkzeugerkennung geprüft
- [ ] Nachinstallation geprüft
- [ ] Referenzzählung geprüft
- [ ] Entfernen ungenutzter Werkzeuge geprüft

## GitHub Release

- [ ] Release über vorgesehenen Release-Workflow erstellt
- [ ] Commit und Tag zeigen auf aktuellen Release-Stand
- [ ] Workflows grün
- [ ] Release-Beschreibung aus aktuellen Release-Notizen erzeugt

### Raspberry Pi / Linux

- [ ] `MediaHub-AI-Node_*.zip` vorhanden
- [ ] zugehörige `.sha256` vorhanden
- [ ] Prüfsumme stimmt

### Windows Setup

- [ ] `MediaHub-Compute-Node_Setup_*.exe` vorhanden
- [ ] zugehörige `.exe.sha256` vorhanden
- [ ] Prüfsumme stimmt
- [ ] als normale Windows-Installation beschrieben

### Windows Portable

- [ ] `MediaHub-Compute-Node_*_Windows_x64.zip` vorhanden
- [ ] zugehörige `.zip.sha256` vorhanden
- [ ] Prüfsumme stimmt
- [ ] als installationsfreie Portable-Version beschrieben

## Deinstallation Raspberry Pi / Linux

- [ ] Systemweiter Uninstaller wurde installiert
- [ ] normale Deinstallation getestet
- [ ] Datensicherung bei Deinstallation getestet
- [ ] `--purge --remove-venv --yes` getestet
- [ ] Dienstdatei und Drop-ins wurden entfernt
- [ ] Port 8765 ist nach Deinstallation frei
- [ ] Linux-Benutzer blieb erhalten

## Deinstallation Windows

- [ ] Compute Node wird vor Deinstallation beendet
- [ ] Programmdateien werden entfernt
- [ ] Abfrage zum Entfernen persistenter Daten erscheint
- [ ] Auswahl „Daten behalten“ getestet
- [ ] Auswahl „Daten löschen“ getestet
- [ ] nach "Daten behalten" bleibt separater Restdaten-Uninstaller verfügbar
- [ ] späterer Restdaten-Uninstaller vollständig getestet
- [ ] Restdaten-Uninstaller entfernt eigenen Apps-/Registry-Eintrag
- [ ] Restdaten-Uninstaller entfernt leeren ProgramData\MediaHub-Elternordner nur dann, wenn er leer ist
- [ ] Port 8766 ist nach Deinstallation frei
