#!/bin/bash
# infrastructure/s3_config.sh
# Configure S3 bucket CORS and lifecycle policies

set -e

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "Configuring S3 bucket: $BUCKET_NAME"
echo "=========================================="

# Configure CORS for frontend access
echo "Configuring CORS..."
aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration '{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag", "x-amz-server-side-encryption", "x-amz-request-id"],
      "MaxAgeSeconds": 3000
    }
  ]
}'
echo "✓ CORS configured"

# Configure Lifecycle Policy for archival to Glacier and retention
echo "Configuring Lifecycle Policy (Glacier after 90 days, Delete after 7 years)..."
aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET_NAME --lifecycle-configuration '{
  "Rules": [
    {
      "Id": "ArchiveToGlacierAfter90Days",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 2555
      }
    },
    {
      "Id": "DeleteOldVersionsAfter30Days",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 30
      }
    }
  ]
}'
echo "✓ Lifecycle policy configured"

# Configure server access logging (optional but recommended)
echo "Configuring server access logging..."
LOGGING_BUCKET="${BUCKET_NAME}-logs"

# Create logging bucket if it doesn't exist
if ! aws s3api head-bucket --bucket $LOGGING_BUCKET 2>/dev/null; then
    echo "Creating logging bucket: $LOGGING_BUCKET"
    aws s3api create-bucket \
        --bucket $LOGGING_BUCKET \
        --region ap-south-1 \
        --create-bucket-configuration LocationConstraint=ap-south-1 || true
    
    # Block public access on logging bucket
    aws s3api put-public-access-block \
        --bucket $LOGGING_BUCKET \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" || true
fi

# Enable logging
aws s3api put-bucket-logging \
    --bucket $BUCKET_NAME \
    --bucket-logging-status '{
        "LoggingEnabled": {
            "TargetBucket": "'$LOGGING_BUCKET'",
            "TargetPrefix": "s3-access-logs/"
        }
    }' || echo "Note: Logging configuration may require additional permissions"

echo "✓ Server access logging configured"

echo ""
echo "=========================================="
echo "S3 configurations applied successfully!"
echo "Bucket: $BUCKET_NAME"
echo "- CORS: Enabled"
echo "- Lifecycle: Archive to Glacier after 90 days, Delete after 7 years"
echo "- Logging: Enabled (if permissions allow)"
echo "=========================================="
