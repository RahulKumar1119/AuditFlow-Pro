# AuditFlow-Pro Quick Start Guide

This guide will help you get AuditFlow-Pro up and running quickly.

## Prerequisites Checklist

- [ ] AWS Account with admin access
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Python 3.8+ installed
- [ ] Node.js 18+ installed (for frontend development)
- [ ] Bash shell environment

## Step-by-Step Setup

### 1. Validate Setup

First, verify that your environment is correctly configured:

```bash
cd auditflow-pro
bash validate_setup.sh
```

This will check for all required tools and project structure.

### 2. Configure Environment

Update the `.env` file with your AWS account details:

```bash
# Edit .env file
nano .env

# Update these values:
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-12-digit-account-id>
```

### 3. Set Up Backend

```bash
cd backend
bash setup.sh
```

This will:
- Create Python virtual environment
- Install all dependencies (boto3, pytest, moto)
- Prepare Lambda deployment packages

**Verify backend setup:**
```bash
source venv/bin/activate
python -c "import boto3; print('boto3 version:', boto3.__version__)"
pytest --version
```

### 4. Set Up Frontend (Optional)

If you have Node.js installed:

```bash
cd frontend
bash setup.sh
```

This will:
- Install Node.js dependencies
- Create .env file from template

**Verify frontend setup:**
```bash
npm --version
node --version
```

### 5. Deploy AWS Infrastructure

**Important:** Make sure AWS CLI is configured with credentials that have admin access.

```bash
cd infrastructure
bash deploy_all.sh
```

This will create:
- ✓ S3 bucket for document storage
- ✓ DynamoDB tables (Documents, AuditRecords)
- ✓ IAM roles and policies
- ✓ Cognito User Pool and Identity Pool

**Deployment time:** Approximately 5-10 minutes

### 6. Configure Frontend with Cognito

After infrastructure deployment, you'll see output like:

```
User Pool ID: us-east-1_XXXXXXXXX
User Pool Client ID: XXXXXXXXXXXXXXXXXXXXXXXXXX
Identity Pool ID: us-east-1:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
```

Copy these values to `frontend/.env`:

```bash
cd frontend
nano .env

# Update with your values:
VITE_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
VITE_IDENTITY_POOL_ID=us-east-1:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
VITE_AWS_REGION=us-east-1
```

### 7. Run Tests

Verify everything is working:

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

Expected output: All tests should pass ✓

### 8. Start Development

#### Backend Development

```bash
cd backend
source venv/bin/activate
# Make changes to Lambda functions in functions/
# Run tests after changes
pytest tests/
```

#### Frontend Development

```bash
cd frontend
npm run dev
```

Access the application at: `http://localhost:5173`

## Common Issues and Solutions

### Issue: "AWS CLI not configured"

**Solution:**
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Enter default region (e.g., us-east-1)
# Enter default output format (json)
```

### Issue: "Permission denied" when running scripts

**Solution:**
```bash
chmod +x backend/setup.sh
chmod +x frontend/setup.sh
chmod +x infrastructure/*.sh
```

### Issue: "Python module not found"

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Node.js not found"

**Solution:**
- Install Node.js from https://nodejs.org/
- Recommended version: 18 LTS or higher

### Issue: "DynamoDB table already exists"

**Solution:**
This is normal if re-running deployment. The script will skip existing resources.

### Issue: "IAM role already exists"

**Solution:**
This is expected behavior. The script continues with existing roles.

## Next Steps

After completing the quick start:

1. **Create Test Users**
   ```bash
   # Create a Loan Officer user
   aws cognito-idp admin-create-user \
     --user-pool-id <your-user-pool-id> \
     --username testuser@example.com \
     --user-attributes Name=email,Value=testuser@example.com \
     --temporary-password TempPass123!
   
   # Add user to LoanOfficers group
   aws cognito-idp admin-add-user-to-group \
     --user-pool-id <your-user-pool-id> \
     --username testuser@example.com \
     --group-name LoanOfficers
   ```

2. **Deploy Lambda Functions**
   - Package Lambda functions
   - Deploy to AWS Lambda
   - Configure triggers

3. **Set Up Step Functions**
   - Deploy state machine definition
   - Configure IAM roles

4. **Create API Gateway**
   - Set up REST API
   - Configure Cognito authorizer
   - Deploy to stage

5. **Deploy Frontend to Amplify**
   - Connect Git repository
   - Configure build settings
   - Deploy

## Useful Commands

### Backend

```bash
# Activate virtual environment
source backend/venv/bin/activate

# Run all tests
pytest backend/tests/

# Run specific test file
pytest backend/tests/test_models.py

# Run with coverage
pytest backend/tests/ --cov=backend

# Deactivate virtual environment
deactivate
```

### Frontend

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint

# Preview production build
npm run preview
```

### Infrastructure

```bash
# Deploy all infrastructure
bash infrastructure/deploy_all.sh

# Deploy specific component
bash infrastructure/iam_policies.sh

# Tear down all infrastructure (CAUTION!)
bash infrastructure/teardown.sh
```

## Getting Help

- **Documentation**: See README.md for detailed information
- **Requirements**: See ../loan-document-auditor/requirements.md
- **Design**: See ../loan-document-auditor/design.md
- **Tasks**: See ../loan-document-auditor/tasks.md
- **Infrastructure**: See infrastructure/README.md

## Verification Checklist

Before proceeding to development, verify:

- [ ] `bash validate_setup.sh` passes with 0 errors
- [ ] Backend virtual environment created and activated
- [ ] Backend tests pass: `pytest backend/tests/`
- [ ] AWS infrastructure deployed successfully
- [ ] Cognito User Pool created
- [ ] DynamoDB tables created
- [ ] S3 bucket created
- [ ] IAM roles created
- [ ] Frontend .env configured with Cognito values
- [ ] Frontend dev server starts: `npm run dev`

If all items are checked, you're ready to start development! 🚀
