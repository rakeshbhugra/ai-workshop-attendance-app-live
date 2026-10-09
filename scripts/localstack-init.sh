#!/bin/sh
# Runs inside the LocalStack container once it reports ready (mounted into
# /etc/localstack/init/ready.d/). Creates the resources the app expects, so
# `make up-aws` gives you a working bucket rather than a NoSuchBucket error on
# the first upload.
#
# Add SQS queues / SNS topics / secrets here as the app grows — this file is the
# local equivalent of your Terraform or CDK stack.
set -e

awslocal s3 mb s3://attendance-local || true

# CORS matters only if the browser ever talks to S3 directly (presigned uploads).
# Harmless to set now, annoying to debug later when you add them.
awslocal s3api put-bucket-cors --bucket attendance-local --cors-configuration '{
  "CORSRules": [{
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
    "AllowedOrigins": ["http://localhost:5173", "http://localhost:8000"],
    "ExposeHeaders": ["ETag"]
  }]
}'

echo "localstack: bucket attendance-local ready"
