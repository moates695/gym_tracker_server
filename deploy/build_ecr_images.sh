#! /bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker build -f "$SCRIPT_DIR/../Dockerfile.api" -t gym-junkie-api "$SCRIPT_DIR/../."
docker build -f "$SCRIPT_DIR/../Dockerfile.redis" -t redis "$SCRIPT_DIR/../."
docker build -f "$SCRIPT_DIR/../sync_redis/Dockerfile.sync_redis" -t gym-junkie-sync-redis "$SCRIPT_DIR/../sync_redis"

# docker tag gym-junkie-api:latest 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/ecs-sync-redis:latest
# docker push 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/ecs-sync-redis:latest

# docker tag ecs-sync-redis:latest 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/ecs-sync-redis:latest
# docker push 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/ecs-sync-redis:latest