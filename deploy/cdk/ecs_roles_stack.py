from aws_cdk import (
    Stack,
    aws_iam as iam,
)
from constructs import Construct

class EcsRolesStackProps:
    def __init__(self, secrets_policy: iam.ManagedPolicy, s3_policy: iam.ManagedPolicy, **kwargs):
        self.secrets_policy = secrets_policy
        self.s3_policy = s3_policy

class EcsRolesStack(Stack):
    @property
    def task_execution_role(self) -> iam.Role:
        return self._task_execution_role

    @property
    def task_role(self) -> iam.Role:
        return self._task_role
    
    @property
    def service_role(self) -> iam.Role:
        return self._service_role

    def __init__(self, scope: Construct, construct_id: str, props: EcsRolesStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        secrets_policy = props.secrets_policy
        s3_policy = props.s3_policy

        self._task_execution_role = iam.Role(
            self, 
            "ECSTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, 
                    "GymJunkieExecutionS3Policy",
                    managed_policy_arn=s3_policy.managed_policy_arn
                ),
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, 
                    "GymJunkieExecutionSecretsPolicy",
                    managed_policy_arn=secrets_policy.managed_policy_arn
                )
            ]
        )

        self._task_role = iam.Role(
            self, 
            "ECSTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, 
                    "GymJunkieTaskSecretsPolicy",
                    managed_policy_arn=secrets_policy.managed_policy_arn
                )
            ]
        )

        self._service_role = iam.Role(
            self,
            "ECSServiceRole",
            assumed_by=iam.ServicePrincipal("ecs.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonEC2ContainerServiceRole"
                )
            ],
        )
