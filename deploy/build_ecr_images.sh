#! /bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker build -f "$SCRIPT_DIR/../Dockerfile.api" -t gym-junkie-api "$SCRIPT_DIR/../."
docker build -f "$SCRIPT_DIR/../Dockerfile.redis" -t redis "$SCRIPT_DIR/../."
docker build -f "$SCRIPT_DIR/../sync_redis/Dockerfile.sync_redis" -t gym-junkie-sync-redis "$SCRIPT_DIR/../sync_redis"