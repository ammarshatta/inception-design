#!/usr/bin/env bash
# Hourly (cron): email the owner when the disk is above 80% or no backup was uploaded today after 05:00.
set -uo pipefail
cd "$(dirname "$0")"
source .env
USED="$(df --output=pcent / | tail -1 | tr -dc 0-9)"
[ "$USED" -gt 80 ] && echo "disk at ${USED}%" | mail -s "Inceptiondesign: disk ${USED}%" "$ALERT_EMAIL"
if [ "$(date +%H)" -ge 5 ] && ! rclone lsf "$RCLONE_REMOTE/$(date +%Y-%m-%d)" >/dev/null 2>&1; then
  echo "no backup for $(date +%F)" | mail -s "Inceptiondesign: no backup today" "$ALERT_EMAIL"
fi
