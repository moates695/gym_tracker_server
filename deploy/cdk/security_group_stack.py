# import aws_cdk.aws_ec2 as ec2
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnParameter,
    RemovalPolicy,
    Aws
)
from constructs import Construct

class SecurityGroupStackProps:
    def __init__(self, vpc: ec2.IVpc, **kwargs):
        self.vpc = vpc

class SecurityGroupStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: SecurityGroupStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = props.vpc

        gym_junkie_sync_redis_sg = ec2.SecurityGroup(
            self, "GymJunkieSyncRedisSG",
            vpc=vpc,
            # security_group_name=f"gym-junkie-sync-redis-sg-{suffix}",
            description="gym junkie ecs sync redis",
            allow_all_outbound=True
        )

        gym_junkie_api_sg = ec2.SecurityGroup(
            self, "GymJunkieApiSG",
            vpc=vpc,
            # security_group_name=f"gym-junkie-api-sg-{suffix}",
            description="gym junkie ecs api",
            allow_all_outbound=True
        )
        
        gym_junkie_api_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )

        gym_junkie_api_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
        )

        gym_junkie_redis_sg = ec2.SecurityGroup(
            self, "GymJunkieRedisSG",
            vpc=vpc,
            # security_group_name=f"gym-junkie-redis-sg-{suffix}",
            description="gym junkie redis cache",
            allow_all_outbound=True
        )
        
        gym_junkie_redis_sg.add_ingress_rule(
            peer=gym_junkie_sync_redis_sg,
            connection=ec2.Port.tcp(6379),
        )

        gym_junkie_db_sg = ec2.SecurityGroup(
            self, "GymJunkieDbSG",
            vpc=vpc,
            # security_group_name=f"gym-junkie-db-sg-{suffix}",
            description="gym junkie postgres db",
            allow_all_outbound=True
        )

        gym_junkie_db_sg.add_ingress_rule(
            peer=gym_junkie_api_sg,
            connection=ec2.Port.tcp(5432),
        )
        
        gym_junkie_db_sg.add_ingress_rule(
            peer=gym_junkie_sync_redis_sg,
            connection=ec2.Port.tcp(5432),
        )
        
        gym_junkie_db_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4("120.155.40.94/32"),
            connection=ec2.Port.tcp(5432),
        )