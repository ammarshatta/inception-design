#!/usr/bin/env bash
# Daily 03:00 (cron): backup with files → encrypted upload (rclone crypt over R2) → prune → alert on failure.
# The rclone crypt passwords live only in the server's rclone.conf and with the owner (two places off the server).
set -euo pipefail
cd "$(dirname "$0")"
source .env
COMPOSE="docker compose --project-name inceptiondesign"
STAMP="$(date +%Y-%m-%d)"
fail() { echo "backup failed: $1" | mail -s "Inceptiondesign backup FAILED $STAMP" "$ALERT_EMAIL" || true; exit 1; }
trap 'fail "line $LINENO"' ERR

$COMPOSE exec -T backend bench --site "$SITE_NAME" backup --with-files
DIR="$($COMPOSE exec -T backend bash -c "ls -td sites/$SITE_NAME/private/backups | head -1")"
TMP="$(mktemp -d)"
$COMPOSE cp "backend:/home/frappe/frappe-bench/sites/$SITE_NAME/private/backups/." "$TMP/"
rclone copy "$TMP" "$RCLONE_REMOTE/$STAMP" --include "*$(date +%Y%m%d)*"
rclone delete "$RCLONE_REMOTE" --min-age "${BACKUP_KEEP_DAYS}d"
rclone rmdirs "$RCLONE_REMOTE" --leave-root
rm -rf "$TMP"
# keep only the last 3 local backups
$COMPOSE exec -T backend bash -c "cd sites/$SITE_NAME/private/backups && ls -t | tail -n +13 | xargs -r rm --"
echo "backup ok $STAMP ($DIR)"
