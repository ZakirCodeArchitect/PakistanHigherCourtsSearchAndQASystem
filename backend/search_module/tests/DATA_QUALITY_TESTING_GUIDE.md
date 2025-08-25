# Data Quality Testing Guide

This guide explains how to use the comprehensive data quality verification test suite to ensure your scraped data and pipeline performance meet quality standards.

## 🎯 Overview

The data quality testing suite provides automated verification of:
- **Data Completeness**: Ensures all tables have data and proper coverage
- **Data Cleaning Effectiveness**: Verifies cleaning processes work correctly
- **Data Consistency**: Checks for orphaned records and duplicates
- **Pipeline Performance**: Validates PDF processing and unified views
- **Quality Scoring**: Provides detailed quality metrics

## 📁 Test Structure

```
tests/
├── test_data_quality_verification.py    # Main test suite
├── run_data_quality_check.py            # Simple runner script
├── reports/                             # Generated test reports
│   └── data_quality_report_YYYYMMDD_HHMMSS.json
└── DATA_QUALITY_TESTING_GUIDE.md        # This guide
```

## 🚀 Quick Start

### 1. Quick Verification (Recommended for daily use)

```bash
# Quick check of essential metrics
python tests/run_data_quality_check.py --quick
```

### 2. Comprehensive Verification (Recommended after major scraping)

```bash
# Full verification with detailed report
python tests/run_data_quality_check.py --save-report
```

### 3. Using Django Test Framework

```bash
# Run specific test class
python manage.py test tests.test_data_quality_verification.DataQualityVerificationTest

# Run quick check only
python manage.py test tests.test_data_quality_verification.QuickDataQualityCheck

# Run with verbose output
python manage.py test tests.test_data_quality_verification -v 2
```

## 📊 What the Tests Check

### Data Completeness Tests
- ✅ All tables have data
- ✅ Case coverage across related tables
- ✅ No empty critical fields

### Data Cleaning Effectiveness Tests
- ✅ Standardized "VS" separators in case titles
- ✅ Expanded legal abbreviations
- ✅ Consistent status values
- ✅ Quality scores above thresholds

### Data Consistency Tests
- ✅ No orphaned records
- ✅ No duplicate case numbers
- ✅ Consistent status and bench values

### Pipeline Performance Tests
- ✅ PDF documents downloaded successfully
- ✅ Text extraction completed
- ✅ Unified views created with complete data

### Quality Scoring Tests
- ✅ Average quality scores for case titles and order texts
- ✅ Percentage of high-quality records (>0.8 score)
- ✅ Range and distribution of quality scores

## 📈 Understanding Test Results

### Quality Metrics

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Case Title Quality Score | >0.8 | 0.6-0.8 | <0.6 |
| Order Text Quality Score | >0.7 | 0.5-0.7 | <0.5 |
| Separator Standardization | >90% | 70-90% | <70% |
| Document Download Rate | >80% | 60-80% | <60% |

### Common Issues and Solutions

#### Issue: Low Case Title Quality Score
**Symptoms**: Average score < 0.8
**Solutions**:
- Run data cleaning: `python manage.py clean_case_data`
- Check for special characters or formatting issues
- Review scraping logic for title extraction

#### Issue: Low Document Download Rate
**Symptoms**: <80% documents downloaded
**Solutions**:
- Check PDF URLs are accessible
- Verify network connectivity
- Review PDF download pipeline

#### Issue: Missing Unified Views
**Symptoms**: No unified_case_views records
**Solutions**:
- Run complete pipeline: `python run_pdf_processing_pipeline.py`
- Check for pipeline errors
- Verify all required data is present

## 🔄 When to Run Tests

### After Scraping New Data
```bash
# 1. Quick verification
python tests/run_data_quality_check.py --quick

# 2. If issues found, run comprehensive test
python tests/run_data_quality_check.py --save-report
```

### After Data Cleaning
```bash
# Verify cleaning effectiveness
python tests/run_data_quality_check.py --save-report
```

### After Pipeline Updates
```bash
# Test pipeline performance
python tests/run_data_quality_check.py --save-report
```

### Regular Monitoring
```bash
# Daily quick check
python tests/run_data_quality_check.py --quick
```

## 📄 Test Reports

### Report Structure
```json
{
  "timestamp": "2025-01-XX...",
  "total_cases": 60,
  "data_quality_scores": {
    "completeness": {...},
    "detailed_scores": {...}
  },
  "cleaning_effectiveness": {...},
  "pipeline_performance": {...},
  "issues_found": [...],
  "recommendations": [...]
}
```

### Using Reports
- **Track Progress**: Compare reports over time
- **Identify Trends**: Monitor quality improvements
- **Debug Issues**: Use detailed metrics for troubleshooting
- **Documentation**: Keep reports for project documentation

## 🛠️ Customizing Tests

### Adding New Quality Checks

1. **Add to DataQualityVerificationTest class**:
```python
def test_custom_quality_check(self):
    """Custom quality check"""
    # Your custom logic here
    pass
```

2. **Add to comprehensive verification**:
```python
def test_comprehensive_verification(self):
    # ... existing tests ...
    self.test_custom_quality_check()
```

### Modifying Thresholds

Edit the test methods to adjust quality thresholds:
```python
# Example: Change quality score threshold
if value < 0.9:  # Changed from 0.8
    self.test_results['issues_found'].append(f"Low {metric}: {value:.2f}")
```

## 🚨 Troubleshooting

### Common Errors

#### Import Errors
```bash
# Ensure Django is set up
export DJANGO_SETTINGS_MODULE=core.settings
python manage.py shell
```

#### Database Connection Issues
```bash
# Check database connection
python manage.py dbshell
```

#### Permission Issues
```bash
# Ensure write permissions for reports directory
chmod 755 tests/reports/
```

### Getting Help

1. **Check the test output** for specific error messages
2. **Review the generated report** for detailed metrics
3. **Run individual test methods** to isolate issues
4. **Check Django logs** for additional error information

## 📚 Best Practices

### 1. Regular Testing
- Run quick tests daily
- Run comprehensive tests weekly
- Run tests after any major changes

### 2. Monitor Trends
- Keep historical reports
- Track quality improvements
- Set up alerts for quality degradation

### 3. Continuous Improvement
- Use test results to improve scraping
- Update cleaning logic based on findings
- Refine pipeline based on performance metrics

### 4. Documentation
- Document any customizations
- Keep test reports for reference
- Update this guide as needed

## 🎉 Success Criteria

Your data quality is excellent when:
- ✅ All tests pass without issues
- ✅ Quality scores are above thresholds
- ✅ Pipeline performance is >80%
- ✅ No critical issues found
- ✅ Recommendations are actionable

---

**Remember**: Data quality is an ongoing process. Regular testing helps maintain high standards and catch issues early!
