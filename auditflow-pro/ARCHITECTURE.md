# AuditFlow-Pro System Architecture

## Overview

AuditFlow-Pro is an AI-powered automated loan document auditor built on AWS serverless architecture. The system processes loan documents (W2s, bank statements, tax forms, driver's licenses) to extract data, cross-validate information, detect inconsistencies, and generate risk reports for loan officers.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Frontend (React + Amplify)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐│
│  │   Login      │  │   Upload     │  │  Dashboard   │  │Audit Records││
│  │   (Cognito)  │  │   Zone       │  │              │  │             ││
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS/TLS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API Gateway + Lambda                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    API Handler Lambda                             │  │
│  │  • Generate presigned POST URLs for S3 uploads                   │  │
│  │  • Fetch audit records from DynamoDB                             │  │
│  │  • Handle authentication via Cognito                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      S3 Document Storage (Encrypted)                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  auditflow-documents-prod-{account-id}                           │  │
│  │  • Server-side encryption (SSE-S3)                               │  │
│  │  • Versioning enabled                                            │  │
│  │  • Event notifications to trigger processing                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ S3 Event Trigger
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Document Processing Pipeline                        │
│                                                                          │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐         │
│  │   Trigger    │─────▶│  Classifier  │─────▶│  Extractor   │         │
│  │   Lambda     │      │   Lambda     │      │   Lambda     │         │
│  └──────────────┘      └──────────────┘      └──────────────┘         │
│         │                      │                      │                 │
│         │                      │                      │                 │
│         ▼                      ▼                      ▼                 │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │              AWS Step Functions Workflow                  │         │
│  │  • Orchestrates multi-step processing                    │         │
│  │  • Error handling and retries                            │         │
│  │  • State management                                      │         │
│  └──────────────────────────────────────────────────────────┘         │
│                                                                          │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐         │
│  │  Validator   │─────▶│ Risk Scorer  │─────▶│   Reporter   │         │
│  │   Lambda     │      │   Lambda     │      │   Lambda     │         │
│  └──────────────┘      └──────────────┘      └──────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI Services Integration                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │   Textract   │  │  Comprehend  │  │  Bedrock (Claude Sonnet 4)   │ │
│  │  • OCR       │  │  • PII       │  │  • Semantic reasoning        │ │
│  │  • Forms     │  │    Detection │  │  • Address matching          │ │
│  │  • Tables    │  │              │  │  • Format variations         │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Data Storage (DynamoDB)                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  AuditFlow-AuditRecords                                          │  │
│  │  • Partition Key: loan_application_id                           │  │
│  │  • Sort Key: timestamp                                          │  │
│  │  • Encryption at rest (AWS managed keys)                        │  │
│  │  • Stores: extracted data, risk scores, inconsistencies        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Security & Monitoring Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Cognito    │  │     IAM      │  │  CloudWatch  │  │    KMS     │ │
│  │  • User Auth │  │  • Policies  │  │  • Logs      │  │  • Keys    │ │
│  │  • MFA       │  │  • Roles     │  │  • Metrics   │  │  • Encrypt │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### 1. Document Upload Flow

```
User → Frontend Upload Zone → API Handler Lambda → Generate Presigned POST URL
                                                   ↓
User Browser → Direct S3 Upload (with presigned URL) → S3 Bucket
                                                        ↓
                                                   S3 Event Notification
                                                        ↓
                                                   Trigger Lambda
```

**Key Points:**
- Frontend requests presigned POST URL from API Handler
- User uploads directly to S3 (bypassing API Gateway size limits)
- Presigned URL includes security policies and checksum validation
- S3 event triggers processing pipeline automatically

### 2. Document Processing Flow

```
S3 Event → Trigger Lambda → Step Functions Workflow
                                    ↓
                            Classifier Lambda
                                    ↓
                            Extractor Lambda (+ Textract + Comprehend)
                                    ↓
                            Validator Lambda (+ Bedrock)
                                    ↓
                            Risk Scorer Lambda
                                    ↓
                            Reporter Lambda → DynamoDB
```

**Processing Stages:**

1. **Trigger Lambda**: Receives S3 event, initiates Step Functions workflow
2. **Classifier Lambda**: Identifies document type (W2, Bank Statement, Tax Form, etc.)
3. **Extractor Lambda**: 
   - Uses AWS Textract for OCR and data extraction
   - Uses AWS Comprehend for PII detection
   - Extracts key-value pairs, tables, and forms
4. **Validator Lambda**:
   - Cross-validates data across documents
   - Uses AWS Bedrock (Claude Sonnet 4) for semantic reasoning
   - Detects inconsistencies in names, addresses, income, SSN, DOB
5. **Risk Scorer Lambda**: Calculates risk score based on inconsistencies
6. **Reporter Lambda**: Generates final audit report and stores in DynamoDB

### 3. Data Retrieval Flow

```
User → Frontend Dashboard → API Handler Lambda → DynamoDB Query
                                                        ↓
                                                  Audit Records
                                                        ↓
                                            Frontend Display (masked PII)
```

**Key Points:**
- API Handler authenticates user via Cognito
- Queries DynamoDB for audit records
- Masks PII in response (first 5 digits of SSN)
- Returns risk scores, inconsistencies, and document metadata

## Data Flow and Processing Stages

### Stage 1: Document Classification

**Input:** Raw document file (PDF, JPEG, PNG)
**Process:**
- Analyze document structure using Textract
- Identify document type based on:
  - Form structure (IRS forms, bank headers)
  - Key identifiers (employer EIN, account numbers)
  - Layout patterns

**Output:** Document type classification (W2, Bank Statement, Tax Form, Driver's License, ID)

### Stage 2: Data Extraction

**Input:** Classified document
**Process:**
- Extract text using Textract OCR
- Extract key-value pairs (e.g., "Name: John Doe")
- Extract tables (e.g., transaction history)
- Extract forms (e.g., W2 boxes)
- Detect PII using Comprehend (SSN, account numbers, DOB, license numbers)

**Output:** Structured extracted data with confidence scores

### Stage 3: Cross-Document Validation

**Input:** Extracted data from multiple documents
**Process:**
- Compare names across all documents (Levenshtein distance > 2 = inconsistency)
- Compare addresses using semantic matching (Bedrock AI)
  - Handle abbreviations: "Street" vs "St", "Avenue" vs "Ave"
  - Component-level validation: street, city, state, ZIP
- Compare income figures (W2 vs Tax Forms, >5% discrepancy = flag)
- Compare SSN across documents (zero tolerance for mismatches)
- Compare DOB across identification documents (zero tolerance)

**Output:** List of inconsistencies with severity levels

### Stage 4: Risk Scoring

**Input:** Inconsistencies from validation
**Process:**
- Calculate risk score (0-100) based on:
  - Name inconsistencies: +15 points each
  - Address mismatches: +20 points each
  - Income discrepancies >10%: +25 points each
  - ID number mismatches: +30 points each
  - Low confidence extractions: +10 points each
  - Illegible documents: +5 points each
- Flag as high-risk if score > 50

**Output:** Risk score and contributing factors

### Stage 5: Report Generation

**Input:** All extracted data, inconsistencies, risk score
**Process:**
- Generate Golden Record (most reliable value for each field)
- Categorize inconsistencies by severity (Critical, High, Medium, Low)
- Create audit report with:
  - Loan application ID
  - Document list
  - Extracted data
  - Inconsistencies with source documents
  - Risk score and breakdown
  - Timestamp

**Output:** Complete audit record stored in DynamoDB

## Security and Encryption Mechanisms

### 1. Data Encryption

**At Rest:**
- **S3 Documents**: Server-side encryption (SSE-S3)
- **DynamoDB**: Encryption at rest using AWS managed keys
- **CloudWatch Logs**: Encrypted by default

**In Transit:**
- **Frontend ↔ API**: HTTPS/TLS 1.2+
- **API ↔ AWS Services**: AWS SDK with TLS
- **S3 Uploads**: HTTPS with presigned URLs

### 2. Authentication and Authorization

**User Authentication:**
- AWS Cognito User Pools
- Email/password authentication
- Session management (30-minute timeout)
- Account lockout after 3 failed attempts (15-minute lockout)
- Password requirements:
  - Minimum 8 characters
  - Uppercase, lowercase, number, special character

**Authorization:**
- Role-based access control (Loan Officer, Administrator)
- Cognito groups for role management
- IAM policies for service-to-service communication

### 3. PII Protection

**Detection:**
- AWS Comprehend DetectPiiEntities API
- Identifies: SSN, bank account numbers, driver's license numbers, DOB

**Handling:**
- PII redacted from CloudWatch logs
- PII masked in frontend display (first 5 digits of SSN)
- PII values NOT logged in application code
- Field-level encryption planned for future (Task 23.3)

### 4. IAM Policies

**Lambda Execution Roles:**
- Minimum required permissions (principle of least privilege)
- Read access to S3 for document retrieval
- Write access to DynamoDB for audit records
- Invoke permissions for AI services (Textract, Comprehend, Bedrock)

**API Handler Role:**
- Generate presigned POST URLs for S3
- Query DynamoDB for audit records
- No direct S3 write access (users upload directly)

### 5. Network Security

**VPC Configuration:**
- Lambda functions can be deployed in VPC (optional)
- Private subnets for enhanced security
- VPC endpoints for AWS services

**S3 Bucket Policies:**
- Block public access
- Require encryption in transit
- Restrict access to authorized IAM roles

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Hosting**: AWS Amplify
- **UI Library**: Tailwind CSS, Lucide React icons
- **State Management**: React Context API
- **Authentication**: AWS Amplify Auth (Cognito)
- **HTTP Client**: Fetch API with AWS Amplify

### Backend
- **Compute**: AWS Lambda (Python 3.10)
- **Orchestration**: AWS Step Functions
- **API**: AWS API Gateway (REST API)
- **Storage**: 
  - Amazon S3 (documents)
  - Amazon DynamoDB (audit records)

### AI Services
- **OCR**: AWS Textract
- **PII Detection**: AWS Comprehend
- **Semantic Reasoning**: AWS Bedrock (Claude Sonnet 4)

### Security & Monitoring
- **Authentication**: AWS Cognito
- **Authorization**: AWS IAM
- **Encryption**: AWS KMS
- **Logging**: AWS CloudWatch
- **Monitoring**: AWS CloudWatch Metrics

### Development & Deployment
- **Version Control**: Git
- **CI/CD**: AWS Amplify (frontend), AWS CLI scripts (backend)
- **Testing**: Pytest, Hypothesis (property-based testing)
- **Infrastructure**: AWS CLI scripts, manual provisioning

## Scalability and Performance

### Auto-Scaling
- **Lambda**: Automatic scaling up to 1000 concurrent executions
- **DynamoDB**: On-demand capacity mode (auto-scales)
- **S3**: Unlimited storage, automatic scaling

### Performance Targets
- Single-page document: < 30 seconds (upload to audit completion)
- 10-page PDF: < 2 minutes
- API response time: < 500ms
- Dashboard load time: < 3 seconds

### Concurrency Limits
- Parallel document processing: Up to 10 concurrent executions
- Step Functions: 1 million concurrent executions (AWS limit)
- API Gateway: 10,000 requests per second (default limit)

## Error Handling and Resilience

### Retry Policies
- **Step Functions**: Exponential backoff (5s, 15s, 45s)
- **Lambda**: Up to 3 retries per stage
- **API Calls**: Automatic retries with AWS SDK

### Error States
- **Processing Failures**: Document moved to failed state, admin notified
- **Partial Failures**: Continue processing remaining documents
- **Timeout Handling**: 5-minute timeout per Lambda, split large documents

### Monitoring and Alerts
- CloudWatch alarms for:
  - Lambda error rates > 5%
  - DynamoDB throttling
  - High-risk applications (score > 80)
  - Processing failures

## Deployment Architecture

### Regions
- **Primary Region**: ap-south-1 (Mumbai)
- **Multi-region**: Not currently implemented

### Environments
- **Production**: auditflow-documents-prod-{account-id}
- **Development**: Local testing with mocked AWS services

### Resource Naming Convention
```
{service}-{environment}-{account-id}
Example: auditflow-documents-prod-438097524343
```

## Future Enhancements

1. **Field-Level Encryption** (Task 23.3)
   - Encrypt PII fields in DynamoDB using KMS
   - Implement encryption/decryption utilities
   - Add PII access audit trail

2. **Multi-Region Deployment**
   - Deploy to multiple AWS regions for disaster recovery
   - Cross-region replication for S3 and DynamoDB

3. **Advanced Analytics**
   - Trend analysis for risk scores
   - Fraud pattern detection
   - Machine learning model training

4. **Enhanced UI**
   - Real-time processing status updates
   - Document comparison view
   - Batch upload support

## References

- [AWS Textract Documentation](https://docs.aws.amazon.com/textract/)
- [AWS Comprehend Documentation](https://docs.aws.amazon.com/comprehend/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [React Documentation](https://react.dev/)
- [AWS Amplify Documentation](https://docs.amplify.aws/)

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-03  
**Maintained By**: AuditFlow-Pro Development Team
