#!/bin/bash
# infrastructure/s3_bucket_policy.sh
# Configure S3 bucket policies for security and access control

set -e

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "Configuring S3 bucket policy for $BUCKET_NAME..."

# Create bucket policy that enforces encryption and secure transport
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::'$BUCKET_NAME'/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    },
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::'$BUCKET_NAME'",
        "arn:aws:s3:::'$BUCKET_NAME'/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    },
    {
      "Sid": "AllowLambdaAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::'$ACCOUNT_ID':role/AuditFlowLambdaExecutionRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::'$BUCKET_NAME'/*"
    },
    {
      "Sid": "AllowLambdaListBucket",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::'$ACCOUNT_ID':role/AuditFlowLambdaExecutionRole"
      },
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::'$BUCKET_NAME'"
    }
  ]
}'

echo "✓ S3 bucket policy configured successfully"

# Enable versioning for data protection
echo "Enabling S3 versioning..."
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

echo "✓ S3 versioning enabled"

# Block public access
echo "Blocking public access..."
aws s3api put-public-access-block \
    --bucket $BUCKET_NAME \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "✓ Public access blocked"

echo "S3 bucket policy configuration complete!"
