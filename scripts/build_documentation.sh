#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/docs/generated"
SOURCE="${ROOT_DIR}/docs/HANDBOOK.md"

mkdir -p "$OUT_DIR"

if ! command -v pandoc >/dev/null 2>&1; then
    echo "Pandoc fehlt. Installation unter Debian/Raspberry Pi OS:"
    echo "sudo apt install -y pandoc"
    exit 1
fi

pandoc "$SOURCE" \
  --standalone \
  --metadata title="MediaHub-AI-Node Handbuch" \
  -o "$OUT_DIR/MediaHub-AI-Node_Handbuch.html"

if command -v weasyprint >/dev/null 2>&1; then
    weasyprint \
      "$OUT_DIR/MediaHub-AI-Node_Handbuch.html" \
      "$OUT_DIR/MediaHub-AI-Node_Handbuch.pdf"
else
    echo "HTML wurde erstellt. Für PDF bitte WeasyPrint installieren."
fi
