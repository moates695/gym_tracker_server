aws lambda update-function-configuration \
  --function-name test-sync-redis \
  --environment "Variables={ENVIRONMENT=prod,SERVER_ADDRESS=https://gymjunkie.moates.com.au,SERVER_PORT=443,DATABASE=gym_tracker,EMAIL=gymtrackeraus@gmail.com,REDIS_HOST=gym-junkie-redis-cluster.2q9to2.0001.apse2.cache.amazonaws.com,REDIS_PORT=6379}" \
  > /dev/null