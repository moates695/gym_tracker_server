from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput
)
from constructs import Construct

class SecurityGroupStackProps:
    def __init__(self, vpc: ec2.IVpc, **kwargs):
        self.vpc = vpc

class SecurityGroupStack(Stack):
    @property
    def sync_redis_sg(self) -> ec2.SecurityGroup:
        return self._sync_redis_sg
    
    @property
    def api_sg(self) -> ec2.SecurityGroup:
        return self._api_sg
    
    @property
    def redis_sg(self) -> ec2.SecurityGroup:
        return self._redis_sg
    
    @property
    def db_sg(self) -> ec2.SecurityGroup:
        return self._db_sg

    def __init__(self, scope: Construct, construct_id: str, props: SecurityGroupStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = props.vpc

        self._sync_redis_sg = ec2.SecurityGroup(
            self, "GymJunkieSyncRedisSG",
            vpc=vpc,
            description="gym junkie ecs sync redis",
            allow_all_outbound=True
        )

        self._api_sg = ec2.SecurityGroup(
            self, "GymJunkieApiSG",
            vpc=vpc,
            description="gym junkie ecs api",
            allow_all_outbound=True
        )
        
        self._api_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
        )

        self._api_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
        )

        self._redis_sg = ec2.SecurityGroup(
            self, "GymJunkieRedisSG",
            vpc=vpc,
            description="gym junkie redis cache",
            allow_all_outbound=True
        )
        
        self._redis_sg.add_ingress_rule(
            peer=self._sync_redis_sg,
            connection=ec2.Port.tcp(6379),
        )

        self._db_sg = ec2.SecurityGroup(
            self, "GymJunkieDbSG",
            vpc=vpc,
            description="gym junkie postgres db",
            allow_all_outbound=True
        )

        self._db_sg.add_ingress_rule(
            peer=self._api_sg,
            connection=ec2.Port.tcp(5432),
        )
        
        self._db_sg.add_ingress_rule(
            peer=self._sync_redis_sg,
            connection=ec2.Port.tcp(5432),
        )
        
        self._db_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4("120.155.40.94/32"),
            connection=ec2.Port.tcp(5432),
        )

        CfnOutput(
            self, "DbSgId",
            value=self._db_sg.security_group_id
        )