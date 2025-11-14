#! /bin/bash

if [ $# -ne 1 ]; then
  echo "Usage: $0 <env_name>"
  exit 1
fi

ENV_NAME=$1

docker exec -it redis-$ENV_NAME redis-cli -a password