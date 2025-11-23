from aws_cdk import (
    Stack,
    aws_iam as iam,
)
from constructs import Construct

class EcrTaskRolesStackProps:
    def __init__(self, secrets_policy_arn: str, **kwargs):
        self.secrets_policy_arn = secrets_policy_arn

class EcrTaskRolesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: EcrTaskRolesStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        secrets_policy_arn = props.secrets_policy_arn

        task_execution_role = iam.Role(
            self, 
            "ECSTaskExecutionRole",
            # role_name="ecsTaskExecutionRole2",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for ECS Task Execution, granting rights to the ECS agent."
        )

        task_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )

        task_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, 
                "GymJunkieS3Policy",
                managed_policy_arn="arn:aws:iam::822961100047:policy/gym-junkie-s3-policy"
            )
        )
        # 3. gym-junkie-secret-policy (custom policy)
        task_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, 
                "GymJunkieExecutionSecretPolicy",
                managed_policy_arn=secrets_policy_arn
            )
        )

        task_role = iam.Role(
            self, 
            "ECSTaskRole",
            # role_name="ecsTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for the application running in the ECS Task."
        )

        task_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, 
                "GymJunkieTaskSecretPolicy",
                managed_policy_arn=secrets_policy_arn
            )
        )
