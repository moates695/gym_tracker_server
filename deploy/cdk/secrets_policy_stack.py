from aws_cdk import (
  Stack,
  CfnParameter,
  aws_iam as iam,
)
from constructs import Construct
from typing import Union, List

class SecretsManagerPolicyStackProps:
    def __init__(self, secret_arns: Union[str, List[str]]):
        self.secret_arns = secret_arns

class SecretsManagerPolicyStack(Stack):
    @property
    def secrets_policy_arn(self) -> str:
        return self._secrets_manager_read_policy

    def __init__(self, scope: Construct, construct_id: str, props: SecretsManagerPolicyStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if isinstance(props.secret_arns, str):
            resource_arns = [props.secret_arns]
        elif isinstance(props.secret_arns, list):
            resource_arns = props.secret_arns
        else:
            raise TypeError("secret_arns must be a string or a list of strings")

        self._secrets_manager_read_policy = iam.ManagedPolicy(self, "SecretsManagerReadPolicy",
            # managed_policy_name="gym-junkie-secret-policy",
            document=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            "secretsmanager:GetSecretValue",
                        ],
                        resources=resource_arns
                    )
                ]
            )
        )