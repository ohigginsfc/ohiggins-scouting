#!/usr/bin/env bash
# Linux host launcher: preserve cache, serialize runs, never print credentials.
set -Eeuo pipefail
umask 077
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p data/runtime data/logs
exec 9>data/runtime/sofascore-weekly.lock
if ! flock -n 9; then
    echo 'Sofascore: another weekly sync is running.' >&2
    exit 75
fi
env_file="${SCOUTING_SYNC_ENV_FILE:-.env.portal}"
if [[ ! -r "$env_file" ]]; then
    echo 'Sofascore: private environment file is missing or unreadable.' >&2
    exit 1
fi
docker compose --env-file "$env_file" -f docker-compose.sync.yml run --rm -T --no-deps publisher \
    weekly --apply --max-requests 240 --seconds 1800
