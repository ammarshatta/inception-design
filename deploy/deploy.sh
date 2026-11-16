#!/usr/bin/env bash
# deploy/deploy.sh vX.Y.Z — the only way to change the live site (CLAUDE.md rule 14).
# backup → pull the tagged image → restart → migrate → ping; on any failure, roll back to the previous tag.
set -euo pipefail
cd "$(dirname "$0")"
NEW_TAG="${1:?usage: deploy.sh vX.Y.Z}"
source .env
PREV_TAG="$CUSTOM_TAG"
COMPOSE="docker compose --project-name inceptiondesign"

set_tag() { sed -i "s/^CUSTOM_TAG=.*/CUSTOM_TAG=$1/" .env; }
up() { set_tag "$1"; $COMPOSE pull backend && $COMPOSE up -d; }
healthy() {
  for _ in $(seq 1 30); do
    curl -fsS "https://$SITE_NAME/api/method/ping" | grep -q pong && return 0
    sleep 5
  done
  return 1
}

./backup.sh
echo "deploying $NEW_TAG (previous $PREV_TAG)"
if up "$NEW_TAG" && $COMPOSE exec -T backend bench --site "$SITE_NAME" migrate && healthy; then
  echo "deployed $NEW_TAG"
else
  echo "deploy of $NEW_TAG failed — rolling back to $PREV_TAG" >&2
  up "$PREV_TAG"
  healthy || echo "ROLLBACK ALSO FAILED: restore from backup (docs/restore.md)" >&2
  exit 1
fi
