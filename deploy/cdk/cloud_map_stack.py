from aws_cdk import (
    Stack,
    CfnParameter,
    Duration,
)
from aws_cdk import aws_servicediscovery as servicediscovery
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

class CloudMapStackProps:
    def __init__(
        self, 
        vpc: ec2.IVpc, 
        namespace_name: str, 
        discovery_service_name: str, 
        **kwargs
    ):
        self.vpc = vpc
        self.namespace_name = namespace_name
        self.discovery_service_name = discovery_service_name

class CloudMapStack(Stack):   
    @property
    def private_namespace(self) -> servicediscovery.PrivateDnsNamespace:
        return self._private_namespace

    @property
    def discovery_service(self) -> servicediscovery.Service:
        return self._discovery_service

    def __init__(self, scope: Construct, construct_id: str, props: CloudMapStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._private_namespace = servicediscovery.PrivateDnsNamespace(
            self,
            "PrivateNamespace",
            name=props.namespace_name,
            vpc=props.vpc,
            description="private namespace for gym junkie"
        )

        self._discovery_service = servicediscovery.Service(
            self,
            "DiscoveryService",
            name=props.discovery_service_name,
            namespace=self._private_namespace,
            description="Cloud Map Service for ECS Service Tasks",
            dns_record_type=servicediscovery.DnsRecordType.A,
            dns_ttl=Duration.seconds(60),
            routing_policy=servicediscovery.RoutingPolicy.MULTIVALUE,
            custom_health_check=servicediscovery.HealthCheckCustomConfig(
                failure_threshold=1
            )
        )
