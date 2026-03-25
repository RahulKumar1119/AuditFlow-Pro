# GitHub Actions Workflows

This directory contains GitHub Actions workflows for AuditFlow-Pro CI/CD pipeline.

## Workflows

### build.yml

**Purpose**: Build, test, and analyze code quality

**Triggers**:
- Push to `main` branch
- Push to `develop` branch
- Pull requests to `main` or `develop`

**Jobs**:
1. **Build and Analyze**
   - Checkout code
   - Setup Node.js and Python
   - Install dependencies
   - Build frontend and backend
   - Run tests with coverage
   - Run linting
   - Execute SonarQube scan
   - Check quality gate
   - Upload coverage reports
   - Archive artifacts

**Duration**: ~10-15 minutes

**Status Badge**:
```markdown
[![Build Status](https://github.com/YOUR_ORG/auditflow-pro/actions/workflows/build.yml/badge.svg)](https://github.com/YOUR_ORG/auditflow-pro/actions/workflows/build.yml)
```

---

## Configuration

### Required Secrets

Add these to GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret | Description | Example |
|--------|-------------|---------|
| `SONAR_TOKEN` | SonarQube authentication token | `squ_1234567890abcdef` |
| `SONAR_HOST_URL` | SonarQube instance URL (self-hosted only) | `https://sonarqube.example.com` |

### Optional Secrets

| Secret | Description |
|--------|-------------|
| `SLACK_WEBHOOK` | Slack notification webhook |
| `CODECOV_TOKEN` | Codecov integration token |

---

## Workflow Steps

### 1. Checkout
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history for analysis
```

### 2. Setup Environment
```yaml
- uses: actions/setup-node@v4
  with:
    node-version: 18.x
    cache: 'npm'

- uses: actions/setup-python@v4
  with:
    python-version: 3.9
    cache: 'pip'
```

### 3. Build
```bash
# Frontend
npm ci
npm run build

# Backend
pip install -r requirements.txt
```

### 4. Test
```bash
# Frontend
npm test -- --coverage --watchAll=false

# Backend
pytest --cov=. --cov-report=xml
```

### 5. Analyze
```bash
# Linting
flake8 . --count
pylint **/*.py

# SonarQube
sonar-scanner \
  -Dsonar.projectKey=AuditFlow-Pro \
  -Dsonar.sources=auditflow-pro
```

### 6. Quality Gate
```yaml
- uses: SonarSource/sonarqube-quality-gate-action@master
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## Monitoring

### GitHub Actions Dashboard

1. Go to repository
2. Click "Actions" tab
3. View workflow runs
4. Click run to see details

### SonarQube Dashboard

1. Go to SonarQube instance
2. Select project: `AuditFlow-Pro`
3. View metrics and issues

### Pull Request Checks

- Workflow status shown in PR
- SonarQube results posted as comment
- Quality gate status displayed

---

## Troubleshooting

### Workflow Failed

1. Click on failed workflow run
2. Expand failed job
3. Check error messages
4. Review logs
5. Fix issues and push

### Coverage Not Reported

Ensure coverage reports are generated:

```bash
# Frontend
npm test -- --coverage

# Backend
pytest --cov=. --cov-report=xml
```

### SonarQube Not Running

Check secrets:
```bash
gh secret list
```

Verify `SONAR_TOKEN` is set.

### Quality Gate Failed

1. Go to SonarQube dashboard
2. Review quality gate conditions
3. Fix code issues
4. Re-run workflow

---

## Performance

### Optimization Tips

1. **Cache Dependencies**
   - npm cache enabled
   - pip cache enabled

2. **Parallel Jobs**
   - Frontend and backend can run in parallel
   - Consider splitting into separate jobs

3. **Conditional Steps**
   - Skip steps if not needed
   - Use `if` conditions

4. **Artifact Management**
   - Archive only necessary files
   - Set retention period

---

## Security

### Best Practices

1. **Secrets Management**
   - Never commit secrets
   - Use GitHub Secrets
   - Rotate tokens regularly

2. **Permissions**
   - Use least privilege
   - Limit token scope
   - Review access regularly

3. **Dependency Updates**
   - Keep actions updated
   - Review dependencies
   - Use pinned versions

---

## Customization

### Add New Steps

```yaml
- name: Custom Step
  run: |
    echo "Running custom step"
    # Your commands here
```

### Add New Jobs

```yaml
jobs:
  build:
    # Existing job
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      # Deployment steps
```

### Add Notifications

```yaml
- name: Notify Slack
  if: always()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [SonarQube Scan Action](https://github.com/SonarSource/sonarqube-scan-action)
- [Node.js Setup Action](https://github.com/actions/setup-node)
- [Python Setup Action](https://github.com/actions/setup-python)

---

## Support

For issues:

1. Check workflow logs
2. Review GitHub Actions documentation
3. Check SonarQube logs
4. Contact team lead

---

**Last Updated**: March 25, 2026  
**Status**: Production Ready
