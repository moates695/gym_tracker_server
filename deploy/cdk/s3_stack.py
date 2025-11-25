import os
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct

LOCAL_FILE_PATH = "../app/envs/"
S3_OBJECT_KEY = "env-files"

class S3Stack(Stack):
    @property
    def bucket(self) -> s3.Bucket:
        return self._bucket
    
    @property
    def s3_policy(self) -> iam.ManagedPolicy:
        return self._s3_policy

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._bucket = s3.Bucket(self, "MyBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )
        
        s3_deployment.BucketDeployment(self, "DeployFile",
            sources=[s3_deployment.Source.asset(f"{LOCAL_FILE_PATH}")],
            destination_bucket=self._bucket,
            destination_key_prefix=S3_OBJECT_KEY,
        )

        list_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetBucketLocation",
                "s3:ListBucket"
            ],
            resources=[self._bucket.bucket_arn]
        )
        
        read_object_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:GetObjectAcl"
            ],
            resources=[f"{self._bucket.bucket_arn}/*"] 
        )
        
        self._s3_policy = iam.ManagedPolicy(self, "MyManagedPolicy",
            statements=[
                list_statement, 
                read_object_statement
            ],
            description="Read-only access policy for the S3 bucket",
        )

        CfnOutput(
            self, "BucketName",
            value=self._bucket.bucket_name
        )
        