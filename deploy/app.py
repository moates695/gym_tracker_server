#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.vpc_stack import VpcStack
from cdk.security_group_stack import SecurityGroupStack, SecurityGroupStackProps

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

app.synth()
