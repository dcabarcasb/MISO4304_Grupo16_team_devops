#!/usr/bin/env bash
# Consulta GET /health cada segundo y registra hora, codigo HTTP y respuesta
# (version + instancia). Se detiene al crear el archivo <log>.stop.
# Uso: scripts/monitor-health.sh <url-base> <archivo-log>
URL="${1:?url base}"
LOG="${2:?archivo log}"
: > "$LOG"
while [ ! -f "$LOG.stop" ]; do
  ts=$(date +%H:%M:%S)
  body=$(curl -s -m 3 -w ' HTTP=%{http_code}' "$URL/health")
  echo "$ts $body" >> "$LOG"
  sleep 1
done
rm -f "$LOG.stop"
