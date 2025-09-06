# Search Benchmarking Module

A comprehensive query benchmark collection and evaluation system for the Pakistan Higher Courts Search and QA System.

## 🎯 Overview

The Search Benchmarking module provides systematic evaluation of search quality and performance through:

- **Benchmark Query Sets**: Organized collections of test queries with expected results
- **Execution Management**: Automated benchmark execution with detailed metrics collection
- **Performance Analysis**: Comprehensive analysis of latency, memory, and CPU usage
- **Quality Evaluation**: Advanced relevance metrics including Precision@K, Recall@K, MRR, and NDCG
- **Comparison Engine**: Statistical comparison between different configurations and algorithms
- **Report Generation**: Detailed HTML and JSON reports for analysis

## 🏗️ Architecture

### Core Components

1. **Models** (`models.py`)
   - `BenchmarkQuerySet`: Collections of benchmark queries
   - `BenchmarkQuery`: Individual queries with expected results
   - `BenchmarkExecution`: Execution records with configuration and results
   - `BenchmarkResult`: Individual query execution results
   - `BenchmarkComparison`: Comparisons between executions
   - `BenchmarkConfiguration`: Saved configurations for reuse

2. **Services** (`services/`)
   - `BenchmarkCollector`: Executes benchmarks and collects data
   - `RelevanceEvaluator`: Evaluates search result relevance
   - `PerformanceAnalyzer`: Analyzes system performance metrics
   - `ComparisonEngine`: Compares different executions
   - `ReportGenerator`: Generates comprehensive reports

3. **API Views** (`views.py`)
   - RESTful endpoints for all benchmark operations
   - Comprehensive error handling and validation
   - Pagination and filtering support

4. **Management Commands** (`management/commands/`)
   - `run_benchmark.py`: Command-line benchmark execution
   - `create_sample_data.py`: Create sample data for testing

5. **Frontend** (`templates/`)
   - Interactive dashboard for monitoring and analysis
   - Real-time updates and visualizations

## 🚀 Quick Start

### 1. Setup

```bash
# Add to INSTALLED_APPS in settings.py
INSTALLED_APPS = [
    # ... other apps
    'search_benchmarking',
]

# Run migrations
python manage.py makemigrations search_benchmarking
python manage.py migrate
```

### 2. Create Sample Data

```bash
# Create sample benchmark data
python manage.py create_sample_data
```

### 3. Run Your First Benchmark

```bash
# List available query sets
python manage.py run_benchmark --list-query-sets

# Run a benchmark
python manage.py run_benchmark --query-set-id 1 --generate-report
```

### 4. Access the Dashboard

Visit `/search/benchmarking/dashboard/` to access the interactive dashboard.

## 📊 Features

### Benchmark Query Sets

Create organized collections of test queries:

```python
# Legal Citations
query_set = BenchmarkQuerySet.objects.create(
    name='Legal Citations Benchmark',
    category='legal_citations',
    description='Test legal citation recognition'
)

# Add queries with expected results
query = BenchmarkQuery.objects.create(
    query_set=query_set,
    query_text='PPC 302',
    query_type='exact_match',
    expected_results=[
        {'case_id': 1, 'relevance': 1.0},
        {'case_id': 15, 'relevance': 0.9}
    ]
)
```

### Execution Management

Run benchmarks with different configurations:

```python
from search_benchmarking.services.benchmark_collector import BenchmarkCollector

collector = BenchmarkCollector()
execution = collector.collect_benchmark_data(
    query_set_id=1,
    execution_name='Performance Test'
)
```

### Performance Analysis

Analyze system performance with detailed metrics:

```python
from search_benchmarking.services.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()
analysis = analyzer.analyze_execution_performance(execution)

# Get latency distribution, memory usage, bottlenecks, etc.
```

### Quality Evaluation

Evaluate search quality with advanced metrics:

```python
from search_benchmarking.services.relevance_evaluator import RelevanceEvaluator

evaluator = RelevanceEvaluator()
metrics = evaluator.evaluate_query_relevance(query, returned_results)

# Get Precision@K, Recall@K, MRR, NDCG, etc.
```

### Configuration Management

Save and reuse benchmark configurations:

```python
config = BenchmarkConfiguration.objects.create(
    name='Fast Hybrid Config',
    search_mode='hybrid',
    ranking_algorithm='fast_ranking',
    ranking_config={
        'vector_weight': 0.6,
        'keyword_weight': 0.4,
        'exact_match_boost': 2.0
    }
)
```

## 📈 Metrics and Analysis

### Performance Metrics

- **Latency Analysis**: Mean, median, percentiles, distribution
- **Memory Usage**: Peak, average, efficiency scores
- **CPU Usage**: Utilization patterns and efficiency
- **Throughput**: Queries per second, success rates
- **Bottleneck Detection**: Automatic identification of performance issues

### Quality Metrics

- **Precision@K**: Accuracy of top-K results
- **Recall@K**: Coverage of relevant results
- **MRR (Mean Reciprocal Rank)**: Average rank of first relevant result
- **NDCG@K**: Normalized Discounted Cumulative Gain
- **MAP (Mean Average Precision)**: Overall precision across all relevant results
- **F1 Score**: Harmonic mean of precision and recall

### Statistical Analysis

- **Comparison Testing**: Statistical significance of differences
- **Trend Analysis**: Performance changes over time
- **Regression Detection**: Automatic identification of performance degradation
- **Confidence Intervals**: Uncertainty quantification for metrics

## 🔧 API Endpoints

### Query Sets
- `GET /api/search/benchmarking/query-sets/` - List query sets
- `POST /api/search/benchmarking/query-sets/` - Create query set
- `GET /api/search/benchmarking/query-sets/{id}/queries/` - Get queries
- `POST /api/search/benchmarking/query-sets/{id}/queries/` - Add query

### Executions
- `GET /api/search/benchmarking/executions/` - List executions
- `POST /api/search/benchmarking/executions/` - Start execution
- `GET /api/search/benchmarking/executions/{id}/` - Get execution details

### Comparisons
- `GET /api/search/benchmarking/comparisons/` - List comparisons
- `POST /api/search/benchmarking/comparisons/` - Create comparison

### Reports
- `POST /api/search/benchmarking/reports/` - Generate report

### Statistics
- `GET /api/search/benchmarking/statistics/` - Get system statistics

## 📋 Management Commands

### Run Benchmark

```bash
# Basic usage
python manage.py run_benchmark --query-set-id 1

# With custom configuration
python manage.py run_benchmark \
    --query-set-id 1 \
    --search-mode hybrid \
    --ranking-algorithm advanced_ranking \
    --generate-report

# List available options
python manage.py run_benchmark --help
```

### Create Sample Data

```bash
# Create sample data
python manage.py create_sample_data

# Reset existing data
python manage.py create_sample_data --reset

# Query sets only
python manage.py create_sample_data --query-sets-only
```

## 🎨 Frontend Dashboard

The interactive dashboard provides:

- **Real-time Monitoring**: Live updates of benchmark executions
- **Performance Visualization**: Charts and graphs for trend analysis
- **Quick Actions**: One-click benchmark execution and report generation
- **Detailed Analysis**: Drill-down into individual executions and results
- **Comparison Tools**: Side-by-side comparison of different configurations

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python manage.py test search_benchmarking

# Run specific test modules
python manage.py test search_benchmarking.tests.test_models
python manage.py test search_benchmarking.tests.test_services

# With coverage
coverage run --source='.' manage.py test search_benchmarking
coverage report
```

## 📊 Sample Query Categories

### Legal Citations
- `PPC 302` - Pakistan Penal Code section references
- `CrPC 497` - Criminal Procedure Code references
- `Case No. 123/2024` - Specific case number lookups

### Semantic Queries
- `murder case` - Concept-based searches
- `property dispute` - Legal domain searches
- `constitutional rights violation` - Complex legal concepts

### Complex Queries
- `murder case in Supreme Court 2023` - Multi-faceted searches
- `property dispute between family members` - Contextual searches

### Edge Cases
- Very short queries (`a`)
- Very long queries (100+ words)
- Non-existent references
- Special characters and formatting

## 🔍 Best Practices

### Query Set Design
1. **Diverse Categories**: Include different types of legal queries
2. **Difficulty Levels**: Range from simple to complex queries
3. **Expected Results**: Provide accurate relevance judgments
4. **Regular Updates**: Keep query sets current with legal developments

### Execution Strategy
1. **Baseline Establishment**: Create stable baseline configurations
2. **Systematic Testing**: Test one variable at a time
3. **Statistical Significance**: Ensure sufficient sample sizes
4. **Reproducibility**: Use versioned configurations

### Performance Monitoring
1. **Regular Execution**: Schedule regular benchmark runs
2. **Trend Analysis**: Monitor performance changes over time
3. **Alerting**: Set up alerts for performance degradation
4. **Documentation**: Document performance changes and optimizations

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure all dependencies are installed
   pip install -r requirements.txt
   ```

2. **Database Issues**
   ```bash
   # Run migrations
   python manage.py migrate
   ```

3. **Performance Issues**
   - Check system resources during execution
   - Monitor database performance
   - Consider reducing query set size for testing

### Getting Help

1. Check the logs for detailed error messages
2. Review the test suite for usage examples
3. Consult the API documentation for endpoint details
4. Use the management commands for debugging

## 🔮 Future Enhancements

- **Machine Learning Integration**: Automated relevance judgment learning
- **Real-time Monitoring**: Live performance dashboards
- **A/B Testing Framework**: Automated configuration testing
- **Advanced Visualizations**: Interactive charts and graphs
- **Export Capabilities**: CSV, Excel, and other format exports
- **Integration APIs**: Connect with external monitoring systems

---

**Note**: This module is designed to be production-ready with comprehensive error handling, logging, and monitoring capabilities. It integrates seamlessly with your existing search system architecture.

