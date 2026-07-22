# Neues GitHub-Repository anlegen

Empfohlener Name:

```text
MediaHub-AI-Node
```

## GitHub

1. Auf GitHub ein neues leeres Repository `MediaHub-AI-Node` erstellen.
2. Keine zusätzliche README, Lizenz oder `.gitignore` erzeugen, da sie bereits vorhanden sind.
3. Repository zunächst öffentlich oder privat nach eigener Entscheidung anlegen.
4. Security Advisories aktivieren.
5. Issues aktivieren.
6. Branch `main` schützen, sobald der erste stabile Stand hochgeladen wurde.

## Lokale Initialisierung

```bash
cd /opt/mediahub/ai-node

git init
git branch -M main
git remote add origin \
  https://github.com/Master0701/MediaHub-AI-Node.git

git add .
git commit -m "Initial MediaHub-AI-Node repository"
git push -u origin main
```

## Vor dem ersten Push

Unbedingt kontrollieren:

```bash
git status
git ls-files
git grep -n -E "token|password|secret|api[_-]?key" -- .
```

Keine `.env`, Datenbank, Backups, Modelle, Logs oder Zugangsdaten hochladen.

## Erster Tag

```bash
git tag -a v0.1.0 -m "MediaHub-AI-Node v0.1.0"
git push origin v0.1.0
```

Der Release-Workflow erstellt das öffentliche Quellpaket und die SHA-256-Prüfsumme.
