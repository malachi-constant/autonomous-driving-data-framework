#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import logging
from typing import Any, cast

import aws_cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import cdk_nag
from aws_cdk import Aspects, Stack, Tags
from aws_cdk.aws_s3_assets import Asset
from cdk_nag import NagPackSuppression, NagSuppressions
from constructs import Construct, IConstruct

_logger: logging.Logger = logging.getLogger(__name__)


class ProxyStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        deployment: str,
        module: str,
        vpc_id: str,
        opensearch_sg_id: str,
        opensearch_domain_endpoint: str,
        install_script: str,
        port: int,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            scope,
            id,
            description="This stack deploys Proxy Tunnel environment to access Opensearch Dashboard",
            **kwargs,
        )
        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        dep_mod = f"addf-{deployment}-{module}"
        # CDK Env Vars
        account: str = aws_cdk.Aws.ACCOUNT_ID
        region: str = aws_cdk.Aws.REGION

        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        os_security_group = ec2.SecurityGroup.from_security_group_id(self, f"{dep_mod}-os-sg", opensearch_sg_id)

        # AMI
        amzn_linux = ec2.MachineImage.latest_amazon_linux2023(
            edition=ec2.AmazonLinuxEdition.STANDARD,
        )

        os_tunnel_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogStream",
                        "logs:CreateLogGroup",
                        "logs:PutLogEvents",
                        "logs:GetLogEvents",
                        "logs:GetLogRecord",
                        "logs:GetLogGroupFields",
                        "logs:GetQueryResults",
                        "logs:DescribeLogGroups",
                    ],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:logs:{region}:{account}:log-group:*"],
                ),
                iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    effect=iam.Effect.ALLOW,
                    resources=[f"arn:aws:iam::{account}:role/addf-*"],
                ),
            ]
        )

        os_tunnel_role = iam.Role(
            self,
            "os_tunnel_role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ec2.amazonaws.com"),
            ),
            inline_policies={"CDKostunnelPolicyDocument": os_tunnel_document},
        )

        os_tunnel_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        instance = ec2.Instance(
            self,
            "OSTunnel",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=amzn_linux,
            vpc=self.vpc,
            security_group=os_security_group,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            role=os_tunnel_role,
        )

        asset = Asset(self, "Asset", path=install_script)
        local_path = instance.user_data.add_s3_download_command(bucket=asset.bucket, bucket_key=asset.s3_object_key)

        args = opensearch_domain_endpoint + " " + str(port)

        instance.user_data.add_execute_file_command(file_path=local_path, arguments=args)
        asset.grant_read(instance.role)

        self.instance_id = instance.instance_id
        # self.instance_dns = instance.instance_public_dns_name
        url = f"http://localhost:{port}/_dashboards/"
        self.dashboard_url = url

        json_params = {"portNumber": [str(port)], "localPortNumber": [str(port)]}

        self.command = (
            f"aws ssm start-session --target {self.instance_id} "
            "--document-name AWS-StartPortForwardingSession "
            f"--parameters '{json.dumps(json_params)}'"
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM4",
                        "reason": "Managed Policies are for service account roles only",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-IAM5",
                        "reason": "Resource access restriced to ADDF resources",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-EC28",
                        "reason": "Detailed Monitoring not enabled as this is a simple tunnel",
                    }
                ),
                NagPackSuppression(
                    **{
                        "id": "AwsSolutions-EC29",
                        "reason": "ASG not enabled as this is a simple tunnel",
                    }
                ),
            ],
        )
