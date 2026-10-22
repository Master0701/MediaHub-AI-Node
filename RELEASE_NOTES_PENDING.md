# MediaHub-AI-Node v0.8.27

## MediaHub-AI-Node v0.8.27

- Weiterentwicklung der gemeinsamen Plugin-Manifest- und Preflight-Prüfungen.
- Anpassungen der Plugin-Voraussetzungen für verwaltete Python-Laufzeiten.
- Verbesserte Prüfung der Plugin-Abhängigkeiten und Laufzeitumgebungen.
- Bestehende Raspberry-Pi-Online-Installation bleibt unverändert.

## Windows Compute Node v0.1.3

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

- 144 Windows-Compute-Node-Tests erfolgreich.
- Ein Test übersprungen.
- Sicherheitsprüfungen für Installationsplan, SHA-256, Abbruch und einmalige Bestätigung erfolgreich.
- HTTP-Handler-Test bestätigt die Sperre direkter Plugin-Installationen.
- Keine echte Plugin-Installation während der Sicherheitstests.

## Release und Kompatibilität

- Windows Compute Node wird weiterhin als eigenständiges Windows-Paket bereitgestellt.
- Raspberry-Pi- und Windows-Installationswege bleiben getrennt.
- Bestehender Raspberry-Pi-Online-Installer wird nicht verändert.