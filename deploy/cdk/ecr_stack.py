from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    RemovalPolicy,
    Duration
)
from constructs import Construct

class EcrStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.container_repository = ecr.Repository(
            self, "ContainerRepository",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        self.container_repository.add_lifecycle_rule(
            tag_status=ecr.TagStatus.UNTAGGED,
            max_image_age=Duration.days(1),
            rule_priority=1,
            description="Expire untagged images after 1 day"
        )