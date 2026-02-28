# backend/functions/validator/app.py
"""
Task 8.1: Cross-Document Validator Lambda Handler
Implements the Lambda handler accepting multiple documents from a loan application
and orchestrates the validation process to detect inconsistencies across documents.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any
import uuid

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

import repositories
import models
import rules

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Task 8.1: Cross-Document Validator Lambda Handler.
    
    Accepts an event with:
    - loan_application_id: The loan application identifier
    - document_ids: List of document IDs to validate
    
    Returns:
    - loan_application_id: The loan application identifier
    - documents: List of loaded document metadata
    - inconsistencies: Empty list (initialized for subsequent validation tasks)
    - validation_status: Status of the validation process
    """
    try:
        # Extract input parameters
        loan_application_id = event.get('loan_application_id')
        document_ids = event.get('document_ids', [])
        
        # Input validation
        if not loan_application_id:
            logger.error("Missing required parameter: loan_application_id")
            raise ValueError("loan_application_id is required")
        
        if not document_ids:
            logger.error(f"No document_ids provided for loan application {loan_application_id}")
            raise ValueError("document_ids list cannot be empty")
        
        logger.info(f"Starting validation for loan application {loan_application_id} with {len(document_ids)} documents")
        
        # Initialize DocumentRepository to load extracted data from DynamoDB
        doc_repository = repositories.DocumentRepository()
        
        # Load extracted data for all documents in the loan application
        loaded_documents = []
        for doc_id in document_ids:
            logger.info(f"Loading document {doc_id} from DynamoDB")
            doc_metadata = doc_repository.get_document(doc_id)
            
            if not doc_metadata:
                logger.warning(f"Document {doc_id} not found in DynamoDB")
                continue
            
            # Verify document belongs to the correct loan application
            if doc_metadata.loan_application_id != loan_application_id:
                logger.warning(f"Document {doc_id} belongs to different loan application: {doc_metadata.loan_application_id}")
                continue
            
            # Verify document has been processed and has extracted data
            if doc_metadata.processing_status != "COMPLETED":
                logger.warning(f"Document {doc_id} has not completed processing: {doc_metadata.processing_status}")
                continue
            
            if not doc_metadata.extracted_data:
                logger.warning(f"Document {doc_id} has no extracted data")
                continue
            
            loaded_documents.append(doc_metadata)
            logger.info(f"Successfully loaded document {doc_id} (type: {doc_metadata.document_type})")
        
        if not loaded_documents:
            logger.error(f"No valid documents loaded for loan application {loan_application_id}")
            raise ValueError("No valid documents available for validation")
        
        logger.info(f"Successfully loaded {len(loaded_documents)} documents for validation")
        
        # Task 8.2: Perform name validation across all documents
        logger.info("Starting name validation across documents")
        
        # Extract name fields from all documents
        name_fields = []
        for doc in loaded_documents:
            extracted_data = doc.extracted_data
            doc_id = doc.document_id
            
            # Check for various name field types based on document type
            name_value = None
            if doc.document_type == 'W2' and 'employee_name' in extracted_data:
                name_value = extracted_data['employee_name']
            elif doc.document_type == 'BANK_STATEMENT' and 'account_holder_name' in extracted_data:
                name_value = extracted_data['account_holder_name']
            elif doc.document_type == 'TAX_FORM' and 'taxpayer_name' in extracted_data:
                name_value = extracted_data['taxpayer_name']
            elif doc.document_type == 'DRIVERS_LICENSE' and 'full_name' in extracted_data:
                name_value = extracted_data['full_name']
            elif doc.document_type == 'ID_DOCUMENT' and 'full_name' in extracted_data:
                name_value = extracted_data['full_name']
            
            # Add to name_fields list if found
            if name_value:
                # Handle both dict and ExtractedField formats
                if isinstance(name_value, dict):
                    value = name_value.get('value')
                elif hasattr(name_value, 'value'):
                    value = name_value.value
                else:
                    value = str(name_value)
                
                if value:
                    name_fields.append({
                        'value': value,
                        'source': doc_id
                    })
                    logger.info(f"Extracted name '{value}' from document {doc_id}")
        
        # Validate names using Levenshtein distance
        name_inconsistencies = []
        if len(name_fields) >= 2:
            logger.info(f"Validating {len(name_fields)} names for inconsistencies")
            name_inconsistencies = rules.validate_names(name_fields)
            logger.info(f"Found {len(name_inconsistencies)} name inconsistencies")
        else:
            logger.info(f"Insufficient names for validation (found {len(name_fields)})")
        
        # Convert inconsistencies to Inconsistency objects
        inconsistencies: List[models.Inconsistency] = []
        for inc in name_inconsistencies:
            inconsistency = models.Inconsistency(
                inconsistency_id=str(uuid.uuid4()),
                field=inc['field'],
                severity=inc['severity'],
                expected_value=inc['expected_value'],
                actual_value=inc['actual_value'],
                source_documents=inc['source_documents'],
                description=inc['description'],
                detected_by='cross_document_validator'
            )
            inconsistencies.append(inconsistency)
        
        # Prepare document summary for response
        document_summary = [
            {
                "document_id": doc.document_id,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "classification_confidence": doc.classification_confidence,
                "extracted_data": doc.extracted_data
            }
            for doc in loaded_documents
        ]
        
        # Convert inconsistencies to dict format for response
        inconsistencies_dict = [inc.to_dict() for inc in inconsistencies]
        
        # Return structure that will hold validation results
        response = {
            "statusCode": 200,
            "loan_application_id": loan_application_id,
            "documents": document_summary,
            "inconsistencies": inconsistencies_dict,
            "validation_status": "NAME_VALIDATION_COMPLETE",
            "documents_loaded": len(loaded_documents),
            "inconsistencies_found": len(inconsistencies),
            "message": f"Name validation complete: {len(inconsistencies)} inconsistencies found"
        }
        
        logger.info(f"Validation initialization complete for loan application {loan_application_id}")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 400,
            "error": "ValidationError",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "error": "InternalError",
            "message": "An unexpected error occurred during validation"
        }
