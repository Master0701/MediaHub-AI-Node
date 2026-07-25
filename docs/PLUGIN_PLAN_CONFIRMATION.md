# Plan-ID und einmalige Bestätigung

## Ablauf

1. MediaHub sendet das Plugin-ZIP an `POST /plugins/plan`.
2. Der AI-Node prüft das Paket und speichert es temporär.
3. Die Antwort enthält eine zufällige Plan-ID.
4. Die Plan-ID ist standardmäßig 15 Minuten gültig.
5. MediaHub zeigt dem Benutzer den Plan.
6. Bei Bestätigung ruft MediaHub auf:

```http
POST /plugins/plan/{plan_id}/confirm
```

Zusätzlich muss dieselbe SHA-256-Prüfsumme übergeben werden:

```text
X-Plugin-SHA256: <SHA-256>
```

## Sicherheit

- Plan-IDs sind zufällig und nicht vorhersagbar.
- Ein Plan kann nur einmal bestätigt werden.
- Abgelaufene Pläne werden entfernt.
- Das temporäre ZIP wird nach Ablauf, Abbruch oder Bestätigung gelöscht.
- Die Prüfsumme bei Bestätigung muss zur ursprünglichen Prüfung passen.
- Pläne mit noch fehlenden Voraussetzungen können nicht bestätigt werden.

## Abbruch

```http
DELETE /plugins/plan/{plan_id}
```

Der Abbruch löscht den Plan und die temporäre Paketdatei.
