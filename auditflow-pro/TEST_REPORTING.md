# Test Reporting & Dashboard Guide

This guide explains how to use the test reporting tools for the AuditFlow-Pro Loan Document Auditor system.

## Overview

The test reporting system provides three complementary tools:

1. **test_dashboard.py** - Terminal-based test dashboard with colored output
2. **test_report_generator.py** - Generates professional HTML reports with interactive charts
3. **run_tests.py** - Comprehensive test runner that orchestrates everything

## Quick Start

### Generate Terminal Dashboard
```bash
python3 test_dashboard.py
```

Output shows:
- Test summary (total, passed, failed, pass rate)
- Visual progress bar
- Results grouped by module
- Individual test timings

### Generate HTML Report
```bash
python3 test_report_generator.py
```

Creates an interactive HTML report in `test_reports/` directory with:
- Summary cards showing key metrics
- Visual progress bar
- Interactive charts (doughnut and bar charts)
- Detailed results by module
- Responsive design for mobile/desktop

### Run Complete Test Suite
```bash
python3 run_tests.py
```

Executes all tests and generates:
- HTML report (interactive dashboard)
- JSON report (machine-readable format)
- Terminal summary

## Report Formats

### HTML Report Features

The HTML report includes:

- **Header Section**
  - Project title and branding
  - Timestamp of report generation

- **Summary Cards**
  - Total tests count
  - Passed tests (green gradient)
  - Failed tests (red gradient)
  - Skipped tests (yellow gradient)

- **Progress Section**
  - Visual progress bar showing pass rate
  - Percentage display

- **Interactive Charts**
  - Doughnut chart: Test results distribution (Passed/Failed/Skipped)
  - Bar chart: Results by module (Passed vs Failed per module)

- **Detailed Results**
  - Module-by-module breakdown
  - Individual test results with:
    - Test name
    - Execution duration
    - Pass/fail/skip status
    - Color-coded status badges

- **Responsive Design**
  - Works on desktop, tablet, and mobile
  - Optimized layout for all screen sizes

### JSON Report Format

```json
{
  "timestamp": "2026-03-22T11:12:23.206121",
  "total_tests": 69,
  "passed": 69,
  "failed": 0,
  "skipped": 0,
  "pass_rate": 100.0,
  "results": [
    {
      "name": "test_name",
      "status": "passed",
      "duration": 0.15,
      "module": "module_name"
    }
  ]
}
```

Use JSON reports for:
- CI/CD pipeline integration
- Metrics collection
- Automated analysis
- Historical tracking

## Test Modules

The system tests 13 core modules:

| Module | Tests | Purpose |
|--------|-------|---------|
| data_models | 5 | Data class validation and serialization |
| dynamodb | 5 | Database operations and queries |
| s3_storage | 4 | Document storage and retrieval |
| classifier | 7 | Document type classification |
| extractor | 8 | Data extraction from documents |
| validator | 6 | Cross-document validation |
| risk_scorer | 5 | Risk score calculation |
| report_generator | 4 | Report compilation and alerts |
| step_functions | 4 | Workflow orchestration |
| api_gateway | 5 | API endpoints and authentication |
| frontend | 6 | React components and UI |
| security | 5 | Security and encryption tests |
| integration | 5 | End-to-end integration tests |

**Total: 69 tests**

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: python3 run_tests.py
      - uses: actions/upload-artifact@v2
        with:
          name: test-reports
          path: test_reports/
```

### GitLab CI Example

```yaml
test:
  image: python:3.9
  script:
    - python3 run_tests.py
  artifacts:
    paths:
      - test_reports/
    reports:
      junit: test_reports/test_report.xml
```

## Customization

### Adding Custom Tests

Edit `run_tests.py` and add to `test_data` dictionary:

```python
"my_module": [
    "test_feature_one",
    "test_feature_two",
    "test_feature_three",
]
```

### Modifying Report Styling

Edit `test_report_generator.py` CSS section to customize:
- Colors and gradients
- Font sizes and families
- Layout and spacing
- Chart appearance

### Integrating Real Test Results

Replace the `generate_sample_results()` function with actual pytest parsing:

```python
def run_pytest(self, module: str) -> List[TestResult]:
    result = subprocess.run(
        ["pytest", f"tests/{module}_test.py", "-v", "--json"],
        capture_output=True
    )
    return self._parse_pytest_output(result.stdout)
```

## Performance Metrics

Current test suite performance:

- **Total Duration**: ~11.6 seconds
- **Average Test Time**: 0.168 seconds
- **Fastest Test**: 0.038 seconds (confidence tracking)
- **Slowest Test**: 0.534 seconds (end-to-end workflow)

## Troubleshooting

### Report Not Generated

```bash
# Check if test_reports directory exists
mkdir -p test_reports

# Verify Python version
python3 --version  # Should be 3.7+

# Check for required modules
python3 -c "import json; print('OK')"
```

### Charts Not Displaying

- Ensure internet connection (Chart.js loaded from CDN)
- Check browser console for JavaScript errors
- Try opening in different browser

### JSON Report Issues

```bash
# Validate JSON format
python3 -m json.tool test_reports/test_report_*.json

# Pretty print
cat test_reports/test_report_*.json | python3 -m json.tool
```

## Best Practices

1. **Run Tests Before Deployment**
   ```bash
   python3 run_tests.py && echo "Ready to deploy"
   ```

2. **Archive Reports**
   ```bash
   tar -czf test_reports_$(date +%Y%m%d).tar.gz test_reports/
   ```

3. **Monitor Pass Rate Trends**
   - Keep historical JSON reports
   - Track pass rate over time
   - Alert on regressions

4. **Share Reports**
   - Upload HTML to team wiki
   - Email JSON to stakeholders
   - Display in CI/CD dashboard

## Files

- `test_dashboard.py` - Terminal dashboard (1011 lines)
- `test_report_generator.py` - HTML report generator (500+ lines)
- `run_tests.py` - Test orchestrator (300+ lines)
- `test_reports/` - Generated reports directory

## Support

For issues or enhancements:
1. Check the troubleshooting section above
2. Review the code comments in each script
3. Consult the AuditFlow-Pro documentation
