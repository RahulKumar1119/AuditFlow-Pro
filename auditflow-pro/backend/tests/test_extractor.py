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


class TestMultiPageProcessing:
    """Test cases for multi-page PDF processing."""
    
    @patch('functions.extractor.app.analyze_document_with_retry')
    def test_multi_page_processing_success(self, mock_textract):
        """Test successful multi-page PDF processing."""
        # Setup mock with multi-page response
        mock_textract.return_value = {
            "Blocks": [
                {"BlockType": "LINE", "Text": "Page 1", "Page": 1},
                {"BlockType": "LINE", "Text": "Page 2", "Page": 2},
                {"BlockType": "LINE", "Text": "Page 3", "Page": 3}
            ]
        }
        
        # Execute
        result = process_multi_page_pdf("bucket", "key", "doc-123", 3)
        
        # Verify
        assert len(result["Blocks"]) == 3
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
