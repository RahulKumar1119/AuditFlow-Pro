# backend/tests/test_extractor.py

import pytest
from unittest.mock import patch, MagicMock
from functions.extractor.parsers import (
    detect_and_mask_pii, 
    parse_w2, 
    parse_bank_statement, 
    parse_tax_form_1040, 
    parse_id_document
)
from functions.extractor.app import process_multipage_document, lambda_handler

# --- 1. Tests for PII Detection and Masking ---

@patch('functions.extractor.parsers.comprehend')
def test_pii_detection_and_masking(mock_comprehend):
    """Test that Comprehend successfully masks SSNs and Accounts."""
    # Mock the Comprehend response
    mock_comprehend.detect_pii_entities.return_value = {
        'Entities': [
            {'Type': 'SSN', 'BeginOffset': 15, 'EndOffset': 26, 'Score': 0.99}
        ]
    }
    
    original_text = "My SSN is here 123-45-6789 and it should be hidden."
    masked_text, pii_types = detect_and_mask_pii(original_text)
    
    assert "123-45-6789" not in masked_text
    assert "***-**-6789" in masked_text
    assert "SSN" in pii_types

# --- 2. Tests for Document Parsers ---

def create_mock_kv_blocks(key_text, val_text, val_confidence=95.0):
    """Helper to simulate Textract Key-Value blocks for testing."""
    return [
        {'BlockType': 'KEY_VALUE_SET', 'Id': 'k1', 'EntityTypes': ['KEY'], 'Relationships': [{'Type': 'VALUE', 'Ids': ['v1']}, {'Type': 'CHILD', 'Ids': ['kw1']}]},
        {'BlockType': 'KEY_VALUE_SET', 'Id': 'v1', 'EntityTypes': ['VALUE'], 'Relationships': [{'Type': 'CHILD', 'Ids': ['vw1']}]},
        {'BlockType': 'WORD', 'Id': 'kw1', 'Text': key_text, 'Confidence': 99.0},
        {'BlockType': 'WORD', 'Id': 'vw1', 'Text': val_text, 'Confidence': val_confidence}
    ]

@patch('functions.extractor.parsers.detect_and_mask_pii')
def test_parse_w2(mock_pii):
    """Test W2 extraction logic and confidence tracking."""
    mock_pii.return_value = ("***-**-1234", ["SSN"])
    
    blocks = create_mock_kv_blocks("1 Wages, tips, other comp", "50000.00", 99.0)
    blocks.extend(create_mock_kv_blocks("a Employee's social security number", "999-99-1234", 75.0)) # Low confidence
    
    extracted = parse_w2(blocks)
    
    assert extracted["wages"]["value"] == "50000.00"
    assert extracted["wages"]["requires_manual_review"] is False
    
    assert extracted["employee_ssn"]["value"] == "***-**-1234"
    assert extracted["employee_ssn"]["requires_manual_review"] is True # 75.0 < 80.0

@patch('functions.extractor.parsers.detect_and_mask_pii')
def test_parse_bank_statement(mock_pii):
    """Test Bank Statement extraction and table detection."""
    mock_pii.return_value = ("*******8901", ["BANK_ACCOUNT_NUMBER"])
    
    blocks = create_mock_kv_blocks("Account Number", "12345678901", 95.0)
    # Add a mock table block
    blocks.append({'BlockType': 'TABLE', 'Id': 't1', 'Confidence': 85.0})
    
    extracted = parse_bank_statement(blocks)
    
    assert extracted["account_number"]["value"] == "*******8901"
    assert extracted["transactions_detected"] is True

@patch('functions.extractor.parsers.detect_and_mask_pii')
def test_parse_tax_form_1040(mock_pii):
    """Test Tax Form 1040 extraction logic."""
    mock_pii.return_value = ("***-**-5555", ["SSN"])
    
    blocks = create_mock_kv_blocks("11 Adjusted gross income", "75000.00", 98.0)
    
    extracted = parse_tax_form_1040(blocks)
    
    assert "adjusted_gross_income" in extracted
    assert extracted["adjusted_gross_income"]["value"] == "75000.00"

@patch('functions.extractor.parsers.detect_and_mask_pii')
def test_parse_id_document(mock_pii):
    """Test the extraction mapping for AnalyzeID responses."""
    mock_pii.return_value = ("***-***-567", ["DRIVER_ID"])
    
    mock_analyze_id_response = {
        'IdentityDocuments': [{
            'IdentityDocumentFields': [
                {'Type': {'Text': 'FIRST_NAME'}, 'ValueDetection': {'Text': 'JOHN', 'Confidence': 99.5}},
                {'Type': {'Text': 'DOCUMENT_NUMBER'}, 'ValueDetection': {'Text': 'D1234567', 'Confidence': 75.0}}
            ]
        }]
    }
    
    extracted = parse_id_document(mock_analyze_id_response)
    
    assert extracted["first_name"]["value"] == "JOHN"
    assert extracted["first_name"]["requires_manual_review"] is False
    assert extracted["document_number"]["value"] == "***-***-567"
    assert extracted["document_number"]["requires_manual_review"] is True # 75.0 < 80.0

# --- 3. Tests for Multi-Page Processing & Lambda Handler ---

@patch('functions.extractor.app.textract')
def test_process_multipage_document(mock_textract):
    """Test the async polling and pagination logic for multi-page PDFs."""
    # Mock starting the job
    mock_textract.start_document_analysis.return_value = {'JobId': 'job-123'}
    
    # Mock polling status (simulate one IN_PROGRESS, then SUCCEEDED)
    mock_textract.get_document_analysis.side_effect = [
        {'JobStatus': 'IN_PROGRESS'},
        {'JobStatus': 'SUCCEEDED', 'NextToken': 'token-1', 'Blocks': [{'Id': 'b1'}]},
        {'JobStatus': 'SUCCEEDED', 'Blocks': [{'Id': 'b2'}]} # No NextToken ends pagination
    ]
    
    # We patch time.sleep to run instantly in tests
    with patch('functions.extractor.app.time.sleep'):
        blocks = process_multipage_document("test-bucket", "test-key.pdf", "W2")
        
    assert len(blocks) == 2
    assert mock_textract.start_document_analysis.called
    assert mock_textract.get_document_analysis.call_count == 3

@patch('functions.extractor.app.textract')
@patch('functions.extractor.app.process_multipage_document')
@patch('functions.extractor.app.parse_w2')
def test_lambda_handler_w2_routing(mock_parse_w2, mock_process_async, mock_textract):
    """Test that the handler correctly routes multi-page W2s to the right parser."""
    event = {
        "document_id": "doc-123",
        "document_type": "W2",
        "metadata": {
            "s3_bucket": "test-bucket",
            "s3_key": "w2.pdf"
        }
    }
    
    mock_process_async.return_value = [{'BlockType': 'mock'}]
    mock_parse_w2.return_value = {"wages": {"value": "50000"}}
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    assert response["extraction_status"] == "SUCCESS"
    assert response["metadata"]["extracted_data"]["wages"]["value"] == "50000"
    mock_process_async.assert_called_once_with("test-bucket", "w2.pdf", "W2")

@patch('functions.extractor.app.textract')
@patch('functions.extractor.app.parse_id_document')
def test_lambda_handler_id_routing(mock_parse_id, mock_textract):
    """Test that the handler correctly routes IDs directly to AnalyzeID (synchronous)."""
    event = {
        "document_id": "doc-456",
        "document_type": "DRIVERS_LICENSE",
        "metadata": {
            "s3_bucket": "test-bucket",
            "s3_key": "id.jpg"
        }
    }
    
    mock_textract.analyze_id.return_value = {'IdentityDocuments': []}
    mock_parse_id.return_value = {"first_name": {"value": "JOHN"}}
    
    response = lambda_handler(event, None)
    
    assert response["statusCode"] == 200
    assert response["metadata"]["extracted_data"]["first_name"]["value"] == "JOHN"
    mock_textract.analyze_id.assert_called_once()
