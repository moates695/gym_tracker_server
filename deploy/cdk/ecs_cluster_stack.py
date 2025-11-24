from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2
)
from constructs import Construct
from aws_cdk import Stack

class EcsClusterStackProps:
    def __init__(
        self, 
        vpc: ec2.Vpc, 
        task_execution_role: iam.ManagedPolicy, 
        task_role: iam.ManagedPolicy, 
        api_repository: ecr.Repository,
        api_sg: ec2.SecurityGroup,
        target_group: elbv2.NetworkTargetGroup,
        **kwargs
    ):
        self.vpc = vpc
        self.task_execution_role = task_execution_role
        self.task_role = task_role
        self.api_repository = api_repository
        self.api_sg = api_sg
        self.target_group = target_group

class EcsClusterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: EcsClusterStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=props.vpc
        )

        api_task_def = ecs.FargateTaskDefinition(
            self,
            "ApiTaskDef",
            cpu=256,
            memory_limit_mib=512,
            execution_role=props.task_execution_role,
            task_role=props.task_role,
        )

        api_task_def.add_container(
            "ApiContainer",
            image=ecs.ContainerImage.from_ecr_repository(props.api_repository),
            port_mappings=[
                ecs.PortMapping(
                    container_port=80, 
                    protocol=ecs.Protocol.TCP
                )
            ]
        )

        api_service = ecs.FargateService(
            self,
            "ApiService",
            cluster=cluster,
            task_definition=api_task_def,
            desired_count=0,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnets=props.vpc.private_subnets),
            security_groups=[props.api_sg],
            min_healthy_percent=100,
            max_healthy_percent=200,
        )

        api_service.attach_to_network_target_group(props.target_group)