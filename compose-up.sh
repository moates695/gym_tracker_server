#! /bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <env_name>"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_NAME=$1
ENV_PATH="$SCRIPT_DIR/app/envs/${ENV_NAME}.env"

if [ ! -f $ENV_PATH ]; then
  echo "Error: $ENV_PATH not found"
  exit 1
fi

set -a
source $ENV_PATH
set +a

# lambda/sync_shared.sh

ENV_NAME=$ENV_NAME docker-compose -p backend-${ENV_NAME} down
ENV_NAME=$ENV_NAME docker-compose -p backend-${ENV_NAME} up -d --build --force-recreate
