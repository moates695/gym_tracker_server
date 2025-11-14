#! /bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <env_name>"
  exit 1
fi

ENV_NAME=$1
ENV_PATH=app/envs/${ENV_NAME}.env

if [ ! -f $ENV_PATH ]; then
  echo "Error: app/envs/${ENV_NAME}.env not found"
  exit 1
fi

set -a
source $ENV_PATH
set +a

ENV_NAME=$ENV_NAME docker-compose up -d --build 