#! /bin/bash

cdk destroy  \
  EcsClusterStack \
  NlbStack \
  EcsRolesStack \
  CloudMapStack \
  S3Stack \
  EcrSyncRedisStack \
  EcrRedisStack \
  EcrApiStack \
  SecretsPolicyStack \
  SecurityGroupStack