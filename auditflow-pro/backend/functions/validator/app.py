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
        
        # Task 8.3: Perform address validation across all documents
        logger.info("Starting address validation across documents")
        
        # Extract address fields from all documents
        address_fields = []
        for doc in loaded_documents:
            extracted_data = doc.extracted_data
            doc_id = doc.document_id
            
            # Check for various address field types based on document type
            address_value = None
            if doc.document_type == 'W2' and 'employee_address' in extracted_data:
                address_value = extracted_data['employee_address']
            elif doc.document_type == 'BANK_STATEMENT' and 'account_holder_address' in extracted_data:
                address_value = extracted_data['account_holder_address']
            elif doc.document_type == 'TAX_FORM' and 'address' in extracted_data:
                address_value = extracted_data['address']
            elif doc.document_type == 'DRIVERS_LICENSE' and 'address' in extracted_data:
                address_value = extracted_data['address']
            
            # Add to address_fields list if found
            if address_value:
                # Handle both dict and ExtractedField formats
                if isinstance(address_value, dict):
                    value = address_value.get('value')
                elif hasattr(address_value, 'value'):
                    value = address_value.value
                else:
                    value = str(address_value)
                
                if value:
                    address_fields.append({
                        'value': value,
                        'source': doc_id
                    })
                    logger.info(f"Extracted address '{value}' from document {doc_id}")
        
        # Validate addresses using component parsing and semantic matching
        address_inconsistencies = []
        if len(address_fields) >= 2:
            logger.info(f"Validating {len(address_fields)} addresses for inconsistencies")
            address_inconsistencies = rules.validate_addresses(address_fields)
            logger.info(f"Found {len(address_inconsistencies)} address inconsistencies")
        else:
            logger.info(f"Insufficient addresses for validation (found {len(address_fields)})")
        
        # Convert all inconsistencies to Inconsistency objects
        inconsistencies: List[models.Inconsistency] = []
        
        # Add name inconsistencies
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
        
        # Add address inconsistencies
        for inc in address_inconsistencies:
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
        
        # Task 8.4: Perform income validation across documents
        logger.info("Starting income validation across documents")
        
        # Extract W2 wage fields from all W2 documents
        w2_wages = []
        for doc in loaded_documents:
            if doc.document_type == 'W2':
                extracted_data = doc.extracted_data
                doc_id = doc.document_id
                
                # Look for wages field in W2
                wage_value = None
                if 'wages' in extracted_data:
                    wage_value = extracted_data['wages']
                
                # Add to w2_wages list if found
                if wage_value:
                    # Handle both dict and ExtractedField formats
                    if isinstance(wage_value, dict):
                        value = wage_value.get('value')
                    elif hasattr(wage_value, 'value'):
                        value = wage_value.value
                    else:
                        value = str(wage_value)
                    
                    if value:
                        w2_wages.append({
                            'value': value,
                            'source': doc_id
                        })
                        logger.info(f"Extracted wages '{value}' from W2 document {doc_id}")
        
        # Extract adjusted gross income from tax form documents
        tax_agi = None
        for doc in loaded_documents:
            if doc.document_type == 'TAX_FORM':
                extracted_data = doc.extracted_data
                doc_id = doc.document_id
                
                # Look for adjusted_gross_income field in tax form
                agi_value = None
                if 'adjusted_gross_income' in extracted_data:
                    agi_value = extracted_data['adjusted_gross_income']
                
                # Use the first tax form AGI found
                if agi_value:
                    # Handle both dict and ExtractedField formats
                    if isinstance(agi_value, dict):
                        value = agi_value.get('value')
                    elif hasattr(agi_value, 'value'):
                        value = agi_value.value
                    else:
                        value = str(agi_value)
                    
                    if value:
                        tax_agi = {
                            'value': value,
                            'source': doc_id
                        }
                        logger.info(f"Extracted AGI '{value}' from tax form document {doc_id}")
                        break  # Use first tax form found
        
        # Validate income using the validate_income function from rules.py
        income_inconsistencies = []
        if w2_wages and tax_agi:
            logger.info(f"Validating income: {len(w2_wages)} W2(s) against tax form AGI")
            income_inconsistencies = rules.validate_income(w2_wages, tax_agi)
            logger.info(f"Found {len(income_inconsistencies)} income inconsistencies")
        else:
            if not w2_wages:
                logger.info("No W2 wages found for income validation")
            if not tax_agi:
                logger.info("No tax form AGI found for income validation")
        
        # Add income inconsistencies
        for inc in income_inconsistencies:
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
        
        # Task 8.5: Perform date of birth validation across identification documents
        logger.info("Starting date of birth validation across identification documents")
        
        # Extract DOB fields from all identification documents
        dob_fields = []
        for doc in loaded_documents:
            # DOB is found in identification documents: DRIVERS_LICENSE, ID_DOCUMENT, TAX_FORM
            if doc.document_type in ['DRIVERS_LICENSE', 'ID_DOCUMENT', 'TAX_FORM']:
                extracted_data = doc.extracted_data
                doc_id = doc.document_id
                
                # Look for date_of_birth field
                dob_value = None
                if 'date_of_birth' in extracted_data:
                    dob_value = extracted_data['date_of_birth']
                
                # Add to dob_fields list if found
                if dob_value:
                    # Handle both dict and ExtractedField formats
                    if isinstance(dob_value, dict):
                        value = dob_value.get('value')
                    elif hasattr(dob_value, 'value'):
                        value = dob_value.value
                    else:
                        value = str(dob_value)
                    
                    if value:
                        dob_fields.append({
                            'value': value,
                            'source': doc_id
                        })
                        logger.info(f"Extracted DOB '{value}' from document {doc_id}")
        
        # Validate DOB using zero-tolerance comparison
        dob_inconsistencies = []
        if len(dob_fields) >= 2:
            logger.info(f"Validating {len(dob_fields)} DOB values for inconsistencies")
            dob_inconsistencies = rules.validate_ssn_dob(dob_fields, 'date_of_birth')
            logger.info(f"Found {len(dob_inconsistencies)} DOB inconsistencies")
        else:
            logger.info(f"Insufficient DOB values for validation (found {len(dob_fields)})")
        
        # Add DOB inconsistencies
        for inc in dob_inconsistencies:
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
        
        # Task 8.5: Perform SSN validation across all documents
        logger.info("Starting SSN validation across documents")
        
        # Extract SSN fields from all documents that contain SSN
        ssn_fields = []
        for doc in loaded_documents:
            extracted_data = doc.extracted_data
            doc_id = doc.document_id
            
            # Check for various SSN field types based on document type
            ssn_value = None
            if doc.document_type == 'W2' and 'employee_ssn' in extracted_data:
                ssn_value = extracted_data['employee_ssn']
            elif doc.document_type == 'TAX_FORM' and 'taxpayer_ssn' in extracted_data:
                ssn_value = extracted_data['taxpayer_ssn']
            
            # Add to ssn_fields list if found
            if ssn_value:
                # Handle both dict and ExtractedField formats
                if isinstance(ssn_value, dict):
                    value = ssn_value.get('value')
                elif hasattr(ssn_value, 'value'):
                    value = ssn_value.value
                else:
                    value = str(ssn_value)
                
                if value:
                    ssn_fields.append({
                        'value': value,
                        'source': doc_id
                    })
                    logger.info(f"Extracted SSN from document {doc_id}")
        
        # Validate SSN using zero-tolerance comparison
        ssn_inconsistencies = []
        if len(ssn_fields) >= 2:
            logger.info(f"Validating {len(ssn_fields)} SSN values for inconsistencies")
            ssn_inconsistencies = rules.validate_ssn_dob(ssn_fields, 'ssn')
            logger.info(f"Found {len(ssn_inconsistencies)} SSN inconsistencies")
        else:
            logger.info(f"Insufficient SSN values for validation (found {len(ssn_fields)})")
        
        # Add SSN inconsistencies
        for inc in ssn_inconsistencies:
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
        
        # Task 8.7: Generate Golden Record
        logger.info("Generating Golden Record from all documents")
        from datetime import datetime
        created_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        golden_record_dict = rules.generate_golden_record(
            loan_application_id=loan_application_id,
            documents=loaded_documents,
            created_timestamp=created_timestamp
        )
        
        logger.info(f"Golden Record generated with {len(golden_record_dict) - 2} fields")
        
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
            "golden_record": golden_record_dict,
            "validation_status": "VALIDATION_COMPLETE_WITH_GOLDEN_RECORD",
            "documents_loaded": len(loaded_documents),
            "inconsistencies_found": len(inconsistencies),
            "message": f"Validation complete with Golden Record: {len(inconsistencies)} inconsistencies found"
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
