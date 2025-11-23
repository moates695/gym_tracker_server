from aws_cdk import (
    Stack,
    CfnParameter,
    Duration,
)
from aws_cdk import aws_servicediscovery as servicediscovery
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

class CloudMapStackProps:
    def __init__(self, vpc: ec2.IVpc, **kwargs):
        self.vpc = vpc

class CloudMapStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, props: CloudMapStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = props.vpc

        private_namespace = servicediscovery.PrivateDnsNamespace(
            self,
            "PrivateNamespace",
            name="gym-junkie.internal",
            vpc=vpc,
            description="private namespace for gym junkie"
        )

        servicediscovery.Service(
            self,
            "DiscoveryService",
            name="redis.gym-junkie.internal",
            namespace=private_namespace,
            description="Cloud Map Service for ECS Service Tasks",
            dns_config=servicediscovery.DnsConfig(
                routing_policy=servicediscovery.DnsRoutingPolicy.MULTIVALUE,
                dns_records=[servicediscovery.DnsRecordSpec(
                    type=servicediscovery.DnsRecordType.A,
                    ttl=Duration.seconds(60)
                )]
            ),
            custom_health_check=servicediscovery.CustomHealthCheckConfig(
                failure_threshold=1
            )
        )
