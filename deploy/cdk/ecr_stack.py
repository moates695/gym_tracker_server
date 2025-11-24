from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct

class EcrStack(Stack):
    @property
    def repository(self) -> ecr.Repository:
        return self._repository

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._repository = ecr.Repository(
            self, "ContainerRepository",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        self._repository.add_lifecycle_rule(
            tag_status=ecr.TagStatus.UNTAGGED,
            max_image_age=Duration.days(1),
            rule_priority=1,
            description="Expire untagged images after 1 day"
        )

        CfnOutput(
            self, "RepoUri",
            value=self._repository.repository_uri,
        )