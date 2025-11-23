#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.vpc_stack import VpcStack
from cdk.security_group_stack import SecurityGroupStack, SecurityGroupStackProps
from cdk.secrets_policy_stack import SecretsManagerPolicyStack, SecretsManagerPolicyStackProps
from cdk.ecr_stack import EcrStack
from cdk.s3_stack import S3Stack

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

secrets_policy_stack = SecretsManagerPolicyStack(
    app,
    "SecretsPolicyStack",
    env=env,
    props=SecretsManagerPolicyStackProps(
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

app.synth()
