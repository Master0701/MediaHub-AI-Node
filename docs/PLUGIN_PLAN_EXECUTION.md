# Kontrollierte Ausführung eines Installationsplans

## Endpunkt

```http
POST /plugins/plan/{plan_id}/execute
```

Der Endpunkt ist durch das AI-Node-Bearer-Token geschützt.

## Aktuell automatisch erlaubt

- Python-Pakete aus der zuvor geprüften `requirements.txt`
- Installation ausschließlich über die aktive Python-Umgebung
- Ausführung ohne Shell über:
  `python -m pip install <Anforderung>`

## Noch nicht automatisch erlaubt

- `sudo apt install`
- beliebige Shell-Befehle
- weitere AI-Plugins
- Dienstneustarts

Diese Schritte bleiben im Installationsplan sichtbar und müssen später über
eigene, eng begrenzte Installationsdienste freigegeben werden.

## Ablauf

1. Plan-ID laden.
2. Nur freigegebene Python-Aktionen ausführen.
3. Plugin-Paket erneut prüfen.
4. Voraussetzungen erneut ermitteln.
5. Persistenten Plan aktualisieren.
6. Status zurückgeben:
   - `ready_for_confirmation`
   - `requirements_pending`

Der Plan wird dabei nicht verbraucht. Erst der anschließende
Bestätigungsendpunkt installiert das eigentliche AI-Plugin.
