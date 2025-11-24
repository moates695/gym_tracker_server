from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_servicediscovery as servicediscovery,
    aws_ecs_patterns as ecs_patterns,
    aws_events as events,
    aws_applicationautoscaling as appscaling,
    aws_events_targets as targets,
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
        sync_redis_repository: ecr.Repository,
        sync_redis_sg: ec2.SecurityGroup,
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
        self.sync_redis_repository = sync_redis_repository
        self.sync_redis_sg = sync_redis_sg

class EcsClusterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: EcsClusterStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=props.vpc,
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
        )

        redis_service.associate_cloud_map_service(
            service=props.discovery_service
        )

        sync_redis_task_def = ecs.FargateTaskDefinition(
            self,
            "SyncRedisTaskDef",
            cpu=256,
            memory_limit_mib=512,
            execution_role=props.task_execution_role,
            task_role=props.task_role,
        )

        sync_redis_task_def.add_container(
            "SyncRedisContainer",
            image=ecs.ContainerImage.from_ecr_repository(props.redis_repository),
        )

        rule = events.Rule(
            self,
            "CronRule",
            schedule=events.Schedule.expression("rate(60 minutes)"),
        )

        rule.add_target(
            targets.EcsTask(
                cluster=cluster,
                task_definition=sync_redis_task_def,
                platform_version=ecs.FargatePlatformVersion.LATEST,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                assign_public_ip=True
            )
        )

        # ecs_patterns.ScheduledFargateTask(
        #     self,
        #     "SyncRedisCronTask",
        #     cluster=cluster,
        #     scheduled_fargate_task_definition_options=ecs_patterns.ScheduledFargateTaskDefinitionOptions(
        #         task_definition=sync_redis_task_def,
        #     ),
        #     subnet_selection=ec2.SubnetSelection(subnets=props.vpc.public_subnets),
        #     security_groups=[props.sync_redis_sg],
        #     schedule=appscaling.Schedule.cron(
        #         minute="0",
        #         hour="*/1",
        #     ),
        #     platform_version=ecs.FargatePlatformVersion.LATEST,
        # )