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

import os
import sys

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template


@pytest.fixture(scope="function")
def stack_defaults():
    os.environ["ADDF_PROJECT_NAME"] = "test-project"
    os.environ["ADDF_DEPLOYMENT_NAME"] = "test-deployment"
    os.environ["ADDF_MODULE_NAME"] = "test-module"
    os.environ["CDK_DEFAULT_ACCOUNT"] = "111111111111"
    os.environ["CDK_DEFAULT_REGION"] = "us-east-1"
    os.environ["ADDF_PARAMETER_VPC_ID"] = "vpc-12345"
    os.environ[
        "ADDF_PARAMETER_OPENSEARCH_DOMAIN_ENDPOINT"
    ] = "vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com"
    os.environ["ADDF_PARAMETER_OPENSEARCH_SG_ID"] = "sg-084c0dd9dc65c6937"

    if "stack" in sys.modules:
        del sys.modules["stack"]


def test_synthesize_stack(stack_defaults):
    import stack

    app = cdk.App()
    dep_name = "test-deployment"
    mod_name = "test-module"

    tunnel = stack.TunnelStack(
        scope=app,
        id=f"addf-{dep_name}-{mod_name}",
        deployment=dep_name,
        module=mod_name,
        vpc_id="vpc-12345",
        opensearch_sg_id="sg-084c0dd9dc65c6937",
        opensearch_domain_endpoint="vpc-addf-aws-solutions--367e660c-something.us-west-2.es.amazonaws.com",
        install_script="install_nginx.sh",
        port=3333,
        env=cdk.Environment(
            account=os.environ["CDK_DEFAULT_ACCOUNT"],
            region=os.environ["CDK_DEFAULT_REGION"],
        ),
    )

    template = Template.from_stack(tunnel)
    template.resource_count_is("AWS::IAM::Role", 1)
    template.resource_count_is("AWS::IAM::InstanceProfile", 1)
    template.resource_count_is("AWS::EC2::Instance", 1)
    template.resource_count_is("AWS::EC2::SecurityGroupIngress", 1)