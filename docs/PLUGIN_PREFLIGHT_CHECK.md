# AI-Plugin-Vorabprüfung

Vor einer automatischen Installation prüft der AI-Node künftig:

- Lizenzdatei im Paket
- Python-Abhängigkeiten aus `requirements.txt`
- benötigte externe Tools
- Abhängigkeiten zu anderen AI-Plugins
- sichere und unterstützte Schreibweise der Anforderungen

## Erlaubte Lizenzdateien

- LICENSE
- LICENSE.txt
- LICENSE.md
- COPYING
- COPYING.txt

Die Lizenzdatei muss direkt im Hauptordner des Plugins liegen.

## Python-Abhängigkeiten

Unterstützte Beispiele:

```text
httpx
httpx>=0.28
pydantic==2.11.0
```

Nicht unterstützt werden unter anderem:

- URLs
- `-r`-Verweise
- lokale Dateipfade
- Git-Abhängigkeiten
- Shell-Befehle

Dadurch wird verhindert, dass ein Plugin über `requirements.txt`
unkontrolliert externe Quellen oder Befehle einschleust.

## Benötigte Tools

Tools werden über `required_tools` in `plugin.json` angegeben:

```json
{
  "required_tools": ["ffmpeg", "tesseract"]
}
```

Die Vorprüfung kontrolliert, ob die Programme im PATH verfügbar sind.

## Plugin-Abhängigkeiten

```json
{
  "dependencies": [
    {
      "id": "provider.base",
      "minimum_version": "1.0.0"
    }
  ]
}
```

Die erste Fassung prüft, ob das benötigte Plugin installiert ist.
Ein genauer Versionsvergleich folgt mit der automatischen
Abhängigkeitsinstallation.
