# AWS Bedrock Usage in AuditFlow Pro

## Overview

AuditFlow Pro leverages **AWS Bedrock** with **Claude 3 Sonnet 4** for AI-powered semantic reasoning in document validation. This enables intelligent comparison of data across multiple documents, handling format variations and abbreviations that would be difficult with traditional string matching.

## Use Cases

### 1. Semantic Address Validation (Task 8.6)

**Purpose:** Compare addresses across documents despite formatting differences and abbreviations.

**Implementation:**
- Located in: `backend/functions/validator/rules.py`
- Function: `semantic_address_check(address1: str, address2: str) -> bool`

**How it works:**
```python
def semantic_address_check(address1: str, address2: str) -> bool:
    """Use AWS Bedrock Claude 3 to reason about address equivalents."""
    prompt = f"""
    Human: You are a strict data validation assistant. 
    Are these two addresses semantically pointing to the exact same location despite abbreviations or formatting differences?
    Address 1: {address1}
    Address 2: {address2}
    Respond ONLY with "YES" or "NO".
    Assistant:
    """
```

**Example Scenarios:**
- "123 Main Street, Springfield, IL 62701" vs "123 Main St, Springfield, Illinois 62701" → YES
- "456 Oak Avenue, Chicago, IL 60601" vs "456 Oak Ave, Chicago, IL 60601" → YES
- "789 Elm Road, Boston, MA 02101" vs "789 Elm Rd, Boston, MA 02101" → YES

**Fallback Behavior:**
If Bedrock invocation fails, the system falls back to basic string comparison:
```python
except Exception as e:
    logger.error(f"Bedrock invocation failed: {str(e)}")
    return address1.lower().strip() == address2.lower().strip()
```

### 2. Semantic Address Component Matching (Task 8.3)

**Purpose:** Compare individual address components (street, city, state, ZIP) handling abbreviations.

**Implementation:**
- Function: `semantic_component_match(component1: str, component2: str, component_type: str) -> bool`

**How it works:**
Handles format variations like:
- "Street" vs "St"
- "Avenue" vs "Ave"
- "Road" vs "Rd"
- "Illinois" vs "IL"

**Example Scenarios:**
- Component Type: "street_type"
  - "Street" vs "St" → YES
  - "Avenue" vs "Ave" → YES
  - "Boulevard" vs "Blvd" → YES

- Component Type: "state"
  - "Illinois" vs "IL" → YES
  - "California" vs "CA" → YES

### 3. Address Inconsistency Detection (Task 8.1)

**Purpose:** Detect and flag address mismatches across documents.

**Implementation:**
- Function: `validate_addresses(addresses: list) -> list`

**Process:**
1. Parses each address into components (street, city, state, ZIP)
2. Compares each component across documents
3. Flags mismatches in any component
4. Uses Bedrock to handle format variations

**Output:**
```json
{
  "field": "address",
  "severity": "HIGH",
  "expected_value": "123 Main Street, Springfield, IL 62701",
  "actual_value": "123 Main Street, Springfield, IL 62702",
  "source_documents": ["document_1", "document_2"],
  "description": "Address mismatch detected in ZIP code"
}
```

## Technical Details

### Bedrock Configuration

**Model Used:** `anthropic.claude-sonnet-4-20250514-v1:0`
- Advanced reasoning capabilities
- Optimized for data validation tasks
- Fast response times

**Region:** `ap-south-1` (Asia Pacific - Mumbai)

**API Version:** `bedrock-2023-05-31`

### Client Initialization

```python
def get_bedrock_client():
    """Get or create Bedrock client (lazy initialization)."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name='ap-south-1')
    return _bedrock_client
```

**Lazy Initialization Benefits:**
- Reduces cold start time
- Reuses client connection across invocations
- Improves Lambda performance

### Request Format

```python
response = bedrock.invoke_model(
    modelId='anthropic.claude-sonnet-4-20250514-v1:0',
    contentType='application/json',
    accept='application/json',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10,  # Minimal tokens for YES/NO responses
        "messages": [{"role": "user", "content": prompt}]
    })
)
```

## Error Handling

### Graceful Degradation

If Bedrock invocation fails:
1. Error is logged: `logger.error(f"Bedrock invocation failed: {str(e)}")`
2. System falls back to traditional string comparison
3. Validation continues without blocking the pipeline

### Common Failure Scenarios

1. **Network Issues:** Bedrock service unavailable
   - Fallback: Exact string matching
   
2. **Rate Limiting:** Too many concurrent requests
   - Fallback: Exact string matching
   
3. **Invalid Model ID:** Model not available in region
   - Fallback: Exact string matching

## Performance Considerations

### Latency
- Average response time: 200-500ms per invocation
- Cached client reduces overhead
- Minimal token usage (max_tokens: 10)

### Cost
- Charged per input/output tokens
- Minimal cost due to short prompts and responses
- Estimated cost: ~$0.0001 per validation

### Optimization Tips
1. Batch similar validations together
2. Use lazy client initialization
3. Set appropriate max_tokens (10 for YES/NO)
4. Implement request timeouts

## Integration Points

### Validator Lambda Function
- **File:** `backend/functions/validator/app.py`
- **Trigger:** Document processing pipeline
- **Input:** Extracted data from documents
- **Output:** Validation report with inconsistencies

### Step Function Integration
- Validator runs as part of the audit pipeline
- Results feed into Risk Scorer
- Inconsistencies flagged for manual review

## Future Enhancements

1. **Caching:** Cache validation results for identical address pairs
2. **Batch Processing:** Process multiple addresses in single Bedrock call
3. **Custom Models:** Fine-tune Claude on domain-specific address formats
4. **Multi-language Support:** Extend to international addresses
5. **Confidence Scoring:** Return confidence levels instead of binary YES/NO

## Troubleshooting

### Issue: Bedrock invocation timeout
**Solution:** Increase Lambda timeout, check network connectivity

### Issue: Inconsistent validation results
**Solution:** Review prompt clarity, ensure consistent input formatting

### Issue: High costs
**Solution:** Implement caching, reduce max_tokens, batch requests

## References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude 3 Model Card](https://www.anthropic.com/news/claude-3-family)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
