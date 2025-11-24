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

env = cdk.Environment(
    account='822961100047', 
    region='ap-southeast-2'
)

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
    props=SecretsPolicyStackProps(
        secret_arns=[
            "arn:aws:secretsmanager:ap-southeast-2:822961100047:secret:prod/gym-junkie/api-SWmGeE",
            "arn:aws:secretsmanager:ap-southeast-2:822961100047:secret:prod/gym-junkie/postgres-kQtGJc"
        ]
    )
)

ecr_stack = EcrStack(
    app,
    "EcrStack",
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
        vpc=vpc_stack.vpc
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

app.synth()
