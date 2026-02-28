import pytest
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import ClientError
from functions.classifier.app import lambda_handler, classify_document, analyze_document_with_retry

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
    """Test classification logic for W2 forms with IRS structure and EIN detection."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "Form W-2"},
        {"BlockType": "LINE", "Text": "Wage and Tax Statement"},
        {"BlockType": "LINE", "Text": "Employer Identification Number: 12-3456789"},
        {"BlockType": "LINE", "Text": "Social Security Wages"},
        {"BlockType": "LINE", "Text": "Federal Income Tax Withheld"},
        {"BlockType": "LINE", "Text": "2023"}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "W2"
    assert confidence >= 0.70  # Should have high confidence with multiple indicators

def test_classify_document_bank_statement():
    """Test classification logic for Bank Statements with institution headers and transaction tables."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "BANK OF AMERICA"},
        {"BlockType": "LINE", "Text": "STATEMENT OF ACCOUNT"},
        {"BlockType": "LINE", "Text": "Account Number: 123456789"},
        {"BlockType": "LINE", "Text": "Statement Period: 01/01/2023 - 01/31/2023"},
        {"BlockType": "LINE", "Text": "Beginning Balance: $1,000.00"},
        {"BlockType": "LINE", "Text": "ENDING BALANCE: $5,000.00"},
        {"BlockType": "LINE", "Text": "TOTAL DEPOSITS"},
        {"BlockType": "LINE", "Text": "TOTAL WITHDRAWALS"}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "BANK_STATEMENT"
    assert confidence >= 0.70  # Should have high confidence with multiple indicators

def test_classify_document_unknown_triggers_manual_review():
    """Test that unrecognized documents receive low confidence and flag for review."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "Just a random letter to the bank."},
        {"BlockType": "LINE", "Text": "Please approve my loan."}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "UNKNOWN"
    assert confidence < 0.70

def test_classify_document_tax_form():
    """Test classification logic for Tax Forms with IRS form numbers and tax year."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "Form 1040"},
        {"BlockType": "LINE", "Text": "U.S. Individual Income Tax Return"},
        {"BlockType": "LINE", "Text": "Department of the Treasury"},
        {"BlockType": "LINE", "Text": "Internal Revenue Service"},
        {"BlockType": "LINE", "Text": "Tax Year 2023"},
        {"BlockType": "LINE", "Text": "Filing Status: Single"},
        {"BlockType": "LINE", "Text": "Adjusted Gross Income"}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "TAX_FORM"
    assert confidence >= 0.70

def test_classify_document_drivers_license():
    """Test classification logic for Driver's Licenses with DMV formats and license numbers."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "DRIVER'S LICENSE"},
        {"BlockType": "LINE", "Text": "Department of Motor Vehicles"},
        {"BlockType": "LINE", "Text": "License Number: D123-4567-8901"},
        {"BlockType": "LINE", "Text": "Date of Birth: 06/15/1985"},
        {"BlockType": "LINE", "Text": "Expiration Date: 06/15/2025"},
        {"BlockType": "LINE", "Text": "Class: C"},
        {"BlockType": "LINE", "Text": "Sex: M"},
        {"BlockType": "LINE", "Text": "Height: 5'10\""}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "DRIVERS_LICENSE"
    assert confidence >= 0.70

def test_classify_document_id_document():
    """Test classification logic for ID Documents with government ID characteristics."""
    mock_blocks = [
        {"BlockType": "LINE", "Text": "PASSPORT"},
        {"BlockType": "LINE", "Text": "United States of America"},
        {"BlockType": "LINE", "Text": "U.S. Department of State"},
        {"BlockType": "LINE", "Text": "Passport Number: 123456789"},
        {"BlockType": "LINE", "Text": "Date of Birth: 06/15/1985"},
        {"BlockType": "LINE", "Text": "Nationality: USA"},
        {"BlockType": "LINE", "Text": "Issuing Authority: U.S. Department of State"}
    ]
    doc_type, confidence = classify_document(mock_blocks)
    assert doc_type == "ID_DOCUMENT"
    assert confidence >= 0.70

def test_classify_document_confidence_scoring():
    """Test that confidence scores are calculated correctly based on indicator strength."""
    # Test with minimal W2 indicators
    minimal_w2_blocks = [
        {"BlockType": "LINE", "Text": "W-2"},
        {"BlockType": "LINE", "Text": "Wage and Tax Statement"}
    ]
    doc_type, confidence = classify_document(minimal_w2_blocks)
    assert doc_type == "W2"
    assert 0.50 <= confidence < 0.70  # Lower confidence with fewer indicators
    
    # Test with strong W2 indicators
    strong_w2_blocks = [
        {"BlockType": "LINE", "Text": "Form W-2"},
        {"BlockType": "LINE", "Text": "Wage and Tax Statement"},
        {"BlockType": "LINE", "Text": "Employer Identification Number: 12-3456789"},
        {"BlockType": "LINE", "Text": "Social Security Wages"},
        {"BlockType": "LINE", "Text": "Federal Income Tax Withheld"},
        {"BlockType": "LINE", "Text": "Internal Revenue Service"}
    ]
    doc_type, confidence = classify_document(strong_w2_blocks)
    assert doc_type == "W2"
    assert confidence >= 0.90  # High confidence with many indicators

@patch('functions.classifier.app.textract')
def test_lambda_handler_success(mock_textract, mock_step_function_event):
    """Test the full Lambda handler execution flow."""
    # Mock the Textract response
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {"BlockType": "LINE", "Text": "Form 1040"},
            {"BlockType": "LINE", "Text": "U.S. Individual Income Tax Return"},
            {"BlockType": "LINE", "Text": "Department of the Treasury"},
            {"BlockType": "LINE", "Text": "Internal Revenue Service"}
        ]
    }
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Assertions
    assert result["document_id"] == "doc-123"
    assert result["document_type"] == "TAX_FORM"
    assert result["confidence"] >= 0.70
    assert result["requires_manual_review"] is False
    assert "metadata" in result


# ============================================================================
# Task 5.3: Error Handling and Logging Tests
# ============================================================================

@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.time.sleep')  # Mock sleep to speed up tests
def test_retry_logic_with_exponential_backoff(mock_sleep, mock_textract):
    """
    Test retry logic with exponential backoff (5s, 15s, 45s).
    Validates Requirement 11.3, 11.4.
    """
    # Simulate throttling on first two attempts, success on third
    mock_textract.analyze_document.side_effect = [
        ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'AnalyzeDocument'
        ),
        ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'AnalyzeDocument'
        ),
        {'Blocks': [{"BlockType": "LINE", "Text": "Success"}]}
    ]
    
    # Call with retry
    result = analyze_document_with_retry('test-bucket', 'test-key', 'doc-123')
    
    # Verify 3 attempts were made
    assert mock_textract.analyze_document.call_count == 3
    
    # Verify exponential backoff delays: 5s, 15s (no third sleep since third attempt succeeded)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(5)
    mock_sleep.assert_any_call(15)
    
    # Verify successful result
    assert result['Blocks'][0]['Text'] == 'Success'


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.time.sleep')
def test_retry_exhaustion_raises_error(mock_sleep, mock_textract):
    """
    Test that retries are exhausted after 3 attempts and error is raised.
    Validates Requirement 11.4.
    """
    # Simulate throttling on all attempts
    mock_textract.analyze_document.side_effect = ClientError(
        {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
        'AnalyzeDocument'
    )
    
    # Should raise after 3 attempts
    with pytest.raises(ClientError) as exc_info:
        analyze_document_with_retry('test-bucket', 'test-key', 'doc-123')
    
    assert exc_info.value.response['Error']['Code'] == 'ThrottlingException'
    assert mock_textract.analyze_document.call_count == 3
    assert mock_sleep.call_count == 2  # Sleep between attempts 1-2 and 2-3


@patch('functions.classifier.app.textract')
def test_non_retryable_error_fails_immediately(mock_textract):
    """
    Test that non-retryable errors (e.g., InvalidS3ObjectException) fail immediately.
    Validates Requirement 11.3.
    """
    # Simulate invalid document error
    mock_textract.analyze_document.side_effect = ClientError(
        {'Error': {'Code': 'InvalidS3ObjectException', 'Message': 'Invalid document'}},
        'AnalyzeDocument'
    )
    
    # Should raise immediately without retries
    with pytest.raises(ClientError) as exc_info:
        analyze_document_with_retry('test-bucket', 'test-key', 'doc-123')
    
    assert exc_info.value.response['Error']['Code'] == 'InvalidS3ObjectException'
    assert mock_textract.analyze_document.call_count == 1  # No retries


@patch('functions.classifier.app.textract')
def test_illegible_document_handling(mock_textract, mock_step_function_event):
    """
    Test graceful handling of illegible documents.
    Validates Requirement 3.7, 11.3.
    """
    # Simulate illegible document error
    mock_textract.analyze_document.side_effect = ClientError(
        {'Error': {'Code': 'InvalidS3ObjectException', 'Message': 'Document is illegible'}},
        'AnalyzeDocument'
    )
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Verify illegible document is handled gracefully
    assert result["document_id"] == "doc-123"
    assert result["document_type"] == "ILLEGIBLE"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True
    assert "error" in result
    assert "illegible" in result["error"].lower()


@patch('functions.classifier.app.textract')
def test_unsupported_document_handling(mock_textract, mock_step_function_event):
    """
    Test graceful handling of unsupported document formats.
    Validates Requirement 3.7.
    """
    # Simulate unsupported document error
    mock_textract.analyze_document.side_effect = ClientError(
        {'Error': {'Code': 'UnsupportedDocumentException', 'Message': 'Unsupported format'}},
        'AnalyzeDocument'
    )
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Verify unsupported document is handled gracefully
    assert result["document_type"] == "ILLEGIBLE"
    assert result["requires_manual_review"] is True


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.logger')
def test_cloudwatch_logging_for_classification_results(mock_logger, mock_textract, mock_step_function_event):
    """
    Test CloudWatch logging for classification results.
    Validates Requirement 18.2.
    """
    # Mock successful Textract response
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {"BlockType": "LINE", "Text": "Form W-2"},
            {"BlockType": "LINE", "Text": "Wage and Tax Statement"},
            {"BlockType": "LINE", "Text": "Employer Identification Number: 12-3456789"}
        ]
    }
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Verify logging includes document ID, type, and confidence
    log_calls = [str(call) for call in mock_logger.info.call_args_list]
    log_output = ' '.join(log_calls)
    
    assert 'doc-123' in log_output  # Document ID
    assert 'W2' in log_output or 'document_type' in log_output  # Document type
    assert 'confidence' in log_output  # Confidence score


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.logger')
def test_manual_review_flag_when_confidence_below_70(mock_logger, mock_textract, mock_step_function_event):
    """
    Test that documents are flagged for manual review when confidence < 70%.
    Validates Requirement 3.7.
    """
    # Mock Textract response with weak indicators (low confidence)
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {"BlockType": "LINE", "Text": "Some random text"},
            {"BlockType": "LINE", "Text": "Not much to classify"}
        ]
    }
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Verify manual review flag
    if result["confidence"] < 0.70:
        assert result["requires_manual_review"] is True
        
        # Verify warning was logged
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        warning_output = ' '.join(warning_calls)
        assert 'manual review' in warning_output.lower()


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.logger')
def test_error_logging_with_context(mock_logger, mock_textract, mock_step_function_event):
    """
    Test that errors are logged with appropriate context information.
    Validates Requirement 18.5.
    """
    # Simulate Textract error
    mock_textract.analyze_document.side_effect = ClientError(
        {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
        'AnalyzeDocument'
    )
    
    # Execute handler (should raise after retries)
    with pytest.raises(ClientError):
        lambda_handler(mock_step_function_event, None)
    
    # Verify error logging includes context
    error_calls = [str(call) for call in mock_logger.error.call_args_list]
    error_output = ' '.join(error_calls)
    
    assert 'doc-123' in error_output  # Document ID
    assert 'loan-456' in error_output or 'loan_application_id' in error_output  # Loan application ID
    assert 'ServiceUnavailable' in error_output or 'error_code' in error_output  # Error code


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.logger')
def test_logging_includes_all_required_fields(mock_logger, mock_textract, mock_step_function_event):
    """
    Test that classification logging includes document ID, type, and confidence.
    Validates Requirement 18.2.
    """
    # Mock successful classification
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {"BlockType": "LINE", "Text": "BANK OF AMERICA"},
            {"BlockType": "LINE", "Text": "STATEMENT OF ACCOUNT"},
            {"BlockType": "LINE", "Text": "Account Number: 123456789"},
            {"BlockType": "LINE", "Text": "ENDING BALANCE: $5,000.00"}
        ]
    }
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Verify result contains required fields
    assert "document_id" in result
    assert "document_type" in result
    assert "confidence" in result
    
    # Verify logging was called
    assert mock_logger.info.called
    
    # Check that at least one log message contains classification results
    info_calls = [str(call) for call in mock_logger.info.call_args_list]
    classification_logged = any(
        'classification' in call.lower() or 'document_type' in call.lower()
        for call in info_calls
    )
    assert classification_logged


@patch('functions.classifier.app.textract')
def test_high_confidence_no_manual_review(mock_textract, mock_step_function_event):
    """
    Test that high-confidence classifications don't trigger manual review.
    Validates Requirement 3.7.
    """
    # Mock strong W2 indicators
    mock_textract.analyze_document.return_value = {
        'Blocks': [
            {"BlockType": "LINE", "Text": "Form W-2"},
            {"BlockType": "LINE", "Text": "Wage and Tax Statement"},
            {"BlockType": "LINE", "Text": "Employer Identification Number: 12-3456789"},
            {"BlockType": "LINE", "Text": "Social Security Wages"},
            {"BlockType": "LINE", "Text": "Federal Income Tax Withheld"},
            {"BlockType": "LINE", "Text": "Internal Revenue Service"}
        ]
    }
    
    # Execute handler
    result = lambda_handler(mock_step_function_event, None)
    
    # Verify high confidence and no manual review
    assert result["confidence"] >= 0.70
    assert result["requires_manual_review"] is False


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.time.sleep')
def test_retry_on_provisioned_throughput_exceeded(mock_sleep, mock_textract):
    """
    Test retry logic for ProvisionedThroughputExceededException.
    Validates Requirement 11.3, 11.4.
    """
    # Simulate throughput exceeded on first attempt, success on second
    mock_textract.analyze_document.side_effect = [
        ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Throughput exceeded'}},
            'AnalyzeDocument'
        ),
        {'Blocks': [{"BlockType": "LINE", "Text": "Success"}]}
    ]
    
    # Call with retry
    result = analyze_document_with_retry('test-bucket', 'test-key', 'doc-123')
    
    # Verify retry occurred
    assert mock_textract.analyze_document.call_count == 2
    mock_sleep.assert_called_once_with(5)  # First retry delay
    assert result['Blocks'][0]['Text'] == 'Success'


@patch('functions.classifier.app.textract')
@patch('functions.classifier.app.time.sleep')
def test_retry_on_service_unavailable(mock_sleep, mock_textract):
    """
    Test retry logic for ServiceUnavailable errors.
    Validates Requirement 11.3.
    """
    # Simulate service unavailable on first attempt, success on second
    mock_textract.analyze_document.side_effect = [
        ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'AnalyzeDocument'
        ),
        {'Blocks': [{"BlockType": "LINE", "Text": "Success"}]}
    ]
    
    # Call with retry
    result = analyze_document_with_retry('test-bucket', 'test-key', 'doc-123')
    
    # Verify retry occurred
    assert mock_textract.analyze_document.call_count == 2
    mock_sleep.assert_called_once_with(5)
    assert result['Blocks'][0]['Text'] == 'Success'
