"""
Unit tests for the Cross-Document Validator Lambda function.
Tests Task 8.1: Lambda handler and validation orchestration.
"""

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add function path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../functions/validator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../shared'))

from app import lambda_handler
from models import DocumentMetadata, ExtractedField
from rules import validate_names, levenshtein_distance


class TestValidatorLambdaHandler:
    """Test suite for Task 8.1: Lambda handler and validation orchestration."""
    
    def test_handler_with_valid_input(self):
        """Test handler accepts valid loan_application_id and document_ids."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents
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
            assert response['loan_application_id'] == 'loan-123'
            assert len(response['documents']) == 2
            assert response['inconsistencies'] == []
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'
            assert response['documents_loaded'] == 2
            assert response['inconsistencies_found'] == 0
            
            # Verify repository was called correctly
            assert mock_repo.get_document.call_count == 2
            mock_repo.get_document.assert_any_call('doc-1')
            mock_repo.get_document.assert_any_call('doc-2')
    
    def test_handler_missing_loan_application_id(self):
        """Test handler returns error when loan_application_id is missing."""
        # Arrange
        event = {
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        assert response['error'] == 'ValidationError'
        assert 'loan_application_id' in response['message']
    
    def test_handler_missing_document_ids(self):
        """Test handler returns error when document_ids is missing."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123'
        }
        context = {}
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        assert response['error'] == 'ValidationError'
        assert 'document_ids' in response['message']
    
    def test_handler_empty_document_ids(self):
        """Test handler returns error when document_ids list is empty."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': []
        }
        context = {}
        
        # Act
        response = lambda_handler(event, context)
        
        # Assert
        assert response['statusCode'] == 400
        assert response['error'] == 'ValidationError'
        assert 'empty' in response['message'].lower()
    
    def test_handler_document_not_found(self):
        """Test handler handles documents not found in DynamoDB."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Mock DocumentRepository returning None (document not found)
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.return_value = None
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 400
            assert response['error'] == 'ValidationError'
            assert 'No valid documents' in response['message']
    
    def test_handler_filters_wrong_loan_application(self):
        """Test handler filters out documents from different loan applications."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with different loan_application_id
        mock_doc1 = DocumentMetadata(
            document_id='doc-1',
            loan_application_id='loan-456',  # Different loan application
            s3_bucket='test-bucket',
            s3_key='test/doc1.pdf',
            upload_timestamp='2024-01-15T10:00:00Z',
            file_name='w2.pdf',
            file_size_bytes=1024,
            file_format='PDF',
            checksum='abc123',
            document_type='W2',
            processing_status='COMPLETED',
            extracted_data={'employee_name': {'value': 'John Doe', 'confidence': 0.98}}
        )
        
        mock_doc2 = DocumentMetadata(
            document_id='doc-2',
            loan_application_id='loan-123',  # Correct loan application
            s3_bucket='test-bucket',
            s3_key='test/doc2.pdf',
            upload_timestamp='2024-01-15T10:05:00Z',
            file_name='tax_form.pdf',
            file_size_bytes=2048,
            file_format='PDF',
            checksum='def456',
            document_type='TAX_FORM',
            processing_status='COMPLETED',
            extracted_data={'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97}}
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
            assert len(response['documents']) == 1  # Only doc-2 should be included
            assert response['documents'][0]['document_id'] == 'doc-2'
    
    def test_handler_filters_incomplete_documents(self):
        """Test handler filters out documents that haven't completed processing."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with different processing statuses
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
            processing_status='PROCESSING',  # Not completed
            extracted_data={}
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
            processing_status='COMPLETED',
            extracted_data={'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97}}
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
            assert len(response['documents']) == 1  # Only doc-2 should be included
            assert response['documents'][0]['document_id'] == 'doc-2'
    
    def test_handler_filters_documents_without_extracted_data(self):
        """Test handler filters out documents with no extracted data."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents
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
            processing_status='COMPLETED',
            extracted_data={}  # No extracted data
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
            processing_status='COMPLETED',
            extracted_data={'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97}}
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
            assert len(response['documents']) == 1  # Only doc-2 should be included
            assert response['documents'][0]['document_id'] == 'doc-2'
    
    def test_handler_initializes_empty_inconsistencies_list(self):
        """Test handler initializes an empty inconsistencies list when no inconsistencies found."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1']
        }
        context = {}
        
        mock_doc = DocumentMetadata(
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
            processing_status='COMPLETED',
            extracted_data={'employee_name': {'value': 'John Doe', 'confidence': 0.98}}
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.return_value = mock_doc
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert 'inconsistencies' in response
            assert isinstance(response['inconsistencies'], list)
            assert len(response['inconsistencies']) == 0
            assert response['inconsistencies_found'] == 0
    
    def test_handler_returns_proper_response_structure(self):
        """Test handler returns the proper response structure."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1']
        }
        context = {}
        
        mock_doc = DocumentMetadata(
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
            extracted_data={'employee_name': {'value': 'John Doe', 'confidence': 0.98}}
        )
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.return_value = mock_doc
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert 'statusCode' in response
            assert 'loan_application_id' in response
            assert 'documents' in response
            assert 'inconsistencies' in response
            assert 'validation_status' in response
            assert 'documents_loaded' in response
            assert 'message' in response
            
            # Verify document structure
            assert len(response['documents']) == 1
            doc = response['documents'][0]
            assert 'document_id' in doc
            assert 'document_type' in doc
            assert 'file_name' in doc
            assert 'classification_confidence' in doc
            assert 'extracted_data' in doc
            
            # Verify response includes new fields
            assert 'inconsistencies_found' in response
            assert response['validation_status'] == 'NAME_ADDRESS_INCOME_DOB_SSN_VALIDATION_COMPLETE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestNameValidation:
    """Test suite for Task 8.2: Name validation logic."""
    
    def test_levenshtein_distance_identical_strings(self):
        """Test Levenshtein distance for identical strings."""
        assert levenshtein_distance("John Doe", "John Doe") == 0
    
    def test_levenshtein_distance_one_character_difference(self):
        """Test Levenshtein distance with one character difference."""
        assert levenshtein_distance("John Doe", "Jon Doe") == 1
    
    def test_levenshtein_distance_two_character_difference(self):
        """Test Levenshtein distance with two character differences."""
        assert levenshtein_distance("John Doe", "Jon Do") == 2
    
    def test_levenshtein_distance_three_character_difference(self):
        """Test Levenshtein distance with three character differences."""
        assert levenshtein_distance("John Doe", "Jon D") == 3
    
    def test_levenshtein_distance_case_insensitive(self):
        """Test that Levenshtein distance is case-insensitive in validate_names."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'},
            {'value': 'john doe', 'source': 'doc-2'}
        ]
        inconsistencies = validate_names(names)
        # Should not flag as inconsistent (case difference only)
        assert len(inconsistencies) == 0
    
    def test_validate_names_no_inconsistencies(self):
        """Test validate_names with identical names."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'},
            {'value': 'John Doe', 'source': 'doc-2'}
        ]
        inconsistencies = validate_names(names)
        assert len(inconsistencies) == 0
    
    def test_validate_names_minor_spelling_variation(self):
        """Test validate_names with minor spelling variation (edit distance <= 2)."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'},
            {'value': 'Jon Doe', 'source': 'doc-2'}  # Edit distance = 1
        ]
        inconsistencies = validate_names(names)
        # Should not flag (edit distance <= 2)
        assert len(inconsistencies) == 0
    
    def test_validate_names_edit_distance_exactly_two(self):
        """Test validate_names with edit distance exactly 2."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'},
            {'value': 'Jon Do', 'source': 'doc-2'}  # Edit distance = 2
        ]
        inconsistencies = validate_names(names)
        # Should not flag (edit distance <= 2)
        assert len(inconsistencies) == 0
    
    def test_validate_names_edit_distance_greater_than_two(self):
        """Test validate_names flags inconsistency when edit distance > 2."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'},
            {'value': 'Jane Smith', 'source': 'doc-2'}  # Edit distance > 2
        ]
        inconsistencies = validate_names(names)
        assert len(inconsistencies) == 1
        assert inconsistencies[0]['field'] == 'name'
        assert inconsistencies[0]['severity'] == 'HIGH'
        assert inconsistencies[0]['expected_value'] == 'John Doe'
        assert inconsistencies[0]['actual_value'] == 'Jane Smith'
        assert 'doc-1' in inconsistencies[0]['source_documents']
        assert 'doc-2' in inconsistencies[0]['source_documents']
    
    def test_validate_names_multiple_documents(self):
        """Test validate_names with multiple documents."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'},
            {'value': 'John Doe', 'source': 'doc-2'},
            {'value': 'Jane Smith', 'source': 'doc-3'}  # Different name
        ]
        inconsistencies = validate_names(names)
        # Should flag 2 inconsistencies: doc-1 vs doc-3, doc-2 vs doc-3
        assert len(inconsistencies) == 2
    
    def test_validate_names_empty_list(self):
        """Test validate_names with empty list."""
        names = []
        inconsistencies = validate_names(names)
        assert len(inconsistencies) == 0
    
    def test_validate_names_single_name(self):
        """Test validate_names with single name."""
        names = [
            {'value': 'John Doe', 'source': 'doc-1'}
        ]
        inconsistencies = validate_names(names)
        assert len(inconsistencies) == 0
    
    def test_validate_names_whitespace_normalization(self):
        """Test that names are normalized (lowercase, strip whitespace)."""
        names = [
            {'value': '  John Doe  ', 'source': 'doc-1'},
            {'value': 'john doe', 'source': 'doc-2'}
        ]
        inconsistencies = validate_names(names)
        # Should not flag (after normalization they're the same)
        assert len(inconsistencies) == 0
    
    def test_handler_with_name_validation(self):
        """Test Lambda handler performs name validation and returns inconsistencies."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with different names
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
                'employee_name': {'value': 'John Doe', 'confidence': 0.98}
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
                'taxpayer_name': {'value': 'Jane Smith', 'confidence': 0.97}
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
            assert inc['field'] == 'name'
            assert inc['severity'] == 'HIGH'
            assert inc['expected_value'] == 'John Doe'
            assert inc['actual_value'] == 'Jane Smith'
            assert 'doc-1' in inc['source_documents']
            assert 'doc-2' in inc['source_documents']
    
    def test_handler_with_matching_names(self):
        """Test Lambda handler with matching names returns no inconsistencies."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2']
        }
        context = {}
        
        # Create mock documents with same names
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
                'employee_name': {'value': 'John Doe', 'confidence': 0.98}
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
                'taxpayer_name': {'value': 'John Doe', 'confidence': 0.97}
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
    
    def test_handler_extracts_names_from_different_document_types(self):
        """Test handler extracts names from all document types."""
        # Arrange
        event = {
            'loan_application_id': 'loan-123',
            'document_ids': ['doc-1', 'doc-2', 'doc-3', 'doc-4', 'doc-5']
        }
        context = {}
        
        # Create mock documents of different types
        mock_docs = [
            DocumentMetadata(
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
                processing_status='COMPLETED',
                extracted_data={'employee_name': {'value': 'John Doe', 'confidence': 0.98}}
            ),
            DocumentMetadata(
                document_id='doc-2',
                loan_application_id='loan-123',
                s3_bucket='test-bucket',
                s3_key='test/doc2.pdf',
                upload_timestamp='2024-01-15T10:01:00Z',
                file_name='bank.pdf',
                file_size_bytes=1024,
                file_format='PDF',
                checksum='def456',
                document_type='BANK_STATEMENT',
                processing_status='COMPLETED',
                extracted_data={'account_holder_name': {'value': 'John Doe', 'confidence': 0.97}}
            ),
            DocumentMetadata(
                document_id='doc-3',
                loan_application_id='loan-123',
                s3_bucket='test-bucket',
                s3_key='test/doc3.pdf',
                upload_timestamp='2024-01-15T10:02:00Z',
                file_name='tax.pdf',
                file_size_bytes=1024,
                file_format='PDF',
                checksum='ghi789',
                document_type='TAX_FORM',
                processing_status='COMPLETED',
                extracted_data={'taxpayer_name': {'value': 'John Doe', 'confidence': 0.96}}
            ),
            DocumentMetadata(
                document_id='doc-4',
                loan_application_id='loan-123',
                s3_bucket='test-bucket',
                s3_key='test/doc4.pdf',
                upload_timestamp='2024-01-15T10:03:00Z',
                file_name='license.pdf',
                file_size_bytes=1024,
                file_format='PDF',
                checksum='jkl012',
                document_type='DRIVERS_LICENSE',
                processing_status='COMPLETED',
                extracted_data={'full_name': {'value': 'John Doe', 'confidence': 0.99}}
            ),
            DocumentMetadata(
                document_id='doc-5',
                loan_application_id='loan-123',
                s3_bucket='test-bucket',
                s3_key='test/doc5.pdf',
                upload_timestamp='2024-01-15T10:04:00Z',
                file_name='id.pdf',
                file_size_bytes=1024,
                file_format='PDF',
                checksum='mno345',
                document_type='ID_DOCUMENT',
                processing_status='COMPLETED',
                extracted_data={'full_name': {'value': 'John Doe', 'confidence': 0.98}}
            )
        ]
        
        # Mock DocumentRepository
        with patch('repositories.DocumentRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_document.side_effect = mock_docs
            mock_repo_class.return_value = mock_repo
            
            # Act
            response = lambda_handler(event, context)
            
            # Assert
            assert response['statusCode'] == 200
            assert len(response['documents']) == 5
            # All names match, so no inconsistencies
            assert len(response['inconsistencies']) == 0
