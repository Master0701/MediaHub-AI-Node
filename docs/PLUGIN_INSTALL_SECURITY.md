# Sicherheit für spätere AI-Plugin-Installationen

## Zweck

Schreibende Plugin-Endpunkte werden erst freigegeben, wenn mindestens folgende
Schutzschichten vorhanden sind:

- starkes API-Token
- konstante Token-Prüfung
- SHA-256-Prüfung
- ZIP-Pfadprüfung
- Schutz vor Path Traversal
- Verbot symbolischer Links
- Größen- und Dateianzahlbegrenzung
- genau ein oberster Plugin-Ordner
- gültiges `plugin.json`
- Übereinstimmung zwischen Plugin-ID und Paketordner
- spätere Backup- und Rollback-Funktion
- spätere Lizenz- und Abhängigkeitsprüfung

## API-Token

Das zukünftige Schreib-Token wird über diese Umgebungsvariable gesetzt:

```text
MEDIAHUB_AI_NODE_API_TOKEN
```

Das Token muss mindestens 32 Zeichen lang sein. Empfohlen ist ein zufällig
erzeugtes Token mit mindestens 48 Zeichen.

Beispiel zur Erzeugung:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Das Token darf nicht in Git eingecheckt werden. Es gehört später in die
geschützte `.env`-Datei oder in eine systemd-Umgebungsdatei.

## Paketformat

Ein Plugin-ZIP muss genau einen obersten Ordner besitzen:

```text
provider.ollama/
├── plugin.json
├── plugin.py
├── LICENSE
└── README.md
```

Alternativ darf der Ordnername Punkte durch Unterstriche ersetzen:

```text
provider_ollama/
```

## Aktueller Stand

Dieses Update stellt nur Token- und Paketprüfungen bereit. Es fügt noch keinen
schreibenden REST-Endpunkt hinzu und entpackt keine Plugins.
