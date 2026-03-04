# AWS Bedrock Usage in AuditFlow-Pro

## Overview

AWS Bedrock (Claude 3 Sonnet) is used in the validator Lambda function for **semantic address validation**. It helps detect address inconsistencies by understanding abbreviations and formatting variations.

## Location

**File**: `auditflow-pro/backend/functions/validator/rules.py`

## Functions Using Bedrock

### 1. `semantic_address_check(address1: str, address2: str) -> bool`

**Purpose**: Compare two full addresses semantically to determine if they point to the same location

**Location**: Lines 102-131

**How it works**:
- Takes two addresses as input
- Sends them to Claude 3 Sonnet via Bedrock
- Claude determines if they're semantically equivalent despite formatting differences
- Returns True if addresses match, False otherwise

**Example**:
```python
# These would be considered equivalent:
semantic_address_check(
    "123 Main Street, Springfield, IL 62701",
    "123 Main St, Springfield, Illinois 62701"
)  # Returns: True
```

**Fallback**: If Bedrock fails, falls back to basic string comparison

### 2. `semantic_component_match(component1: str, component2: str, component_type: str) -> bool`

**Purpose**: Compare individual address components (street, city, state, ZIP) semantically

**Location**: Lines 180-230

**How it works**:
- Takes two address components and component type (e.g., "street", "city")
- Sends them to Claude 3 Sonnet via Bedrock
- Claude checks if they're semantically equivalent
- Handles common abbreviations:
  - Street/St/St.
  - Avenue/Ave/Ave.
  - Road/Rd/Rd.
  - Boulevard/Blvd/Blvd.
  - Drive/Dr/Dr.
  - Lane/Ln/Ln.
  - Court/Ct/Ct.
  - Place/Pl/Pl.
  - Directions: North/N, South/S, East/E, West/W

**Example**:
```python
# These would be considered equivalent:
semantic_component_match("Street", "St", "street")  # Returns: True
semantic_component_match("Avenue", "Ave", "street")  # Returns: True
```

**Fallback**: If Bedrock fails, falls back to normalized string comparison

## Bedrock Configuration

### Model Used
- **Model ID**: `anthropic.claude-sonnet-4-20250514-v1:0`
- **Model**: Claude 3 Sonnet 4 (latest)
- **Region**: `ap-south-1` (Asia Pacific - Mumbai)

### API Details
- **Service**: `bedrock-runtime`
- **Content Type**: `application/json`
- **Max Tokens**: 10 (since response is just "YES" or "NO")
- **Anthropic Version**: `bedrock-2023-05-31`

### Client Initialization
```python
def get_bedrock_client():
    """Get or create Bedrock client (lazy initialization)."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client('bedrock-runtime', region_name='ap-south-1')
    return _bedrock_client
```

## Prompts Sent to Bedrock

### Address Comparison Prompt
```
Human: You are a strict data validation assistant. 
Are these two addresses semantically pointing to the exact same location despite abbreviations or formatting differences?
Address 1: {address1}
Address 2: {address2}
Respond ONLY with "YES" or "NO".
Assistant:
```

### Component Comparison Prompt
```
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
```

## Integration in Validation Flow

The Bedrock functions are called from `validate_addresses()`:

```
validate_addresses()
    ↓
parse_address_components() - Parse each address into components
    ↓
For each component pair:
    ├─ semantic_component_match() - Compare using Bedrock
    └─ If mismatch detected → Add to inconsistencies
    ↓
For full addresses:
    ├─ semantic_address_check() - Compare using Bedrock
    └─ If mismatch detected → Add to inconsistencies
```

## Error Handling

Both functions have graceful fallback mechanisms:

1. **Bedrock Invocation Fails**:
   - Logs error: `"Bedrock invocation failed: {error}"`
   - Falls back to basic string comparison
   - Validation continues without AI assistance

2. **Network Issues**:
   - Caught by exception handler
   - Falls back to normalized comparison
   - No validation failure

## IAM Permissions Required

The Lambda execution role needs Bedrock permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel"
  ],
  "Resource": [
    "arn:aws:bedrock:ap-south-1::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0"
  ]
}
```

## Cost Considerations

- **Model**: Claude 3 Sonnet 4
- **Input Tokens**: ~50-100 per address comparison
- **Output Tokens**: ~1-2 per response
- **Pricing**: Check AWS Bedrock pricing for ap-south-1 region
- **Frequency**: Called only when addresses need semantic comparison

## Performance Notes

- **Latency**: ~500ms-2s per Bedrock invocation
- **Timeout**: Lambda has 300s timeout, so multiple comparisons are fine
- **Caching**: No caching implemented (each comparison is fresh)
- **Concurrency**: Bedrock has account-level rate limits

## Testing Bedrock Integration

To test Bedrock functionality:

```python
from auditflow-pro.backend.functions.validator.rules import (
    semantic_address_check,
    semantic_component_match
)

# Test address comparison
result = semantic_address_check(
    "123 Main Street, Springfield, IL 62701",
    "123 Main St, Springfield, Illinois 62701"
)
print(f"Addresses match: {result}")

# Test component comparison
result = semantic_component_match("Street", "St", "street")
print(f"Components match: {result}")
```

## Troubleshooting

### Bedrock Invocation Fails
**Symptoms**: Validation completes but uses fallback comparison

**Causes**:
- IAM role missing Bedrock permissions
- Model not available in region
- Rate limit exceeded
- Network connectivity issue

**Solution**:
1. Check IAM permissions
2. Verify model availability in ap-south-1
3. Check CloudWatch logs for specific error
4. Verify network connectivity

### Unexpected Validation Results
**Symptoms**: Addresses that should match are flagged as mismatches

**Causes**:
- Bedrock model interpretation differs from expectations
- Prompt needs refinement
- Fallback comparison being used

**Solution**:
1. Check CloudWatch logs for Bedrock errors
2. Review the prompt in rules.py
3. Test with simpler address formats
4. Consider adjusting prompt for clarity

## Future Improvements

1. **Caching**: Cache Bedrock responses for common address patterns
2. **Batch Processing**: Use Bedrock batch API for multiple comparisons
3. **Custom Model**: Fine-tune Claude on address validation examples
4. **Fallback Strategy**: Implement more sophisticated fallback logic
5. **Monitoring**: Add metrics for Bedrock invocation success rate

## References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude 3 Models](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
- [Bedrock Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html)
