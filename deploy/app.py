#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.vpc_stack import VpcStack
from cdk.security_group_stack import SecurityGroupStack, SecurityGroupStackProps
from cdk.secrets_policy_stack import SecretsPolicyStack, SecretsPolicyStackProps
from cdk.ecr_stack import EcrStack
from cdk.s3_stack import S3Stack
from cdk.cloud_map_stack import CloudMapStack, CloudMapStackProps
from cdk.ecs_roles_stack import EcsRolesStack, EcsRolesStackProps
from cdk.ecs_cluster_stack import EcsClusterStack, EcsClusterStackProps
from cdk.nlb_stack import NlbStack, NlbStackProps

env = cdk.Environment(
    account='822961100047', 
    region='ap-southeast-2'
)

namespace_name = "gym-junkie.internal"
discovery_service_name = "redis.gym-junkie.internal"
certificate_arn = "arn:aws:acm:ap-southeast-2:822961100047:certificate/dcc73684-264a-4dd9-bdfc-1c4abd33337b"
secret_arns=[
    "arn:aws:secretsmanager:ap-southeast-2:822961100047:secret:prod/gym-junkie/api-SWmGeE",
    "arn:aws:secretsmanager:ap-southeast-2:822961100047:secret:prod/gym-junkie/postgres-kQtGJc"
]

app = cdk.App()

vpc_stack = VpcStack(
    app,
    "VpcStack",
    env=env
)

security_group_stack = SecurityGroupStack(
    app,
    "SecurityGroupStack",
    env=env,
    props=SecurityGroupStackProps(
        vpc=vpc_stack.vpc
    )
)

secrets_policy_stack = SecretsPolicyStack(
    app,
    "SecretsPolicyStack",
    env=env,
    props=SecretsPolicyStackProps(secret_arns=secret_arns)
)

ecr_api_stack = EcrStack(
    app,
    "EcrApiStack",
    env=env
)

ecr_redis_stack = EcrStack(
    app,
    "EcrRedisStack",
    env=env
)

ecr_sync_redis_stack = EcrStack(
    app,
    "EcrSyncRedisStack",
    env=env
)

s3_stack = S3Stack(
    app,
    "S3Stack",
    env=env
)

cloud_map_stack = CloudMapStack(
    app,
    "CloudMapStack",
    env=env,
    props=CloudMapStackProps(
        vpc=vpc_stack.vpc,
        namespace_name=namespace_name,
        discovery_service_name=discovery_service_name
    )
)

ecs_roles_stack = EcsRolesStack(
    app,
    "EcsRolesStack",
    env=env,
    props=EcsRolesStackProps(
        secrets_policy=secrets_policy_stack.secrets_policy,
        s3_policy=s3_stack.s3_policy
    )
)

nlb_stack = NlbStack(
    app,
    "NlbStack",
    env=env,
    props=NlbStackProps(
        vpc=vpc_stack.vpc,
        certificate_arn=certificate_arn
    )
)

ecs_cluster_stack = EcsClusterStack(
    app,
    "EcsClusterStack",
    env=env,
    props=EcsClusterStackProps(
        vpc=vpc_stack.vpc,
        task_execution_role=ecs_roles_stack.task_execution_role,
        task_role=ecs_roles_stack.task_role,
        api_repository=ecr_api_stack.repository,
        api_sg=security_group_stack.api_sg,
        target_group=nlb_stack.target_group,
        redis_repository=ecr_redis_stack.repository,
        redis_sg=security_group_stack.redis_sg,
        private_namespace=cloud_map_stack.private_namespace,
        discovery_service_name=discovery_service_name,
        discovery_service=cloud_map_stack.discovery_service
    )
)

app.synth()
