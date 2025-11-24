from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
)
from constructs import Construct
from aws_cdk import Stack

class EcsClusterStackProps:
    def __init__(self, **kwargs):
        pass

class EcsClusterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: EcsClusterStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        