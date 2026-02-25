import pytest
from unittest.mock import patch, MagicMock
from functions.classifier.app import lambda_handler, classify_document

@pytest.fixture
def mock_step_function_event():
    return {
        "document_id": "doc-123",
        "loan_application_id": "loan-456",
        "s3_bucket": "auditflow-documents-prod",
        "s3_key": "uploads/user-1/w2_form.pdf",
        "file_size_bytes": 1024,
        "checksum": "abc123hash"
    }

def test_classify_document_w2():
    """Test classification logic for W2 forms."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "Form W-2"},
        {"BlockType": "LINE", "Text": "Wage and Tax Statement"},
        {"BlockType": "LINE", "Text": "2023"}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "W2"
    assert confidence == 0.95

def test_classify_document_bank_statement():
    """Test classification logic for Bank Statements."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "STATEMENT OF ACCOUNT"},
        {"BlockType": "LINE", "Text": "ENDING BALANCE: $5,000.00"},
        {"BlockType": "LINE", "Text": "TOTAL DEPOSITS"},
        {"BlockType": "LINE", "Text": "TOTAL WITHDRAWALS"}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "BANK_STATEMENT"
    assert confidence == 0.90

def test_classify_document_unknown_triggers_manual_review():
    """Test that unrecognized documents receive low confidence and flag for review."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "Just a random letter to the bank."},
        {"BlockType": "LINE", "Text": "Please approve my loan."}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "UNKNOWN"
    assert confidence < 0.70

@patch('functions.classifier.app.textract')
def test_lambda_handler_success(mock_textract, mock_step_function_event):
    """Test the full Lambda handler execution flow."""
    # Mock the Textract response
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {"BlockType": "LINE", "Text": "Form 1040"},
            {"BlockType": "LINE", "Text": "U.S. Individual Income Tax Return"}
        ]
    }
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Assertions
    assert result["document_id"] == "doc-123"
    assert result["document_type"] == "TAX_FORM"
    assert result["confidence"] == 0.95
    assert result["requires_manual_review"] is False
    assert "metadata" in result
