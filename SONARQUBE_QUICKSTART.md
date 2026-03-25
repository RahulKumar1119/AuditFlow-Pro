# SonarQube GitHub Actions - Quick Start Guide

## 5-Minute Setup

### Step 1: Create SonarQube Project (2 min)

**Option A: SonarQube Cloud**
1. Go to https://sonarcloud.io
2. Sign in with GitHub
3. Create organization
4. Create project: `AuditFlow-Pro`

**Option B: Self-Hosted**
1. Log in to your SonarQube instance
2. Create project: `AuditFlow-Pro`

### Step 2: Generate Token (1 min)

1. Go to your profile → Security
2. Click "Generate Tokens"
3. Name: `GitHub-Actions`
4. Copy token

### Step 3: Add GitHub Secret (1 min)

1. Go to GitHub repo → Settings → Secrets
2. Click "New repository secret"
3. Name: `SONAR_TOKEN`
4. Value: Paste your token
5. Click "Add secret"

### Step 4: Test (1 min)

1. Push code to `main` or `develop`
2. Go to Actions tab
3. Watch workflow run
4. Check SonarQube dashboard

---

## Workflow Overview

```
Push Code
    ↓
GitHub Actions Triggered
    ↓
Build & Test
    ├─ Frontend: npm build + test
    └─ Backend: pytest + linting
    ↓
SonarQube Scan
    ├─ Code analysis
    ├─ Coverage check
    └─ Quality gate
    ↓
Results
    ├─ GitHub PR comment
    ├─ SonarQube dashboard
    └─ Build status
```

---

## Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/build.yml` | Workflow definition |
| `sonar-project.properties` | SonarQube config |
| `SONARQUBE_SETUP.md` | Detailed guide |
| `.github/workflows/README.md` | Workflow docs |

---

## Monitoring

### GitHub Actions
- Go to Actions tab
- Click workflow run
- View logs and artifacts

### SonarQube Dashboard
- Go to your project
- View metrics
- Check issues
- Monitor trends

### Pull Requests
- SonarQube posts comments
- Quality gate status shown
- Build checks displayed

---

## Troubleshooting

### Workflow Not Running
- Check `.github/workflows/build.yml` exists
- Verify branch is `main` or `develop`
- Check Actions are enabled

### SonarQube Not Scanning
- Verify `SONAR_TOKEN` secret exists
- Check token is valid
- Review workflow logs

### Quality Gate Failed
- Go to SonarQube dashboard
- Review quality gate conditions
- Fix code issues
- Re-run workflow

---

## Next Steps

1. **Read Full Guide**: `SONARQUBE_SETUP.md`
2. **Customize Quality Gate**: Set coverage thresholds
3. **Add Notifications**: Slack, email, etc.
4. **Monitor Metrics**: Weekly reviews
5. **Improve Code**: Address issues

---

## Support

- **Setup Issues**: See `SONARQUBE_SETUP.md`
- **Workflow Issues**: See `.github/workflows/README.md`
- **SonarQube Help**: https://docs.sonarqube.org
- **GitHub Actions Help**: https://docs.github.com/en/actions

---

**Status**: ✓ Ready to Use  
**Created**: March 25, 2026
