from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_servicediscovery as servicediscovery,

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
        redis_repository: ecr.Repository,
        redis_sg: ec2.SecurityGroup,
        private_namespace: servicediscovery.PrivateDnsNamespace,
        discovery_service_name: str,
        discovery_service: servicediscovery.Service,
        **kwargs
    ):
        self.vpc = vpc
        self.task_execution_role = task_execution_role
        self.task_role = task_role
        self.api_repository = api_repository
        self.api_sg = api_sg
        self.target_group = target_group
        self.redis_repository = redis_repository
        self.redis_sg = redis_sg
        self.private_namespace = private_namespace
        self.discovery_service_name = discovery_service_name
        self.discovery_service = discovery_service

class EcsClusterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: EcsClusterStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # existing_namespace = servicediscovery.PrivateDnsNamespace.from_private_dns_namespace_attributes(
        #     self,
        #     "ExistingNamespace",
        #     namespace_name=props.private_namespace.namespace_name,
        #     namespace_id=props.private_namespace.namespace_id,
        #     namespace_arn=props.private_namespace.namespace_arn
        #     # vpc=props.vpc,
        # )

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=props.vpc,
            # cloud_map_namespace=props.private_namespace
            # default_cloud_map_namespace=existing_namespace
        )
        # cluster.default_cloud_map_namespace = props.private_namespace
        # cluster.add_default_cloud_map_namespace(
        #     name=props.private_namespace.namespace_name,
        #     vpc=props.vpc
        # )

        # namespace = cluster.add_default_cloud_map_namespace(
        #     name=props.namespace_name
        # )

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

        redis_task_def = ecs.FargateTaskDefinition(
            self,
            "RedisTaskDef",
            cpu=256,
            memory_limit_mib=512,
            execution_role=props.task_execution_role,
            task_role=props.task_role,
        )

        redis_task_def.add_container(
            "RedisContainer",
            image=ecs.ContainerImage.from_ecr_repository(props.redis_repository),
            port_mappings=[
                ecs.PortMapping(
                    container_port=6379, 
                    protocol=ecs.Protocol.TCP
                )
            ]
        )

        redis_service = ecs.FargateService(
            self,
            "RedisEcsService",
            service_name="redis",
            cluster=cluster,
            task_definition=redis_task_def,
            desired_count=0,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnets=props.vpc.private_subnets),
            security_groups=[props.redis_sg],
            min_healthy_percent=100,
            max_healthy_percent=200,
            # cloud_map_options=ecs.CloudMapOptions(
            #     cloud_map_namespace=props.private_namespace,
            #     name=props.discovery_service_name,
            #     container=redis_task_def._containers[0],
            #     container_port=6379
            # )
        )

        redis_service.associate_cloud_map_service(
            service=props.discovery_service
        )