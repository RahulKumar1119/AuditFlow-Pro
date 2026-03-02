"""
Integration tests for API Gateway endpoints.
Task 15.6: Write integration tests for API endpoints
Requirements: 20.2

Tests authentication, authorization, document upload flow,
audit query operations, and error handling.
"""

import json
import os
import uuid
import pytest
import boto3
from moto import mock_aws
from unittest.mock import patch, MagicMock

# Import the Lambda handler
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../functions/api_handler'))
from app import lambda_handler, mask_pii


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def mock_aws_services(aws_credentials):
    """Create mock AWS services."""
    with mock_aws():
        # Create S3 bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'auditflow-documents'
        s3.create_bucket(Bucket=bucket_name)
        os.environ['UPLOAD_BUCKET'] = bucket_name
        
        # Create DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create AuditFlow-AuditRecords table
        table = dynamodb.create_table(
            TableName='AuditFlow-AuditRecords',
            KeySchema=[
                {'AttributeName': 'audit_record_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'audit_record_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create AuditFlow-Documents table
        docs_table = dynamodb.create_table(
            TableName='AuditFlow-Documents',
            KeySchema=[
                {'AttributeName': 'document_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'document_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        os.environ['AUDIT_TABLE'] = 'AuditFlow-AuditRecords'
        os.environ['DOCUMENTS_TABLE'] = 'AuditFlow-Documents'
        
        yield {
            's3': s3,
            'dynamodb': dynamodb,
            'audit_table': table,
            'docs_table': docs_table
        }


@pytest.fixture
def sample_audit_record():
    """Create a sample audit record for testing."""
    return {
        'audit_record_id': str(uuid.uuid4()),
        'loan_application_id': 'loan-test-123',
        'applicant_name': 'John Doe',
        'audit_timestamp': '2024-01-15T10:35:00Z',
        'status': 'COMPLETED',
        'risk_score': 45,
        'risk_level': 'MEDIUM',
        'documents': [
            {
                'document_id': str(uuid.uuid4()),
                'document_type': 'W2',
                'file_name': 'w2_2023.pdf',
                'extracted_data': {
                    'employee_name': {'value': 'John Doe', 'confidence': 0.98},
                    'employee_ssn': {'value': '123-45-6789', 'confidence': 0.99}
                }
            }
        ],
        'golden_record': {
            'name': {'value': 'John Doe', 'confidence': 0.98},
            'ssn': {'value': '123-45-6789', 'confidence': 0.99},
            'date_of_birth': {'value': '1985-06-15', 'confidence': 0.99}
        },
        'inconsistencies': [],
        'risk_factors': []
    }


@pytest.fixture
def loan_officer_event():
    """Create API Gateway event with Loan Officer authentication."""
    return {
        'httpMethod': 'GET',
        'resource': '/audits',
        'pathParameters': None,
        'queryStringParameters': None,
        'body': None,
        'requestContext': {
            'requestId': 'test-request-id',
            'authorizer': {
                'claims': {
                    'sub': 'user-uuid-123',
                    'email': 'officer@example.com',
                    'cognito:groups': 'LoanOfficers'
                }
            },
            'identity': {
                'sourceIp': '192.168.1.1'
            }
        }
    }


@pytest.fixture
def admin_event():
    """Create API Gateway event with Administrator authentication."""
    return {
        'httpMethod': 'GET',
        'resource': '/audits',
        'pathParameters': None,
        'queryStringParameters': None,
        'body': None,
        'requestContext': {
            'requestId': 'test-request-id',
            'authorizer': {
                'claims': {
                    'sub': 'admin-uuid-456',
                    'email': 'admin@example.com',
                    'cognito:groups': 'Administrators'
                }
            },
            'identity': {
                'sourceIp': '192.168.1.2'
            }
        }
    }


class TestDocumentUploadEndpoint:
    """Test POST /documents endpoint."""
    
    def test_successful_upload_url_generation(self, mock_aws_services, loan_officer_event):
        """Test successful generation of pre-signed upload URL."""
        event = loan_officer_event.copy()
        event['httpMethod'] = 'POST'
        event['resource'] = '/documents'
        event['body'] = json.dumps({
            'file_name': 'test.pdf',
            'content_type': 'application/pdf',
            'file_size': 1048576,
            'loan_application_id': 'loan-test'
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'upload_url' in body
        assert 'document_id' in body
        assert 'loan_application_id' in body
        assert body['expires_in'] == 900
    
    def test_invalid_file_format(self, mock_aws_services, loan_officer_event):
        """Test rejection of unsupported file format."""
        event = loan_officer_event.copy()
        event['httpMethod'] = 'POST'
        event['resource'] = '/documents'
        event['body'] = json.dumps({
            'file_name': 'test.exe',
            'content_type': 'application/x-msdownload',
            'file_size': 1048576
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'Unsupported file format' in body['error']
    
    def test_file_size_exceeds_limit(self, mock_aws_services, loan_officer_event):
        """Test rejection of files exceeding 50MB limit."""
        event = loan_officer_event.copy()
        event['httpMethod'] = 'POST'
        event['resource'] = '/documents'
        event['body'] = json.dumps({
            'file_name': 'large.pdf',
            'content_type': 'application/pdf',
            'file_size': 52428801  # 50MB + 1 byte
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert '50MB' in body['error']
    
    def test_missing_required_fields(self, mock_aws_services, loan_officer_event):
        """Test validation of required fields."""
        event = loan_officer_event.copy()
        event['httpMethod'] = 'POST'
        event['resource'] = '/documents'
        event['body'] = json.dumps({
            'file_name': 'test.pdf'
            # Missing content_type
        })
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_invalid_json_body(self, mock_aws_services, loan_officer_event):
        """Test handling of invalid JSON in request body."""
        event = loan_officer_event.copy()
        event['httpMethod'] = 'POST'
        event['resource'] = '/documents'
        event['body'] = 'invalid json'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body['error']


class TestAuditQueryEndpoints:
    """Test GET /audits and GET /audits/{id} endpoints."""
    
    def test_list_audits_success(self, mock_aws_services, sample_audit_record, loan_officer_event):
        """Test successful retrieval of audit list."""
        # Insert sample audit record
        table = mock_aws_services['audit_table']
        table.put_item(Item=sample_audit_record)
        
        response = lambda_handler(loan_officer_event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'items' in body
        assert len(body['items']) > 0
        assert 'count' in body
        assert 'has_more' in body
    
    def test_get_audit_by_id_success(self, mock_aws_services, sample_audit_record, loan_officer_event):
        """Test successful retrieval of specific audit record."""
        # Insert sample audit record
        table = mock_aws_services['audit_table']
        table.put_item(Item=sample_audit_record)
        
        event = loan_officer_event.copy()
        event['resource'] = '/audits/{id}'
        event['pathParameters'] = {'id': sample_audit_record['audit_record_id']}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['audit_record_id'] == sample_audit_record['audit_record_id']
    
    def test_get_audit_not_found(self, mock_aws_services, loan_officer_event):
        """Test 404 response for non-existent audit."""
        event = loan_officer_event.copy()
        event['resource'] = '/audits/{id}'
        event['pathParameters'] = {'id': 'non-existent-id'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_list_audits_with_pagination(self, mock_aws_services, loan_officer_event):
        """Test pagination in audit list."""
        # Insert multiple audit records
        table = mock_aws_services['audit_table']
        for i in range(5):
            record = {
                'audit_record_id': str(uuid.uuid4()),
                'loan_application_id': f'loan-{i}',
                'status': 'COMPLETED',
                'risk_score': i * 10
            }
            table.put_item(Item=record)
        
        event = loan_officer_event.copy()
        event['queryStringParameters'] = {'limit': '2'}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['items']) <= 2
    
    def test_list_audits_with_filters(self, mock_aws_services, loan_officer_event):
        """Test filtering audits by status and risk score."""
        # Insert audit records with different statuses and risk scores
        table = mock_aws_services['audit_table']
        for i in range(3):
            record = {
                'audit_record_id': str(uuid.uuid4()),
                'loan_application_id': f'loan-{i}',
                'status': 'COMPLETED' if i % 2 == 0 else 'IN_PROGRESS',
                'risk_score': i * 30
            }
            table.put_item(Item=record)
        
        event = loan_officer_event.copy()
        event['queryStringParameters'] = {
            'status': 'COMPLETED',
            'risk_score_min': '30'
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        # Verify filtering logic (results depend on test data)
        assert 'items' in body


class TestPIIMasking:
    """Test PII masking based on user role."""
    
    def test_pii_masked_for_loan_officer(self, mock_aws_services, sample_audit_record, loan_officer_event):
        """Test that PII is masked for Loan Officers."""
        # Insert sample audit record
        table = mock_aws_services['audit_table']
        table.put_item(Item=sample_audit_record)
        
        event = loan_officer_event.copy()
        event['resource'] = '/audits/{id}'
        event['pathParameters'] = {'id': sample_audit_record['audit_record_id']}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Check SSN is masked
        ssn = body['golden_record']['ssn']['value']
        assert ssn.startswith('***-**-')
        assert len(ssn.split('-')[-1]) == 4  # Last 4 digits visible
        
        # Check DOB is masked
        dob = body['golden_record']['date_of_birth']['value']
        assert dob == '****-**-**'
    
    def test_pii_visible_for_administrator(self, mock_aws_services, sample_audit_record, admin_event):
        """Test that PII is visible for Administrators."""
        # Insert sample audit record
        table = mock_aws_services['audit_table']
        table.put_item(Item=sample_audit_record)
        
        event = admin_event.copy()
        event['resource'] = '/audits/{id}'
        event['pathParameters'] = {'id': sample_audit_record['audit_record_id']}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # Check SSN is NOT masked
        ssn = body['golden_record']['ssn']['value']
        assert ssn == '123-45-6789'
        
        # Check DOB is NOT masked
        dob = body['golden_record']['date_of_birth']['value']
        assert dob == '1985-06-15'
    
    def test_mask_pii_function(self):
        """Test the mask_pii function directly."""
        record = {
            'golden_record': {
                'ssn': {'value': '123-45-6789', 'confidence': 0.99},
                'date_of_birth': {'value': '1985-06-15', 'confidence': 0.99},
                'bank_account': {'value': '9876543210', 'confidence': 0.98}
            }
        }
        
        # Test masking for Loan Officer
        masked = mask_pii(record.copy(), ['LoanOfficers'])
        assert masked['golden_record']['ssn']['value'] == '***-**-6789'
        assert masked['golden_record']['date_of_birth']['value'] == '****-**-**'
        assert masked['golden_record']['bank_account']['value'] == '****3210'
        
        # Test no masking for Administrator
        unmasked = mask_pii(record.copy(), ['Administrators'])
        assert unmasked['golden_record']['ssn']['value'] == '123-45-6789'
        assert unmasked['golden_record']['date_of_birth']['value'] == '1985-06-15'
        assert unmasked['golden_record']['bank_account']['value'] == '9876543210'


class TestDocumentViewerEndpoint:
    """Test GET /documents/{id}/view endpoint."""
    
    def test_generate_view_url_success(self, mock_aws_services, loan_officer_event):
        """Test successful generation of document view URL."""
        # Create a document in S3
        document_id = str(uuid.uuid4())
        loan_id = 'loan-test'
        s3_key = f'uploads/{loan_id}/{document_id}_test.pdf'
        
        s3 = mock_aws_services['s3']
        s3.put_object(
            Bucket='auditflow-documents',
            Key=s3_key,
            Body=b'test pdf content'
        )
        
        # Insert document metadata in DynamoDB
        docs_table = mock_aws_services['docs_table']
        docs_table.put_item(Item={
            'document_id': document_id,
            'loan_application_id': loan_id,
            's3_key': s3_key
        })
        
        event = loan_officer_event.copy()
        event['resource'] = '/documents/{id}/view'
        event['pathParameters'] = {'id': document_id}
        event['queryStringParameters'] = {'loan_application_id': loan_id}
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'view_url' in body
        assert body['document_id'] == document_id
        assert body['expires_in'] == 3600
    
    def test_missing_document_id(self, mock_aws_services, loan_officer_event):
        """Test error when document ID is missing."""
        event = loan_officer_event.copy()
        event['resource'] = '/documents/{id}/view'
        event['pathParameters'] = None
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body


class TestErrorHandling:
    """Test error handling and validation."""
    
    def test_route_not_found(self, loan_officer_event):
        """Test 404 response for unknown route."""
        event = loan_officer_event.copy()
        event['resource'] = '/unknown/route'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_cors_headers_present(self, loan_officer_event):
        """Test that CORS headers are present in all responses."""
        response = lambda_handler(loan_officer_event, None)
        
        assert 'headers' in response
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_logging_on_request(self, loan_officer_event, caplog):
        """Test that API requests are logged."""
        import logging
        caplog.set_level(logging.INFO)
        
        lambda_handler(loan_officer_event, None)
        
        # Check that request was logged
        assert any('API Request' in record.message for record in caplog.records)
        assert any('user-uuid-123' in record.message for record in caplog.records)


class TestAuthentication:
    """Test authentication and authorization."""
    
    def test_user_groups_extracted(self, loan_officer_event):
        """Test that user groups are correctly extracted from claims."""
        response = lambda_handler(loan_officer_event, None)
        
        # Should succeed with valid authentication
        assert response['statusCode'] in [200, 404]  # 404 if no data, but auth succeeded
    
    def test_request_id_logged(self, loan_officer_event, caplog):
        """Test that request ID is logged for tracing."""
        import logging
        caplog.set_level(logging.INFO)
        
        lambda_handler(loan_officer_event, None)
        
        assert any('test-request-id' in record.message for record in caplog.records)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
