#! /bin/bash

docker build -f sync_redis/Dockerfile.sync_redis -t ecs-sync-redis sync_redis/

docker tag ecs-sync-redis:latest 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/ecs-sync-redis:latest

docker push 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/ecs-sync-redis:latest