#!/usr/bin/env bash

set -Eeuo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8765}"

curl -sS "$BASE_URL/health" | python -m json.tool

curl -sS -X POST \
  "$BASE_URL/knowledge/import/item" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Creed II",
    "media_type": "movie",
    "year": 2018,
    "external_ids": {
      "tmdb": "480530",
      "imdb": "tt6343314"
    },
    "source": "example",
    "dry_run": true
  }' | python -m json.tool
