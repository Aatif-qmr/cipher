#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QUEUE_FILE="$BASE_DIR/qnt/memory/.sync_queue"
SYNC_SCRIPT="$BASE_DIR/qnt/memory/sync_memory.sh"
LOG="$BASE_DIR/logs/memory_sync.log"
WAS_OFFLINE=false

while true; do
  if nc -zw3 8.8.8.8 53 2>/dev/null; then
    if [ "$WAS_OFFLINE" = true ] || [ -f "$QUEUE_FILE" ]; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] RECONNECTED - immediate sync" >> "$LOG"
      bash "$SYNC_SCRIPT"
      WAS_OFFLINE=false
    fi
  else
    if [ "$WAS_OFFLINE" = false ]; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] WENT_OFFLINE" >> "$LOG"
      WAS_OFFLINE=true
    fi
  fi
  sleep 30
done
