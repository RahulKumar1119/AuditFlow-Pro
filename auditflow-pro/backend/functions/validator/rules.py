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
            modelId='anthropic.claude-3-haiku-20240307-v1:0', # Using Haiku for fast, cheap text reasoning
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

def validate_addresses(addresses: list) -> list:
    """Task 8.3 & 8.6: Compare addresses across documents using AI."""
    inconsistencies = []
    for i in range(len(addresses)):
        for j in range(i + 1, len(addresses)):
            # Use the Bedrock AI to check if they mean the same thing
            is_match = semantic_address_check(addresses[i]['value'], addresses[j]['value'])
            
            if not is_match:
                inconsistencies.append({
                    "field": "address",
                    "severity": "HIGH",
                    "expected_value": addresses[i]['value'],
                    "actual_value": addresses[j]['value'],
                    "source_documents": [addresses[i]['source'], addresses[j]['source']],
                    "description": "Address mismatch detected based on semantic AI check."
                })
    return inconsistencies
