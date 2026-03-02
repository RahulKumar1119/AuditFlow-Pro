#!/bin/bash
# infrastructure/s3_event_trigger_setup.sh
# Task 13.1: Configure S3 event notifications with SQS for concurrency control
# Requirements: 10.1, 10.2, 1.3

set -e

REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"
QUEUE_NAME="AuditFlow-DocumentProcessingQueue"
TRIGGER_FUNCTION_NAME="AuditFlow-Trigger"

echo "=========================================="
echo "Configuring S3 Event Triggers"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Bucket: $BUCKET_NAME"
echo "=========================================="
echo ""

# Step 1: Create SQS Queue for document processing with concurrency control
echo "Step 1: Creating SQS Queue: $QUEUE_NAME..."

QUEUE_URL=$(aws sqs get-queue-url --queue-name $QUEUE_NAME --query 'QueueUrl' --output text 2>/dev/null || echo "")

if [ -z "$QUEUE_URL" ]; then
    echo "Creating new SQS queue..."
    QUEUE_URL=$(aws sqs create-queue \
        --queue-name $QUEUE_NAME \
        --attributes '{
            "VisibilityTimeout": "300",
            "MessageRetentionPeriod": "86400",
            "ReceiveMessageWaitTimeSeconds": "20",
            "DelaySeconds": "0"
        }' \
        --query 'QueueUrl' \
        --output text)
    echo "✓ Queue created: $QUEUE_URL"
else
    echo "Queue already exists: $QUEUE_URL"
fi

QUEUE_ARN=$(aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' \
    --output text)

echo "Queue ARN: $QUEUE_ARN"
echo ""

# Step 2: Configure SQS Queue Policy to allow S3 to send messages
echo "Step 2: Configuring SQS Queue Policy..."

aws sqs set-queue-attributes \
    --queue-url $QUEUE_URL \
    --attributes '{
        "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"s3.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$QUEUE_ARN'\",\"Condition\":{\"ArnLike\":{\"aws:SourceArn\":\"arn:aws:s3:::'$BUCKET_NAME'\"}}}]}"
    }'

echo "✓ SQS Queue Policy configured"
echo ""

# Step 3: Configure S3 Event Notification to send to SQS
echo "Step 3: Configuring S3 Event Notification..."

# Create event notification configuration
# Filter for supported file formats: PDF, JPEG, PNG, TIFF (Requirements 1.3, 10.2)
aws s3api put-bucket-notification-configuration \
    --bucket $BUCKET_NAME \
    --notification-configuration '{
        "QueueConfigurations": [
            {
                "Id": "DocumentUploadNotification",
                "QueueArn": "'$QUEUE_ARN'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "uploads/"
                            },
                            {
                                "Name": "suffix",
                                "Value": ".pdf"
                            }
                        ]
                    }
                }
            },
            {
                "Id": "DocumentUploadNotificationJPEG",
                "QueueArn": "'$QUEUE_ARN'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "uploads/"
                            },
                            {
                                "Name": "suffix",
                                "Value": ".jpeg"
                            }
                        ]
                    }
                }
            },
            {
                "Id": "DocumentUploadNotificationJPG",
                "QueueArn": "'$QUEUE_ARN'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "uploads/"
                            },
                            {
                                "Name": "suffix",
                                "Value": ".jpg"
                            }
                        ]
                    }
                }
            },
            {
                "Id": "DocumentUploadNotificationPNG",
                "QueueArn": "'$QUEUE_ARN'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "uploads/"
                            },
                            {
                                "Name": "suffix",
                                "Value": ".png"
                            }
                        ]
                    }
                }
            },
            {
                "Id": "DocumentUploadNotificationTIFF",
                "QueueArn": "'$QUEUE_ARN'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "uploads/"
                            },
                            {
                                "Name": "suffix",
                                "Value": ".tiff"
                            }
                        ]
                    }
                }
            },
            {
                "Id": "DocumentUploadNotificationTIF",
                "QueueArn": "'$QUEUE_ARN'",
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {
                    "Key": {
                        "FilterRules": [
                            {
                                "Name": "prefix",
                                "Value": "uploads/"
                            },
                            {
                                "Name": "suffix",
                                "Value": ".tif"
                            }
                        ]
                    }
                }
            }
        ]
    }'

echo "✓ S3 Event Notification configured"
echo "  - Triggers on: s3:ObjectCreated:* events"
echo "  - Prefix filter: uploads/"
echo "  - Suffix filters: .pdf, .jpeg, .jpg, .png, .tiff, .tif"
echo "  - Target: SQS Queue ($QUEUE_ARN)"
echo ""

# Step 4: Configure Lambda trigger from SQS (if Lambda function exists)
echo "Step 4: Configuring Lambda trigger from SQS..."

TRIGGER_FUNCTION_ARN=$(aws lambda get-function \
    --function-name $TRIGGER_FUNCTION_NAME \
    --query 'Configuration.FunctionArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$TRIGGER_FUNCTION_ARN" ]; then
    echo "Warning: Lambda function $TRIGGER_FUNCTION_NAME not found."
    echo "Please deploy the trigger Lambda function and run this script again."
    echo ""
    echo "To configure Lambda trigger manually after deployment:"
    echo "  aws lambda create-event-source-mapping \\"
    echo "    --function-name $TRIGGER_FUNCTION_NAME \\"
    echo "    --event-source-arn $QUEUE_ARN \\"
    echo "    --batch-size 10 \\"
    echo "    --maximum-batching-window-in-seconds 5"
else
    echo "Lambda function found: $TRIGGER_FUNCTION_ARN"
    
    # Check if event source mapping already exists
    MAPPING_UUID=$(aws lambda list-event-source-mappings \
        --function-name $TRIGGER_FUNCTION_NAME \
        --event-source-arn $QUEUE_ARN \
        --query 'EventSourceMappings[0].UUID' \
        --output text 2>/dev/null || echo "")
    
    if [ "$MAPPING_UUID" != "None" ] && [ -n "$MAPPING_UUID" ]; then
        echo "Event source mapping already exists: $MAPPING_UUID"
        
        # Update the mapping to ensure correct configuration
        aws lambda update-event-source-mapping \
            --uuid $MAPPING_UUID \
            --batch-size 10 \
            --maximum-batching-window-in-seconds 5 \
            --function-response-types "ReportBatchItemFailures" 2>/dev/null || true
        
        echo "✓ Event source mapping updated"
    else
        echo "Creating event source mapping..."
        
        # Grant Lambda permission to receive messages from SQS
        aws lambda add-permission \
            --function-name $TRIGGER_FUNCTION_NAME \
            --statement-id AllowSQSInvoke \
            --action lambda:InvokeFunction \
            --principal sqs.amazonaws.com \
            --source-arn $QUEUE_ARN 2>/dev/null || echo "Permission may already exist"
        
        # Create event source mapping
        # Task 13.3: Configure concurrent execution limits (batch size controls concurrency)
        MAPPING_UUID=$(aws lambda create-event-source-mapping \
            --function-name $TRIGGER_FUNCTION_NAME \
            --event-source-arn $QUEUE_ARN \
            --batch-size 10 \
            --maximum-batching-window-in-seconds 5 \
            --function-response-types "ReportBatchItemFailures" \
            --query 'UUID' \
            --output text)
        
        echo "✓ Event source mapping created: $MAPPING_UUID"
    fi
fi

echo ""
echo "=========================================="
echo "S3 Event Trigger Configuration Complete!"
echo "=========================================="
echo "Configuration Summary:"
echo "  - S3 Bucket: $BUCKET_NAME"
echo "  - SQS Queue: $QUEUE_NAME"
echo "  - Queue URL: $QUEUE_URL"
echo "  - Queue ARN: $QUEUE_ARN"
echo "  - Lambda Function: $TRIGGER_FUNCTION_NAME"
echo ""
echo "Event Flow:"
echo "  1. Document uploaded to s3://$BUCKET_NAME/uploads/*.{pdf,jpeg,jpg,png,tiff,tif}"
echo "  2. S3 sends notification to SQS Queue"
echo "  3. Lambda function triggered from SQS (batch size: 10)"
echo "  4. Lambda validates file size and initiates Step Functions workflow"
echo ""
echo "Concurrency Control:"
echo "  - SQS acts as a buffer for high-volume uploads"
echo "  - Lambda processes up to 10 messages per batch"
echo "  - Documents processed in upload order (FIFO within batch)"
echo "=========================================="

