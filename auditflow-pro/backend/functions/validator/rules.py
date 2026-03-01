# backend/functions/validator/rules.py

import json
import boto3
import logging

logger = logging.getLogger(__name__)

# Lazy initialization of Bedrock client for AI-powered semantic reasoning
_bedrock_client = None

def get_bedrock_client():
    """Get or create Bedrock client (lazy initialization)."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    return _bedrock_client

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates the minimum number of single-character edits between two strings."""
    if len(s1) < len(s2): return levenshtein_distance(s2, s1)
    if len(s2) == 0: return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def validate_names(names: list) -> list:
    """Task 8.2: Flags inconsistencies with edit distance > 2 characters."""
    inconsistencies = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            # Normalize names: lowercase and strip whitespace
            name1 = names[i]['value'].lower().strip()
            name2 = names[j]['value'].lower().strip()
            dist = levenshtein_distance(name1, name2)
            if dist > 2:
                inconsistencies.append({
                    "field": "name",
                    "severity": "HIGH",
                    "expected_value": names[i]['value'],
                    "actual_value": names[j]['value'],
                    "source_documents": [names[i]['source'], names[j]['source']],
                    "description": f"Name mismatch detected (Edit distance: {dist})"
                })
    return inconsistencies

def validate_ssn_dob(values: list, field_name: str) -> list:
    """Task 8.5: Compare SSN/DOB with zero tolerance."""
    inconsistencies = []
    if not values: return inconsistencies
    
    baseline = values[0]
    for val in values[1:]:
        if val['value'] != baseline['value']:
            inconsistencies.append({
                "field": field_name,
                "severity": "CRITICAL",
                "expected_value": baseline['value'],
                "actual_value": val['value'],
                "source_documents": [baseline['source'], val['source']],
                "description": f"Critical {field_name.upper()} mismatch detected."
            })
    return inconsistencies

def validate_income(w2_wages: list, tax_agi: dict) -> list:
    """Task 8.4: Compare summed W2 wages with Tax Form AGI (> 5% discrepancy)."""
    inconsistencies = []
    if not w2_wages or not tax_agi: return inconsistencies

    try:
        # Sum multiple W2s
        total_w2_income = sum([float(str(w['value']).replace(',', '').replace('$', '')) for w in w2_wages])
        agi_value = float(str(tax_agi['value']).replace(',', '').replace('$', ''))
        
        difference = abs(total_w2_income - agi_value)
        discrepancy_percentage = (difference / max(total_w2_income, 1)) * 100
        
        if discrepancy_percentage > 5.0:
            severity = "HIGH" if discrepancy_percentage > 10.0 else "MEDIUM"
            inconsistencies.append({
                "field": "income",
                "severity": severity,
                "expected_value": str(total_w2_income),
                "actual_value": str(agi_value),
                "source_documents": [w['source'] for w in w2_wages] + [tax_agi['source']],
                "description": f"Income discrepancy of {discrepancy_percentage:.2f}% detected between W2s and Tax Form."
            })
    except ValueError as e:
        logger.error(f"Failed to parse income values: {str(e)}")
        
    return inconsistencies

def semantic_address_check(address1: str, address2: str) -> bool:
    """Task 8.6: Use AWS Bedrock Claude 3 to reason about address equivalents."""
    prompt = f"""
    Human: You are a strict data validation assistant. 
    Are these two addresses semantically pointing to the exact same location despite abbreviations or formatting differences?
    Address 1: {address1}
    Address 2: {address2}
    Respond ONLY with "YES" or "NO".
    Assistant:
    """
    
    try:
        bedrock = get_bedrock_client()
        response = bedrock.invoke_model(
            modelId='anthropic.claude-sonnet-4-20250514-v1:0', # Using Claude Sonnet 4 for advanced reasoning
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        result = json.loads(response['body'].read())
        answer = result['content'][0]['text'].strip().upper()
        return answer == "YES"
    except Exception as e:
        logger.error(f"Bedrock invocation failed: {str(e)}")
        # Fallback to basic string comparison if AI fails
        return address1.lower().strip() == address2.lower().strip()

def parse_address_components(address: str) -> dict:
    """
    Task 8.3: Parse address into components (street, city, state, ZIP).
    
    This is a simple parser that handles common US address formats.
    Format: "123 Main St, Springfield, IL 62701"
    """
    components = {
        'street': None,
        'city': None,
        'state': None,
        'zip': None,
        'raw': address
    }
    
    if not address:
        return components
    
    # Clean and normalize the address
    address = address.strip()
    
    # Split by comma to get major components
    parts = [p.strip() for p in address.split(',')]
    
    if len(parts) >= 1:
        # First part is typically the street address
        components['street'] = parts[0]
    
    if len(parts) >= 2:
        # Second part is typically the city
        components['city'] = parts[1]
    
    if len(parts) >= 3:
        # Third part typically contains state and ZIP
        state_zip = parts[2].strip()
        # Split by space to separate state and ZIP
        state_zip_parts = state_zip.split()
        
        if len(state_zip_parts) >= 1:
            components['state'] = state_zip_parts[0]
        
        if len(state_zip_parts) >= 2:
            # ZIP code is typically the last part
            components['zip'] = state_zip_parts[-1]
    
    return components

def semantic_component_match(component1: str, component2: str, component_type: str) -> bool:
    """
    Task 8.3 & 8.6: Use Bedrock to check if address components are semantically equivalent.
    Handles format variations like "Street" vs "St", "Avenue" vs "Ave", etc.
    """
    if not component1 or not component2:
        return component1 == component2
    
    # Normalize for basic comparison
    c1_normalized = component1.lower().strip()
    c2_normalized = component2.lower().strip()
    
    # If they're exactly the same after normalization, they match
    if c1_normalized == c2_normalized:
        return True
    
    # Use Bedrock for semantic comparison to handle abbreviations
    prompt = f"""
    Human: You are a strict address validation assistant.
    Are these two {component_type} components semantically equivalent despite abbreviations or formatting differences?
    Component 1: {component1}
    Component 2: {component2}
    
    Consider common abbreviations like:
    - Street/St/St., Avenue/Ave/Ave., Road/Rd/Rd., Boulevard/Blvd/Blvd.
    - Drive/Dr/Dr., Lane/Ln/Ln., Court/Ct/Ct., Place/Pl/Pl.
    - North/N, South/S, East/E, West/W
    
    Respond ONLY with "YES" or "NO".
    Assistant:
    """
    
    try:
        bedrock = get_bedrock_client()
        response = bedrock.invoke_model(
            modelId='anthropic.claude-sonnet-4-20250514-v1:0', # Using Claude Sonnet 4 for advanced reasoning
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        result = json.loads(response['body'].read())
        answer = result['content'][0]['text'].strip().upper()
        return answer == "YES"
    except Exception as e:
        logger.error(f"Bedrock invocation failed for component matching: {str(e)}")
        # Fallback to exact match if AI fails
        return c1_normalized == c2_normalized

def validate_addresses(addresses: list) -> list:
    """
    Task 8.3 & 8.6: Parse addresses into components and compare each component.
    
    This function:
    1. Parses addresses into components (street, city, state, ZIP)
    2. Compares each component across documents
    3. Flags mismatches in any component
    4. Uses Bedrock to handle format variations (e.g., "Street" vs "St")
    """
    inconsistencies = []
    
    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            addr1 = addresses[i]['value']
            addr2 = addresses[j]['value']
            
            # Parse both addresses into components
            components1 = parse_address_components(addr1)
            components2 = parse_address_components(addr2)
            
            # Track which components don't match
            mismatched_components = []
            
            # Compare street component
            if components1['street'] and components2['street']:
                if not semantic_component_match(components1['street'], components2['street'], 'street'):
                    mismatched_components.append(f"street ('{components1['street']}' vs '{components2['street']}')")
            elif components1['street'] != components2['street']:
                # One is None and the other isn't
                mismatched_components.append(f"street ('{components1['street']}' vs '{components2['street']}')")
            
            # Compare city component
            if components1['city'] and components2['city']:
                if not semantic_component_match(components1['city'], components2['city'], 'city'):
                    mismatched_components.append(f"city ('{components1['city']}' vs '{components2['city']}')")
            elif components1['city'] != components2['city']:
                mismatched_components.append(f"city ('{components1['city']}' vs '{components2['city']}')")
            
            # Compare state component
            if components1['state'] and components2['state']:
                if not semantic_component_match(components1['state'], components2['state'], 'state'):
                    mismatched_components.append(f"state ('{components1['state']}' vs '{components2['state']}')")
            elif components1['state'] != components2['state']:
                mismatched_components.append(f"state ('{components1['state']}' vs '{components2['state']}')")
            
            # Compare ZIP component
            if components1['zip'] and components2['zip']:
                # ZIP codes should match exactly (no semantic matching needed)
                if components1['zip'].lower().strip() != components2['zip'].lower().strip():
                    mismatched_components.append(f"ZIP ('{components1['zip']}' vs '{components2['zip']}')")
            elif components1['zip'] != components2['zip']:
                mismatched_components.append(f"ZIP ('{components1['zip']}' vs '{components2['zip']}')")
            
            # If any components don't match, flag as inconsistency
            if mismatched_components:
                description = f"Address mismatch detected in: {', '.join(mismatched_components)}"
                inconsistencies.append({
                    "field": "address",
                    "severity": "HIGH",
                    "expected_value": addr1,
                    "actual_value": addr2,
                    "source_documents": [addresses[i]['source'], addresses[j]['source']],
                    "description": description
                })
                logger.info(f"Address mismatch: {description}")
    
    return inconsistencies

def generate_golden_record(loan_application_id: str, documents: list, created_timestamp: str) -> dict:
    """
    Task 8.7: Generate Golden Record by selecting the most reliable value for each field.
    
    Reliability hierarchy: Government ID > Tax Forms > W2 > Bank Statements
    - Government ID (DRIVERS_LICENSE, ID_DOCUMENT): reliability = 4
    - Tax Forms (TAX_FORM): reliability = 3
    - W2: reliability = 2
    - Bank Statements (BANK_STATEMENT): reliability = 1
    
    When sources have equal reliability, use the highest confidence value.
    Store alternative values for reference.
    
    Args:
        loan_application_id: The loan application identifier
        documents: List of DocumentMetadata objects with extracted data
        created_timestamp: Timestamp for the Golden Record creation
    
    Returns:
        Dictionary representing the GoldenRecord with consolidated data
    """
    from datetime import datetime
    
    # Define reliability hierarchy
    RELIABILITY_HIERARCHY = {
        'DRIVERS_LICENSE': 4,
        'ID_DOCUMENT': 4,
        'TAX_FORM': 3,
        'W2': 2,
        'BANK_STATEMENT': 1
    }
    
    def get_reliability(doc_type: str) -> int:
        """Get reliability score for a document type."""
        return RELIABILITY_HIERARCHY.get(doc_type, 0)
    
    def extract_field_value(field_data):
        """Extract value and confidence from field data (handles dict and object formats)."""
        if field_data is None:
            return None, 0.0
        
        if isinstance(field_data, dict):
            value = field_data.get('value')
            confidence = field_data.get('confidence', 0.0)
        elif hasattr(field_data, 'value'):
            value = field_data.value
            confidence = getattr(field_data, 'confidence', 0.0)
        else:
            value = str(field_data)
            confidence = 1.0
        
        return value, float(confidence) if confidence else 0.0
    
    def select_best_value(candidates: list) -> dict:
        """
        Select the best value from candidates based on reliability and confidence.
        
        Args:
            candidates: List of dicts with keys: value, source_document, confidence, reliability, doc_type
        
        Returns:
            Dict with: value, source_document, confidence, alternative_values, verified_by
        """
        if not candidates:
            return None
        
        # Sort by reliability (descending), then by confidence (descending)
        sorted_candidates = sorted(
            candidates,
            key=lambda x: (x['reliability'], x['confidence']),
            reverse=True
        )
        
        # Best candidate is the first one
        best = sorted_candidates[0]
        
        # Collect alternative values (excluding the best one)
        alternative_values = []
        verified_by = []
        
        for candidate in sorted_candidates[1:]:
            # Only add as alternative if the value is different
            if candidate['value'] != best['value']:
                alternative_values.append(candidate['value'])
            else:
                # Same value from different source - add to verified_by
                verified_by.append(candidate['source_document'])
        
        return {
            'value': best['value'],
            'source_document': best['source_document'],
            'confidence': best['confidence'],
            'alternative_values': alternative_values,
            'verified_by': verified_by
        }
    
    # Initialize field collectors
    name_candidates = []
    dob_candidates = []
    ssn_candidates = []
    address_candidates = []
    employer_candidates = []
    employer_ein_candidates = []
    annual_income_candidates = []
    bank_account_candidates = []
    ending_balance_candidates = []
    drivers_license_number_candidates = []
    drivers_license_state_candidates = []
    
    # Extract fields from all documents
    for doc in documents:
        doc_type = doc.document_type
        doc_id = doc.document_id
        extracted_data = doc.extracted_data
        reliability = get_reliability(doc_type)
        
        if not extracted_data:
            continue
        
        # Extract name field (varies by document type)
        name_field = None
        if doc_type == 'W2' and 'employee_name' in extracted_data:
            name_field = extracted_data['employee_name']
        elif doc_type == 'BANK_STATEMENT' and 'account_holder_name' in extracted_data:
            name_field = extracted_data['account_holder_name']
        elif doc_type == 'TAX_FORM' and 'taxpayer_name' in extracted_data:
            name_field = extracted_data['taxpayer_name']
        elif doc_type in ['DRIVERS_LICENSE', 'ID_DOCUMENT'] and 'full_name' in extracted_data:
            name_field = extracted_data['full_name']
        
        if name_field:
            value, confidence = extract_field_value(name_field)
            if value:
                name_candidates.append({
                    'value': value,
                    'source_document': doc_id,
                    'confidence': confidence,
                    'reliability': reliability,
                    'doc_type': doc_type
                })
        
        # Extract date of birth (from identification documents)
        if 'date_of_birth' in extracted_data:
            value, confidence = extract_field_value(extracted_data['date_of_birth'])
            if value:
                dob_candidates.append({
                    'value': value,
                    'source_document': doc_id,
                    'confidence': confidence,
                    'reliability': reliability,
                    'doc_type': doc_type
                })
        
        # Extract SSN
        ssn_field = None
        if doc_type == 'W2' and 'employee_ssn' in extracted_data:
            ssn_field = extracted_data['employee_ssn']
        elif doc_type == 'TAX_FORM' and 'taxpayer_ssn' in extracted_data:
            ssn_field = extracted_data['taxpayer_ssn']
        
        if ssn_field:
            value, confidence = extract_field_value(ssn_field)
            if value:
                ssn_candidates.append({
                    'value': value,
                    'source_document': doc_id,
                    'confidence': confidence,
                    'reliability': reliability,
                    'doc_type': doc_type
                })
        
        # Extract address (varies by document type)
        address_field = None
        if doc_type == 'W2' and 'employee_address' in extracted_data:
            address_field = extracted_data['employee_address']
        elif doc_type == 'BANK_STATEMENT' and 'account_holder_address' in extracted_data:
            address_field = extracted_data['account_holder_address']
        elif doc_type == 'TAX_FORM' and 'address' in extracted_data:
            address_field = extracted_data['address']
        elif doc_type == 'DRIVERS_LICENSE' and 'address' in extracted_data:
            address_field = extracted_data['address']
        
        if address_field:
            value, confidence = extract_field_value(address_field)
            if value:
                address_candidates.append({
                    'value': value,
                    'source_document': doc_id,
                    'confidence': confidence,
                    'reliability': reliability,
                    'doc_type': doc_type
                })
        
        # Extract employer information (from W2)
        if doc_type == 'W2':
            if 'employer_name' in extracted_data:
                value, confidence = extract_field_value(extracted_data['employer_name'])
                if value:
                    employer_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
            
            if 'employer_ein' in extracted_data:
                value, confidence = extract_field_value(extracted_data['employer_ein'])
                if value:
                    employer_ein_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
            
            if 'wages' in extracted_data:
                value, confidence = extract_field_value(extracted_data['wages'])
                if value:
                    annual_income_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
        
        # Extract income from tax form
        if doc_type == 'TAX_FORM' and 'adjusted_gross_income' in extracted_data:
            value, confidence = extract_field_value(extracted_data['adjusted_gross_income'])
            if value:
                annual_income_candidates.append({
                    'value': value,
                    'source_document': doc_id,
                    'confidence': confidence,
                    'reliability': reliability,
                    'doc_type': doc_type
                })
        
        # Extract bank account information (from bank statement)
        if doc_type == 'BANK_STATEMENT':
            if 'account_number' in extracted_data:
                value, confidence = extract_field_value(extracted_data['account_number'])
                if value:
                    bank_account_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
            
            if 'ending_balance' in extracted_data:
                value, confidence = extract_field_value(extracted_data['ending_balance'])
                if value:
                    ending_balance_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
        
        # Extract driver's license information
        if doc_type == 'DRIVERS_LICENSE':
            if 'license_number' in extracted_data:
                value, confidence = extract_field_value(extracted_data['license_number'])
                if value:
                    drivers_license_number_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
            
            if 'state' in extracted_data:
                value, confidence = extract_field_value(extracted_data['state'])
                if value:
                    drivers_license_state_candidates.append({
                        'value': value,
                        'source_document': doc_id,
                        'confidence': confidence,
                        'reliability': reliability,
                        'doc_type': doc_type
                    })
    
    # Build Golden Record by selecting best value for each field
    golden_record = {
        'loan_application_id': loan_application_id,
        'created_timestamp': created_timestamp
    }
    
    # Select best values for each field
    if name_candidates:
        golden_record['name'] = select_best_value(name_candidates)
    
    if dob_candidates:
        golden_record['date_of_birth'] = select_best_value(dob_candidates)
    
    if ssn_candidates:
        golden_record['ssn'] = select_best_value(ssn_candidates)
    
    if address_candidates:
        golden_record['address'] = select_best_value(address_candidates)
    
    if employer_candidates:
        golden_record['employer'] = select_best_value(employer_candidates)
    
    if employer_ein_candidates:
        golden_record['employer_ein'] = select_best_value(employer_ein_candidates)
    
    if annual_income_candidates:
        golden_record['annual_income'] = select_best_value(annual_income_candidates)
    
    if bank_account_candidates:
        golden_record['bank_account'] = select_best_value(bank_account_candidates)
    
    if ending_balance_candidates:
        golden_record['ending_balance'] = select_best_value(ending_balance_candidates)
    
    if drivers_license_number_candidates:
        golden_record['drivers_license_number'] = select_best_value(drivers_license_number_candidates)
    
    if drivers_license_state_candidates:
        golden_record['drivers_license_state'] = select_best_value(drivers_license_state_candidates)
    
    logger.info(f"Generated Golden Record for loan application {loan_application_id} with {len(golden_record) - 2} fields")
    
    return golden_record
