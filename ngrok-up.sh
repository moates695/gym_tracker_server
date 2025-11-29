#! /bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <env_name>"
  exit 1
fi

ENV_NAME=$1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_PATH="$SCRIPT_DIR/app/envs/${ENV_NAME}.env"

set -a
source $ENV_PATH
set +a

ngrok http --url=subtly-ample-bluebird.ngrok-free.app $SERVER_PORT