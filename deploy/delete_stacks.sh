#! /bin/bash

cdk destroy  \
  GymJunkieEcsClusterStack \
  GymJunkieNlbStack \
  GymJunkieEcsRolesStack \
  GymJunkieCloudMapStack \
  GymJunkieS3Stack \
  GymJunkieEcrSyncRedisStack \
  GymJunkieEcrRedisStack \
  GymJunkieEcrApiStack \
  GymJunkieSecretsPolicyStack \
  GymJunkieSecurityGroupStack