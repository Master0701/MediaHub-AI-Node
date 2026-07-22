# REST-API

Basisadresse im lokalen System:

```text
http://127.0.0.1:8765
```

## Health

```http
GET /health
```

Beispiel:

```bash
curl -sS http://127.0.0.1:8765/health \
  | python -m json.tool
```

## OpenAPI

```http
GET /openapi.json
GET /docs
```

## Wissenseintrag importieren

```http
POST /knowledge/import/item
```

Beispiel:

```bash
curl -sS -X POST \
  http://127.0.0.1:8765/knowledge/import/item \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Creed II",
    "media_type": "movie",
    "year": 2018,
    "external_ids": {
      "tmdb": "480530",
      "imdb": "tt6343314"
    },
    "metadata": {
      "franchise": "Rocky / Creed",
      "collection": "Creed"
    },
    "source": "api_test",
    "dry_run": true
  }'
```

## Beziehung importieren

```http
POST /knowledge/import/relation
```

```bash
curl -sS -X POST \
  http://127.0.0.1:8765/knowledge/import/relation \
  -H "Content-Type: application/json" \
  -d '{
    "source": {"item_id": 3},
    "target": {"item_id": 2},
    "relation_type": "sequel-of",
    "order_type": "release-order",
    "position": 2,
    "notes": "Creed II setzt die Handlung von Creed fort.",
    "dry_run": true
  }'
```

## Merge

```http
POST /knowledge/import/merge
```

Der konkrete Payload muss mit dem jeweils aktuellen OpenAPI-Schema abgeglichen werden.

## API-Stabilität

Während der Alpha-Phase können sich Strukturen ändern. Änderungen müssen im Changelog und in der API-Dokumentation festgehalten werden.
