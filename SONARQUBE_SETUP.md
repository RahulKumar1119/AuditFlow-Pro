# SonarQube Setup Guide for AuditFlow-Pro

## Overview

This guide explains how to set up SonarQube code quality analysis for the AuditFlow-Pro project using GitHub Actions and the SonarSource SonarQube Scan Action.

---

## Prerequisites

- GitHub repository with Actions enabled
- SonarQube instance (Cloud or Self-Hosted)
- SonarQube project created
- SonarQube token generated

---

## Step 1: Create SonarQube Project

### Option A: SonarQube Cloud

1. Go to [SonarQube Cloud](https://sonarcloud.io)
2. Sign in with GitHub account
3. Click "Create organization"
4. Select "GitHub" as the platform
5. Authorize SonarQube to access your GitHub account
6. Create new project:
   - Organization: Your organization
   - Project Key: `AuditFlow-Pro`
   - Project Name: `AuditFlow-Pro`
   - Visibility: Private (recommended for banking data)

### Option B: Self-Hosted SonarQube

1. Access your SonarQube instance
2. Log in as administrator
3. Go to Administration → Projects
4. Click "Create Project"
5. Fill in:
   - Project Key: `AuditFlow-Pro`
   - Project Name: `AuditFlow-Pro`
   - Visibility: Private

---

## Step 2: Generate SonarQube Token

### SonarQube Cloud

1. Go to [SonarQube Cloud](https://sonarcloud.io)
2. Click your profile icon (top right)
3. Select "Security"
4. Click "Generate Tokens"
5. Enter token name: `GitHub-Actions`
6. Select type: `Global Analysis Token`
7. Click "Generate"
8. Copy the token (you won't see it again)

### Self-Hosted SonarQube

1. Log in to your SonarQube instance
2. Click your profile icon (top right)
3. Select "My Account"
4. Go to "Security" tab
5. Click "Generate Tokens"
6. Enter token name: `GitHub-Actions`
7. Click "Generate"
8. Copy the token

---

## Step 3: Add GitHub Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add the following secrets:

### Required Secrets

**SONAR_TOKEN**
- Name: `SONAR_TOKEN`
- Value: Your SonarQube token from Step 2

**SONAR_HOST_URL** (only for self-hosted)
- Name: `SONAR_HOST_URL`
- Value: Your SonarQube instance URL (e.g., `https://sonarqube.example.com`)
- Skip this if using SonarQube Cloud

---

## Step 4: Configure GitHub Actions

The workflow file `.github/workflows/build.yml` is already configured with:

- **Triggers**: Push to main/develop, Pull requests
- **Matrix**: Node.js 18.x, Python 3.9
- **Steps**:
  1. Checkout code
  2. Setup Node.js and Python
  3. Install dependencies
  4. Build frontend and backend
  5. Run tests with coverage
  6. Run linting
  7. Execute SonarQube scan
  8. Check quality gate
  9. Upload coverage reports
  10. Archive artifacts

---

## Step 5: Configure SonarQube Properties

The `sonar-project.properties` file contains:

```properties
sonar.projectKey=AuditFlow-Pro
sonar.projectName=AuditFlow-Pro
sonar.projectVersion=1.0.0
sonar.sources=auditflow-pro
sonar.exclusions=**/node_modules/**,**/__pycache__/**,**/dist/**,**/build/**
sonar.javascript.lcov.reportPaths=auditflow-pro/frontend/coverage/lcov.info
sonar.python.coverage.reportPaths=auditflow-pro/backend/coverage.xml
sonar.qualitygate.wait=true
```

---

## Step 6: Set Up Quality Gate

### In SonarQube

1. Go to Quality Gates
2. Create new Quality Gate: `AuditFlow-Pro`
3. Add conditions:
   - Coverage: >= 80%
   - Duplicated Lines: < 3%
   - Code Smells: < 10
   - Bugs: 0
   - Vulnerabilities: 0
   - Security Hotspots: 0

4. Set as default for project

### In GitHub Actions

The workflow includes:
```yaml
- name: SonarQube Quality Gate
  uses: SonarSource/sonarqube-quality-gate-action@master
```

This will fail the build if quality gate is not met.

---

## Step 7: Configure Coverage Reports

### Frontend (React/TypeScript)

In `auditflow-pro/frontend/package.json`:

```json
{
  "scripts": {
    "test": "jest --coverage --watchAll=false"
  },
  "jest": {
    "collectCoverageFrom": [
      "src/**/*.{ts,tsx}",
      "!src/**/*.d.ts",
      "!src/index.tsx"
    ],
    "coverageReporters": ["lcov", "text", "html"]
  }
}
```

### Backend (Python)

In `auditflow-pro/backend/requirements.txt`:

```
pytest>=7.0.0
pytest-cov>=4.0.0
coverage>=6.0
```

Run tests with coverage:
```bash
pytest --cov=. --cov-report=xml --cov-report=html
```

---

## Step 8: First Run

1. Push code to GitHub
2. Go to Actions tab
3. Watch the workflow execute
4. Check SonarQube dashboard for results

---

## Workflow Execution

### Triggers

The workflow runs on:
- Push to `main` branch
- Push to `develop` branch
- Pull requests to `main` or `develop`

### Steps Breakdown

```
1. Checkout Code
   ↓
2. Setup Node.js & Python
   ↓
3. Install Dependencies
   ↓
4. Build Frontend
   ↓
5. Run Frontend Tests
   ↓
6. Run Backend Linting
   ↓
7. Run Backend Tests
   ↓
8. SonarQube Scan
   ↓
9. Quality Gate Check
   ↓
10. Upload Coverage
   ↓
11. Archive Artifacts
```

---

## Monitoring Results

### SonarQube Dashboard

1. Go to your SonarQube instance
2. Select project: `AuditFlow-Pro`
3. View:
   - Code Quality metrics
   - Coverage percentage
   - Issues and bugs
   - Code smells
   - Duplications
   - Security hotspots

### GitHub Actions

1. Go to repository Actions tab
2. Click on workflow run
3. View:
   - Build status
   - Test results
   - Coverage reports
   - Artifacts

### Pull Request Integration

When a PR is created:
1. Workflow automatically runs
2. SonarQube analysis is performed
3. Quality gate check is executed
4. Results posted as PR comment
5. Build status shown in PR checks

---

## Troubleshooting

### Issue: "SONAR_TOKEN not found"

**Solution**: Add `SONAR_TOKEN` to GitHub Secrets

```bash
# Verify secret exists
gh secret list
```

### Issue: "SonarQube project not found"

**Solution**: Verify project key matches

```properties
sonar.projectKey=AuditFlow-Pro
```

### Issue: "Coverage report not found"

**Solution**: Ensure tests generate coverage reports

```bash
# Frontend
npm test -- --coverage

# Backend
pytest --cov=. --cov-report=xml
```

### Issue: "Quality gate failed"

**Solution**: Check SonarQube quality gate conditions

1. Go to Quality Gates in SonarQube
2. Review conditions
3. Fix code issues
4. Re-run workflow

### Issue: "Timeout waiting for quality gate"

**Solution**: Increase timeout or disable wait

```yaml
- name: SonarQube Scan
  uses: SonarSource/sonarqube-scan-action@v6
  with:
    args: >
      -Dsonar.qualitygate.wait=false
```

---

## Best Practices

### 1. Code Coverage

- Maintain >= 80% coverage
- Focus on critical paths
- Test error scenarios
- Mock external services

### 2. Code Quality

- Fix bugs immediately
- Address security hotspots
- Reduce code smells
- Eliminate duplications

### 3. Pull Requests

- Require quality gate pass
- Review SonarQube comments
- Address issues before merge
- Monitor trends over time

### 4. Continuous Improvement

- Review metrics weekly
- Set improvement goals
- Track progress
- Celebrate improvements

---

## Advanced Configuration

### Custom Rules

In `sonar-project.properties`:

```properties
# Exclude specific rules
sonar.issue.ignore.multicriteria=e1,e2
sonar.issue.ignore.multicriteria.e1.ruleKey=python:S1481
sonar.issue.ignore.multicriteria.e2.ruleKey=javascript:S1234
```

### Performance Tuning

```properties
# Parallel analysis
sonar.analysis.mode=publish
sonar.host.url=https://sonarqube.example.com
sonar.sourceEncoding=UTF-8
```

### Security Scanning

```properties
# Enable security analysis
sonar.security.hotspots.exclusions=**/test/**
sonar.security.config.file=.sonarqube/security.json
```

---

## Integration with Other Tools

### Slack Notifications

Add to workflow:

```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "SonarQube Analysis Complete",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "Quality Gate: ${{ job.status }}"
            }
          }
        ]
      }
```

### Email Notifications

Configure in SonarQube:
1. Administration → Configuration → Email
2. Set SMTP settings
3. Enable notifications

### Jira Integration

1. Go to SonarQube Administration
2. Configure Jira integration
3. Link issues to Jira tickets

---

## Maintenance

### Regular Tasks

- **Weekly**: Review SonarQube dashboard
- **Monthly**: Update dependencies
- **Quarterly**: Review quality gate settings
- **Annually**: Audit security hotspots

### Updating Workflow

To update the workflow:

1. Edit `.github/workflows/build.yml`
2. Commit and push
3. Workflow automatically uses new version

---

## References

- [SonarQube Documentation](https://docs.sonarqube.org)
- [SonarSource GitHub Actions](https://github.com/SonarSource/sonarqube-scan-action)
- [Quality Gate Documentation](https://docs.sonarqube.org/latest/user-guide/quality-gates/)
- [Coverage Reports](https://docs.sonarqube.org/latest/analysis/coverage/)

---

## Support

For issues or questions:

1. Check SonarQube logs
2. Review GitHub Actions logs
3. Consult SonarQube documentation
4. Contact SonarQube support

---

**Document Version**: 1.0  
**Last Updated**: March 25, 2026  
**Status**: Production Ready
