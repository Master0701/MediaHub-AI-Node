# Sicherheitsrichtlinie

## Unterstützte Versionen

Sicherheitskorrekturen werden grundsätzlich für den aktuellen Entwicklungsstand
und das neueste veröffentlichte Release vorgesehen.

## Sicherheitsprobleme melden

Sicherheitslücken nicht öffentlich mit vollständigen Ausnutzungsdetails melden.
Stattdessen einen privaten GitHub-Security-Advisory-Entwurf verwenden, sofern
diese Funktion für das Repository verfügbar ist.

## Betriebsregeln

- AI-Node standardmäßig nur im vertrauenswürdigen Heimnetz betreiben
- keine Ports ungeprüft ins Internet weiterleiten
- Tokens und Passwörter nicht im Repository speichern
- Dateirechte einschränken
- System und Python-Abhängigkeiten aktuell halten
- vor öffentlichem Zugriff Authentifizierung und TLS einrichten
- Backups sicher und getrennt aufbewahren
