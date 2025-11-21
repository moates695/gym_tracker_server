#! /bin/bash

docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  -t sync-redis:latest \
  .

docker tag \
  sync-redis:latest \
  822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/sync-redis:latest

docker push 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/sync-redis:latest

aws lambda update-function-code \
  --function-name test-sync-redis \
  --image-uri 822961100047.dkr.ecr.ap-southeast-2.amazonaws.com/sync-redis:latest \
  --publish \
  > /dev/null