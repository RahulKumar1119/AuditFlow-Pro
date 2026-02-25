# backend/functions/validator/app.py

import json
import logging
from rules import (
    validate_names, 
    validate_ssn_dob, 
    validate_income, 
    validate_addresses
)
from golden_record import generate_golden_record

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def aggregate_document_data(documents: list) -> dict:
    """
    Groups extracted fields by field name across all documents.
    Example output: {'first_name': [{'value': 'John', 'confidence': 99.0, 'source': 'doc1'}, ...]}
    """
    aggregated = {}
    
    for doc in documents:
        doc_id = doc.get('document_id')
        doc_type = doc.get('document_type')
        extracted = doc.get('metadata', {}).get('extracted_data', {})
        
        for field_name, field_data in extracted.items():
            if field_name not in aggregated:
                aggregated[field_name] = []
                
            aggregated[field_name].append({
                "value": field_data.get('value'),
                "confidence": field_data.get('confidence'),
                "source": doc_id,
                "document_type": doc_type
            })
            
    return aggregated

def lambda_handler(event, context):
    """
    Task 8.1: Cross-Document Validator Lambda Handler.
    Orchestrates validation, runs all inconsistency rules, and generates the golden record.
    """
    logger.info(f"Received validation request for application: {event.get('loan_application_id')}")
    
    # Event should contain an array of processed documents from the CheckAllDocumentsProcessed state
    documents = event.get('documents', [])
    if not documents:
        logger.error("No documents provided for validation.")
        raise ValueError("No documents provided for validation.")
        
    aggregated_data = aggregate_document_data(documents)
    inconsistencies = []

    # 1. Validate Names (Task 8.2)
    name_fields = aggregated_data.get('first_name', []) + aggregated_data.get('employer_name', []) + aggregated_data.get('last_name', [])
    inconsistencies.extend(validate_names(name_fields))
    
    # 2. Validate SSN & DOB (Task 8.5)
    inconsistencies.extend(validate_ssn_dob(aggregated_data.get('ssn', []) + aggregated_data.get('employee_ssn', []), "ssn"))
    inconsistencies.extend(validate_ssn_dob(aggregated_data.get('date_of_birth', []), "date_of_birth"))
    
    # 3. Validate Income: W2 vs Tax Form (Task 8.4)
    w2_wages = [w for w in aggregated_data.get('wages', []) if w.get('document_type') == 'W2']
    tax_agi = next((a for a in aggregated_data.get('adjusted_gross_income', []) if a.get('document_type') == 'TAX_FORM'), None)
    if w2_wages and tax_agi:
        inconsistencies.extend(validate_income(w2_wages, tax_agi))
        
    # 4. Validate Addresses using AI (Task 8.3 & 8.6)
    address_fields = aggregated_data.get('address', []) + aggregated_data.get('employee_address', [])
    inconsistencies.extend(validate_addresses(address_fields))
        
    # 5. Generate Golden Record (Task 8.7)
    golden_record = generate_golden_record(aggregated_data)
    
    # Return formatted output for the Risk Score Calculator (Task 8.8)
    return {
        "statusCode": 200,
        "loan_application_id": event.get('loan_application_id'),
        "documents": [{"document_id": d.get("document_id"), "type": d.get("document_type")} for d in documents],
        "inconsistencies": inconsistencies,
        "golden_record": golden_record
    }
