from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_certificatemanager as acm,
    Stack,
    Duration,
)
from constructs import Construct

class NlbStackProps:
    def __init__(self, vpc: ec2.IVpc, certificate_arn: str, **kwargs):
        self.vpc = vpc
        self.certificate_arn = certificate_arn

class NlbStack(Stack):
    @property
    def target_group(self) -> elbv2.NetworkTargetGroup:
        return self._target_group

    def __init__(self, scope: Construct, id: str, props: NlbStackProps, **kwargs):
        super().__init__(scope, id, **kwargs)

        self._target_group = elbv2.NetworkTargetGroup(
            self,
            "GymJunkieNLBTargetGroup",
            # target_group_name="gym-junkie-nlb-target-group",
            vpc=props.vpc,
            protocol=elbv2.Protocol.TCP,
            port=80,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                protocol=elbv2.Protocol.HTTP,
                path="/",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )

        nlb = elbv2.NetworkLoadBalancer(
            self,
            "GymJunkieNLB",
            # load_balancer_name="gym-junkie-nlb-2",
            vpc=props.vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
        )

        certificate = acm.Certificate.from_certificate_arn(
            self, 
            "Certificate", 
            props.certificate_arn
        )

        elbv2.NetworkListener(
            self,
            "TLSListener",
            load_balancer=nlb,
            port=443,
            protocol=elbv2.Protocol.TLS,
            certificates=[certificate],
            default_target_groups=[self._target_group],
        )