#!/usr/bin/env bash
# Build MoodAI static frontend for Vercel (no Python runtime).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/phases/phase-3/static"
OUT="$ROOT/dist"

rm -rf "$OUT"
mkdir -p "$OUT/assets"

cp "$SRC/index.html" "$OUT/index.html"
cp "$SRC/app.js" "$OUT/assets/app.js"

API_URL="${MOODAI_API_URL:-}"
if [ -n "$API_URL" ]; then
  printf 'window.__MOODAI_CONFIG__ = { apiBaseUrl: "%s" };\n' "$API_URL" > "$OUT/config.js"
else
  printf 'window.__MOODAI_CONFIG__ = { apiBaseUrl: "" };\n' > "$OUT/config.js"
fi

echo "Vercel build complete: dist/ ($(wc -c < "$OUT/index.html") bytes HTML, API=${API_URL:-same-origin})"
