#!/usr/bin/env bash
# Build, start headless, hit /health, and report size and idle memory.
# Fails over budget: binary <= 12 MB, idle memory <= 30 MB.
set -euo pipefail
cd "$(dirname "$0")"
exe=./helper-bin; [ "${RUNNER_OS:-}" = Windows ] && exe=./helper-bin.exe
go build -trimpath -ldflags='-s -w' -o "$exe" .
size=$(wc -c < "$exe"); echo "binary: $((size/1024/1024)) MB ($size bytes)"
[ "$size" -le 12582912 ] || { echo "binary over 12 MB"; exit 1; }
"$exe" version
"$exe" serve > url.txt &
pid=$!
trap 'kill $pid 2>/dev/null || true; rm -f url.txt "$exe"' EXIT
for _ in $(seq 1 50); do [ -s url.txt ] && break; sleep 0.1; done
url=$(head -n1 url.txt | tr -d '\r')
for _ in 1 2 3; do curl -fsS "$url/health" | grep -q ok; done
sleep 1
if [ "${RUNNER_OS:-}" = Windows ]; then
  kb=$(powershell -NoProfile -Command "(Get-Process -Name helper-bin).WorkingSet64 / 1024" | tr -d '\r' | cut -d. -f1)
else
  kb=$(ps -o rss= -p "$pid" | tr -d ' ')
fi
echo "idle memory: $((kb/1024)) MB (${kb} kB)"
[ "$kb" -le 30720 ] || { echo "idle memory over 30 MB"; exit 1; }
