# AuditFlow-Pro: AI-Powered Loan Document Auditor

AuditFlow-Pro is a serverless, AI-powered loan document auditor built on AWS that automates the extraction, validation, and cross-referencing of data across multiple loan documents. The system processes W2s, bank statements, tax forms, driver's licenses, and identification documents to identify inconsistencies before human review, generating risk reports with confidence scores to accelerate loan approval workflows.

## Features

- **Automated Document Classification**: AI-powered identification of document types
- **Intelligent Data Extraction**: AWS Textract for OCR and structured data extraction
- **Cross-Document Validation**: AI reasoning to detect inconsistencies across documents
- **Risk Scoring**: Automated calculation of risk scores based on detected issues
- **PII Protection**: Automatic detection and masking of sensitive information
- **Real-Time Processing**: Event-driven architecture for immediate document processing
- **Secure Authentication**: AWS Cognito with role-based access control
- **Banking-Grade Security**: Encryption at rest and in transit, comprehensive audit logging

## Architecture

### Technology Stack

- **Frontend**: React (TypeScript), AWS Amplify
- **Backend**: AWS Lambda (Python), Step Functions
- **AI Services**: AWS Textract, Bedrock, Comprehend
- **Storage**: S3 (documents), DynamoDB (audit records)
- **Security**: Cognito, KMS, IAM
- **Monitoring**: CloudWatch

### System Components

```
Frontend (React) → API Gateway → Lambda Functions → Step Functions
                                        ↓
                            AI Services (Textract, Bedrock, Comprehend)
                                        ↓
                            Storage (S3, DynamoDB)
```

## Project Structure

```
auditflow-pro/
├── backend/                    # Python Lambda functions
│   ├── functions/             # Individual Lambda function handlers
│   │   ├── classifier/        # Document classification
│   │   ├── extractor/         # Data extraction
│   │   ├── validator/         # Cross-document validation
│   │   ├── risk_scorer/       # Risk score calculation
│   │   ├── reporter/          # Report generation
│   │   ├── trigger/           # S3 event handler
│   │   └── api_handler/       # API Gateway handler
│   ├── shared/                # Shared modules
│   │   ├── models.py          # Data models
│   │   ├── repositories.py    # DynamoDB access layer
│   │   └── storage.py         # S3 access layer
│   ├── step_functions/        # Step Functions definitions
│   ├── tests/                 # Unit and integration tests
│   ├── requirements.txt       # Python dependencies
│   └── setup.sh              # Backend setup script
│
├── frontend/                  # React TypeScript application
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── contexts/         # React contexts
│   │   └── services/         # API services
│   ├── package.json          # Node.js dependencies
│   ├── .env.template         # Environment variables template
│   └── setup.sh             # Frontend setup script
│
├── infrastructure/           # AWS deployment scripts
│   ├── deploy_all.sh        # Master deployment script
│   ├── deploy.sh            # Base infrastructure
│   ├── s3_config.sh         # S3 configuration
│   ├── dynamodb_config.sh   # DynamoDB configuration
│   ├── iam_policies.sh      # IAM roles and policies
│   ├── cognito_setup.sh     # Authentication setup
│   ├── teardown.sh          # Infrastructure cleanup
│   └── README.md            # Infrastructure documentation
│
├── .env                      # Application configuration
└── README.md                # This file
```

## Getting Started

### Prerequisites

- **AWS Account** with appropriate permissions
- **AWS CLI** installed and configured
- **Python 3.8+** for backend development
- **Node.js 18+** for frontend development
- **Bash** shell environment

### Installation

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd auditflow-pro
```

#### 2. Configure Environment

Update `.env` with your AWS configuration:

```bash
cp .env .env.local
# Edit .env.local with your AWS account details
```

#### 3. Set Up Backend

```bash
cd backend
bash setup.sh
source venv/bin/activate
```

This will:
- Create a Python virtual environment
- Install all dependencies (boto3, pytest, moto)
- Prepare Lambda deployment packages

#### 4. Set Up Frontend

```bash
cd frontend
bash setup.sh
```

This will:
- Install Node.js dependencies
- Create .env file from template

#### 5. Deploy Infrastructure

```bash
cd infrastructure
bash deploy_all.sh
```

This will create:
- S3 bucket for document storage
- DynamoDB tables for audit records
- IAM roles and policies
- Cognito User Pool and Identity Pool

After deployment, update `frontend/.env` with the Cognito configuration values provided in the output.

### Running Locally

#### Backend Tests

```bash
cd backend
source venv/bin/activate
pytest tests/
```

#### Frontend Development Server

```bash
cd frontend
npm run dev
```

The application will be available at `http://localhost:5173`

## Deployment

### Backend Lambda Functions

Package and deploy Lambda functions:

```bash
cd backend
# Create deployment package
zip -r deployment_package.zip functions/ shared/ package/

# Deploy using AWS CLI
aws lambda create-function \
  --function-name AuditFlow-Classifier \
  --runtime python3.8 \
  --handler functions/classifier/handler.lambda_handler \
  --zip-file fileb://deployment_package.zip \
  --role arn:aws:iam::ACCOUNT_ID:role/AuditFlowLambdaExecutionRole
```

### Frontend to AWS Amplify

1. Connect your Git repository to AWS Amplify
2. Configure build settings:
   - Build command: `npm run build`
   - Output directory: `dist`
3. Set environment variables in Amplify console
4. Deploy

## Configuration

### Environment Variables

#### Backend (.env)
- `AWS_REGION`: AWS region for deployment
- `S3_DOCUMENT_BUCKET`: S3 bucket name for documents
- `CONFIDENCE_THRESHOLD`: Minimum confidence for data extraction (0.80)
- `PROCESSING_TIMEOUT_SECONDS`: Max processing time (300)
- `CRITICAL_RISK_THRESHOLD`: Risk score threshold for alerts (80)

#### Frontend (.env)
- `VITE_USER_POOL_ID`: Cognito User Pool ID
- `VITE_USER_POOL_CLIENT_ID`: Cognito Client ID
- `VITE_IDENTITY_POOL_ID`: Cognito Identity Pool ID
- `VITE_API_GATEWAY_URL`: API Gateway endpoint URL

### User Roles

- **Loan Officer**: Can upload documents and view audit results
- **Administrator**: Full system access including user management

## Testing

### Unit Tests

```bash
cd backend
pytest tests/test_*.py
```

### Integration Tests

```bash
cd backend
pytest tests/integration/
```

### Property-Based Tests

Property-based tests validate correctness properties:
- Round-trip serialization
- Golden Record determinism
- Risk score monotonicity
- Encryption integrity

## Security

- **Encryption at Rest**: All S3 and DynamoDB data encrypted with KMS
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Authentication**: AWS Cognito with MFA support
- **Authorization**: Role-based access control (RBAC)
- **PII Protection**: Automatic detection and masking
- **Audit Logging**: Comprehensive CloudWatch logging

## Monitoring

### CloudWatch Logs

- Lambda functions: `/aws/lambda/AuditFlow-{FunctionName}`
- Step Functions: `/aws/states/AuditFlowWorkflow`
- API Gateway: Configured via API Gateway role

### Metrics

- Document processing time
- Risk score distribution
- Error rates
- API usage

### Alerts

- Lambda failures after retries
- High risk scores (>80)
- System error rate >5%
- DynamoDB throttling

## Cost Optimization

- **DynamoDB**: Pay-per-request billing
- **S3**: Lifecycle policy (Glacier after 90 days)
- **Lambda**: Automatic scaling
- **CloudWatch**: 1-year log retention

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **AWS permission errors**
   - Verify IAM roles have correct policies
   - Check AWS CLI credentials

3. **Frontend build errors**
   - Ensure Node.js 18+ is installed
   - Delete `node_modules` and run `npm install`

4. **Cognito authentication errors**
   - Verify .env has correct Cognito values
   - Check User Pool configuration

## Documentation

- [Requirements Document](../loan-document-auditor/requirements.md)
- [Technical Design](../loan-document-auditor/design.md)
- [Implementation Tasks](../loan-document-auditor/tasks.md)
- [Infrastructure Guide](infrastructure/README.md)

## License

Copyright © 2024 AuditFlow-Pro. All rights reserved.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review CloudWatch logs
3. Consult AWS documentation
4. Contact system administrator
