from aws_cdk import (
    Stack,
    aws_logs as logs,
    RemovalPolicy
)
from constructs import Construct

class LogsStack(Stack):
    @property
    def log_group(self) -> logs.LogGroup:
        return self._log_group

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._log_group = logs.LogGroup(
            self, "LogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )