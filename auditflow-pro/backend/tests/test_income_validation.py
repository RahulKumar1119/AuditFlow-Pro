"""
Unit tests for Task 8.4: Income validation logic.
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
from rules import validate_income


class TestIncomeValidation:
    """Test suite for Task 8.4: Income validation logic."""
    
    def test_validate_income_no_discrepancy(self):
        """Test validate_income with matching W2 and AGI."""
        w2_wages = [
            {'value': 75000.00, 'source': 'doc-1'}
        ]
        tax_agi = {'value': 75000.00, 'source': 'doc-2'}
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 0
    
    def test_validate_income_small_discrepancy(self):
        """Test validate_income with discrepancy <= 5%."""
        w2_wages = [
            {'value': 75000.00, 'source': 'doc-1'}
        ]
        tax_agi = {'value': 78000.00, 'source': 'doc-2'}  # 4% discrepancy
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 0
    
    def test_validate_income_medium_discrepancy(self):
        """Test validate_income with discrepancy > 5% but <= 10%."""
        w2_wages = [
            {'value': 75000.00, 'source': 'doc-1'}
        ]
        tax_agi = {'value': 80000.00, 'source': 'doc-2'}  # 6.67% discrepancy
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['field'] == 'income'
        assert inconsistencies[0]['severity'] == 'MEDIUM'
        assert inconsistencies[0]['expected_value'] == '75000.0'
        assert inconsistencies[0]['actual_value'] == '80000.0'
        assert 'doc-1' in inconsistencies[0]['source_documents']
        assert 'doc-2' in inconsistencies[0]['source_documents']
    
    def test_validate_income_large_discrepancy(self):
        """Test validate_income with discrepancy > 10%."""
        w2_wages = [
            {'value': 75000.00, 'source': 'doc-1'}
        ]
        tax_agi = {'value': 90000.00, 'source': 'doc-2'}  # 20% discrepancy
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['field'] == 'income'
        assert inconsistencies[0]['severity'] == 'HIGH'
    
    def test_validate_income_multiple_w2s(self):
        """Test validate_income sums multiple W2 wages."""
        w2_wages = [
            {'value': 50000.00, 'source': 'doc-1'},
            {'value': 25000.00, 'source': 'doc-2'}
        ]
        tax_agi = {'value': 75000.00, 'source': 'doc-3'}
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 0
    
    def test_validate_income_multiple_w2s_with_discrepancy(self):
        """Test validate_income with multiple W2s and discrepancy."""
        w2_wages = [
            {'value': 50000.00, 'source': 'doc-1'},
            {'value': 25000.00, 'source': 'doc-2'}
        ]
        tax_agi = {'value': 85000.00, 'source': 'doc-3'}  # 13.33% discrepancy
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['severity'] == 'HIGH'
        assert 'doc-1' in inconsistencies[0]['source_documents']
        assert 'doc-2' in inconsistencies[0]['source_documents']
        assert 'doc-3' in inconsistencies[0]['source_documents']
    
    def test_validate_income_empty_w2_wages(self):
        """Test validate_income with no W2 wages."""
        w2_wages = []
        tax_agi = {'value': 75000.00, 'source': 'doc-1'}
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 0
    
    def test_validate_income_no_tax_agi(self):
        """Test validate_income with no tax AGI."""
        w2_wages = [
            {'value': 75000.00, 'source': 'doc-1'}
        ]
        tax_agi = None
        
        inconsistencies = validate_income(w2_wages, tax_agi)
        assert len(inconsistencies) == 0
    
    def test_handler_with_income_validation(self):
        """Test Lambda handler performs income validation."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with W2 and tax form
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
                'wages': {'value': 75000.00, 'confidence': 0.99}
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
                'adjusted_gross_income': {'value': 90000.00, 'confidence': 0.98}  # 20% discrepancy
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
            assert inc['field'] == 'income'
            assert inc['severity'] == 'HIGH'
            assert 'doc-1' in inc['source_documents']
            assert 'doc-2' in inc['source_documents']
    
    def test_handler_with_matching_income(self):
        """Test Lambda handler with matching income returns no inconsistencies."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with matching income
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
                'wages': {'value': 75000.00, 'confidence': 0.99}
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
                'adjusted_gross_income': {'value': 75000.00, 'confidence': 0.98}
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
    
    def test_handler_with_multiple_w2s(self):
        """Test Lambda handler sums multiple W2 wages."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2', 'doc-3']
        }
        context = {}
        
        # Create mock documents with two W2s and one tax form
        mock_doc1 = DocumentMetadata(
            document_id='doc-1',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc1.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='w2_job1.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='W2',
            classification_confidence=0.95,
            processing_status='COMPLETED',
            extracted_data={
                'employee_name': {'value': 'John Doe', 'confidence': 0.98},
                'wages': {'value': 50000.00, 'confidence': 0.99}
            }
        )
        
        mock_doc2 = DocumentMetadata(
            document_id='doc-2',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc2.pdf',
            upload_timestamp='2024-01-15T10:01:00Z',
            file_name='w2_job2.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='def456',
            document_type='W2',
            classification_confidence=0.96,
            processing_status='COMPLETED',
            extracted_data={
                'employee_name': {'value': 'John Doe', 'confidence': 0.98},
                'wages': {'value': 25000.00, 'confidence': 0.99}
            }
        )
        
        mock_doc3 = DocumentMetadata(
            document_id='doc-3',
            loan_application_id='loan-123',
            s3_bucket='test-bucket',
            s3_key='test/doc3.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='tax_form.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='ghi789',
            document_type='TAX_FORM',
            classification_confidence=0.92,
            processing_status='COMPLETED',
            extracted_data={
                'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97},
                'adjusted_gross_income': {'value': 75000.00, 'confidence': 0.98}
            }
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = [mock_doc1, mock_doc2, mock_doc3]
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'
            # Should sum 50000 + 25000 = 75000, which matches AGI of 75000
            assert len(response['inconsistencies']) == 0
            assert response['inconsistencies_found'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
