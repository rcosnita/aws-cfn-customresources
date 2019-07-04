#!/usr/bin/env bash
set -eo pipefail

S3_BUCKET_PATH=s3://rcosnita-opensource/cfn-customresource

aws s3 cp --acl=public-read --recursive customresource ${S3_BUCKET_PATH}/customresource
aws s3 cp --acl=public-read bootstrap.sh ${S3_BUCKET_PATH}/bootstrap.sh
aws s3 cp --acl=public-read requirements.txt ${S3_BUCKET_PATH}/requirements.txt
