#!/usr/bin/env bash
set -eox pipefail

S3_BUCKET_PATH=${1}
QUEUE_URL=${2}

rm -Rf customresource || true
mkdir customresource

cd /home/ec2-user
wget --directory-prefix=customresource ${S3_BUCKET_PATH}/customresource/__init__.py
wget --directory-prefix=customresource ${S3_BUCKET_PATH}/customresource/provider.py
wget ${S3_BUCKET_PATH}/requirements.txt

sudo yum install -y python3 python3-pip

python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt

EC2_AVAIL_ZONE=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
export AWS_DEFAULT_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"

rm -f nohup.out || true
nohup python customresource/provider.py --cfn-queue ${QUEUE_URL} &
