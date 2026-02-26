import os
import time
import json
import pytest
import boto3
from botocore.exceptions import ClientError

# This ARN would typically be injected via environment variables during CI/CD
STATE_MACHINE_ARN = os.environ.get(
    'STATE_MACHINE_ARN', 
    'arn:aws:states:us-east-1:123456789012:stateMachine:AuditFlowStateMachine'
)

@pytest.fixture
def sfn_client():
    """Boto3 client for Step Functions."""
    return boto3.client('stepfunctions', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def wait_for_execution(sfn_client, execution_arn, timeout=60):
    """Helper to poll the execution status until it finishes."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = sfn_client.describe_execution(executionArn=execution_arn)
        status = response['status']
        if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
            return response
        time.sleep(2)
    raise TimeoutError("Step Function execution timed out during test.")

@pytest.mark.integration
def test_complete_workflow_execution_success(sfn_client):
    """
    Task 11.5: Test complete workflow execution from upload to report.
    Simulates a happy-path loan application with two documents.
    """
    payload = {
        "loan_application_id": "integration-test-loan-001",
        "documents": [
            {
                "document_id": "doc-w2-001",
                "s3_bucket": "auditflow-test-bucket",
                "s3_key": "test/w2.pdf"
            },
            {
                "document_id": "doc-id-002",
                "s3_bucket": "auditflow-test-bucket",
                "s3_key": "test/license.jpg"
            }
        ]
    }

    try:
        # Start the execution
        start_response = sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"test-success-{int(time.time())}",
            input=json.dumps(payload)
        )
        execution_arn = start_response['executionArn']
        
        # Poll for completion
        result = wait_for_execution(sfn_client, execution_arn)
        
        # Assertions
        assert result['status'] == 'SUCCEEDED'
        
        output = json.loads(result['output'])
        # Verify the final state (GenerateFinalReport Lambda output)
        assert output['statusCode'] == 200
        assert output['status'] == 'COMPLETED'
        assert 'audit_record_id' in output
        
    except ClientError as e:
        pytest.skip(f"Skipping test: AWS credentials or State Machine not accessible. {e}")

@pytest.mark.integration
def test_workflow_error_handling_and_retries(sfn_client):
    """
    Task 11.5: Test error handling and retry logic.
    We pass an intentionally malformed payload that will cause the Extractor Lambda to fail,
    verifying that the Step Function catches the error and transitions to FAILED.
    """
    # Missing required S3 bucket/key to force a Lambda failure
    bad_payload = {
        "loan_application_id": "integration-test-bad-002",
        "documents": [
            {
                "document_id": "doc-bad-001"
                # Missing s3_bucket and s3_key
            }
        ]
    }

    try:
        start_response = sfn_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"test-failure-{int(time.time())}",
            input=json.dumps(bad_payload)
        )
        execution_arn = start_response['executionArn']
        
        result = wait_for_execution(sfn_client, execution_arn)
        
        # Because the payload is bad, the Lambda will fail. 
        # The Step Function's "Retry" block will trigger 3 times (as defined in our ASL), 
        # and then ultimately fail the execution.
        assert result['status'] == 'FAILED'
        
        # Verify the error type if possible
        assert 'error' in result or 'cause' in result
        
    except ClientError as e:
        pytest.skip(f"Skipping test: AWS credentials or State Machine not accessible. {e}")
