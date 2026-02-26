# backend/tests/test_reporter.py

import os
import pytest
import boto3
from moto import mock_aws
from functions.reporter.app import lambda_handler, save_audit_record, trigger_alerts

# Set environment variables for testing
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AUDIT_RECORDS_TABLE'] = 'AuditFlow-AuditRecords-Test'
os.environ['DOCUMENTS_TABLE'] = 'AuditFlow-Documents-Test'

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'

@pytest.fixture
def mock_infrastructure(aws_credentials):
    """Set up mocked DynamoDB tables and SNS topic."""
    with mock_aws():
        # 1. Setup DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        audit_table = dynamodb.create_table(
            TableName=os.environ['AUDIT_RECORDS_TABLE'],
            KeySchema=[{'AttributeName': 'audit_record_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'audit_record_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        doc_table = dynamodb.create_table(
            TableName=os.environ['DOCUMENTS_TABLE'],
            KeySchema=[{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'document_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Populate a mock document so we can test the status update
        doc_table.put_item(Item={'document_id': 'doc-123', 'processing_status': 'PROCESSING'})
        
        # 2. Setup SNS
        sns = boto3.client('sns', region_name='us-east-1')
        topic = sns.create_topic(Name='AuditFlow-Alerts-Test')
        os.environ['ALERTS_TOPIC_ARN'] = topic['TopicArn']
        
        yield dynamodb, sns

@pytest.fixture
def sample_event():
    return {
        "loan_application_id": "loan-999",
        "documents": [{"document_id": "doc-123", "type": "W2"}],
        "inconsistencies": [],
        "golden_record": {
            "first_name": {"value": "Jane"},
            "last_name": {"value": "Doe"}
        },
        "risk_assessment": {
            "risk_score": 85,
            "risk_level": "CRITICAL",
            "risk_factors": [{"description": "High risk test factor"}]
        }
    }

def test_lambda_handler_success(mock_infrastructure, sample_event):
    """Test full audit record compilation and storage (Task 10.1 & 10.2)."""
    dynamodb, sns = mock_infrastructure
    
    # Run the handler
    response = lambda_handler(sample_event, None)
    
    assert response["statusCode"] == 200
    assert response["status"] == "COMPLETED"
    
    # Verify Audit Record was saved to DynamoDB
    audit_table = dynamodb.Table(os.environ['AUDIT_RECORDS_TABLE'])
    audit_response = audit_table.get_item(Key={'audit_record_id': response['audit_record_id']})
    assert 'Item' in audit_response
    assert audit_response['Item']['applicant_name'] == "Jane Doe"
    assert audit_response['Item']['risk_score'] == 85
    assert len(audit_response['Item']['alerts_triggered']) == 1 # Because score is 85
    
    # Verify Document status was updated to COMPLETED
    doc_table = dynamodb.Table(os.environ['DOCUMENTS_TABLE'])
    doc_response = doc_table.get_item(Key={'document_id': 'doc-123'})
    assert doc_response['Item']['processing_status'] == "COMPLETED"

def test_trigger_alerts_thresholds(mock_infrastructure):
    """Test alert triggering logic for different risk scores (Task 10.3)."""
    # Test CRITICAL (> 80)
    critical_record = {"loan_application_id": "loan-1", "risk_score": 85}
    alerts = trigger_alerts(critical_record)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "CRITICAL"
    
    # Test HIGH (> 50)
    high_record = {"loan_application_id": "loan-2", "risk_score": 60}
    alerts = trigger_alerts(high_record)
    assert len(alerts) == 1
    assert alerts[0]["type"] == "HIGH"
    
    # Test NO ALERT (<= 50)
    low_record = {"loan_application_id": "loan-3", "risk_score": 25}
    alerts = trigger_alerts(low_record)
    assert len(alerts) == 0
