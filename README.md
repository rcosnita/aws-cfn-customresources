# aws-cfn-customresources

Provides a simple example of how to add support for custom resources using cloud formation and python.
This follows the official [CloudFormation documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html) for custom resources.

## Prerequisites

In order to run this example you need access to a valid AWS account. The experiment will rely on the following services:

* CloudFormation
* SNS
* SQS
* EC2 Instance

## Getting started

In order to be able to setup the project, make sure you install a python3 interpreter on your system.

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

export AWS_DEFAULT_PROFILE=<your aws profile> # skip this if you want to use the default profile.
export AWS_DEFAULT_REGION=eu-central-1 # skip this if you want to use the default region.

aws cloudformation create-stack \
    --stack-name custom-resource-example \
    --template-body file://$(pwd)/stack.yaml \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameters ParameterKey=TopicName,ParameterValue=custom-resource-sns-topic \
        ParameterKey=ResourceName,ParameterValue=custom-resource-example \
        ParameterKey=EnvironmentSshKeyId,ParameterValue=rcosnita-dev \
        ParameterKey=EnvironmentFriendlyName,ParameterValue=customresource \
    --timeout-in-minutes 10

python customresource/provider.py --cfn-queue <sqs url>
```

You can extract **sqs url** from the SQS management console of your account. Search for the sqs created by the newly submitted cloudformation stack.
