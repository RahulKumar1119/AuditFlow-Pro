# Step Functions Workflow Orchestration

This directory contains the AWS Step Functions state machine definition for orchestrating the AuditFlow-Pro document processing workflow.

## Overview

The Step Functions state machine coordinates the execution of Lambda functions in the following sequence:

1. **ProcessAllDocuments** (Map State) - Parallel processing of all documents
   - **ClassifyDocument** - Identify document type using AWS Textract
   - **CheckClassificationConfidence** - Verify classification confidence
   - **ExtractData** - Extract structured data from documents
   - **HandleDocumentError** - Catch individual document failures

2. **CheckAllDocumentsProcessed** - Aggregation point for all documents

3. **ValidateDocuments** - Cross-document validation and inconsistency detection

4. **CalculateRiskScore** - Calculate risk score based on inconsistencies

5. **GenerateReport** - Compile audit record and store in DynamoDB

## State Machine Features

### Parallel Processing
- Uses Map state to process multiple documents concurrently
- MaxConcurrency set to 10 to limit parallel executions
- Each document is classified and extracted independently

### Retry Policies
All Lambda invocations are configured with retry policies:
- **Max Attempts**: 3
- **Backoff Rate**: 3.0 (exponential)
- **Intervals**: 5s, 15s, 45s
- **Retry on**: TaskFailed, Timeout, Lambda service exceptions

### Error Handling
- Individual document failures are caught and don't stop the workflow
- Failed documents are marked with `extraction_status: "FAILED"`
- Global workflow errors are caught and logged
- Workflow fails gracefully with descriptive error messages

### CloudWatch Logging
- Log level: ALL
- Includes execution data for debugging
- Logs all state transitions
- 1-year retention policy

### State Resumption
- Step Functions automatically persists state
- Workflows can resume from last successful state after interruption
- Execution history is maintained for audit trails

## Deployment

### Prerequisites
1. All Lambda functions must be deployed:
   - AuditFlow-Classifier
   - AuditFlow-Extractor
   - AuditFlow-Validator
   - AuditFlow-RiskScorer
   - AuditFlow-Reporter

2. IAM permissions to create Step Functions state machines

### Deploy State Machine

```bash
cd auditflow-pro
bash infrastructure/step_functions_deploy.sh
```

This script will:
1. Retrieve Lambda function ARNs
2. Create IAM execution role for Step Functions
3. Create CloudWatch Log Group
4. Deploy or update the state machine
5. Configure logging

### Manual Deployment

If you prefer to deploy manually:

```bash
# Get Lambda ARNs
CLASSIFIER_ARN=$(aws lambda get-function --function-name AuditFlow-Classifier --query 'Configuration.FunctionArn' --output text)
EXTRACTOR_ARN=$(aws lambda get-function --function-name AuditFlow-Extractor --query 'Configuration.FunctionArn' --output text)
VALIDATOR_ARN=$(aws lambda get-function --function-name AuditFlow-Validator --query 'Configuration.FunctionArn' --output text)
RISK_SCORER_ARN=$(aws lambda get-function --function-name AuditFlow-RiskScorer --query 'Configuration.FunctionArn' --output text)
REPORTER_ARN=$(aws lambda get-function --function-name AuditFlow-Reporter --query 'Configuration.FunctionArn' --output text)

# Substitute ARNs in state machine definition
sed -e "s|\${ClassifierFunctionArn}|$CLASSIFIER_ARN|g" \
    -e "s|\${ExtractorFunctionArn}|$EXTRACTOR_ARN|g" \
    -e "s|\${ValidatorFunctionArn}|$VALIDATOR_ARN|g" \
    -e "s|\${RiskScorerFunctionArn}|$RISK_SCORER_ARN|g" \
    -e "s|\${ReporterFunctionArn}|$REPORTER_ARN|g" \
    backend/step_functions/state_machine.asl.json > /tmp/state_machine.json

# Create state machine
aws stepfunctions create-state-machine \
    --name AuditFlowDocumentProcessing \
    --definition file:///tmp/state_machine.json \
    --role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/AuditFlowStepFunctionsRole
```

## Testing

### Run Integration Tests

```bash
cd auditflow-pro/backend
pytest tests/integration/test_step_functions_workflow.py -v -s
```

### Manual Test Execution

Start a test execution:

```bash
aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:ap-south-1:YOUR_ACCOUNT_ID:stateMachine:AuditFlowDocumentProcessing \
    --name test-execution-$(date +%s) \
    --input '{
        "loan_application_id": "test-loan-123",
        "documents": [
            {
                "document_id": "doc-1",
                "s3_bucket": "auditflow-documents-prod-YOUR_ACCOUNT_ID",
                "s3_key": "test/sample-w2.pdf"
            },
            {
                "document_id": "doc-2",
                "s3_bucket": "auditflow-documents-prod-YOUR_ACCOUNT_ID",
                "s3_key": "test/sample-bank-statement.pdf"
            }
        ]
    }'
```

Check execution status:

```bash
aws stepfunctions describe-execution \
    --execution-arn arn:aws:states:ap-south-1:YOUR_ACCOUNT_ID:execution:AuditFlowDocumentProcessing:test-execution-123
```

View execution history:

```bash
aws stepfunctions get-execution-history \
    --execution-arn arn:aws:states:ap-south-1:YOUR_ACCOUNT_ID:execution:AuditFlowDocumentProcessing:test-execution-123 \
    --max-results 100
```

## Input Format

The state machine expects input in the following format:

```json
{
    "loan_application_id": "string (UUID)",
    "documents": [
        {
            "document_id": "string (UUID)",
            "s3_bucket": "string (bucket name)",
            "s3_key": "string (object key)"
        }
    ]
}
```

## Output Format

Successful execution produces output in this format:

```json
{
    "loan_application_id": "string",
    "processed_documents": [
        {
            "document_id": "string",
            "document_type": "W2|BANK_STATEMENT|TAX_FORM|DRIVERS_LICENSE|ID_DOCUMENT",
            "extraction_status": "COMPLETED|FAILED|SKIPPED_NEEDS_REVIEW"
        }
    ],
    "validation_results": {
        "inconsistencies": [...],
        "golden_record": {...},
        "documents": [...]
    },
    "risk_results": {
        "risk_assessment": {
            "risk_score": 0-100,
            "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
            "contributing_factors": [...]
        }
    }
}
```

## Monitoring

### CloudWatch Logs

View state machine logs:

```bash
aws logs tail /aws/vendedlogs/states/AuditFlowDocumentProcessing --follow
```

### CloudWatch Metrics

Key metrics to monitor:
- `ExecutionsFailed` - Number of failed executions
- `ExecutionsSucceeded` - Number of successful executions
- `ExecutionTime` - Duration of executions
- `ExecutionsTimedOut` - Number of timed out executions

### Alarms

Set up CloudWatch alarms for:
- High failure rate (> 5% over 5 minutes)
- Long execution times (> 5 minutes)
- Execution timeouts

## Troubleshooting

### Execution Failed

1. Check execution history for error details:
   ```bash
   aws stepfunctions get-execution-history --execution-arn YOUR_EXECUTION_ARN
   ```

2. Look for `TaskFailed` or `ExecutionFailed` events

3. Check Lambda function logs for the failed step

### Execution Timed Out

1. Check if Lambda functions are timing out
2. Verify Lambda timeout settings (should be < 5 minutes)
3. Check for large documents causing slow processing

### Retry Exhausted

1. Check Lambda function errors in CloudWatch Logs
2. Verify IAM permissions for Lambda functions
3. Check if AWS service quotas are exceeded

### Document Processing Stuck

1. Check Map state iterations in execution history
2. Verify all documents have valid S3 keys
3. Check Lambda concurrency limits

## Performance Optimization

### Concurrent Processing
- Adjust `MaxConcurrency` in Map state based on Lambda concurrency limits
- Default is 10, can be increased up to 100 for high-volume processing

### Timeout Configuration
- State machine timeout: 1 hour (default)
- Lambda function timeouts: 5 minutes (recommended)
- Adjust based on document size and complexity

### Cost Optimization
- Use Standard workflow for long-running processes
- Consider Express workflow for high-volume, short-duration executions
- Monitor state transitions to optimize workflow design

## Security

### IAM Permissions
The Step Functions execution role requires:
- `lambda:InvokeFunction` on all Lambda functions
- `logs:CreateLogDelivery` and related permissions for CloudWatch Logs

### Encryption
- State machine input/output is encrypted at rest
- CloudWatch Logs are encrypted with AWS managed keys
- Consider using customer-managed KMS keys for additional security

### Audit Trail
- All state transitions are logged to CloudWatch
- Execution history is retained for 90 days
- Enable AWS CloudTrail for API call auditing

## References

- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [Amazon States Language Specification](https://states-language.net/spec.html)
- [Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/bp-express.html)
- [Error Handling in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)
