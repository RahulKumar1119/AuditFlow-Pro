# backend/functions/validator/golden_record.py

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def generate_golden_record(aggregated_data: Dict[str, list]) -> Dict[str, Any]:
    """
    Task 8.7: Generates the Golden Record (Single Source of Truth).
    It evaluates all extracted values for a given field across multiple documents and selects 
    the best one based on a predefined document reliability hierarchy and Textract confidence scores.
    """
    # Define reliability hierarchy (Lower index = higher priority/more trusted)
    hierarchy = {
        "name": ["ID_DOCUMENT", "DRIVERS_LICENSE", "W2", "TAX_FORM", "BANK_STATEMENT"],
        "ssn": ["W2", "TAX_FORM", "BANK_STATEMENT"],
        "address": ["DRIVERS_LICENSE", "ID_DOCUMENT", "BANK_STATEMENT", "W2", "TAX_FORM"],
        "dob": ["DRIVERS_LICENSE", "ID_DOCUMENT"]
    }
    
    golden_record = {}
    
    for field, values_list in aggregated_data.items():
        if not values_list:
            continue
            
        # Determine the primary hierarchy for the current field
        # E.g., 'first_name', 'last_name', 'employer_name' all fall under the 'name' hierarchy
        field_category = next((k for k in hierarchy.keys() if k in field.lower()), "default")
        current_hierarchy = hierarchy.get(field_category, [])
        
        # Sort values based on:
        # 1. Hierarchy priority (trusted documents come first)
        # 2. Textract Confidence score (highest confidence breaks ties)
        def sort_key(val):
            doc_type = val.get('document_type', 'UNKNOWN')
            # If doc_type is in the hierarchy, use its index. Otherwise, give it a low priority (99).
            priority = current_hierarchy.index(doc_type) if doc_type in current_hierarchy else 99
            confidence = val.get('confidence', 0.0)
            
            # Return tuple: (lowest priority number first, highest confidence first)
            return (priority, -confidence) 
            
        sorted_values = sorted(values_list, key=sort_key)
        
        # The top item becomes the golden value, the rest are stored as alternatives for human review
        best_match = sorted_values[0]
        golden_record[field] = {
            "value": best_match.get('value'),
            "source_document": best_match.get('source'),
            "confidence": best_match.get('confidence'),
            "alternative_values": [v.get('value') for v in sorted_values[1:] if v.get('value') != best_match.get('value')]
        }
        
    logger.info(f"Successfully generated Golden Record with {len(golden_record)} distinct fields.")
    return golden_record
