# backend/tests/integration/test_api.py

import json
import pytest
from functions.api_handler.app import lambda_handler

def generate_api_event(resource, method, body=None, path_params=None, query_params=None, groups="LoanOfficer"):
    return {
        "resource": resource,
        "httpMethod": method,
        "body": json.dumps(body) if body else None,
        "pathParameters": path_params,
        "queryStringParameters": query_params,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user-123",
                    "cognito:groups": groups
                }
            }
        }
    }

def test_post_documents_success():
    """Test document upload flow and presigned URL generation (Task 15.6)."""
    event = generate_api_event(
        resource="/documents",
        method="POST",
        body={"file_name": "w2.pdf", "content_type": "application/pdf"}
    )
    
    response = lambda_handler(event, None)
    assert response["statusCode"] == 200
    
    body = json.loads(response["body"])
    assert "upload_url_data" in body
    assert "document_id" in body

def test_post_documents_invalid_type():
    """Test error handling for invalid file types (Task 15.6)."""
    event = generate_api_event(
        resource="/documents",
        method="POST",
        body={"file_name": "malicious.exe", "content_type": "application/x-msdownload"}
    )
    
    response = lambda_handler(event, None)
    assert response["statusCode"] == 400
    assert "Unsupported file format" in response["body"]

def test_get_document_view():
    """Test generating a view URL (Task 15.6)."""
    event = generate_api_event(
        resource="/documents/{id}/view",
        method="GET",
        path_params={"id": "doc-456"},
        query_params={"loan_application_id": "loan-789"}
    )
    
    response = lambda_handler(event, None)
    assert response["statusCode"] == 200
    assert "view_url" in json.loads(response["body"])

def test_pii_masking_for_loan_officers(mocker):
    """Test that SSN is masked for non-admins but visible for admins (Task 15.6)."""
    # Mock DynamoDB response
    mock_item = {"audit_record_id": "1", "golden_record": {"ssn": {"value": "123-45-6789"}}}
    
    mocker.patch('boto3.resource') # Mock boto3 resource completely for unit testing logic
    mocker.patch('functions.api_handler.app.dynamodb.Table.get_item', return_value={'Item': mock_item})
    
    # 1. Test Loan Officer (Should be masked)
    event_lo = generate_api_event("/audits/{id}", "GET", path_params={"id": "1"}, groups="LoanOfficer")
    resp_lo = lambda_handler(event_lo, None)
    assert "***-**-****" in resp_lo["body"]
    assert "123-45-6789" not in resp_lo["body"]
    
    # 2. Test Administrator (Should NOT be masked)
    event_admin = generate_api_event("/audits/{id}", "GET", path_params={"id": "1"}, groups="Administrator")
    resp_admin = lambda_handler(event_admin, None)
    assert "123-45-6789" in resp_admin["body"]
