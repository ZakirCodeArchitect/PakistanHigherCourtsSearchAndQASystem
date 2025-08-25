# Test Suite Documentation

This directory contains comprehensive tests for the Pakistan Higher Courts Search and QA System.

## 📁 Test Structure

```
tests/
├── test_data_quality_verification.py    # Comprehensive data quality tests (Django TestCase)
├── simple_data_quality_check.py         # Simple standalone data quality check
├── run_data_quality_check.py            # Runner for Django test framework
├── test_data_quality.py                 # Legacy data quality tests
├── test_pdf_pipeline.py                 # PDF processing pipeline tests
├── test_data_cleaning_pipeline.py       # Data cleaning pipeline tests
├── run_all_tests.py                     # Run all tests
├── reports/                             # Generated test reports
│   └── data_quality_report_YYYYMMDD_HHMMSS.json
├── DATA_QUALITY_TESTING_GUIDE.md        # Detailed testing guide
└── README.md                            # This file
```

## 🚀 Quick Start

### For Daily Use (Recommended)
```bash
# Quick data quality check
python tests/simple_data_quality_check.py --quick
```

### For Comprehensive Verification
```bash
# Full verification with report
python tests/simple_data_quality_check.py --save-report
```

### Using Django Test Framework
```bash
# Run all tests
python manage.py test tests

# Run specific test
python manage.py test tests.test_data_quality_verification

# Run with verbose output
python manage.py test tests -v 2
```

## 📊 What Gets Tested

### Data Quality Verification
- ✅ **Data Completeness**: All tables have data and proper coverage
- ✅ **Data Cleaning Effectiveness**: Standardized separators, expanded abbreviations
- ✅ **Data Consistency**: No orphaned records or duplicates
- ✅ **Pipeline Performance**: PDF processing and unified views
- ✅ **Quality Scoring**: Detailed quality metrics for all data types

### PDF Processing Pipeline
- ✅ **Document Download**: PDF files are downloaded successfully
- ✅ **Text Extraction**: Text is extracted from PDFs with OCR fallback
- ✅ **Text Cleaning**: Extracted text is cleaned and normalized
- ✅ **Unified Views**: Complete case views are created

### Data Cleaning Pipeline
- ✅ **Case Titles**: Standardized "VS" separators
- ✅ **Legal Terms**: Expanded abbreviations (D&SJ → District & Sessions Judge)
- ✅ **Status Values**: Consistent capitalization
- ✅ **Party Names**: Cleaned and normalized

## 📈 Quality Metrics

| Metric | Excellent | Good | Warning | Critical |
|--------|-----------|------|---------|----------|
| Case Title Quality | >0.9 | 0.8-0.9 | 0.6-0.8 | <0.6 |
| Order Text Quality | >0.8 | 0.7-0.8 | 0.5-0.7 | <0.5 |
| Separator Standardization | >95% | 90-95% | 70-90% | <70% |
| Document Download Rate | >90% | 80-90% | 60-80% | <60% |
| Unified Views Completion | >95% | 80-95% | 60-80% | <60% |

## 🔄 When to Run Tests

### After Scraping New Data
```bash
# 1. Quick verification
python tests/simple_data_quality_check.py --quick

# 2. If issues found, run comprehensive test
python tests/simple_data_quality_check.py --save-report
```

### After Data Cleaning
```bash
# Verify cleaning effectiveness
python tests/simple_data_quality_check.py --save-report
```

### After Pipeline Updates
```bash
# Test pipeline performance
python tests/simple_data_quality_check.py --save-report
```

### Regular Monitoring
```bash
# Daily quick check
python tests/simple_data_quality_check.py --quick
```

## 📄 Test Reports

Reports are automatically generated and saved to `tests/reports/` with timestamps:

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

## 🛠️ Customization

### Adding New Tests
1. Add test methods to `DataQualityVerificationTest` class
2. Update `test_comprehensive_verification()` to include new tests
3. Add corresponding checks to `simple_data_quality_check.py`

### Modifying Thresholds
Edit quality thresholds in the test files:
```python
# Example: Change quality score threshold
if value < 0.9:  # Changed from 0.8
    results['issues_found'].append(f"Low {metric}: {value:.2f}")
```

## 🚨 Troubleshooting

### Common Issues

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
1. Check test output for specific error messages
2. Review generated reports for detailed metrics
3. Run individual test methods to isolate issues
4. Check Django logs for additional error information

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
- Update guides as needed

## 🎉 Success Criteria

Your data quality is excellent when:
- ✅ All tests pass without issues
- ✅ Quality scores are above thresholds
- ✅ Pipeline performance is >80%
- ✅ No critical issues found
- ✅ Recommendations are actionable

## 📖 Additional Resources

- [Data Quality Testing Guide](DATA_QUALITY_TESTING_GUIDE.md) - Detailed guide for using the test suite
- [Pipeline Documentation](../PIPELINE_DOCUMENTATION.md) - PDF processing pipeline documentation
- [Data Cleaning Documentation](../DATA_QUALITY_ANALYSIS_REPORT.md) - Data cleaning process documentation

---

**Remember**: Data quality is an ongoing process. Regular testing helps maintain high standards and catch issues early!
