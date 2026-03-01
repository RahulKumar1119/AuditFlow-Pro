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
