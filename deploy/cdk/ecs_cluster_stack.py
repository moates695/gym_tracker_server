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
    aws_s3 as s3,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
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
        discovery_service: servicediscovery.Service,
        sync_redis_repository: ecr.Repository,
        sync_redis_sg: ec2.SecurityGroup,
        bucket: s3.Bucket,
        log_group: logs.LogGroup,
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
        self.discovery_service = discovery_service
        self.sync_redis_repository = sync_redis_repository
        self.sync_redis_sg = sync_redis_sg
        self.bucket = bucket
        self.log_group=log_group

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

        db_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "GymJunkieDbSecret", "rds!db-984dacd4-02d8-4bb4-9c25-7dfb407b0427"
        )

        api_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "GymJunkieApiSecret", "prod/gym-junkie/api"
        )

        api_task_def.add_container(
            "ApiContainer",
            image=ecs.ContainerImage.from_ecr_repository(props.api_repository),
            port_mappings=[
                ecs.PortMapping(
                    container_port=80, 
                    protocol=ecs.Protocol.TCP
                )
            ],
            environment_files=[
                ecs.EnvironmentFile.from_bucket(props.bucket, "env-files/prod.env")
            ],
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(db_secret, field="username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, field="password"),
                "DB_HOST": ecs.Secret.from_secrets_manager(api_secret, field="DB_HOST"),
                "DB_PORT": ecs.Secret.from_secrets_manager(api_secret, field="DB_PORT"),
                "SECRET_KEY": ecs.Secret.from_secrets_manager(api_secret, field="SECRET_KEY"),
                "TEMP_SECRET_KEY": ecs.Secret.from_secrets_manager(api_secret, field="TEMP_SECRET_KEY"),
                # "REDIS_PASSWORD": ecs.Secret.from_secrets_manager(api_secret, field="REDIS_PASSWORD"),
                "EMAIL_PWD": ecs.Secret.from_secrets_manager(api_secret, field="EMAIL_PWD"),
            },
            logging=ecs.LogDriver.aws_logs(
                log_group=props.log_group,
                stream_prefix="ecs/api"
            )
        )

        api_service = ecs.FargateService(
            self,
            "ApiService",
            cluster=cluster,
            task_definition=api_task_def,
            desired_count=1,
            assign_public_ip=False,
            # vpc_subnets=ec2.SubnetSelection(subnets=props.vpc.private_subnets),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
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
            ],
            logging=ecs.LogDriver.aws_logs(
                log_group=props.log_group,
                stream_prefix="ecs/redis"
            )
        )

        redis_service = ecs.FargateService(
            self,
            "RedisEcsService",
            service_name="redis",
            cluster=cluster,
            task_definition=redis_task_def,
            desired_count=1,
            assign_public_ip=False,
            # vpc_subnets=ec2.SubnetSelection(subnets=props.vpc.private_subnets),
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
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
            image=ecs.ContainerImage.from_ecr_repository(props.sync_redis_repository),
            environment_files=[
                ecs.EnvironmentFile.from_bucket(props.bucket, "env-files/prod.env")
            ],
            secrets={
                "DB_USER": ecs.Secret.from_secrets_manager(db_secret, field="username"),
                "DB_PASSWORD": ecs.Secret.from_secrets_manager(db_secret, field="password"),
                "DB_HOST": ecs.Secret.from_secrets_manager(api_secret, field="DB_HOST"),
                "DB_PORT": ecs.Secret.from_secrets_manager(api_secret, field="DB_PORT"),
            },
            logging=ecs.LogDriver.aws_logs(
                log_group=props.log_group,
                stream_prefix="ecs/sync-redis"
            )
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
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                assign_public_ip=False,
                security_groups=[props.sync_redis_sg]
            )
        )