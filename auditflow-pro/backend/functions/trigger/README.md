# S3 Event Trigger Lambda Function

## Overview

The S3 Event Trigger Lambda function is the entry point to the AuditFlow-Pro document processing workflow. It automatically initiates document processing when files are uploaded to S3, bridging S3 uploads to Step Functions orchestration.

**Task**: 13 - Implement S3 event triggers and Lambda integration  
**Requirements**: 10.1, 10.2, 1.3, 1.4, 10.3, 10.5, 19.6, 20.2

## Architecture

```
┌─────────────────┐
│   S3 Bucket     │
│  (Document      │
│   Upload)       │
└────────┬────────┘
         │ Object Created Event
         │ (*.pdf, *.jpeg, *.png, *.tiff)
         ▼
┌─────────────────┐
│   SQS Queue     │
│  (Buffering &   │
│   Ordering)     │
└────────┬────────┘
         │ Batch of 10 messages
         │ (Concurrency Control)
         ▼
┌─────────────────┐
│  Trigger Lambda │
│  - Validate     │
│  - Extract      │
│  - Initiate     │
└────────┬────────┘
         │ Start Execution
         ▼
┌─────────────────┐
│ Step Functions  │
│   Workflow      │
└─────────────────┘
```

## Key Features

### 1. Automatic Event Processing (Requirement 10.1, 10.2)
- S3 sends event notifications within seconds of document upload
- Lambda triggered automatically via SQS queue
- Real-time processing initiation

### 2. File Format Filtering (Requirement 1.3)
Supported formats:
- PDF (`.pdf`)
- JPEG (`.jpeg`, `.jpg`)
- PNG (`.png`)
- TIFF (`.tiff`, `.tif`)

Only files with these extensions in the `uploads/` prefix trigger processing.

### 3. File Size Validation (Requirement 1.4)
- Maximum file size: 50MB
- Files exceeding limit are rejected with error logging
- No workflow initiated for oversized files

### 4. Concurrency Control (Requirement 10.5, 19.6)
- **Reserved Concurrent Executions**: 10
- **SQS Batch Size**: 10 messages
- **Queuing**: Excess requests buffered in SQS
- **Processing Order**: FIFO within batch (Requirement 10.4)

### 5. Document Metadata Extraction (Task 13.2)
Extracts from S3 event:
- Bucket name
- Object key (URL-decoded)
- File size
- Upload timestamp
- Loan application ID (from S3 key path)
- Generated document ID

### 6. Workflow Initiation (Requirement 10.3)
- Constructs Step Functions input payload
- Starts workflow execution with unique name
- Logs execution ARN for tracking

## Function Configuration

### Environment Variables
- `STATE_MACHINE_ARN`: ARN of the Step Functions state machine
- `AWS_REGION`: AWS region (default: ap-south-1)

### Runtime Settings
- **Runtime**: Python 3.10
- **Timeout**: 300 seconds (5 minutes)
- **Memory**: 256 MB
- **Concurrency**: 10 (reserved)

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectMetadata",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::auditflow-documents-prod-*",
        "arn:aws:s3:::auditflow-documents-prod-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "states:StartExecution",
      "Resource": "arn:aws:states:*:*:stateMachine:AuditFlowDocumentProcessing"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:AuditFlow-DocumentProcessingQueue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/AuditFlow-Trigger:*"
    }
  ]
}
```

## Deployment

### Prerequisites
1. S3 bucket created: `auditflow-documents-prod-{ACCOUNT_ID}`
2. Step Functions state machine deployed: `AuditFlowDocumentProcessing`
3. IAM role created: `AuditFlowLambdaExecutionRole`

### Deploy Lambda Function
```bash
# Deploy the trigger Lambda function
bash infrastructure/deploy_trigger_lambda.sh
```

This script:
1. Retrieves Step Functions ARN
2. Configures IAM role and policies
3. Packages Lambda function code
4. Creates/updates Lambda function
5. Configures concurrency limits
6. Sets up S3 event notifications

### Configure S3 Event Notifications
```bash
# Configure S3 to send events to SQS
bash infrastructure/s3_event_trigger_setup.sh
```

This script:
1. Creates SQS queue for document processing
2. Configures queue policy for S3 access
3. Sets up S3 event notifications with file format filters
4. Creates Lambda event source mapping from SQS

### Configure Concurrency Limits
```bash
# Set Lambda concurrency to 10
bash infrastructure/lambda_concurrency_setup.sh
```

## Event Flow

### 1. Document Upload
User uploads document to S3:
```
s3://auditflow-documents-prod-{ACCOUNT_ID}/uploads/{loan_id}/{filename}.pdf
```

### 2. S3 Event Notification
S3 sends event to SQS queue:
```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "eventName": "ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "auditflow-documents-prod-123456789012"
        },
        "object": {
          "key": "uploads/loan-123/w2-2023.pdf",
          "size": 1024000
        }
      },
      "eventTime": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

### 3. SQS Queuing
- Message buffered in SQS
- Visibility timeout: 300 seconds
- Batch size: 10 messages

### 4. Lambda Invocation
Lambda receives SQS batch:
```json
{
  "Records": [
    {
      "messageId": "msg-123",
      "body": "{...S3 event...}"
    }
  ]
}
```

### 5. Processing
For each message:
1. Parse S3 event from SQS body
2. Extract document metadata
3. Validate file format (supported extensions)
4. Validate file size (≤ 50MB)
5. Initiate Step Functions workflow

### 6. Workflow Initiation
Step Functions input:
```json
{
  "loan_application_id": "loan-123",
  "documents": [
    {
      "document_id": "doc-abc12345-20240115103000",
      "s3_bucket": "auditflow-documents-prod-123456789012",
      "s3_key": "uploads/loan-123/w2-2023.pdf",
      "file_size_bytes": 1024000,
      "upload_timestamp": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

### 7. Batch Item Failures
If processing fails:
```json
{
  "batchItemFailures": [
    {
      "itemIdentifier": "msg-123"
    }
  ]
}
```
Failed messages return to SQS for retry.

## Error Handling

### File Size Validation Failure
```
Validation Failed: File uploads/loan-123/large-doc.pdf exceeds 50MB limit (60.5MB). Rejecting.
```
- File rejected (not processed)
- Error logged to CloudWatch
- No workflow initiated
- SQS message deleted (not retried)

### Unsupported File Format
```
Unsupported file format: uploads/loan-123/document.docx. Supported formats: .pdf, .jpeg, .jpg, .png, .tiff, .tif
```
- File rejected (not processed)
- Warning logged to CloudWatch
- No workflow initiated
- SQS message deleted (not retried)

### Step Functions Failure
```
Error processing S3 record for key uploads/loan-123/doc.pdf: Step Functions error
```
- Error logged to CloudWatch
- SQS message marked as failed
- Message returns to queue for retry
- Retry with exponential backoff

### S3 Test Event
```
Received S3 Test Event. Skipping.
```
- Test event ignored
- No processing performed
- SQS message deleted

## Testing

### Unit Tests
Run unit tests:
```bash
cd backend
python3 -m pytest tests/test_trigger.py -v
```

Test coverage:
- File format validation (supported/unsupported)
- File size validation (within/exceeds limit)
- Document metadata extraction
- Workflow initiation
- Lambda handler event processing
- Batch failure handling
- Concurrency control

### Integration Tests
Test with real S3 upload:
```bash
# Upload test document
aws s3 cp test-document.pdf s3://auditflow-documents-prod-{ACCOUNT_ID}/uploads/test-loan-123/

# Monitor Lambda logs
aws logs tail /aws/lambda/AuditFlow-Trigger --follow

# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:ap-south-1:{ACCOUNT_ID}:stateMachine:AuditFlowDocumentProcessing
```

### Load Testing
Test concurrent processing:
```bash
# Upload 20 documents simultaneously
for i in {1..20}; do
  aws s3 cp test-doc-$i.pdf s3://auditflow-documents-prod-{ACCOUNT_ID}/uploads/load-test/ &
done

# Monitor SQS queue depth
aws sqs get-queue-attributes \
  --queue-url https://sqs.ap-south-1.amazonaws.com/{ACCOUNT_ID}/AuditFlow-DocumentProcessingQueue \
  --attribute-names ApproximateNumberOfMessages
```

Expected behavior:
- First 10 documents processed immediately (concurrent limit)
- Remaining 10 queued in SQS
- All documents processed in order
- No errors or throttling

## Monitoring

### CloudWatch Metrics
- **Invocations**: Number of Lambda invocations
- **Duration**: Execution time per invocation
- **Errors**: Failed invocations
- **Throttles**: Throttled invocations (should be 0)
- **ConcurrentExecutions**: Active Lambda instances (max 10)

### CloudWatch Logs
Log group: `/aws/lambda/AuditFlow-Trigger`

Key log messages:
```
Received event with 10 SQS records.
Processing document: uploads/loan-123/doc.pdf (size: 1024000 bytes, loan: loan-123)
Successfully started workflow loan-123-doc-abc12345. Execution ARN: arn:aws:states:...
Batch processing complete. Processed: 10, Failed: 0
```

### SQS Metrics
- **ApproximateNumberOfMessages**: Messages waiting in queue
- **ApproximateAgeOfOldestMessage**: Age of oldest message
- **NumberOfMessagesReceived**: Messages received by Lambda
- **NumberOfMessagesDeleted**: Successfully processed messages

## Troubleshooting

### Issue: Lambda not triggered on S3 upload
**Possible causes**:
1. S3 event notification not configured
2. File uploaded to wrong prefix (not `uploads/`)
3. Unsupported file format
4. SQS queue policy incorrect

**Solution**:
```bash
# Verify S3 event notification
aws s3api get-bucket-notification-configuration \
  --bucket auditflow-documents-prod-{ACCOUNT_ID}

# Verify SQS queue policy
aws sqs get-queue-attributes \
  --queue-url https://sqs.ap-south-1.amazonaws.com/{ACCOUNT_ID}/AuditFlow-DocumentProcessingQueue \
  --attribute-names Policy

# Re-run setup script
bash infrastructure/s3_event_trigger_setup.sh
```

### Issue: Step Functions not starting
**Possible causes**:
1. STATE_MACHINE_ARN environment variable not set
2. IAM permissions missing
3. State machine doesn't exist

**Solution**:
```bash
# Verify environment variable
aws lambda get-function-configuration \
  --function-name AuditFlow-Trigger \
  --query 'Environment.Variables.STATE_MACHINE_ARN'

# Verify IAM permissions
aws iam get-role-policy \
  --role-name AuditFlowLambdaExecutionRole \
  --policy-name AuditFlowTriggerLambdaPolicy

# Deploy Step Functions
bash infrastructure/step_functions_deploy.sh
```

### Issue: Messages stuck in SQS queue
**Possible causes**:
1. Lambda function failing repeatedly
2. Visibility timeout too short
3. Concurrency limit reached

**Solution**:
```bash
# Check Lambda errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-Trigger \
  --filter-pattern "ERROR"

# Check concurrent executions
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=AuditFlow-Trigger \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum

# Increase visibility timeout if needed
aws sqs set-queue-attributes \
  --queue-url https://sqs.ap-south-1.amazonaws.com/{ACCOUNT_ID}/AuditFlow-DocumentProcessingQueue \
  --attributes VisibilityTimeout=600
```

## Performance

### Latency
- **S3 to SQS**: < 1 second
- **SQS to Lambda**: < 5 seconds (Requirement 10.2)
- **Lambda execution**: 100-500ms per document
- **Total (upload to workflow start)**: < 10 seconds

### Throughput
- **Concurrent executions**: 10
- **Batch size**: 10 documents
- **Processing rate**: ~100 documents/minute
- **Queue capacity**: Unlimited (SQS)

### Scalability
- Automatically scales with upload volume
- SQS buffers excess load
- No manual intervention required
- Cost-effective (pay per use)

## Cost Optimization

### Lambda Costs
- **Invocations**: $0.20 per 1M requests
- **Duration**: $0.0000166667 per GB-second
- **Typical cost**: ~$0.001 per 1000 documents

### SQS Costs
- **Requests**: $0.40 per 1M requests
- **Data transfer**: Free (same region)
- **Typical cost**: ~$0.0004 per 1000 documents

### S3 Event Notifications
- Free (no additional charge)

## Security

### Encryption
- **In transit**: TLS 1.2+ for all AWS API calls
- **At rest**: S3 server-side encryption with KMS
- **SQS**: Server-side encryption enabled

### Access Control
- **Least privilege**: IAM role with minimal permissions
- **Resource-based policies**: S3 bucket policy, SQS queue policy
- **No public access**: All resources private

### Logging
- **CloudWatch Logs**: All invocations logged
- **PII redaction**: Sensitive data masked in logs
- **Audit trail**: Complete event history

## Compliance

### Requirements Satisfied
- ✅ 10.1: Event trigger on S3 upload
- ✅ 10.2: Lambda invoked within 5 seconds
- ✅ 10.3: Lambda initiates workflow
- ✅ 10.4: Documents processed in order
- ✅ 10.5: Up to 10 concurrent executions
- ✅ 1.3: Support PDF, JPEG, PNG, TIFF formats
- ✅ 1.4: Reject files > 50MB
- ✅ 19.6: Queue excess requests
- ✅ 20.2: Integration tests

## References

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html)
- [SQS Integration with Lambda](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [Step Functions Integration](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-invoke-sfn.html)

