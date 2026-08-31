# MediaHub-AI-Node Release

Dieses Release enthält den Raspberry-Pi-/Linux-AI-Node sowie erstmals die
getrennten Windows-Varianten des MediaHub Compute Node.

## MediaHub-AI-Node – Raspberry Pi / Linux

Version: **0.8.19**

- bestehender Raspberry-Pi-/Linux-AI-Node
- bestehender Online-Installer bleibt unverändert
- Debian-/Raspberry-Pi-Systemdienst
- REST-API weiterhin standardmäßig auf Port `8765`
- AI-Node-Plugin- und Aufgabeninfrastruktur

### Download

Das Raspberry-Pi-/Linux-Paket wird als ZIP-Datei zusammen mit einer
separaten SHA-256-Prüfsumme veröffentlicht.

## MediaHub Compute Node – Windows Setup

Version: **0.1.0**

Die Setup-Variante ist für die normale und dauerhafte Installation auf
einem Windows-x64-System vorgesehen.

Enthalten bzw. unterstützt:

- eigenständige Windows-Anwendung
- Installation über Windows Setup
- Startmenü-Eintrag
- optionales Desktop-Symbol
- optionaler Autostart
- Windows-Deinstallation
- persistente Einstellungen und Node-Daten
- persistente Daten können bei der normalen Deinstallation wahlweise behalten oder gelöscht werden
- bei zunächst behaltenen Daten bleibt ein eigener Windows-Eintrag "MediaHub Compute Node - gespeicherte Daten entfernen" verfügbar
- über diesen separaten Eintrag können verbliebene Einstellungen, Node-ID, Pairing-Daten, API-Token, Jobs, Logs und Compute-Plugins später vollständig entfernt werden
- Hardware- und Capability-Erkennung
- CPU-/GPU-Auswahl
- Tray-Oberfläche
- Health- und Identity-Endpunkte
- Standardport `8766`
- Vorbereitung bzw. Unterstützung lokaler Compute-Plugins

Das Setup wird als eigene EXE-Datei zusammen mit einer separaten
SHA-256-Prüfsumme veröffentlicht.

## MediaHub Compute Node – Windows Portable

Version: **0.1.0**

Die Portable-Variante benötigt keine Installation.

ZIP-Datei entpacken und den MediaHub Compute Node direkt starten.

Sie ist insbesondere für Tests oder portable Nutzung vorgesehen.

Das Portable-Paket enthält keine lokalen API-Token, Pairing-Daten,
Node-Identity, benutzerspezifischen Einstellungen oder Logs aus der
Entwicklungsumgebung.

Die Portable-Version wird als eigene ZIP-Datei zusammen mit einer
separaten SHA-256-Prüfsumme veröffentlicht.

## Gemeinsamer Betrieb

Der Raspberry-Pi-/Linux-AI-Node und der Windows Compute Node sind getrennte
Ausführungsknoten.

- Raspberry Pi / Linux: Port `8765`
- Windows Compute Node: Port `8766`

Der Windows Compute Node ersetzt den Raspberry-Pi-AI-Node nicht.
Beide können unabhängig voneinander verwendet werden.

Die interne MediaHub-KI bleibt die zentrale Orchestrierungs- und
Entscheidungsinstanz.

## Release-Dateien

Das GitHub-Release muss folgende sechs Dateien enthalten:

1. Raspberry-Pi-/Linux-ZIP
2. SHA-256 für Raspberry-Pi-/Linux-ZIP
3. Windows-Setup-EXE
4. SHA-256 für Windows-Setup-EXE
5. Windows-Portable-ZIP
6. SHA-256 für Windows-Portable-ZIP
