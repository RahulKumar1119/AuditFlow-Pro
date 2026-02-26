# backend/tests/integration/test_trigger.py

import os
import json
import pytest
import boto3
from moto import mock_aws
from functions.trigger.app import lambda_handler

@pytest.fixture
def mock_aws_env():
    """Set up mocked AWS environment."""
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['STATE_MACHINE_ARN'] = 'arn:aws:states:us-east-1:123456789012:stateMachine:MockMachine'
    
    with mock_aws():
        # Mock Step Functions client
        sfn = boto3.client('stepfunctions', region_name='us-east-1')
        
        # We need to create a dummy state machine so start_execution doesn't fail
        role_arn = 'arn:aws:iam::123456789012:role/DummyRole'
        response = sfn.create_state_machine(
            name='MockMachine',
            definition=json.dumps({"StartAt": "Pass", "States": {"Pass": {"Type": "Pass", "End": True}}}),
            roleArn=role_arn
        )
        os.environ['STATE_MACHINE_ARN'] = response['stateMachineArn']
        
        yield sfn

class MockContext:
    def __init__(self):
        self.aws_request_id = "test-request-id-12345"

def generate_sqs_s3_event(bucket: str, key: str, size: int):
    """Helper to generate a mock SQS message containing an S3 event."""
    s3_event = {
        "Records": [{
            "eventTime": "2026-02-26T12:00:00.000Z",
            "s3": {
                "bucket": {"name": bucket},
                "object": {"key": key, "size": size}
            }
        }]
    }
    return {
        "Records": [{
            "body": json.dumps(s3_event)
        }]
    }

def test_lambda_handler_success(mock_aws_env):
    """Task 13.4: Test successful parsing and workflow initiation."""
    sfn_client = mock_aws_env
    
    # 1MB file (Valid)
    event = generate_sqs_s3_event("auditflow-uploads", "uploads/loan-abc/w2.pdf", 1024 * 1024)
    
    response = lambda_handler(event, MockContext())
    assert response["statusCode"] == 200
    
    # Verify Step Function was triggered
    executions = sfn_client.list_executions(stateMachineArn=os.environ['STATE_MACHINE_ARN'])
    assert len(executions['executions']) == 1
    
    # Verify execution name format (loan_id + doc_id)
    exec_name = executions['executions'][0]['name']
    assert "loan-abc" in exec_name

def test_lambda_handler_rejects_large_files(mock_aws_env, caplog):
    """Task 13.4: Test validation of file size > 50MB."""
    sfn_client = mock_aws_env
    
    # 60MB file (Invalid)
    event = generate_sqs_s3_event("auditflow-uploads", "uploads/loan-xyz/huge.pdf", 60 * 1024 * 1024)
    
    response = lambda_handler(event, MockContext())
    assert response["statusCode"] == 200 # The batch succeeds (we just skipped the bad file)
    
    # Verify Step Function was NOT triggered
    executions = sfn_client.list_executions(stateMachineArn=os.environ['STATE_MACHINE_ARN'])
    assert len(executions['executions']) == 0
    
    # Verify the error was logged
    assert "exceeds 50MB limit" in caplog.text
