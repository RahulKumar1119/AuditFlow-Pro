#!/bin/bash
# infrastructure/s3_config.sh

BUCKET_NAME="auditflow-documents-prod-$(aws sts get-caller-identity --query Account --output text)"

echo "Configuring CORS for $BUCKET_NAME..."
aws s3api put-bucket-cors --bucket $BUCKET_NAME --cors-configuration '{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

echo "Configuring Lifecycle Policy for $BUCKET_NAME (Glacier after 90 days, Delete after 7 years)..."
aws s3api put-bucket-lifecycle-configuration --bucket $BUCKET_NAME --lifecycle-configuration '{
  "Rules": [
    {
      "ID": "ArchiveAndRetain",
      "Filter": {"Prefix": ""},
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 2555
      }
    }
  ]
}'
echo "S3 configurations applied!"
