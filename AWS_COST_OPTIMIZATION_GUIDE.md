# AWS Cost Optimization Guide - AuditFlow-Pro

## Executive Summary

AuditFlow-Pro is a serverless AI-powered loan document auditor built on AWS. This guide provides resource optimization strategies and expected running costs for the Asia Pacific (Mumbai) region.

---

## 1. Current Architecture Overview

### Services Used
- **AWS Lambda** - Document processing, extraction, classification
- **Amazon DynamoDB** - Audit records, user data, cache
- **Amazon S3** - Document storage, logs
- **AWS Amplify** - Frontend hosting
- **Amazon Bedrock** - AI/ML inference (Claude)
- **AWS API Gateway** - REST API endpoints
- **AWS Step Functions** - Workflow orchestration
- **Amazon Cognito** - Authentication
- **AWS CloudWatch** - Monitoring and logs


---

## 2. Resource Optimization Strategies

### 2.1 AWS Lambda Optimization

#### Current Implementation
```python
# Backend functions in auditflow-pro/backend/functions/
- extractor/lambda_handler.py      # PDF extraction
- classifier/lambda_handler.py     # Document classification
- validator/lambda_handler.py      # Income validation
- reporter/lambda_handler.py       # Report generation
- risk_scorer/lambda_handler.py    # Risk scoring
```

#### Optimization Strategies

**A. Memory Optimization**
```
Current: 512 MB per function
Optimized: 256-384 MB

Impact:
- 50% cost reduction for memory
- Faster execution (more CPU allocated)
- Better price-to-performance ratio

Implementation:
1. Profile each Lambda function
2. Set memory to minimum required + 10% buffer
3. Monitor CloudWatch metrics
```

**B. Timeout Optimization**
```
Current: 300 seconds (5 minutes)
Optimized: 60-120 seconds per function

Breakdown:
- Extractor: 60 seconds (PDF parsing)
- Classifier: 45 seconds (AI inference)
- Validator: 30 seconds (data validation)
- Reporter: 90 seconds (report generation)
- Risk Scorer: 45 seconds (scoring logic)

Implementation:
1. Set appropriate timeouts per function
2. Implement async processing for long tasks
3. Use Step Functions for orchestration
```

**C. Concurrency Control**
```
Reserved Concurrency: 10-20 concurrent executions
Provisioned Concurrency: 5 (for critical functions)

Cost Savings:
- Avoid cold starts
- Predictable performance
- Reduced throttling

Monthly Cost:
- Provisioned: ~$0.015 per hour × 730 hours = $10.95
- Savings from reduced cold starts: ~$15-20/month
```

**D. Code Optimization**
```python
# Optimization techniques in your code:

1. Connection Pooling
   - Reuse DynamoDB connections
   - Reuse S3 clients
   - Implement connection caching

2. Lazy Loading
   - Import heavy libraries only when needed
   - Load ML models on first invocation

3. Batch Operations
   - Batch DynamoDB writes
   - Batch S3 operations
   - Reduce API calls

4. Caching
   - Cache Bedrock responses
   - Cache classification results
   - Use DynamoDB TTL for cache expiration
```

### 2.2 DynamoDB Optimization

#### Current Implementation
```
Tables:
- AuditFlow-AuditRecords (main data)
- AuditFlow-Users (user profiles)
- AuditFlow-Cache (temporary data)
```

#### Optimization Strategies

**A. Billing Mode**
```
Current: On-Demand (pay per request)
Optimized: Provisioned (for predictable workloads)

Comparison:
On-Demand:
- Read: $1.25 per million RCU
- Write: $6.25 per million WCU
- Good for: Unpredictable traffic

Provisioned:
- Read: $0.00013 per RCU-hour
- Write: $0.00065 per WCU-hour
- Good for: Predictable traffic

Recommendation for AuditFlow-Pro:
- Use Provisioned for main tables
- Use On-Demand for cache/temporary tables

Expected Savings: 40-60% on DynamoDB costs
```

**B. Capacity Planning**
```
Estimated Daily Usage:
- 100 audit requests/day
- 500 reads/day
- 200 writes/day

Provisioned Capacity:
- Read: 10 RCU (handles 400 reads/sec)
- Write: 5 WCU (handles 5 writes/sec)

Monthly Cost:
- Read: 10 RCU × 730 hours × $0.00013 = $0.95
- Write: 5 WCU × 730 hours × $0.00065 = $2.37
- Total: ~$3.32/month (vs $15-20 on-demand)
```

**C. TTL and Cleanup**
```python
# Implement TTL for cache tables
{
    "TableName": "AuditFlow-Cache",
    "TimeToLiveSpecification": {
        "AttributeName": "ExpirationTime",
        "Enabled": true
    }
}

# Automatic cleanup saves storage costs
# Reduces table size by 30-40%
```

**D. Global Secondary Indexes (GSI)**
```
Current GSIs:
- UserID-CreatedAt (for user queries)
- Status-CreatedAt (for status queries)

Optimization:
- Remove unused GSIs
- Consolidate queries to use fewer indexes
- Use sparse indexes (only for relevant items)

Savings: $0.10-0.25/month per removed GSI
```

### 2.3 S3 Optimization

#### Current Implementation
```
Buckets:
- auditflow-documents (uploaded PDFs)
- auditflow-reports (generated reports)
- auditflow-logs (CloudWatch logs)
```

#### Optimization Strategies

**A. Storage Classes**
```
Current: Standard (all files)
Optimized: Tiered approach

Tier 1 - Standard (0-30 days)
- Active documents
- Recent reports
- Cost: $0.023/GB

Tier 2 - Intelligent-Tiering (30-90 days)
- Archived documents
- Cost: $0.0125/GB (auto-optimized)

Tier 3 - Glacier (90+ days)
- Long-term archive
- Cost: $0.004/GB

Implementation:
- Set lifecycle policies
- Auto-transition after 30/90 days
- Reduce storage costs by 60-70%
```

**B. Lifecycle Policies**
```json
{
    "Rules": [
        {
            "Id": "TransitionToIA",
            "Status": "Enabled",
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"
                }
            ],
            "Expiration": {
                "Days": 365
            }
        }
    ]
}
```

**C. Versioning and Cleanup**
```
Current: Versioning enabled (stores all versions)
Optimized: Limit version history

Implementation:
- Keep only last 3 versions
- Delete old versions after 30 days
- Reduces storage by 50-70%

Savings: ~$5-10/month
```

**D. Compression**
```python
# Compress documents before upload
import gzip

def compress_document(file_path):
    with open(file_path, 'rb') as f_in:
        with gzip.open(f_path + '.gz', 'wb') as f_out:
            f_out.writelines(f_in)
    
    # Reduces size by 70-80% for PDFs
    # Saves bandwidth and storage
```

### 2.4 Bedrock (AI/ML) Optimization

#### Current Implementation
```python
# Using Claude for document analysis
import boto3

bedrock = boto3.client('bedrock-runtime', region_name='ap-south-1')

response = bedrock.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps({
        "prompt": document_text,
        "max_tokens": 1024
    })
)
```

#### Optimization Strategies

**A. Model Selection**
```
Current: Claude 3 Sonnet
- Cost: $3/1M input tokens, $15/1M output tokens
- Quality: High
- Speed: Medium

Alternatives:
1. Claude 3 Haiku (faster, cheaper)
   - Cost: $0.25/1M input, $1.25/1M output
   - 80% cost reduction
   - Good for: Simple classification

2. Claude 3 Opus (more accurate)
   - Cost: $15/1M input, $75/1M output
   - Better for: Complex analysis

Recommendation:
- Use Haiku for classification (80% of calls)
- Use Sonnet for complex analysis (20% of calls)
- Expected savings: 60-70%
```

**B. Prompt Optimization**
```python
# Reduce token usage by 40-50%

# Before (verbose)
prompt = """
Please analyze this loan document and extract all relevant 
financial information including income, debts, assets, and 
liabilities. Also provide a risk assessment based on the 
extracted data.
"""

# After (concise)
prompt = """
Extract: income, debts, assets, liabilities, risk score
Format: JSON
"""

# Savings: 50-60% fewer tokens
```

**C. Caching Responses**
```python
# Cache Bedrock responses in DynamoDB

def get_classification(document_hash):
    # Check cache first
    cache_response = dynamodb.get_item(
        TableName='AuditFlow-Cache',
        Key={'DocumentHash': {'S': document_hash}}
    )
    
    if 'Item' in cache_response:
        return cache_response['Item']
    
    # Call Bedrock if not cached
    result = bedrock.invoke_model(...)
    
    # Cache for 7 days
    dynamodb.put_item(
        TableName='AuditFlow-Cache',
        Item={
            'DocumentHash': {'S': document_hash},
            'Result': {'S': json.dumps(result)},
            'ExpirationTime': {'N': str(int(time.time()) + 604800)}
        }
    )
    
    return result

# Reduces Bedrock calls by 30-40%
# Savings: $50-100/month
```

**D. Batch Processing**
```python
# Process multiple documents in batch

def batch_classify_documents(documents):
    results = []
    for doc in documents:
        # Batch similar requests
        # Reuse connections
        # Reduce overhead
        result = classify_document(doc)
        results.append(result)
    
    return results

# Reduces API overhead by 20-30%
```

### 2.5 API Gateway Optimization

#### Current Implementation
```
Endpoints:
- POST /audit (upload document)
- GET /audit/{id} (get results)
- GET /audit (list audits)
- DELETE /audit/{id} (delete audit)
```

#### Optimization Strategies

**A. Caching**
```
Enable API Gateway caching:
- Cache TTL: 300 seconds (5 minutes)
- Cache size: 0.5 GB
- Cost: $0.02/hour

Reduces backend calls by 40-50%
Savings: $10-15/month
```

**B. Request Throttling**
```
Throttle settings:
- Rate: 10,000 requests/second
- Burst: 5,000 requests

Prevents abuse and reduces costs
```

**C. Compression**
```
Enable gzip compression:
- Reduces response size by 70-80%
- Reduces bandwidth costs
- Improves client performance
```

### 2.6 CloudWatch Optimization

#### Current Implementation
```
Logs from:
- Lambda functions
- API Gateway
- DynamoDB
- Step Functions
```

#### Optimization Strategies

**A. Log Retention**
```
Current: Indefinite retention
Optimized: Tiered retention

- ERROR logs: 30 days
- WARN logs: 14 days
- INFO logs: 7 days
- DEBUG logs: 1 day

Reduces storage by 80-90%
Savings: $5-10/month
```

**B. Log Filtering**
```python
# Filter unnecessary logs

# Don't log:
- Health checks
- Successful requests (sample only)
- Verbose debug info

# Do log:
- Errors
- Warnings
- Performance metrics
- Business events

Reduces log volume by 60-70%
```

**C. Metrics Optimization**
```
Use custom metrics only for:
- Business KPIs
- Performance bottlenecks
- Error rates

Avoid:
- Logging every request
- Duplicate metrics
- High-cardinality metrics

Savings: $5-20/month
```

---

## 3. Expected Running Costs

### 3.1 Monthly Cost Breakdown (Current)

```
Service                    Current Cost    Optimized Cost    Savings
─────────────────────────────────────────────────────────────────────
AWS Lambda                 $150-200        $60-80           60-70%
Amazon DynamoDB            $50-80          $15-25           70%
Amazon S3                  $30-50          $10-15           70%
AWS Bedrock               $200-300        $60-100          70%
AWS Amplify               $50-100         $30-50           40%
API Gateway               $20-30          $10-15           50%
CloudWatch                $30-50          $5-10            80%
Step Functions            $10-15          $5-10            50%
Cognito                   $0 (free tier)  $0               -

─────────────────────────────────────────────────────────────────────
TOTAL                     $560-835        $205-320         65%
```

### 3.2 Cost Estimation by Usage Tier

#### Tier 1: Development/Testing
```
Monthly Audits: 100
Monthly API Calls: 5,000

Estimated Costs:
- Lambda: $15
- DynamoDB: $2
- S3: $2
- Bedrock: $20
- Other: $10
─────────────
TOTAL: $49/month
```

#### Tier 2: Small Production
```
Monthly Audits: 1,000
Monthly API Calls: 50,000

Estimated Costs:
- Lambda: $60
- DynamoDB: $8
- S3: $8
- Bedrock: $80
- Other: $30
─────────────
TOTAL: $186/month
```

#### Tier 3: Medium Production
```
Monthly Audits: 10,000
Monthly API Calls: 500,000

Estimated Costs:
- Lambda: $150
- DynamoDB: $25
- S3: $20
- Bedrock: $200
- Other: $75
─────────────
TOTAL: $470/month
```

#### Tier 4: Large Production
```
Monthly Audits: 100,000
Monthly API Calls: 5,000,000

Estimated Costs:
- Lambda: $300
- DynamoDB: $80
- S3: $50
- Bedrock: $500
- Other: $150
─────────────
TOTAL: $1,080/month
```

### 3.3 Cost Per Audit

```
Breakdown per audit (optimized):

Lambda Processing:        $0.05
DynamoDB Storage:         $0.01
S3 Storage:              $0.02
Bedrock AI Analysis:     $0.10
API Gateway:             $0.01
CloudWatch/Monitoring:   $0.01
─────────────────────────────
COST PER AUDIT:          $0.20

Pricing Model:
- Small batch (1-10):    $0.25/audit
- Medium batch (11-100): $0.20/audit
- Large batch (100+):    $0.15/audit
```

### 3.4 Annual Cost Projections

```
Usage Level          Monthly    Annual      Optimized Annual
─────────────────────────────────────────────────────────────
Development          $49        $588        $588
Small Prod           $186       $2,232      $2,232
Medium Prod          $470       $5,640      $5,640
Large Prod           $1,080     $12,960     $12,960
Enterprise           $2,500     $30,000     $30,000
```

---

## 4. Implementation Roadmap

### Phase 1: Quick Wins (Week 1-2)
- [ ] Enable S3 lifecycle policies
- [ ] Set DynamoDB TTL
- [ ] Reduce CloudWatch log retention
- [ ] Enable API Gateway caching
- **Expected Savings: 20-30%**

### Phase 2: Medium Effort (Week 3-4)
- [ ] Optimize Lambda memory settings
- [ ] Implement Bedrock response caching
- [ ] Switch DynamoDB to provisioned capacity
- [ ] Compress S3 objects
- **Expected Savings: 40-50%**

### Phase 3: Long-term (Month 2-3)
- [ ] Implement Lambda provisioned concurrency
- [ ] Optimize Bedrock model selection
- [ ] Implement batch processing
- [ ] Advanced monitoring and alerting
- **Expected Savings: 60-70%**

---

## 5. Monitoring and Alerts

### Key Metrics to Monitor

```python
# CloudWatch metrics to track

1. Lambda Metrics
   - Duration (ms)
   - Memory Used (MB)
   - Errors
   - Throttles
   - Cold Starts

2. DynamoDB Metrics
   - Consumed Read/Write Capacity
   - Throttled Requests
   - Item Count
   - Table Size

3. S3 Metrics
   - Bucket Size (GB)
   - Number of Objects
   - Request Count

4. Bedrock Metrics
   - Input Tokens
   - Output Tokens
   - Latency
   - Errors

5. Cost Metrics
   - Daily Spend
   - Cost per Audit
   - Cost Trend
```

### Alert Thresholds

```
Lambda:
- Duration > 30 seconds: WARNING
- Error rate > 1%: ALERT
- Throttles > 0: ALERT

DynamoDB:
- Throttled requests > 0: ALERT
- Table size > 100 GB: WARNING

S3:
- Bucket size > 500 GB: WARNING
- Cost > $100/month: ALERT

Bedrock:
- Cost > $300/month: WARNING
- Latency > 5 seconds: ALERT
```

---

## 6. Cost Optimization Checklist

- [ ] Lambda memory optimized
- [ ] Lambda timeouts configured
- [ ] DynamoDB provisioned capacity enabled
- [ ] DynamoDB TTL configured
- [ ] S3 lifecycle policies enabled
- [ ] S3 versioning limited
- [ ] Bedrock response caching implemented
- [ ] API Gateway caching enabled
- [ ] CloudWatch log retention reduced
- [ ] Unused resources removed
- [ ] Reserved capacity purchased
- [ ] Cost alerts configured
- [ ] Monthly cost review scheduled

---

## 7. References

- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)
- [S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)

---

## 8. Support and Questions

For cost optimization questions:
1. Review AWS Cost Explorer
2. Check CloudWatch metrics
3. Run AWS Trusted Advisor
4. Contact AWS Support (Business/Enterprise plan)

---

**Document Version**: 1.0
**Last Updated**: March 26, 2026
**Region**: Asia Pacific (Mumbai) - ap-south-1
