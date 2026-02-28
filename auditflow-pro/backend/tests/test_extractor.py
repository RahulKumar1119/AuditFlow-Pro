import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from functions.extractor.app import (
    lambda_handler,
    analyze_document_with_retry,
    detect_pii,
    process_multi_page_pdf,
    extract_key_value_pairs,
    route_to_extractor
)


@pytest.fixture
def sample_event():
    """Sample Step Functions event for extraction."""
    return {
        "document_id": "test-doc-123",
        "document_type": "W2",
        "s3_bucket": "test-bucket",
        "s3_key": "documents/test.pdf",
        "page_count": 1,
        "loan_application_id": "loan-456"
    }


@pytest.fixture
def sample_textract_response():
    """Sample Textract API response."""
    return {
        "Blocks": [
            {
                "BlockType": "LINE",
                "Id": "block-1",
                "Text": "W-2 Wage and Tax Statement",
                "Confidence": 99.5,
                "Page": 1
            },
            {
                "BlockType": "KEY_VALUE_SET",
                "Id": "key-1",
                "EntityTypes": ["KEY"],
                "Confidence": 95.0,
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word-1"]},
                    {"Type": "VALUE", "Ids": ["value-1"]}
                ]
            },
            {
                "BlockType": "WORD",
                "Id": "word-1",
                "Text": "Employee Name",
                "Confidence": 95.0
            },
            {
                "BlockType": "KEY_VALUE_SET",
                "Id": "value-1",
                "EntityTypes": ["VALUE"],
                "Confidence": 90.0,
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word-2"]}
                ]
            },
            {
                "BlockType": "WORD",
                "Id": "word-2",
                "Text": "John Doe",
                "Confidence": 90.0
            }
        ]
    }


class TestLambdaHandler:
    """Test cases for the main Lambda handler."""
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    @patch('functions.extractor.app.route_to_extractor')
    @patch('functions.extractor.app.detect_pii')
    def test_successful_extraction(self, mock_pii, mock_route, mock_textract, sample_event, sample_textract_response):
        """Test successful document extraction."""
        # Setup mocks
        mock_textract.return_value = sample_textract_response
        mock_route.return_value = MagicMock(to_dict=lambda: {"document_type": "W2"})
        mock_pii.return_value = ["SSN", "DATE_OF_BIRTH"]
        
        # Execute
        result = lambda_handler(sample_event, None)
        
        # Verify
        assert result["document_id"] == "test-doc-123"
        assert result["document_type"] == "W2"
        assert result["processing_status"] == "COMPLETED"
        assert "extraction_timestamp" in result
        assert result["pii_detected"] == ["SSN", "DATE_OF_BIRTH"]
        assert "extracted_data" in result
        
        # Verify Textract was called
        mock_textract.assert_called_once_with("test-bucket", "documents/test.pdf", "test-doc-123")
    
    def test_missing_required_field(self):
        """Test validation of required input fields."""
        invalid_event = {"document_id": "test-123"}
        
        with pytest.raises(ValueError) as exc_info:
            lambda_handler(invalid_event, None)
        
        assert "Missing required field" in str(exc_info.value)
    
    @patch('functions.extractor.app.process_multi_page_pdf')
    @patch('functions.extractor.app.route_to_extractor')
    @patch('functions.extractor.app.detect_pii')
    def test_multi_page_pdf_handling(self, mock_pii, mock_route, mock_multi_page, sample_event, sample_textract_response):
        """Test multi-page PDF processing."""
        # Setup for multi-page document
        sample_event["page_count"] = 5
        mock_multi_page.return_value = sample_textract_response
        mock_route.return_value = MagicMock(to_dict=lambda: {"document_type": "W2"})
        mock_pii.return_value = []
        
        # Execute
        result = lambda_handler(sample_event, None)
        
        # Verify multi-page handler was called
        mock_multi_page.assert_called_once_with(
            "test-bucket", "documents/test.pdf", "test-doc-123", 5
        )
        assert result["page_count"] == 5
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_illegible_document_handling(self, mock_textract, sample_event):
        """Test handling of illegible or corrupted documents."""
        # Setup mock to raise InvalidS3ObjectException
        error_response = {'Error': {'Code': 'InvalidS3ObjectException', 'Message': 'Invalid document'}}
        mock_textract.side_effect = ClientError(error_response, 'AnalyzeDocument')
        
        # Execute
        result = lambda_handler(sample_event, None)
        
        # Verify error handling
        assert result["processing_status"] == "FAILED"
        assert "error" in result
        assert "illegible or corrupted" in result["error"].lower()
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    @patch('functions.extractor.app.route_to_extractor')
    @patch('functions.extractor.app.detect_pii')
    def test_low_confidence_field_flagging(self, mock_pii, mock_route, mock_textract, sample_event, sample_textract_response):
        """Test flagging of low confidence fields."""
        # Setup mock with low confidence field
        mock_textract.return_value = sample_textract_response
        mock_route.return_value = MagicMock(to_dict=lambda: {
            "document_type": "W2",
            "employee_name": {"value": "John Doe", "confidence": 0.75},
            "wages": {"value": "50000", "confidence": 0.95}
        })
        mock_pii.return_value = []
        
        # Execute
        result = lambda_handler(sample_event, None)
        
        # Verify low confidence field is flagged
        assert "employee_name" in result["low_confidence_fields"]
        assert "wages" not in result["low_confidence_fields"]
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    @patch('functions.extractor.app.route_to_extractor')
    @patch('functions.extractor.app.detect_pii')
    @patch('functions.extractor.app.logger')
    def test_low_confidence_field_logging(self, mock_logger, mock_pii, mock_route, mock_textract, sample_event, sample_textract_response):
        """
        Test that low confidence fields are logged with appropriate context.
        
        Validates Requirements:
        - 4.8: Flag fields with confidence < 80% for manual verification
        - 4.9: Store extracted data with confidence scores
        - 18.5: Log low-confidence extractions
        """
        # Setup mock with multiple low confidence fields
        mock_textract.return_value = sample_textract_response
        mock_route.return_value = MagicMock(to_dict=lambda: {
            "document_type": "W2",
            "employee_name": {"value": "John Doe", "confidence": 0.75},
            "employee_address": {"value": "123 Main St", "confidence": 0.65},
            "wages": {"value": "50000", "confidence": 0.95},
            "employer_name": {"value": "Acme Corp", "confidence": 0.85}
        })
        mock_pii.return_value = []
        
        # Execute
        result = lambda_handler(sample_event, None)
        
        # Verify low confidence fields are flagged
        assert len(result["low_confidence_fields"]) == 2
        assert "employee_name" in result["low_confidence_fields"]
        assert "employee_address" in result["low_confidence_fields"]
        assert "wages" not in result["low_confidence_fields"]
        assert "employer_name" not in result["low_confidence_fields"]
        
        # Verify logging occurred for low confidence fields
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                        if 'Low confidence field detected' in str(call)]
        assert len(warning_calls) == 2
        
        # Verify log messages contain required context
        log_messages = [str(call) for call in warning_calls]
        assert any('employee_name' in msg and 'confidence=0.75' in msg for msg in log_messages)
        assert any('employee_address' in msg and 'confidence=0.65' in msg for msg in log_messages)
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    @patch('functions.extractor.app.route_to_extractor')
    @patch('functions.extractor.app.detect_pii')
    def test_confidence_scores_stored_in_output(self, mock_pii, mock_route, mock_textract, sample_event, sample_textract_response):
        """
        Test that confidence scores are properly stored in extracted data output.
        
        Validates Requirement 4.9: Store extracted data with confidence scores.
        """
        # Setup mock with various confidence levels
        mock_textract.return_value = sample_textract_response
        extracted_data = {
            "document_type": "W2",
            "employee_name": {"value": "John Doe", "confidence": 0.98},
            "wages": {"value": "50000", "confidence": 0.95},
            "employer_name": {"value": "Acme Corp", "confidence": 0.82}
        }
        mock_route.return_value = MagicMock(to_dict=lambda: extracted_data)
        mock_pii.return_value = []
        
        # Execute
        result = lambda_handler(sample_event, None)
        
        # Verify confidence scores are preserved in output
        assert result["extracted_data"]["employee_name"]["confidence"] == 0.98
        assert result["extracted_data"]["wages"]["confidence"] == 0.95
        assert result["extracted_data"]["employer_name"]["confidence"] == 0.82
        
        # Verify no fields are flagged (all above threshold)
        assert len(result["low_confidence_fields"]) == 0


class TestTextractRetry:
    """Test cases for Textract retry logic."""
    
    @patch('functions.extractor.app.textract')
    @patch('time.sleep')
    def test_successful_retry_after_throttling(self, mock_sleep, mock_textract_client):
        """Test successful retry after throttling error."""
        # Setup mock to fail once then succeed
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_textract_client.analyze_document.side_effect = [
            ClientError(error_response, 'AnalyzeDocument'),
            {"Blocks": []}
        ]
        
        # Execute
        result = analyze_document_with_retry("bucket", "key", "doc-123")
        
        # Verify retry occurred
        assert mock_textract_client.analyze_document.call_count == 2
        mock_sleep.assert_called_once_with(5)  # First retry delay
        assert result == {"Blocks": []}
    
    @patch('functions.extractor.app.textract')
    @patch('time.sleep')
    def test_exhausted_retries(self, mock_sleep, mock_textract_client):
        """Test behavior when all retries are exhausted."""
        # Setup mock to always fail
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_textract_client.analyze_document.side_effect = ClientError(error_response, 'AnalyzeDocument')
        
        # Execute and verify exception is raised
        with pytest.raises(ClientError):
            analyze_document_with_retry("bucket", "key", "doc-123", max_retries=3)
        
        # Verify all retries were attempted
        assert mock_textract_client.analyze_document.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries
    
    @patch('functions.extractor.app.textract')
    def test_non_retryable_error(self, mock_textract_client):
        """Test that non-retryable errors are not retried."""
        # Setup mock with non-retryable error
        error_response = {'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid param'}}
        mock_textract_client.analyze_document.side_effect = ClientError(error_response, 'AnalyzeDocument')
        
        # Execute and verify exception is raised immediately
        with pytest.raises(ClientError):
            analyze_document_with_retry("bucket", "key", "doc-123")
        
        # Verify only one attempt was made
        assert mock_textract_client.analyze_document.call_count == 1


class TestPIIDetection:
    """Test cases for PII detection."""
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_success(self, mock_comprehend_client):
        """Test successful PII detection."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "SSN", "Score": 0.99},
                {"Type": "DATE_OF_BIRTH", "Score": 0.95},
                {"Type": "SSN", "Score": 0.98}  # Duplicate
            ]
        }
        
        # Execute
        result = detect_pii("Sample text with SSN 123-45-6789", "doc-123")
        
        # Verify
        assert "SSN" in result
        assert "DATE_OF_BIRTH" in result
        assert len(result) == 2  # Duplicates removed
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_empty_text(self, mock_comprehend_client):
        """Test PII detection with empty text."""
        result = detect_pii("", "doc-123")
        assert result == []
        mock_comprehend_client.detect_pii_entities.assert_not_called()
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_error_handling(self, mock_comprehend_client):
        """Test PII detection error handling."""
        # Setup mock to raise error
        mock_comprehend_client.detect_pii_entities.side_effect = Exception("API error")
        
        # Execute - should not raise, just return empty list
        result = detect_pii("Sample text", "doc-123")
        assert result == []
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_all_types(self, mock_comprehend_client):
        """Test detection of all major PII types (Requirement 7.2)."""
        # Setup mock with all PII types
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "SSN", "Score": 0.99},
                {"Type": "BANK_ACCOUNT_NUMBER", "Score": 0.98},
                {"Type": "DRIVER_ID", "Score": 0.97},
                {"Type": "DATE_OF_BIRTH", "Score": 0.96},
                {"Type": "PASSPORT_NUMBER", "Score": 0.95},
                {"Type": "PHONE", "Score": 0.94},
                {"Type": "EMAIL", "Score": 0.93},
                {"Type": "ADDRESS", "Score": 0.92}
            ]
        }
        
        # Execute
        text = "John Doe, SSN 123-45-6789, DOB 01/15/1985, Account 9876543210"
        result = detect_pii(text, "doc-all-pii")
        
        # Verify all types detected
        assert "SSN" in result
        assert "BANK_ACCOUNT_NUMBER" in result
        assert "DRIVER_ID" in result
        assert "DATE_OF_BIRTH" in result
        assert "PASSPORT_NUMBER" in result
        assert "PHONE" in result
        assert "EMAIL" in result
        assert "ADDRESS" in result
        assert len(result) == 8
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_ssn_only(self, mock_comprehend_client):
        """Test detection of SSN specifically (Requirement 7.2)."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "SSN", "Score": 0.99, "BeginOffset": 10, "EndOffset": 21}
            ]
        }
        
        # Execute
        result = detect_pii("SSN: 123-45-6789", "doc-ssn")
        
        # Verify
        assert result == ["SSN"]
        mock_comprehend_client.detect_pii_entities.assert_called_once()
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_account_number(self, mock_comprehend_client):
        """Test detection of bank account numbers (Requirement 7.2)."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "BANK_ACCOUNT_NUMBER", "Score": 0.98}
            ]
        }
        
        # Execute
        result = detect_pii("Account Number: 1234567890", "doc-account")
        
        # Verify
        assert result == ["BANK_ACCOUNT_NUMBER"]
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_license_number(self, mock_comprehend_client):
        """Test detection of driver's license numbers (Requirement 7.2)."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "DRIVER_ID", "Score": 0.97}
            ]
        }
        
        # Execute
        result = detect_pii("License: D123-4567-8901", "doc-license")
        
        # Verify
        assert result == ["DRIVER_ID"]
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_date_of_birth(self, mock_comprehend_client):
        """Test detection of dates of birth (Requirement 7.2)."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "DATE_OF_BIRTH", "Score": 0.96}
            ]
        }
        
        # Execute
        result = detect_pii("DOB: 01/15/1985", "doc-dob")
        
        # Verify
        assert result == ["DATE_OF_BIRTH"]
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_multiple_same_type(self, mock_comprehend_client):
        """Test detection with multiple instances of same PII type."""
        # Setup mock with multiple SSNs
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "SSN", "Score": 0.99},
                {"Type": "SSN", "Score": 0.98},
                {"Type": "SSN", "Score": 0.97},
                {"Type": "DATE_OF_BIRTH", "Score": 0.96}
            ]
        }
        
        # Execute
        result = detect_pii("Multiple SSNs in document", "doc-multi")
        
        # Verify - should deduplicate
        assert "SSN" in result
        assert "DATE_OF_BIRTH" in result
        assert len(result) == 2
        assert result.count("SSN") == 1  # No duplicates
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_text_truncation(self, mock_comprehend_client):
        """Test that long text is truncated to 5000 bytes."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [{"Type": "SSN", "Score": 0.99}]
        }
        
        # Execute with very long text
        long_text = "A" * 10000  # 10000 characters
        result = detect_pii(long_text, "doc-long")
        
        # Verify Comprehend was called with truncated text
        call_args = mock_comprehend_client.detect_pii_entities.call_args
        assert len(call_args[1]['Text']) == 5000
        assert result == ["SSN"]
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_whitespace_only(self, mock_comprehend_client):
        """Test PII detection with whitespace-only text."""
        result = detect_pii("   \n\t  ", "doc-whitespace")
        assert result == []
        mock_comprehend_client.detect_pii_entities.assert_not_called()
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_none_text(self, mock_comprehend_client):
        """Test PII detection with None text."""
        result = detect_pii(None, "doc-none")
        assert result == []
        mock_comprehend_client.detect_pii_entities.assert_not_called()
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_client_error(self, mock_comprehend_client):
        """Test PII detection with AWS ClientError."""
        # Setup mock to raise ClientError
        error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
        mock_comprehend_client.detect_pii_entities.side_effect = ClientError(error_response, 'DetectPiiEntities')
        
        # Execute - should handle gracefully
        result = detect_pii("Sample text", "doc-error")
        assert result == []
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_no_entities(self, mock_comprehend_client):
        """Test PII detection when no PII is found."""
        # Setup mock with empty entities
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": []
        }
        
        # Execute
        result = detect_pii("This is clean text with no PII", "doc-clean")
        
        # Verify
        assert result == []
        mock_comprehend_client.detect_pii_entities.assert_called_once()
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_malformed_response(self, mock_comprehend_client):
        """Test PII detection with malformed API response."""
        # Setup mock with malformed response
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "SSN"},  # Missing Score
                {"Score": 0.99},  # Missing Type
                None,  # Invalid entity
                {"Type": "DATE_OF_BIRTH", "Score": 0.96}
            ]
        }
        
        # Execute - should handle gracefully
        result = detect_pii("Sample text", "doc-malformed")
        
        # Verify - should only include valid entities
        assert "SSN" in result
        assert "DATE_OF_BIRTH" in result
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_language_code(self, mock_comprehend_client):
        """Test that PII detection uses English language code."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {"Entities": []}
        
        # Execute
        detect_pii("Sample text", "doc-lang")
        
        # Verify language code is 'en'
        call_args = mock_comprehend_client.detect_pii_entities.call_args
        assert call_args[1]['LanguageCode'] == 'en'
    
    @patch('functions.extractor.app.comprehend')
    def test_pii_detection_preserves_order(self, mock_comprehend_client):
        """Test that PII types are returned in order of first detection."""
        # Setup mock
        mock_comprehend_client.detect_pii_entities.return_value = {
            "Entities": [
                {"Type": "SSN", "Score": 0.99},
                {"Type": "DATE_OF_BIRTH", "Score": 0.96},
                {"Type": "BANK_ACCOUNT_NUMBER", "Score": 0.98},
                {"Type": "SSN", "Score": 0.97}  # Duplicate
            ]
        }
        
        # Execute
        result = detect_pii("Sample text", "doc-order")
        
        # Verify order is preserved (first occurrence)
        assert result == ["SSN", "DATE_OF_BIRTH", "BANK_ACCOUNT_NUMBER"]


class TestMultiPageProcessing:
    """Test cases for multi-page PDF processing."""
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_success(self, mock_textract):
        """Test successful multi-page PDF processing with all pages."""
        # Setup mock with multi-page response
        mock_textract.return_value = {
            "Blocks": [
                {"BlockType": "PAGE", "Page": 1, "Confidence": 99.5},
                {"BlockType": "LINE", "Text": "Page 1 content", "Page": 1},
                {"BlockType": "PAGE", "Page": 2, "Confidence": 98.7},
                {"BlockType": "LINE", "Text": "Page 2 content", "Page": 2},
                {"BlockType": "PAGE", "Page": 3, "Confidence": 99.1},
                {"BlockType": "LINE", "Text": "Page 3 content", "Page": 3}
            ]
        }
        
        # Execute
        result = process_multi_page_pdf("bucket", "key", "doc-123", 3)
        
        # Verify
        assert len(result["Blocks"]) == 6
        assert result["PageProcessingMetadata"]["total_pages"] == 3
        assert result["PageProcessingMetadata"]["pages_processed"] == 3
        assert result["PageProcessingMetadata"]["pages_processed_list"] == [1, 2, 3]
        assert result["PageProcessingMetadata"]["missing_pages"] == []
        assert result["PageProcessingMetadata"]["corrupted_pages"] == []
        assert result["PageProcessingMetadata"]["processing_complete"] is True
        mock_textract.assert_called_once()
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_failure(self, mock_textract):
        """Test multi-page PDF processing failure."""
        # Setup mock to raise error
        mock_textract.side_effect = Exception("Processing failed")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception) as exc_info:
            process_multi_page_pdf("bucket", "key", "doc-123", 5)
        
        assert "Processing failed" in str(exc_info.value)
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_with_missing_pages(self, mock_textract):
        """Test multi-page PDF processing with missing/corrupted pages.
        
        Validates Requirement 5.6: Handle corrupted or illegible pages gracefully.
        """
        # Setup mock with response missing page 2
        mock_textract.return_value = {
            "Blocks": [
                {"BlockType": "PAGE", "Page": 1, "Confidence": 99.5},
                {"BlockType": "LINE", "Text": "Page 1 content", "Page": 1},
                {"BlockType": "PAGE", "Page": 3, "Confidence": 99.1},
                {"BlockType": "LINE", "Text": "Page 3 content", "Page": 3}
            ]
        }
        
        # Execute
        result = process_multi_page_pdf("bucket", "key", "doc-123", 3)
        
        # Verify - should continue processing despite missing page
        assert result["PageProcessingMetadata"]["total_pages"] == 3
        assert result["PageProcessingMetadata"]["pages_processed"] == 2
        assert result["PageProcessingMetadata"]["pages_processed_list"] == [1, 3]
        assert result["PageProcessingMetadata"]["missing_pages"] == [2]
        assert result["PageProcessingMetadata"]["processing_complete"] is False
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_with_low_confidence_pages(self, mock_textract):
        """Test multi-page PDF processing with low confidence (corrupted) pages.
        
        Validates Requirement 5.6: Handle corrupted or illegible pages gracefully.
        """
        # Setup mock with low confidence page (indicates corruption/illegibility)
        mock_textract.return_value = {
            "Blocks": [
                {"BlockType": "PAGE", "Page": 1, "Confidence": 99.5},
                {"BlockType": "LINE", "Text": "Page 1 content", "Page": 1},
                {"BlockType": "PAGE", "Page": 2, "Confidence": 35.2},  # Low confidence
                {"BlockType": "LINE", "Text": "Garbled text", "Page": 2},
                {"BlockType": "PAGE", "Page": 3, "Confidence": 98.7},
                {"BlockType": "LINE", "Text": "Page 3 content", "Page": 3}
            ]
        }
        
        # Execute
        result = process_multi_page_pdf("bucket", "key", "doc-123", 3)
        
        # Verify - should flag low confidence page as corrupted
        assert result["PageProcessingMetadata"]["total_pages"] == 3
        assert result["PageProcessingMetadata"]["pages_processed"] == 3
        assert result["PageProcessingMetadata"]["corrupted_pages"] == [2]
        assert result["PageProcessingMetadata"]["processing_complete"] is True
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_exceeds_page_limit(self, mock_textract):
        """Test multi-page PDF processing with too many pages.
        
        Validates Requirement 5.5: Handle documents up to 100 pages.
        """
        # Execute with 101 pages (exceeds limit)
        with pytest.raises(ValueError) as exc_info:
            process_multi_page_pdf("bucket", "key", "doc-123", 101)
        
        assert "exceeds maximum page limit" in str(exc_info.value)
        assert "101 > 100" in str(exc_info.value)
        # Should not call Textract if page limit exceeded
        mock_textract.assert_not_called()
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_at_page_limit(self, mock_textract):
        """Test multi-page PDF processing at exactly 100 pages.
        
        Validates Requirement 5.5: Handle documents up to 100 pages.
        """
        # Setup mock with 100 pages
        blocks = []
        for page_num in range(1, 101):
            blocks.append({"BlockType": "PAGE", "Page": page_num, "Confidence": 99.0})
            blocks.append({"BlockType": "LINE", "Text": f"Page {page_num}", "Page": page_num})
        
        mock_textract.return_value = {"Blocks": blocks}
        
        # Execute with exactly 100 pages (should succeed)
        result = process_multi_page_pdf("bucket", "key", "doc-123", 100)
        
        # Verify
        assert result["PageProcessingMetadata"]["total_pages"] == 100
        assert result["PageProcessingMetadata"]["pages_processed"] == 100
        assert result["PageProcessingMetadata"]["processing_complete"] is True
        mock_textract.assert_called_once()
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_sequential_page_tracking(self, mock_textract):
        """Test that pages are tracked sequentially with correct page numbers.
        
        Validates Requirement 5.1, 5.2: Process pages sequentially with page number tracking.
        """
        # Setup mock with pages in non-sequential order (Textract may return out of order)
        mock_textract.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Page 3", "Page": 3},
                {"BlockType": "LINE", "Text": "Page 1", "Page": 1},
                {"BlockType": "LINE", "Text": "Page 5", "Page": 5},
                {"BlockType": "LINE", "Text": "Page 2", "Page": 2},
                {"BlockType": "LINE", "Text": "Page 4", "Page": 4}
            ]
        }
        
        # Execute
        result = process_multi_page_pdf("bucket", "key", "doc-123", 5)
        
        # Verify pages are tracked and sorted correctly
        assert result["PageProcessingMetadata"]["pages_processed_list"] == [1, 2, 3, 4, 5]
        assert result["PageProcessingMetadata"]["pages_processed"] == 5
        assert result["PageProcessingMetadata"]["processing_complete"] is True
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_aggregates_data(self, mock_textract):
        """Test that data from multiple pages is aggregated correctly.
        
        Validates Requirement 5.3: Aggregate data from multiple pages.
        """
        # Setup mock with different data on each page
        mock_textract.return_value = {
            "Blocks": [
                {"BlockType": "KEY_VALUE_SET", "Text": "Name: John", "Page": 1},
                {"BlockType": "KEY_VALUE_SET", "Text": "Address: 123 Main", "Page": 2},
                {"BlockType": "KEY_VALUE_SET", "Text": "SSN: 123-45-6789", "Page": 3}
            ]
        }
        
        # Execute
        result = process_multi_page_pdf("bucket", "key", "doc-123", 3)
        
        # Verify all blocks are aggregated in single response
        assert len(result["Blocks"]) == 3
        assert result["Blocks"][0]["Page"] == 1
        assert result["Blocks"][1]["Page"] == 2
        assert result["Blocks"][2]["Page"] == 3
        # All data should be in one response for downstream processing
        assert "Blocks" in result
        assert result["PageProcessingMetadata"]["processing_complete"] is True


class TestKeyValueExtraction:
    """Test cases for key-value pair extraction."""
    
    def test_extract_key_value_pairs(self, sample_textract_response):
        """Test extraction of key-value pairs from Textract response."""
        result = extract_key_value_pairs(sample_textract_response["Blocks"])
        
        # Verify key-value pairs were extracted
        assert isinstance(result, dict)
        assert "Employee Name" in result
        assert result["Employee Name"]["value"] == "John Doe"
        assert "confidence" in result["Employee Name"]
    
    def test_extract_key_value_pairs_empty_blocks(self):
        """Test key-value extraction with empty blocks."""
        result = extract_key_value_pairs([])
        assert result == {}


class TestDocumentTypeRouting:
    """Test cases for document type routing."""
    
    @patch('functions.extractor.app.extract_w2_data')
    def test_route_to_w2_extractor(self, mock_w2_extractor, sample_textract_response):
        """Test routing to W2 extractor."""
        from shared.models import W2Data
        mock_w2_extractor.return_value = W2Data()
        
        result = route_to_extractor("W2", sample_textract_response, "doc-123")
        
        mock_w2_extractor.assert_called_once()
        assert isinstance(result, W2Data)
    
    @patch('functions.extractor.app.extract_bank_statement_data')
    def test_route_to_bank_statement_extractor(self, mock_bank_extractor, sample_textract_response):
        """Test routing to Bank Statement extractor."""
        from shared.models import BankStatementData
        mock_bank_extractor.return_value = BankStatementData()
        
        result = route_to_extractor("BANK_STATEMENT", sample_textract_response, "doc-123")
        
        mock_bank_extractor.assert_called_once()
        assert isinstance(result, BankStatementData)
    
    @patch('functions.extractor.app.extract_id_document_data')
    def test_route_to_id_document_extractor(self, mock_id_extractor, sample_textract_response):
        """Test routing to ID Document extractor."""
        from shared.models import IDDocumentData
        mock_id_extractor.return_value = IDDocumentData()
        
        result = route_to_extractor("ID_DOCUMENT", sample_textract_response, "doc-123")
        
        mock_id_extractor.assert_called_once()
        assert isinstance(result, IDDocumentData)
    
    def test_route_unknown_document_type(self, sample_textract_response):
        """Test routing with unknown document type."""
        result = route_to_extractor("UNKNOWN", sample_textract_response, "doc-123")
        assert result == {}


class TestW2Extraction:
    """Test cases for W2 form data extraction."""
    
    @pytest.fixture
    def sample_w2_kvs(self):
        """Sample key-value pairs for W2 form."""
        return {
            "Tax Year": {"value": "2023", "confidence": 0.99},
            "Employer Name": {"value": "Acme Corporation", "confidence": 0.97},
            "Employer Identification Number": {"value": "12-3456789", "confidence": 0.98},
            "Employee Name": {"value": "John Doe", "confidence": 0.98},
            "Social Security Number": {"value": "123-45-6789", "confidence": 0.99},
            "Address": {"value": "123 Main St, Springfield, IL 62701", "confidence": 0.95},
            "Wages, tips, other compensation": {"value": "75000.00", "confidence": 0.99},
            "Federal income tax withheld": {"value": "12000.00", "confidence": 0.98},
            "Social Security wages": {"value": "75000.00", "confidence": 0.99},
            "Medicare wages and tips": {"value": "75000.00", "confidence": 0.99},
            "State": {"value": "IL", "confidence": 0.99},
            "State income tax": {"value": "3000.00", "confidence": 0.98}
        }
    
    def test_extract_w2_all_fields(self, sample_w2_kvs):
        """Test extraction of all W2 fields."""
        from functions.extractor.app import extract_w2_data
        
        result = extract_w2_data(sample_w2_kvs, [], "doc-123")
        
        # Verify all fields were extracted
        assert result.tax_year is not None
        assert result.tax_year.value == "2023"
        assert result.tax_year.confidence == 0.99
        
        assert result.employer_name is not None
        assert result.employer_name.value == "Acme Corporation"
        
        assert result.employer_ein is not None
        assert result.employer_ein.value == "12-3456789"
        
        assert result.employee_name is not None
        assert result.employee_name.value == "John Doe"
        
        assert result.employee_ssn is not None
        assert "***-**-" in result.employee_ssn.value  # SSN should be masked
        assert result.employee_ssn.value.endswith("6789")
        
        assert result.employee_address is not None
        assert result.employee_address.value == "123 Main St, Springfield, IL 62701"
        
        assert result.wages is not None
        assert result.wages.value == 75000.00
        
        assert result.federal_tax_withheld is not None
        assert result.federal_tax_withheld.value == 12000.00
        
        assert result.social_security_wages is not None
        assert result.social_security_wages.value == 75000.00
        
        assert result.medicare_wages is not None
        assert result.medicare_wages.value == 75000.00
        
        assert result.state is not None
        assert result.state.value == "IL"
        
        assert result.state_tax_withheld is not None
        assert result.state_tax_withheld.value == 3000.00
    
    def test_extract_w2_partial_fields(self):
        """Test extraction with only some fields present."""
        from functions.extractor.app import extract_w2_data
        
        partial_kvs = {
            "Employee Name": {"value": "Jane Smith", "confidence": 0.95},
            "Wages": {"value": "$50,000.00", "confidence": 0.98}
        }
        
        result = extract_w2_data(partial_kvs, [], "doc-456")
        
        # Verify extracted fields
        assert result.employee_name is not None
        assert result.employee_name.value == "Jane Smith"
        
        assert result.wages is not None
        assert result.wages.value == 50000.00  # Currency formatting removed
        
        # Verify missing fields are None
        assert result.employer_ein is None
        assert result.federal_tax_withheld is None
    
    def test_extract_w2_low_confidence_flagging(self):
        """Test that low confidence fields are flagged for manual review."""
        from functions.extractor.app import extract_w2_data
        
        low_confidence_kvs = {
            "Employee Name": {"value": "John Doe", "confidence": 0.75},  # Below 0.80 threshold
            "Wages": {"value": "60000", "confidence": 0.95}  # Above threshold
        }
        
        result = extract_w2_data(low_confidence_kvs, [], "doc-789")
        
        # Verify low confidence field is flagged
        assert result.employee_name.requires_manual_review is True
        assert result.wages.requires_manual_review is False
    
    def test_extract_w2_numeric_parsing(self):
        """Test numeric value parsing with various formats."""
        from functions.extractor.app import extract_w2_data
        
        numeric_kvs = {
            "Wages": {"value": "$75,000.00", "confidence": 0.99},
            "Federal tax": {"value": "12,500", "confidence": 0.98},
            "State tax": {"value": "3000.50", "confidence": 0.97}
        }
        
        result = extract_w2_data(numeric_kvs, [], "doc-numeric")
        
        # Verify numeric parsing
        assert result.wages.value == 75000.00
        assert result.federal_tax_withheld.value == 12500.00
        assert result.state_tax_withheld.value == 3000.50
    
    def test_extract_w2_ssn_masking(self):
        """Test that SSN is properly masked."""
        from functions.extractor.app import extract_w2_data
        
        ssn_kvs = {
            "Social Security Number": {"value": "123-45-6789", "confidence": 0.99}
        }
        
        result = extract_w2_data(ssn_kvs, [], "doc-ssn")
        
        # Verify SSN masking
        assert result.employee_ssn is not None
        assert result.employee_ssn.value == "***-**-6789"
        assert "123" not in result.employee_ssn.value
    
    def test_extract_w2_case_insensitive_matching(self):
        """Test that field matching is case-insensitive."""
        from functions.extractor.app import extract_w2_data
        
        mixed_case_kvs = {
            "EMPLOYEE NAME": {"value": "Bob Smith", "confidence": 0.96},
            "employer name": {"value": "Tech Corp", "confidence": 0.94},
            "WaGeS": {"value": "80000", "confidence": 0.98}
        }
        
        result = extract_w2_data(mixed_case_kvs, [], "doc-case")
        
        # Verify case-insensitive matching worked
        assert result.employee_name is not None
        assert result.employee_name.value == "Bob Smith"
        assert result.employer_name is not None
        assert result.employer_name.value == "Tech Corp"
        assert result.wages is not None
        assert result.wages.value == 80000.00
    
    def test_extract_w2_empty_kvs(self):
        """Test extraction with empty key-value pairs."""
        from functions.extractor.app import extract_w2_data
        
        result = extract_w2_data({}, [], "doc-empty")
        
        # Verify all fields are None
        assert result.tax_year is None
        assert result.employer_name is None
        assert result.employee_name is None
        assert result.wages is None
    
    def test_extract_w2_confidence_scores_preserved(self):
        """Test that confidence scores are preserved in extracted fields."""
        from functions.extractor.app import extract_w2_data
        
        confidence_kvs = {
            "Employee Name": {"value": "Alice Johnson", "confidence": 0.92},
            "Wages": {"value": "65000", "confidence": 0.88}
        }
        
        result = extract_w2_data(confidence_kvs, [], "doc-conf")
        
        # Verify confidence scores are preserved
        assert result.employee_name.confidence == 0.92
        assert result.wages.confidence == 0.88


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestBankStatementExtraction:
    """Test cases for Bank Statement data extraction."""
    
    @pytest.fixture
    def sample_bank_statement_kvs(self):
        """Sample key-value pairs for Bank Statement."""
        return {
            "Bank Name": {"value": "First National Bank", "confidence": 0.98},
            "Account Holder": {"value": "John Doe", "confidence": 0.97},
            "Account Number": {"value": "1234567890", "confidence": 0.99},
            "Statement Period From": {"value": "2023-12-01", "confidence": 0.99},
            "Statement Period To": {"value": "2023-12-31", "confidence": 0.99},
            "Beginning Balance": {"value": "$5,000.00", "confidence": 0.98},
            "Ending Balance": {"value": "$6,200.00", "confidence": 0.98},
            "Total Deposits": {"value": "$7,500.00", "confidence": 0.97},
            "Total Withdrawals": {"value": "$6,300.00", "confidence": 0.97},
            "Address": {"value": "123 Main St, Springfield, IL 62701", "confidence": 0.95}
        }
    
    def test_extract_bank_statement_all_fields(self, sample_bank_statement_kvs):
        """Test extraction of all Bank Statement fields."""
        from functions.extractor.app import extract_bank_statement_data
        
        result = extract_bank_statement_data(sample_bank_statement_kvs, [], "doc-123")
        
        # Verify all fields were extracted
        assert result.bank_name is not None
        assert result.bank_name.value == "First National Bank"
        assert result.bank_name.confidence == 0.98
        
        assert result.account_holder_name is not None
        assert result.account_holder_name.value == "John Doe"
        
        assert result.account_number is not None
        assert "****" in result.account_number.value  # Account number should be masked
        assert result.account_number.value.endswith("7890")
        
        assert result.statement_period_start is not None
        assert result.statement_period_start.value == "2023-12-01"
        
        assert result.statement_period_end is not None
        assert result.statement_period_end.value == "2023-12-31"
        
        assert result.beginning_balance is not None
        assert result.beginning_balance.value == 5000.00
        
        assert result.ending_balance is not None
        assert result.ending_balance.value == 6200.00
        
        assert result.total_deposits is not None
        assert result.total_deposits.value == 7500.00
        
        assert result.total_withdrawals is not None
        assert result.total_withdrawals.value == 6300.00
        
        assert result.account_holder_address is not None
        assert result.account_holder_address.value == "123 Main St, Springfield, IL 62701"
    
    def test_extract_bank_statement_partial_fields(self):
        """Test extraction with only some fields present."""
        from functions.extractor.app import extract_bank_statement_data
        
        partial_kvs = {
            "Bank Name": {"value": "Community Bank", "confidence": 0.96},
            "Account Holder": {"value": "Jane Smith", "confidence": 0.95},
            "Ending Balance": {"value": "$3,500.00", "confidence": 0.98}
        }
        
        result = extract_bank_statement_data(partial_kvs, [], "doc-456")
        
        # Verify extracted fields
        assert result.bank_name is not None
        assert result.bank_name.value == "Community Bank"
        
        assert result.account_holder_name is not None
        assert result.account_holder_name.value == "Jane Smith"
        
        assert result.ending_balance is not None
        assert result.ending_balance.value == 3500.00
        
        # Verify missing fields are None
        assert result.account_number is None
        assert result.beginning_balance is None
        assert result.total_deposits is None
    
    def test_extract_bank_statement_low_confidence_flagging(self):
        """Test that low confidence fields are flagged for manual review."""
        from functions.extractor.app import extract_bank_statement_data
        
        low_confidence_kvs = {
            "Bank Name": {"value": "Test Bank", "confidence": 0.75},  # Below 0.80 threshold
            "Ending Balance": {"value": "5000", "confidence": 0.95}  # Above threshold
        }
        
        result = extract_bank_statement_data(low_confidence_kvs, [], "doc-789")
        
        # Verify low confidence field is flagged
        assert result.bank_name.requires_manual_review is True
        assert result.ending_balance.requires_manual_review is False
    
    def test_extract_bank_statement_numeric_parsing(self):
        """Test numeric value parsing with various formats."""
        from functions.extractor.app import extract_bank_statement_data
        
        numeric_kvs = {
            "Beginning Balance": {"value": "$10,500.50", "confidence": 0.99},
            "Ending Balance": {"value": "12,750.25", "confidence": 0.98},
            "Total Deposits": {"value": "$5,000", "confidence": 0.97},
            "Total Withdrawals": {"value": "2750.25", "confidence": 0.96}
        }
        
        result = extract_bank_statement_data(numeric_kvs, [], "doc-numeric")
        
        # Verify numeric parsing
        assert result.beginning_balance.value == 10500.50
        assert result.ending_balance.value == 12750.25
        assert result.total_deposits.value == 5000.00
        assert result.total_withdrawals.value == 2750.25
    
    def test_extract_bank_statement_account_number_masking(self):
        """Test that account number is properly masked."""
        from functions.extractor.app import extract_bank_statement_data
        
        account_kvs = {
            "Account Number": {"value": "9876543210", "confidence": 0.99}
        }
        
        result = extract_bank_statement_data(account_kvs, [], "doc-acct")
        
        # Verify account number masking
        assert result.account_number is not None
        assert result.account_number.value == "****3210"
        assert "9876" not in result.account_number.value
    
    def test_extract_bank_statement_short_account_number(self):
        """Test masking of short account numbers."""
        from functions.extractor.app import extract_bank_statement_data
        
        short_account_kvs = {
            "Account Number": {"value": "123", "confidence": 0.99}
        }
        
        result = extract_bank_statement_data(short_account_kvs, [], "doc-short")
        
        # Verify short account number is not masked (less than 4 digits)
        assert result.account_number is not None
        assert result.account_number.value == "123"
    
    def test_extract_bank_statement_case_insensitive_matching(self):
        """Test that field matching is case-insensitive."""
        from functions.extractor.app import extract_bank_statement_data
        
        mixed_case_kvs = {
            "BANK NAME": {"value": "Capital Bank", "confidence": 0.96},
            "account holder": {"value": "Bob Smith", "confidence": 0.94},
            "EnDiNg BaLaNcE": {"value": "8000", "confidence": 0.98}
        }
        
        result = extract_bank_statement_data(mixed_case_kvs, [], "doc-case")
        
        # Verify case-insensitive matching worked
        assert result.bank_name is not None
        assert result.bank_name.value == "Capital Bank"
        assert result.account_holder_name is not None
        assert result.account_holder_name.value == "Bob Smith"
        assert result.ending_balance is not None
        assert result.ending_balance.value == 8000.00
    
    def test_extract_bank_statement_empty_kvs(self):
        """Test extraction with empty key-value pairs."""
        from functions.extractor.app import extract_bank_statement_data
        
        result = extract_bank_statement_data({}, [], "doc-empty")
        
        # Verify all fields are None
        assert result.bank_name is None
        assert result.account_holder_name is None
        assert result.account_number is None
        assert result.ending_balance is None
    
    def test_extract_bank_statement_confidence_scores_preserved(self):
        """Test that confidence scores are preserved in extracted fields."""
        from functions.extractor.app import extract_bank_statement_data
        
        confidence_kvs = {
            "Bank Name": {"value": "Trust Bank", "confidence": 0.92},
            "Ending Balance": {"value": "4500", "confidence": 0.88}
        }
        
        result = extract_bank_statement_data(confidence_kvs, [], "doc-conf")
        
        # Verify confidence scores are preserved
        assert result.bank_name.confidence == 0.92
        assert result.ending_balance.confidence == 0.88
    
    def test_extract_bank_statement_negative_balance(self):
        """Test extraction of negative balance values."""
        from functions.extractor.app import extract_bank_statement_data
        
        negative_kvs = {
            "Beginning Balance": {"value": "($500.00)", "confidence": 0.98},
            "Ending Balance": {"value": "-250.50", "confidence": 0.97}
        }
        
        result = extract_bank_statement_data(negative_kvs, [], "doc-negative")
        
        # Verify negative values are parsed correctly
        assert result.beginning_balance is not None
        assert result.beginning_balance.value == -500.00
        assert result.ending_balance is not None
        assert result.ending_balance.value == -250.50
    
    def test_extract_bank_statement_alternative_field_names(self):
        """Test extraction with alternative field name patterns."""
        from functions.extractor.app import extract_bank_statement_data
        
        alternative_kvs = {
            "Financial Institution": {"value": "Regional Bank", "confidence": 0.96},
            "Customer Name": {"value": "Alice Johnson", "confidence": 0.95},
            "Acct Number": {"value": "5555666677", "confidence": 0.98},
            "Closing Balance": {"value": "7500", "confidence": 0.97},
            "Opening Balance": {"value": "6000", "confidence": 0.96}
        }
        
        result = extract_bank_statement_data(alternative_kvs, [], "doc-alt")
        
        # Verify alternative field names are recognized
        assert result.bank_name is not None
        assert result.bank_name.value == "Regional Bank"
        assert result.account_holder_name is not None
        assert result.account_holder_name.value == "Alice Johnson"
        assert result.account_number is not None
        assert result.account_number.value == "****6677"
        assert result.ending_balance is not None
        assert result.ending_balance.value == 7500.00
        assert result.beginning_balance is not None
        assert result.beginning_balance.value == 6000.00
    
    def test_extract_bank_statement_document_type(self):
        """Test that document_type is correctly set."""
        from functions.extractor.app import extract_bank_statement_data
        
        result = extract_bank_statement_data({}, [], "doc-type")
        
        # Verify document type
        assert result.document_type == "BANK_STATEMENT"
    
    def test_extract_bank_statement_to_dict_serialization(self):
        """Test that extracted data can be serialized to dictionary."""
        from functions.extractor.app import extract_bank_statement_data
        
        kvs = {
            "Bank Name": {"value": "Test Bank", "confidence": 0.95},
            "Ending Balance": {"value": "1000", "confidence": 0.90}
        }
        
        result = extract_bank_statement_data(kvs, [], "doc-serial")
        result_dict = result.to_dict()
        
        # Verify serialization
        assert isinstance(result_dict, dict)
        assert result_dict["document_type"] == "BANK_STATEMENT"
        assert "bank_name" in result_dict
        assert result_dict["bank_name"]["value"] == "Test Bank"
        assert result_dict["bank_name"]["confidence"] == 0.95
        assert "ending_balance" in result_dict
        assert result_dict["ending_balance"]["value"] == 1000.00



class TestTaxFormExtraction:
    """Test cases for Tax Form (1040) data extraction."""
    
    @pytest.fixture
    def sample_tax_form_kvs(self):
        """Sample key-value pairs for Tax Form (1040)."""
        return {
            "Form": {"value": "1040", "confidence": 0.99},
            "Tax Year": {"value": "2023", "confidence": 0.99},
            "Your Name": {"value": "John Doe", "confidence": 0.98},
            "Your Social Security Number": {"value": "123-45-6789", "confidence": 0.99},
            "Spouse Name": {"value": "Jane Doe", "confidence": 0.97},
            "Filing Status": {"value": "Married Filing Jointly", "confidence": 0.98},
            "Home Address": {"value": "123 Main St, Springfield, IL 62701", "confidence": 0.95},
            "Wages, salaries, tips": {"value": "75000.00", "confidence": 0.98},
            "Adjusted Gross Income": {"value": "75000.00", "confidence": 0.98},
            "Taxable Income": {"value": "62000.00", "confidence": 0.97},
            "Total Tax": {"value": "9500.00", "confidence": 0.98},
            "Federal Income Tax Withheld": {"value": "12000.00", "confidence": 0.98},
            "Refund": {"value": "2500.00", "confidence": 0.98}
        }
    
    def test_extract_tax_form_all_fields(self, sample_tax_form_kvs):
        """Test extraction of all Tax Form fields."""
        from functions.extractor.app import extract_tax_form_data
        
        result = extract_tax_form_data(sample_tax_form_kvs, [], "doc-123")
        
        # Verify all fields were extracted
        assert result.form_type is not None
        assert result.form_type.value == "1040"
        assert result.form_type.confidence == 0.99
        
        assert result.tax_year is not None
        assert result.tax_year.value == "2023"
        
        assert result.taxpayer_name is not None
        assert result.taxpayer_name.value == "John Doe"
        
        assert result.taxpayer_ssn is not None
        assert "***-**-" in result.taxpayer_ssn.value  # SSN should be masked
        assert result.taxpayer_ssn.value.endswith("6789")
        
        assert result.spouse_name is not None
        assert result.spouse_name.value == "Jane Doe"
        
        assert result.filing_status is not None
        assert result.filing_status.value == "Married Filing Jointly"
        
        assert result.address is not None
        assert result.address.value == "123 Main St, Springfield, IL 62701"
        
        assert result.wages_salaries is not None
        assert result.wages_salaries.value == 75000.00
        
        assert result.adjusted_gross_income is not None
        assert result.adjusted_gross_income.value == 75000.00
        
        assert result.taxable_income is not None
        assert result.taxable_income.value == 62000.00
        
        assert result.total_tax is not None
        assert result.total_tax.value == 9500.00
        
        assert result.federal_tax_withheld is not None
        assert result.federal_tax_withheld.value == 12000.00
        
        assert result.refund_amount is not None
        assert result.refund_amount.value == 2500.00
    
    def test_extract_tax_form_partial_fields(self):
        """Test extraction with only some fields present."""
        from functions.extractor.app import extract_tax_form_data
        
        partial_kvs = {
            "Taxpayer Name": {"value": "Jane Smith", "confidence": 0.95},
            "Tax Year": {"value": "2023", "confidence": 0.99},
            "Adjusted Gross Income": {"value": "$50,000.00", "confidence": 0.98}
        }
        
        result = extract_tax_form_data(partial_kvs, [], "doc-456")
        
        # Verify extracted fields
        assert result.taxpayer_name is not None
        assert result.taxpayer_name.value == "Jane Smith"
        
        assert result.tax_year is not None
        assert result.tax_year.value == "2023"
        
        assert result.adjusted_gross_income is not None
        assert result.adjusted_gross_income.value == 50000.00  # Currency formatting removed
        
        # Verify missing fields are None
        assert result.spouse_name is None
        assert result.federal_tax_withheld is None
    
    def test_extract_tax_form_low_confidence_flagging(self):
        """Test that low confidence fields are flagged for manual review."""
        from functions.extractor.app import extract_tax_form_data
        
        low_confidence_kvs = {
            "Taxpayer Name": {"value": "John Doe", "confidence": 0.75},  # Below 0.80 threshold
            "Adjusted Gross Income": {"value": "60000", "confidence": 0.95}  # Above threshold
        }
        
        result = extract_tax_form_data(low_confidence_kvs, [], "doc-789")
        
        # Verify low confidence field is flagged
        assert result.taxpayer_name.requires_manual_review is True
        assert result.adjusted_gross_income.requires_manual_review is False
    
    def test_extract_tax_form_numeric_parsing(self):
        """Test numeric value parsing with various formats."""
        from functions.extractor.app import extract_tax_form_data
        
        numeric_kvs = {
            "Wages": {"value": "$75,000.00", "confidence": 0.99},
            "AGI": {"value": "72,500", "confidence": 0.98},
            "Total Tax": {"value": "9500.50", "confidence": 0.97}
        }
        
        result = extract_tax_form_data(numeric_kvs, [], "doc-numeric")
        
        # Verify numeric parsing
        assert result.wages_salaries.value == 75000.00
        assert result.adjusted_gross_income.value == 72500.00
        assert result.total_tax.value == 9500.50
    
    def test_extract_tax_form_ssn_masking(self):
        """Test that SSN is properly masked."""
        from functions.extractor.app import extract_tax_form_data
        
        ssn_kvs = {
            "Social Security Number": {"value": "987-65-4321", "confidence": 0.99}
        }
        
        result = extract_tax_form_data(ssn_kvs, [], "doc-ssn")
        
        # Verify SSN masking
        assert result.taxpayer_ssn is not None
        assert result.taxpayer_ssn.value == "***-**-4321"
        assert "987" not in result.taxpayer_ssn.value
    
    def test_extract_tax_form_short_ssn(self):
        """Test masking of short SSN values."""
        from functions.extractor.app import extract_tax_form_data
        
        short_ssn_kvs = {
            "SSN": {"value": "123", "confidence": 0.99}
        }
        
        result = extract_tax_form_data(short_ssn_kvs, [], "doc-short")
        
        # Verify short SSN is not masked (less than 4 digits)
        assert result.taxpayer_ssn is not None
        assert result.taxpayer_ssn.value == "123"
    
    def test_extract_tax_form_case_insensitive_matching(self):
        """Test that field matching is case-insensitive."""
        from functions.extractor.app import extract_tax_form_data
        
        mixed_case_kvs = {
            "TAXPAYER NAME": {"value": "Bob Smith", "confidence": 0.96},
            "filing status": {"value": "Single", "confidence": 0.94},
            "AdJuStEd GrOsS iNcOmE": {"value": "80000", "confidence": 0.98}
        }
        
        result = extract_tax_form_data(mixed_case_kvs, [], "doc-case")
        
        # Verify case-insensitive matching worked
        assert result.taxpayer_name is not None
        assert result.taxpayer_name.value == "Bob Smith"
        assert result.filing_status is not None
        assert result.filing_status.value == "Single"
        assert result.adjusted_gross_income is not None
        assert result.adjusted_gross_income.value == 80000.00
    
    def test_extract_tax_form_empty_kvs(self):
        """Test extraction with empty key-value pairs."""
        from functions.extractor.app import extract_tax_form_data
        
        result = extract_tax_form_data({}, [], "doc-empty")
        
        # Verify all fields are None
        assert result.form_type is None
        assert result.tax_year is None
        assert result.taxpayer_name is None
        assert result.adjusted_gross_income is None
    
    def test_extract_tax_form_confidence_scores_preserved(self):
        """Test that confidence scores are preserved in extracted fields."""
        from functions.extractor.app import extract_tax_form_data
        
        confidence_kvs = {
            "Taxpayer Name": {"value": "Alice Johnson", "confidence": 0.92},
            "Adjusted Gross Income": {"value": "65000", "confidence": 0.88}
        }
        
        result = extract_tax_form_data(confidence_kvs, [], "doc-conf")
        
        # Verify confidence scores are preserved
        assert result.taxpayer_name.confidence == 0.92
        assert result.adjusted_gross_income.confidence == 0.88
    
    def test_extract_tax_form_single_filing_status(self):
        """Test extraction with single filing status (no spouse)."""
        from functions.extractor.app import extract_tax_form_data
        
        single_kvs = {
            "Taxpayer Name": {"value": "John Single", "confidence": 0.98},
            "Filing Status": {"value": "Single", "confidence": 0.99},
            "Adjusted Gross Income": {"value": "55000", "confidence": 0.97}
        }
        
        result = extract_tax_form_data(single_kvs, [], "doc-single")
        
        # Verify single filer data
        assert result.taxpayer_name is not None
        assert result.taxpayer_name.value == "John Single"
        assert result.filing_status is not None
        assert result.filing_status.value == "Single"
        assert result.spouse_name is None  # No spouse for single filer
    
    def test_extract_tax_form_alternative_field_names(self):
        """Test extraction with alternative field name patterns."""
        from functions.extractor.app import extract_tax_form_data
        
        alternative_kvs = {
            "Form 1040": {"value": "1040", "confidence": 0.99},
            "For the year": {"value": "2023", "confidence": 0.98},
            "First name and initial": {"value": "Robert J.", "confidence": 0.96},
            "Line 11": {"value": "70000", "confidence": 0.97},  # AGI line
            "Line 24": {"value": "8500", "confidence": 0.96},  # Total tax line
            "Line 25": {"value": "10000", "confidence": 0.95}  # Federal tax withheld line
        }
        
        result = extract_tax_form_data(alternative_kvs, [], "doc-alt")
        
        # Verify alternative field names are recognized
        assert result.form_type is not None
        assert result.form_type.value == "1040"
        assert result.tax_year is not None
        assert result.tax_year.value == "2023"
        assert result.taxpayer_name is not None
        assert result.taxpayer_name.value == "Robert J."
        assert result.adjusted_gross_income is not None
        assert result.adjusted_gross_income.value == 70000.00
        assert result.total_tax is not None
        assert result.total_tax.value == 8500.00
        assert result.federal_tax_withheld is not None
        assert result.federal_tax_withheld.value == 10000.00
    
    def test_extract_tax_form_document_type(self):
        """Test that document_type is correctly set."""
        from functions.extractor.app import extract_tax_form_data
        
        result = extract_tax_form_data({}, [], "doc-type")
        
        # Verify document type
        assert result.document_type == "TAX_FORM"
    
    def test_extract_tax_form_to_dict_serialization(self):
        """Test that extracted data can be serialized to dictionary."""
        from functions.extractor.app import extract_tax_form_data
        
        kvs = {
            "Taxpayer Name": {"value": "Test User", "confidence": 0.95},
            "Adjusted Gross Income": {"value": "50000", "confidence": 0.90}
        }
        
        result = extract_tax_form_data(kvs, [], "doc-serial")
        result_dict = result.to_dict()
        
        # Verify serialization
        assert isinstance(result_dict, dict)
        assert result_dict["document_type"] == "TAX_FORM"
        assert "taxpayer_name" in result_dict
        assert result_dict["taxpayer_name"]["value"] == "Test User"
        assert result_dict["taxpayer_name"]["confidence"] == 0.95
        assert "adjusted_gross_income" in result_dict
        assert result_dict["adjusted_gross_income"]["value"] == 50000.00
    
    def test_extract_tax_form_exclude_spouse_from_taxpayer_ssn(self):
        """Test that spouse-related fields don't interfere with taxpayer SSN extraction."""
        from functions.extractor.app import extract_tax_form_data
        
        kvs = {
            "Your Social Security Number": {"value": "111-22-3333", "confidence": 0.99},
            "Spouse Social Security Number": {"value": "444-55-6666", "confidence": 0.98}
        }
        
        result = extract_tax_form_data(kvs, [], "doc-spouse-ssn")
        
        # Verify taxpayer SSN is extracted correctly (not spouse SSN)
        assert result.taxpayer_ssn is not None
        assert result.taxpayer_ssn.value == "***-**-3333"
        assert "6666" not in result.taxpayer_ssn.value
    
    def test_extract_tax_form_exclude_spouse_from_taxpayer_name(self):
        """Test that spouse name doesn't interfere with taxpayer name extraction."""
        from functions.extractor.app import extract_tax_form_data
        
        kvs = {
            "Your Name": {"value": "John Taxpayer", "confidence": 0.98},
            "Spouse Name": {"value": "Jane Spouse", "confidence": 0.97}
        }
        
        result = extract_tax_form_data(kvs, [], "doc-spouse-name")
        
        # Verify taxpayer name is extracted correctly (not spouse name)
        assert result.taxpayer_name is not None
        assert result.taxpayer_name.value == "John Taxpayer"
        assert result.spouse_name is not None
        assert result.spouse_name.value == "Jane Spouse"
    
    def test_extract_tax_form_form_type_extraction(self):
        """Test that form type is extracted correctly from various patterns."""
        from functions.extractor.app import extract_tax_form_data
        
        # Test with "Form 1040" pattern
        kvs1 = {"Form 1040": {"value": "Form 1040", "confidence": 0.99}}
        result1 = extract_tax_form_data(kvs1, [], "doc-form1")
        assert result1.form_type is not None
        assert "1040" in result1.form_type.value
        
        # Test with just "1040" pattern
        kvs2 = {"Form": {"value": "1040", "confidence": 0.99}}
        result2 = extract_tax_form_data(kvs2, [], "doc-form2")
        assert result2.form_type is not None
        assert result2.form_type.value == "1040"
    
    def test_extract_tax_form_exclude_withheld_from_total_tax(self):
        """Test that 'withheld' and 'refund' patterns don't interfere with total tax extraction."""
        from functions.extractor.app import extract_tax_form_data
        
        kvs = {
            "Total Tax": {"value": "9000", "confidence": 0.98},
            "Federal Tax Withheld": {"value": "11000", "confidence": 0.97},
            "Refund": {"value": "2000", "confidence": 0.96}
        }
        
        result = extract_tax_form_data(kvs, [], "doc-tax-exclude")
        
        # Verify total tax is extracted correctly (not withheld or refund)
        assert result.total_tax is not None
        assert result.total_tax.value == 9000.00
        assert result.federal_tax_withheld is not None
        assert result.federal_tax_withheld.value == 11000.00
        assert result.refund_amount is not None
        assert result.refund_amount.value == 2000.00
    
    def test_extract_tax_form_various_filing_statuses(self):
        """Test extraction of various filing status values."""
        from functions.extractor.app import extract_tax_form_data
        
        filing_statuses = [
            "Single",
            "Married Filing Jointly",
            "Married Filing Separately",
            "Head of Household",
            "Qualifying Widow(er)"
        ]
        
        for status in filing_statuses:
            kvs = {"Filing Status": {"value": status, "confidence": 0.98}}
            result = extract_tax_form_data(kvs, [], f"doc-{status.replace(' ', '-')}")
            
            assert result.filing_status is not None
            assert result.filing_status.value == status



class TestDriversLicenseExtraction:
    """Test cases for Driver's License data extraction."""
    
    @pytest.fixture
    def sample_drivers_license_kvs(self):
        """Sample key-value pairs for Driver's License."""
        return {
            "State": {"value": "IL", "confidence": 0.99},
            "License Number": {"value": "D123-4567-8901", "confidence": 0.98},
            "Name": {"value": "John Doe", "confidence": 0.98},
            "Date of Birth": {"value": "1985-06-15", "confidence": 0.99},
            "Address": {"value": "123 Main St, Springfield, IL 62701", "confidence": 0.95},
            "Issue Date": {"value": "2020-06-15", "confidence": 0.97},
            "Expiration Date": {"value": "2025-06-15", "confidence": 0.97},
            "Sex": {"value": "M", "confidence": 0.99},
            "Height": {"value": "5'10\"", "confidence": 0.95},
            "Eye Color": {"value": "BRN", "confidence": 0.96}
        }
    
    def test_extract_drivers_license_all_fields(self, sample_drivers_license_kvs):
        """Test extraction of all Driver's License fields."""
        from functions.extractor.app import extract_drivers_license_data
        
        result = extract_drivers_license_data(sample_drivers_license_kvs, [], "doc-123")
        
        # Verify all fields were extracted
        assert result.state is not None
        assert result.state.value == "IL"
        assert result.state.confidence == 0.99
        
        assert result.license_number is not None
        assert result.license_number.value == "D123-4567-8901"
        assert result.license_number.confidence == 0.98
        
        assert result.full_name is not None
        assert result.full_name.value == "John Doe"
        assert result.full_name.confidence == 0.98
        
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1985-06-15"
        assert result.date_of_birth.confidence == 0.99
        
        assert result.address is not None
        assert result.address.value == "123 Main St, Springfield, IL 62701"
        assert result.address.confidence == 0.95
        
        assert result.issue_date is not None
        assert result.issue_date.value == "2020-06-15"
        assert result.issue_date.confidence == 0.97
        
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2025-06-15"
        assert result.expiration_date.confidence == 0.97
        
        assert result.sex is not None
        assert result.sex.value == "M"
        assert result.sex.confidence == 0.99
        
        assert result.height is not None
        assert result.height.value == "5'10\""
        assert result.height.confidence == 0.95
        
        assert result.eye_color is not None
        assert result.eye_color.value == "BRN"
        assert result.eye_color.confidence == 0.96
    
    def test_extract_drivers_license_required_fields_only(self):
        """Test extraction with only required fields (name, DOB, license number, address, expiration)."""
        from functions.extractor.app import extract_drivers_license_data
        
        required_kvs = {
            "Full Name": {"value": "Jane Smith", "confidence": 0.97},
            "DOB": {"value": "1990-03-20", "confidence": 0.98},
            "DL Number": {"value": "S987654321", "confidence": 0.96},
            "Address": {"value": "456 Oak Ave, Chicago, IL 60601", "confidence": 0.94},
            "Expiration": {"value": "2026-03-20", "confidence": 0.95},
            "State": {"value": "IL", "confidence": 0.99}
        }
        
        result = extract_drivers_license_data(required_kvs, [], "doc-456")
        
        # Verify required fields were extracted
        assert result.full_name is not None
        assert result.full_name.value == "Jane Smith"
        
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1990-03-20"
        
        assert result.license_number is not None
        assert result.license_number.value == "S987654321"
        
        assert result.address is not None
        assert result.address.value == "456 Oak Ave, Chicago, IL 60601"
        
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2026-03-20"
        
        assert result.state is not None
        assert result.state.value == "IL"
        
        # Verify optional fields are None
        assert result.sex is None
        assert result.height is None
        assert result.eye_color is None
    
    def test_extract_drivers_license_low_confidence_flagging(self):
        """Test that low confidence fields are flagged for manual review."""
        from functions.extractor.app import extract_drivers_license_data
        
        low_confidence_kvs = {
            "Name": {"value": "John Doe", "confidence": 0.75},  # Below 0.80 threshold
            "License Number": {"value": "D123456", "confidence": 0.95},  # Above threshold
            "Address": {"value": "123 Main St", "confidence": 0.78}  # Below threshold
        }
        
        result = extract_drivers_license_data(low_confidence_kvs, [], "doc-789")
        
        # Verify low confidence fields are flagged
        assert result.full_name.requires_manual_review is True
        assert result.license_number.requires_manual_review is False
        assert result.address.requires_manual_review is True
    
    def test_extract_drivers_license_case_insensitive_matching(self):
        """Test that field matching is case-insensitive."""
        from functions.extractor.app import extract_drivers_license_data
        
        mixed_case_kvs = {
            "NAME": {"value": "Bob Smith", "confidence": 0.96},
            "license number": {"value": "L555666777", "confidence": 0.94},
            "DaTe Of BiRtH": {"value": "1988-12-10", "confidence": 0.98},
            "STATE": {"value": "CA", "confidence": 0.99}
        }
        
        result = extract_drivers_license_data(mixed_case_kvs, [], "doc-case")
        
        # Verify case-insensitive matching worked
        assert result.full_name is not None
        assert result.full_name.value == "Bob Smith"
        assert result.license_number is not None
        assert result.license_number.value == "L555666777"
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1988-12-10"
        assert result.state is not None
        assert result.state.value == "CA"
    
    def test_extract_drivers_license_empty_kvs(self):
        """Test extraction with empty key-value pairs."""
        from functions.extractor.app import extract_drivers_license_data
        
        result = extract_drivers_license_data({}, [], "doc-empty")
        
        # Verify all fields are None
        assert result.state is None
        assert result.license_number is None
        assert result.full_name is None
        assert result.date_of_birth is None
        assert result.address is None
        assert result.issue_date is None
        assert result.expiration_date is None
        assert result.sex is None
        assert result.height is None
        assert result.eye_color is None
    
    def test_extract_drivers_license_confidence_scores_preserved(self):
        """Test that confidence scores are preserved in extracted fields."""
        from functions.extractor.app import extract_drivers_license_data
        
        confidence_kvs = {
            "Name": {"value": "Alice Johnson", "confidence": 0.92},
            "License Number": {"value": "J123456789", "confidence": 0.88},
            "State": {"value": "TX", "confidence": 0.95}
        }
        
        result = extract_drivers_license_data(confidence_kvs, [], "doc-conf")
        
        # Verify confidence scores are preserved
        assert result.full_name.confidence == 0.92
        assert result.license_number.confidence == 0.88
        assert result.state.confidence == 0.95
    
    def test_extract_drivers_license_alternative_field_names(self):
        """Test extraction with alternative field name patterns."""
        from functions.extractor.app import extract_drivers_license_data
        
        alternative_kvs = {
            "Driver Name": {"value": "Robert Brown", "confidence": 0.96},
            "DL#": {"value": "B987654321", "confidence": 0.95},
            "Birth Date": {"value": "1992-08-25", "confidence": 0.98},
            "Residence": {"value": "789 Pine St, Austin, TX 78701", "confidence": 0.93},
            "Iss": {"value": "2018-08-25", "confidence": 0.94},
            "Exp": {"value": "2026-08-25", "confidence": 0.94},
            "Gender": {"value": "M", "confidence": 0.99},
            "Hgt": {"value": "6'2\"", "confidence": 0.92},
            "Eyes": {"value": "BLU", "confidence": 0.95},
            "ST": {"value": "TX", "confidence": 0.99}
        }
        
        result = extract_drivers_license_data(alternative_kvs, [], "doc-alt")
        
        # Verify alternative field names are recognized
        assert result.full_name is not None
        assert result.full_name.value == "Robert Brown"
        assert result.license_number is not None
        assert result.license_number.value == "B987654321"
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1992-08-25"
        assert result.address is not None
        assert result.address.value == "789 Pine St, Austin, TX 78701"
        assert result.issue_date is not None
        assert result.issue_date.value == "2018-08-25"
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2026-08-25"
        assert result.sex is not None
        assert result.sex.value == "M"
        assert result.height is not None
        assert result.height.value == "6'2\""
        assert result.eye_color is not None
        assert result.eye_color.value == "BLU"
        assert result.state is not None
        assert result.state.value == "TX"
    
    def test_extract_drivers_license_document_type(self):
        """Test that document_type is correctly set."""
        from functions.extractor.app import extract_drivers_license_data
        
        result = extract_drivers_license_data({}, [], "doc-type")
        
        # Verify document type
        assert result.document_type == "DRIVERS_LICENSE"
    
    def test_extract_drivers_license_to_dict_serialization(self):
        """Test that extracted data can be serialized to dictionary."""
        from functions.extractor.app import extract_drivers_license_data
        
        kvs = {
            "Name": {"value": "Test Driver", "confidence": 0.95},
            "License Number": {"value": "T123456789", "confidence": 0.90},
            "State": {"value": "NY", "confidence": 0.98}
        }
        
        result = extract_drivers_license_data(kvs, [], "doc-serial")
        result_dict = result.to_dict()
        
        # Verify serialization
        assert isinstance(result_dict, dict)
        assert result_dict["document_type"] == "DRIVERS_LICENSE"
        assert "full_name" in result_dict
        assert result_dict["full_name"]["value"] == "Test Driver"
        assert result_dict["full_name"]["confidence"] == 0.95
        assert "license_number" in result_dict
        assert result_dict["license_number"]["value"] == "T123456789"
        assert "state" in result_dict
        assert result_dict["state"]["value"] == "NY"
    
    def test_extract_drivers_license_various_states(self):
        """Test extraction with various state abbreviations."""
        from functions.extractor.app import extract_drivers_license_data
        
        states = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
        
        for state in states:
            kvs = {
                "State": {"value": state, "confidence": 0.99},
                "Name": {"value": "Test Person", "confidence": 0.95}
            }
            result = extract_drivers_license_data(kvs, [], f"doc-{state}")
            
            assert result.state is not None
            assert result.state.value == state
    
    def test_extract_drivers_license_various_date_formats(self):
        """Test extraction with various date formats."""
        from functions.extractor.app import extract_drivers_license_data
        
        date_formats = [
            "1985-06-15",
            "06/15/1985",
            "06-15-1985",
            "15 Jun 1985",
            "June 15, 1985"
        ]
        
        for date_format in date_formats:
            kvs = {
                "Date of Birth": {"value": date_format, "confidence": 0.98},
                "Issue Date": {"value": date_format, "confidence": 0.97},
                "Expiration Date": {"value": date_format, "confidence": 0.96}
            }
            result = extract_drivers_license_data(kvs, [], f"doc-date-{date_formats.index(date_format)}")
            
            # Verify dates are extracted (format validation is not part of extraction)
            assert result.date_of_birth is not None
            assert result.date_of_birth.value == date_format
            assert result.issue_date is not None
            assert result.issue_date.value == date_format
            assert result.expiration_date is not None
            assert result.expiration_date.value == date_format
    
    def test_extract_drivers_license_various_sex_values(self):
        """Test extraction with various sex/gender values."""
        from functions.extractor.app import extract_drivers_license_data
        
        sex_values = ["M", "F", "Male", "Female", "X"]
        
        for sex in sex_values:
            kvs = {"Sex": {"value": sex, "confidence": 0.99}}
            result = extract_drivers_license_data(kvs, [], f"doc-sex-{sex}")
            
            assert result.sex is not None
            assert result.sex.value == sex
    
    def test_extract_drivers_license_various_height_formats(self):
        """Test extraction with various height formats."""
        from functions.extractor.app import extract_drivers_license_data
        
        height_formats = [
            "5'10\"",
            "5-10",
            "510",
            "5 ft 10 in",
            "178 cm"
        ]
        
        for height in height_formats:
            kvs = {"Height": {"value": height, "confidence": 0.95}}
            result = extract_drivers_license_data(kvs, [], f"doc-height-{height_formats.index(height)}")
            
            assert result.height is not None
            assert result.height.value == height
    
    def test_extract_drivers_license_various_eye_colors(self):
        """Test extraction with various eye color codes."""
        from functions.extractor.app import extract_drivers_license_data
        
        eye_colors = ["BRN", "BLU", "GRN", "HAZ", "GRY", "BLK"]
        
        for eye_color in eye_colors:
            kvs = {"Eye Color": {"value": eye_color, "confidence": 0.96}}
            result = extract_drivers_license_data(kvs, [], f"doc-eye-{eye_color}")
            
            assert result.eye_color is not None
            assert result.eye_color.value == eye_color
    
    def test_extract_drivers_license_exclude_patterns(self):
        """Test that exclude patterns work correctly to avoid field confusion."""
        from functions.extractor.app import extract_drivers_license_data
        
        # Test that "statement" doesn't match "state"
        kvs = {
            "State": {"value": "CA", "confidence": 0.99},
            "Statement Period": {"value": "2023-01-01", "confidence": 0.95}
        }
        result = extract_drivers_license_data(kvs, [], "doc-exclude-state")
        
        assert result.state is not None
        assert result.state.value == "CA"
        
        # Test that "issuing authority" doesn't match "issue date"
        kvs2 = {
            "Issue Date": {"value": "2020-01-01", "confidence": 0.97},
            "Issuing Authority": {"value": "DMV", "confidence": 0.95}
        }
        result2 = extract_drivers_license_data(kvs2, [], "doc-exclude-issue")
        
        assert result2.issue_date is not None
        assert result2.issue_date.value == "2020-01-01"
    
    def test_extract_drivers_license_partial_extraction(self):
        """Test extraction with only a few fields present."""
        from functions.extractor.app import extract_drivers_license_data
        
        partial_kvs = {
            "Name": {"value": "Partial Data", "confidence": 0.90},
            "State": {"value": "FL", "confidence": 0.98}
        }
        
        result = extract_drivers_license_data(partial_kvs, [], "doc-partial")
        
        # Verify extracted fields
        assert result.full_name is not None
        assert result.full_name.value == "Partial Data"
        assert result.state is not None
        assert result.state.value == "FL"
        
        # Verify missing fields are None
        assert result.license_number is None
        assert result.date_of_birth is None
        assert result.address is None
        assert result.issue_date is None
        assert result.expiration_date is None
        assert result.sex is None
        assert result.height is None
        assert result.eye_color is None
    
    def test_extract_drivers_license_dmv_specific_fields(self):
        """Test extraction of DMV-specific fields like restrictions and endorsements."""
        from functions.extractor.app import extract_drivers_license_data
        
        # Note: The current schema includes sex, height, eye_color as DMV-specific fields
        dmv_kvs = {
            "Name": {"value": "DMV Test", "confidence": 0.95},
            "License Number": {"value": "D999888777", "confidence": 0.96},
            "Sex": {"value": "F", "confidence": 0.99},
            "Height": {"value": "5'6\"", "confidence": 0.94},
            "Eye Color": {"value": "GRN", "confidence": 0.95},
            "State": {"value": "WA", "confidence": 0.99}
        }
        
        result = extract_drivers_license_data(dmv_kvs, [], "doc-dmv")
        
        # Verify DMV-specific fields are extracted
        assert result.sex is not None
        assert result.sex.value == "F"
        assert result.height is not None
        assert result.height.value == "5'6\""
        assert result.eye_color is not None
        assert result.eye_color.value == "GRN"
    
    def test_extract_drivers_license_multiline_address(self):
        """Test extraction of multi-line addresses."""
        from functions.extractor.app import extract_drivers_license_data
        
        multiline_kvs = {
            "Address": {"value": "123 Main Street Apt 4B Springfield, IL 62701", "confidence": 0.93}
        }
        
        result = extract_drivers_license_data(multiline_kvs, [], "doc-multiline")
        
        # Verify multi-line address is extracted as-is
        assert result.address is not None
        assert "123 Main Street" in result.address.value
        assert "Springfield" in result.address.value
        assert "62701" in result.address.value
    
    def test_extract_drivers_license_license_number_formats(self):
        """Test extraction with various license number formats from different states."""
        from functions.extractor.app import extract_drivers_license_data
        
        license_formats = [
            "D123-4567-8901",  # Illinois format
            "A1234567",  # California format
            "12345678",  # Texas format
            "H123-456-789-012",  # Florida format
            "123456789012"  # New York format
        ]
        
        for lic_num in license_formats:
            kvs = {"License Number": {"value": lic_num, "confidence": 0.97}}
            result = extract_drivers_license_data(kvs, [], f"doc-lic-{license_formats.index(lic_num)}")
            
            assert result.license_number is not None
            assert result.license_number.value == lic_num



class TestIDDocumentExtraction:
    """Test cases for ID Document data extraction."""
    
    @pytest.fixture
    def sample_passport_kvs(self):
        """Sample key-value pairs for a passport."""
        return {
            "Passport Number": {"value": "123456789", "confidence": 0.98},
            "Surname": {"value": "Doe", "confidence": 0.97},
            "Given Name": {"value": "John", "confidence": 0.97},
            "Date of Birth": {"value": "1985-06-15", "confidence": 0.99},
            "Issuing Authority": {"value": "U.S. Department of State", "confidence": 0.96},
            "Date of Issue": {"value": "2019-01-15", "confidence": 0.97},
            "Date of Expiry": {"value": "2029-01-15", "confidence": 0.97},
            "Nationality": {"value": "USA", "confidence": 0.98}
        }
    
    @pytest.fixture
    def sample_state_id_kvs(self):
        """Sample key-value pairs for a state ID."""
        return {
            "State ID Number": {"value": "S123456789", "confidence": 0.97},
            "Full Name": {"value": "Jane Smith", "confidence": 0.96},
            "Date of Birth": {"value": "1990-03-22", "confidence": 0.98},
            "Issuing State": {"value": "California", "confidence": 0.95},
            "Issue Date": {"value": "2020-05-10", "confidence": 0.96},
            "Expiration Date": {"value": "2025-05-10", "confidence": 0.96}
        }
    
    def test_extract_id_document_passport_all_fields(self, sample_passport_kvs):
        """Test extraction of all passport fields."""
        from functions.extractor.app import extract_id_document_data
        
        result = extract_id_document_data(sample_passport_kvs, [], "doc-passport-123")
        
        # Verify ID type detection
        assert result.id_type is not None
        assert result.id_type.value == "PASSPORT"
        assert result.id_type.confidence == 0.95
        
        # Verify all fields extracted
        assert result.document_number is not None
        assert result.document_number.value == "123456789"
        assert result.document_number.confidence == 0.98
        
        assert result.full_name is not None
        assert "Doe" in result.full_name.value or "John" in result.full_name.value
        
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1985-06-15"
        assert result.date_of_birth.confidence == 0.99
        
        assert result.issuing_authority is not None
        assert result.issuing_authority.value == "U.S. Department of State"
        assert result.issuing_authority.confidence == 0.96
        
        assert result.issue_date is not None
        assert result.issue_date.value == "2019-01-15"
        
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2029-01-15"
        
        assert result.nationality is not None
        assert result.nationality.value == "USA"
        assert result.nationality.confidence == 0.98
    
    def test_extract_id_document_state_id_all_fields(self, sample_state_id_kvs):
        """Test extraction of all state ID fields."""
        from functions.extractor.app import extract_id_document_data
        
        result = extract_id_document_data(sample_state_id_kvs, [], "doc-stateid-456")
        
        # Verify ID type detection
        assert result.id_type is not None
        assert result.id_type.value == "STATE_ID"
        assert result.id_type.confidence == 0.90
        
        # Verify all fields extracted
        assert result.document_number is not None
        assert result.document_number.value == "S123456789"
        
        assert result.full_name is not None
        assert result.full_name.value == "Jane Smith"
        
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1990-03-22"
        
        assert result.issuing_authority is not None
        assert result.issuing_authority.value == "California"
        
        assert result.issue_date is not None
        assert result.issue_date.value == "2020-05-10"
        
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2025-05-10"
    
    def test_extract_id_document_required_fields_only(self):
        """Test extraction with only required fields (name, DOB, document number, issuing authority, expiration)."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Document Number": {"value": "987654321", "confidence": 0.96},
            "Full Name": {"value": "Alice Johnson", "confidence": 0.95},
            "Date of Birth": {"value": "1988-11-30", "confidence": 0.97},
            "Issuing Authority": {"value": "State of Texas", "confidence": 0.94},
            "Expiration Date": {"value": "2026-12-31", "confidence": 0.95}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-789")
        
        # Verify required fields
        assert result.document_number is not None
        assert result.document_number.value == "987654321"
        
        assert result.full_name is not None
        assert result.full_name.value == "Alice Johnson"
        
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1988-11-30"
        
        assert result.issuing_authority is not None
        assert result.issuing_authority.value == "State of Texas"
        
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2026-12-31"
        
        # Optional fields should be None
        assert result.issue_date is None
        assert result.nationality is None
    
    def test_extract_id_document_low_confidence_flagging(self):
        """Test that low confidence fields are flagged for manual review."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Document Number": {"value": "123456", "confidence": 0.75},
            "Full Name": {"value": "Bob Brown", "confidence": 0.92},
            "Date of Birth": {"value": "1995-07-20", "confidence": 0.88}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-low-conf")
        
        # Low confidence field should be flagged
        assert result.document_number.requires_manual_review is True
        
        # High confidence fields should not be flagged
        assert result.full_name.requires_manual_review is False
        assert result.date_of_birth.requires_manual_review is False
    
    def test_extract_id_document_case_insensitive_matching(self):
        """Test that field matching is case-insensitive."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "DOCUMENT NUMBER": {"value": "ABC123", "confidence": 0.96},
            "full name": {"value": "Charlie Davis", "confidence": 0.94},
            "Date Of Birth": {"value": "1992-04-15", "confidence": 0.97},
            "EXPIRATION DATE": {"value": "2027-08-20", "confidence": 0.95}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-case")
        
        assert result.document_number is not None
        assert result.document_number.value == "ABC123"
        
        assert result.full_name is not None
        assert result.full_name.value == "Charlie Davis"
        
        assert result.date_of_birth is not None
        assert result.date_of_birth.value == "1992-04-15"
        
        assert result.expiration_date is not None
        assert result.expiration_date.value == "2027-08-20"
    
    def test_extract_id_document_empty_kvs(self):
        """Test extraction with empty key-value pairs."""
        from functions.extractor.app import extract_id_document_data
        
        result = extract_id_document_data({}, [], "doc-id-empty")
        
        # Should return IDDocumentData with only id_type set (default detection)
        assert result.document_type == "ID_DOCUMENT"
        assert result.id_type is not None  # Default type detection
        assert result.document_number is None
        assert result.full_name is None
        assert result.date_of_birth is None
        assert result.issuing_authority is None
        assert result.issue_date is None
        assert result.expiration_date is None
        assert result.nationality is None
    
    def test_extract_id_document_confidence_scores_preserved(self):
        """Test that confidence scores are preserved in extracted fields."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Document Number": {"value": "XYZ789", "confidence": 0.93},
            "Full Name": {"value": "Diana Evans", "confidence": 0.91}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-conf")
        
        assert result.document_number.confidence == 0.93
        assert result.full_name.confidence == 0.91
    
    def test_extract_id_document_alternative_field_names(self):
        """Test extraction with alternative field name patterns."""
        from functions.extractor.app import extract_id_document_data
        
        # Test various alternative field names
        kvs1 = {
            "ID Number": {"value": "ID123", "confidence": 0.95},
            "Holder Name": {"value": "Eve Foster", "confidence": 0.94},
            "Born": {"value": "1987-09-10", "confidence": 0.96},
            "Issued By": {"value": "Government Agency", "confidence": 0.93},
            "Valid Until": {"value": "2028-09-10", "confidence": 0.94}
        }
        
        result1 = extract_id_document_data(kvs1, [], "doc-id-alt1")
        
        assert result1.document_number is not None
        assert result1.document_number.value == "ID123"
        
        assert result1.full_name is not None
        assert result1.full_name.value == "Eve Foster"
        
        assert result1.date_of_birth is not None
        assert result1.date_of_birth.value == "1987-09-10"
        
        assert result1.issuing_authority is not None
        assert result1.issuing_authority.value == "Government Agency"
        
        assert result1.expiration_date is not None
        assert result1.expiration_date.value == "2028-09-10"
        
        # Test more alternatives
        kvs2 = {
            "Card Number": {"value": "CARD456", "confidence": 0.96},
            "Surname": {"value": "Garcia", "confidence": 0.95},
            "Birthdate": {"value": "1993-12-05", "confidence": 0.97},
            "Authority": {"value": "State Department", "confidence": 0.94},
            "Expires": {"value": "2029-12-05", "confidence": 0.95}
        }
        
        result2 = extract_id_document_data(kvs2, [], "doc-id-alt2")
        
        assert result2.document_number is not None
        assert result2.document_number.value == "CARD456"
        
        assert result2.full_name is not None
        assert result2.full_name.value == "Garcia"
        
        assert result2.date_of_birth is not None
        assert result2.date_of_birth.value == "1993-12-05"
        
        assert result2.issuing_authority is not None
        assert result2.issuing_authority.value == "State Department"
        
        assert result2.expiration_date is not None
        assert result2.expiration_date.value == "2029-12-05"
    
    def test_extract_id_document_document_type(self):
        """Test that document_type is correctly set."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {"Document Number": {"value": "TEST123", "confidence": 0.95}}
        result = extract_id_document_data(kvs, [], "doc-id-type")
        
        assert result.document_type == "ID_DOCUMENT"
    
    def test_extract_id_document_to_dict_serialization(self):
        """Test that extracted data can be serialized to dictionary."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Passport Number": {"value": "P987654", "confidence": 0.97},
            "Full Name": {"value": "Frank Harris", "confidence": 0.96},
            "Date of Birth": {"value": "1991-02-28", "confidence": 0.98},
            "Nationality": {"value": "Canada", "confidence": 0.95}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-serial")
        result_dict = result.to_dict()
        
        assert result_dict["document_type"] == "ID_DOCUMENT"
        assert result_dict["id_type"]["value"] == "PASSPORT"
        assert result_dict["document_number"]["value"] == "P987654"
        assert result_dict["full_name"]["value"] == "Frank Harris"
        assert result_dict["date_of_birth"]["value"] == "1991-02-28"
        assert result_dict["nationality"]["value"] == "Canada"
    
    def test_extract_id_document_passport_detection(self):
        """Test that passport documents are correctly detected."""
        from functions.extractor.app import extract_id_document_data
        
        passport_indicators = [
            {"Passport No": {"value": "P123", "confidence": 0.95}},
            {"PASSPORT NUMBER": {"value": "P456", "confidence": 0.96}},
            {"Passport#": {"value": "P789", "confidence": 0.94}},
            {"P<USADOE<<JOHN": {"value": "MRZ", "confidence": 0.90}}  # Machine Readable Zone
        ]
        
        for idx, kvs in enumerate(passport_indicators):
            result = extract_id_document_data(kvs, [], f"doc-passport-{idx}")
            assert result.id_type.value == "PASSPORT"
            assert result.id_type.confidence == 0.95
    
    def test_extract_id_document_state_id_detection(self):
        """Test that state ID documents are correctly detected."""
        from functions.extractor.app import extract_id_document_data
        
        state_id_indicators = [
            {"State ID": {"value": "S123", "confidence": 0.95}},
            {"Identification Card": {"value": "IC456", "confidence": 0.96}},
            {"ID Card Number": {"value": "ID789", "confidence": 0.94}},
            {"State Identification": {"value": "SI012", "confidence": 0.93}}
        ]
        
        for idx, kvs in enumerate(state_id_indicators):
            result = extract_id_document_data(kvs, [], f"doc-stateid-{idx}")
            assert result.id_type.value == "STATE_ID"
            assert result.id_type.confidence == 0.90
    
    def test_extract_id_document_other_type_default(self):
        """Test that unknown ID documents default to OTHER type."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Document Number": {"value": "DOC123", "confidence": 0.95},
            "Full Name": {"value": "Grace Irwin", "confidence": 0.94}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-other")
        
        assert result.id_type.value == "OTHER"
        assert result.id_type.confidence == 0.70
    
    def test_extract_id_document_various_date_formats(self):
        """Test extraction with various date formats."""
        from functions.extractor.app import extract_id_document_data
        
        date_formats = [
            "1990-05-15",
            "05/15/1990",
            "15-05-1990",
            "May 15, 1990",
            "15 May 1990"
        ]
        
        for date_format in date_formats:
            kvs = {"Date of Birth": {"value": date_format, "confidence": 0.96}}
            result = extract_id_document_data(kvs, [], f"doc-id-date-{date_formats.index(date_format)}")
            
            assert result.date_of_birth is not None
            assert result.date_of_birth.value == date_format
    
    def test_extract_id_document_various_nationalities(self):
        """Test extraction with various nationality values."""
        from functions.extractor.app import extract_id_document_data
        
        nationalities = ["USA", "Canada", "United Kingdom", "Germany", "Japan", "Australia"]
        
        for nationality in nationalities:
            kvs = {"Nationality": {"value": nationality, "confidence": 0.95}}
            result = extract_id_document_data(kvs, [], f"doc-id-nat-{nationalities.index(nationality)}")
            
            assert result.nationality is not None
            assert result.nationality.value == nationality
    
    def test_extract_id_document_exclude_patterns(self):
        """Test that exclude patterns work correctly to avoid field confusion."""
        from functions.extractor.app import extract_id_document_data
        
        # Test that issuing authority fields don't interfere with name extraction
        kvs1 = {
            "Full Name": {"value": "Henry Jackson", "confidence": 0.95},
            "Issuing Authority Name": {"value": "Department of State", "confidence": 0.94}
        }
        
        result1 = extract_id_document_data(kvs1, [], "doc-id-excl1")
        assert result1.full_name.value == "Henry Jackson"
        assert result1.issuing_authority.value == "Department of State"
        
        # Test that issue date doesn't get confused with issuing authority
        kvs2 = {
            "Issue Date": {"value": "2020-01-01", "confidence": 0.96},
            "Issuing Country": {"value": "United States", "confidence": 0.95}
        }
        
        result2 = extract_id_document_data(kvs2, [], "doc-id-excl2")
        assert result2.issue_date.value == "2020-01-01"
        assert result2.issuing_authority.value == "United States"
    
    def test_extract_id_document_partial_extraction(self):
        """Test extraction with only a few fields present."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Document Number": {"value": "PARTIAL123", "confidence": 0.94},
            "Full Name": {"value": "Iris Kelly", "confidence": 0.93}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-partial")
        
        # Present fields
        assert result.document_number is not None
        assert result.document_number.value == "PARTIAL123"
        assert result.full_name is not None
        assert result.full_name.value == "Iris Kelly"
        
        # Missing fields
        assert result.date_of_birth is None
        assert result.issuing_authority is None
        assert result.issue_date is None
        assert result.expiration_date is None
        assert result.nationality is None
    
    def test_extract_id_document_multiline_name(self):
        """Test extraction of multi-line names (surname and given name separate)."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Surname": {"value": "Lee", "confidence": 0.96},
            "Given Name": {"value": "Jennifer", "confidence": 0.95},
            "Document Number": {"value": "ML789", "confidence": 0.97}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-multiname")
        
        # Should extract at least one name field
        assert result.full_name is not None
        assert "Lee" in result.full_name.value or "Jennifer" in result.full_name.value
    
    def test_extract_id_document_various_document_number_formats(self):
        """Test extraction with various document number formats."""
        from functions.extractor.app import extract_id_document_data
        
        doc_numbers = [
            "123456789",  # Numeric
            "ABC123456",  # Alphanumeric
            "P<123456789",  # Passport MRZ format
            "S-123-456-789",  # Dashed format
            "ID2023-001234"  # Year-based format
        ]
        
        for doc_num in doc_numbers:
            kvs = {"Document Number": {"value": doc_num, "confidence": 0.96}}
            result = extract_id_document_data(kvs, [], f"doc-id-num-{doc_numbers.index(doc_num)}")
            
            assert result.document_number is not None
            assert result.document_number.value == doc_num
    
    def test_extract_id_document_issuing_authority_variations(self):
        """Test extraction with various issuing authority formats."""
        from functions.extractor.app import extract_id_document_data
        
        authorities = [
            "U.S. Department of State",
            "State of California",
            "Government of Canada",
            "Ministry of Interior",
            "Federal Republic of Germany"
        ]
        
        for authority in authorities:
            kvs = {"Issuing Authority": {"value": authority, "confidence": 0.94}}
            result = extract_id_document_data(kvs, [], f"doc-id-auth-{authorities.index(authority)}")
            
            assert result.issuing_authority is not None
            assert result.issuing_authority.value == authority
    
    def test_extract_id_document_field_count_logging(self):
        """Test that field count is correctly calculated and logged."""
        from functions.extractor.app import extract_id_document_data
        
        kvs = {
            "Passport Number": {"value": "P123", "confidence": 0.97},
            "Full Name": {"value": "Kevin Moore", "confidence": 0.96},
            "Date of Birth": {"value": "1989-08-20", "confidence": 0.98},
            "Issuing Authority": {"value": "US Dept of State", "confidence": 0.95},
            "Expiration Date": {"value": "2029-08-20", "confidence": 0.96},
            "Nationality": {"value": "USA", "confidence": 0.97}
        }
        
        result = extract_id_document_data(kvs, [], "doc-id-count")
        
        # Count non-None fields (including id_type which is always set)
        field_count = sum(1 for field in [
            result.id_type, result.document_number, result.full_name,
            result.date_of_birth, result.issuing_authority, result.issue_date,
            result.expiration_date, result.nationality
        ] if field is not None)
        
        # Should have 7 fields (id_type + 6 extracted fields, issue_date is None)
        assert field_count == 7
