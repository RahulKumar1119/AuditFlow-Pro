"""
Unit tests for Task 8.5: Date of Birth and SSN validation logic.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add function path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/validator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../shared'))

from app import lambda_handler
from models import DocumentMetadata
from rules import validate_ssn_dob


class TestDOBValidation:
    """Test suite for Task 8.5: Date of Birth validation logic."""
    
    def test_validate_dob_no_discrepancy(self):
        """Test validate_ssn_dob with matching DOB values."""
        dob_values = [
            {'value': '1985-06-15', 'source': 'doc-1'},
            {'value': '1985-06-15', 'source': 'doc-2'}
        ]
        
        inconsistencies = validate_ssn_dob(dob_values, 'date_of_birth')
        assert len(inconsistencies) == 0
    
    def test_validate_dob_with_mismatch(self):
        """Test validate_ssn_dob flags DOB mismatch (zero tolerance)."""
        dob_values = [
            {'value': '1985-06-15', 'source': 'doc-1'},
            {'value': '1985-06-16', 'source': 'doc-2'}  # Different DOB
        ]
        
        inconsistencies = validate_ssn_dob(dob_values, 'date_of_birth')
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['field'] == 'date_of_birth'
        assert inconsistencies[0]['severity'] == 'CRITICAL'
        assert inconsistencies[0]['expected_value'] == '1985-06-15'
        assert inconsistencies[0]['actual_value'] == '1985-06-16'
        assert 'doc-1' in inconsistencies[0]['source_documents']
        assert 'doc-2' in inconsistencies[0]['source_documents']
    
    def test_validate_dob_multiple_documents(self):
        """Test validate_ssn_dob with multiple documents."""
        dob_values = [
            {'value': '1985-06-15', 'source': 'doc-1'},
            {'value': '1985-06-15', 'source': 'doc-2'},
            {'value': '1990-01-01', 'source': 'doc-3'}  # Different DOB
        ]
        
        inconsistencies = validate_ssn_dob(dob_values, 'date_of_birth')
        # Should flag 1 inconsistency: baseline (doc-1) vs doc-3
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['expected_value'] == '1985-06-15'
        assert inconsistencies[0]['actual_value'] == '1990-01-01'
    
    def test_validate_dob_empty_list(self):
        """Test validate_ssn_dob with empty list."""
        dob_values = []
        
        inconsistencies = validate_ssn_dob(dob_values, 'date_of_birth')
        assert len(inconsistencies) == 0
    
    def test_validate_dob_single_value(self):
        """Test validate_ssn_dob with single DOB value."""
        dob_values = [
            {'value': '1985-06-15', 'source': 'doc-1'}
        ]
        
        inconsistencies = validate_ssn_dob(dob_values, 'date_of_birth')
        assert len(inconsistencies) == 0
    
    def test_handler_with_dob_validation(self):
        """Test Lambda handler performs DOB validation."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with different DOBs
        mock_doc1 = DocumentMetadata(
            document_id='doc-1',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc1.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='license.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='DRIVERS_LICENSE',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'full_name': {'value': 'John Doe', 'confidence': 0.98},
                'date_of_birth': {'value': '1985-06-15', 'confidence': 0.99}
            }
        )
        
        mock_doc2 = DocumentMetadata(
            document_id='doc-2',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc2.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='id.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='ID_DOCUMENT',
            classification_confidence=0.92,
            processing_status='COMPLETED',
            extracted_data={
                'full_name': {'value': 'John Doe', 'confidence': 0.97},
                'date_of_birth': {'value': '1985-06-16', 'confidence': 0.98}  # Different DOB
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_doc1, mock_doc2]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'
            assert len(response['inconsistencies']) == 1
            assert response['inconsistencies_found'] == 1
            
            # Verify inconsistency details
            inc = response['inconsistencies'][0]
            assert inc['field'] == 'date_of_birth'
            assert inc['severity'] == 'CRITICAL'
            assert 'doc-1' in inc['source_documents']
            assert 'doc-2' in inc['source_documents']
    
    def test_handler_with_matching_dob(self):
        """Test Lambda handler with matching DOB returns no inconsistencies."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with same DOB
        mock_doc1 = DocumentMetadata(
            document_id='doc-1',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc1.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='license.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='DRIVERS_LICENSE',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'full_name': {'value': 'John Doe', 'confidence': 0.98},
                'date_of_birth': {'value': '1985-06-15', 'confidence': 0.99}
            }
        )
        
        mock_doc2 = DocumentMetadata(
            document_id='doc-2',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc2.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='id.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='ID_DOCUMENT',
            classification_confidence=0.92,
            processing_status='COMPLETED',
            extracted_data={
                'full_name': {'value': 'John Doe', 'confidence': 0.97},
                'date_of_birth': {'value': '1985-06-15', 'confidence': 0.98}
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_doc1, mock_doc2]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'
            assert len(response['inconsistencies']) == 0
            assert response['inconsistencies_found'] == 0


class TestSSNValidation:
    """Test suite for Task 8.5: SSN validation logic."""
    
    def test_validate_ssn_no_discrepancy(self):
        """Test validate_ssn_dob with matching SSN values."""
        ssn_values = [
            {'value': '***-**-1234', 'source': 'doc-1'},
            {'value': '***-**-1234', 'source': 'doc-2'}
        ]
        
        inconsistencies = validate_ssn_dob(ssn_values, 'ssn')
        assert len(inconsistencies) == 0
    
    def test_validate_ssn_with_mismatch(self):
        """Test validate_ssn_dob flags SSN mismatch (zero tolerance)."""
        ssn_values = [
            {'value': '***-**-1234', 'source': 'doc-1'},
            {'value': '***-**-5678', 'source': 'doc-2'}  # Different SSN
        ]
        
        inconsistencies = validate_ssn_dob(ssn_values, 'ssn')
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['field'] == 'ssn'
        assert inconsistencies[0]['severity'] == 'CRITICAL'
        assert inconsistencies[0]['expected_value'] == '***-**-1234'
        assert inconsistencies[0]['actual_value'] == '***-**-5678'
        assert 'doc-1' in inconsistencies[0]['source_documents']
        assert 'doc-2' in inconsistencies[0]['source_documents']
    
    def test_validate_ssn_multiple_documents(self):
        """Test validate_ssn_dob with multiple documents."""
        ssn_values = [
            {'value': '***-**-1234', 'source': 'doc-1'},
            {'value': '***-**-1234', 'source': 'doc-2'},
            {'value': '***-**-5678', 'source': 'doc-3'}  # Different SSN
        ]
        
        inconsistencies = validate_ssn_dob(ssn_values, 'ssn')
        # Should flag 1 inconsistency: baseline (doc-1) vs doc-3
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['expected_value'] == '***-**-1234'
        assert inconsistencies[0]['actual_value'] == '***-**-5678'
    
    def test_validate_ssn_empty_list(self):
        """Test validate_ssn_dob with empty list."""
        ssn_values = []
        
        inconsistencies = validate_ssn_dob(ssn_values, 'ssn')
        assert len(inconsistencies) == 0
    
    def test_validate_ssn_single_value(self):
        """Test validate_ssn_dob with single SSN value."""
        ssn_values = [
            {'value': '***-**-1234', 'source': 'doc-1'}
        ]
        
        inconsistencies = validate_ssn_dob(ssn_values, 'ssn')
        assert len(inconsistencies) == 0
    
    def test_handler_with_ssn_validation(self):
        """Test Lambda handler performs SSN validation."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with different SSNs
        mock_doc1 = DocumentMetadata(
            document_id='doc-1',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc1.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='w2.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='W2',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'employee_name': {'value': 'John Doe', 'confidence': 0.98},
                'employee_ssn': {'value': '***-**-1234', 'confidence': 0.99}
            }
        )
        
        mock_doc2 = DocumentMetadata(
            document_id='doc-2',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc2.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='tax_form.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='TAX_FORM',
            classification_confidence=0.92,
            processing_status='COMPLETED',
            extracted_data={
                'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97},
                'taxpayer_ssn': {'value': '***-**-5678', 'confidence': 0.98}  # Different SSN
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_doc1, mock_doc2]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'
            assert len(response['inconsistencies']) == 1
            assert response['inconsistencies_found'] == 1
            
            # Verify inconsistency details
            inc = response['inconsistencies'][0]
            assert inc['field'] == 'ssn'
            assert inc['severity'] == 'CRITICAL'
            assert 'doc-1' in inc['source_documents']
            assert 'doc-2' in inc['source_documents']
    
    def test_handler_with_matching_ssn(self):
        """Test Lambda handler with matching SSN returns no inconsistencies."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with same SSN
        mock_doc1 = DocumentMetadata(
            document_id='doc-1',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc1.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='w2.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='W2',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'employee_name': {'value': 'John Doe', 'confidence': 0.98},
                'employee_ssn': {'value': '***-**-1234', 'confidence': 0.99}
            }
        )
        
        mock_doc2 = DocumentMetadata(
            document_id='doc-2',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc2.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='tax_form.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='TAX_FORM',
            classification_confidence=0.92,
            processing_status='COMPLETED',
            extracted_data={
                'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97},
                'taxpayer_ssn': {'value': '***-**-1234', 'confidence': 0.98}
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_doc1, mock_doc2]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'
            assert len(response['inconsistencies']) == 0
            assert response['inconsistencies_found'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
