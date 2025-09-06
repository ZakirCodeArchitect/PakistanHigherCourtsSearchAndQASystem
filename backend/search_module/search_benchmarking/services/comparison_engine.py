"""
Comparison Engine Service
Compares different benchmark executions and configurations.
"""

import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from search_benchmarking.models import BenchmarkExecution, BenchmarkResult, BenchmarkComparison

logger = logging.getLogger(__name__)


class ComparisonEngine:
    """Service for comparing benchmark executions and configurations"""
    
    def __init__(self):
        self.significance_threshold = 0.05  # 5% significance level
        self.minimum_sample_size = 10  # Minimum queries for statistical comparison
    
    def compare_executions(self, 
                         baseline_execution_id: int,
                         comparison_execution_ids: List[int],
                         comparison_name: str = None) -> BenchmarkComparison:
        """
        Compare multiple benchmark executions against a baseline
        
        Args:
            baseline_execution_id: ID of baseline execution
            comparison_execution_ids: List of execution IDs to compare
            comparison_name: Name for the comparison
            
        Returns:
            BenchmarkComparison object
        """
        try:
            # Get executions
            baseline_execution = BenchmarkExecution.objects.get(id=baseline_execution_id)
            comparison_executions = BenchmarkExecution.objects.filter(
                id__in=comparison_execution_ids
            )
            
            if not comparison_name:
                comparison_name = f"Comparison_{baseline_execution.execution_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create comparison record
            comparison = BenchmarkComparison.objects.create(
                name=comparison_name,
                baseline_execution=baseline_execution,
                description=f"Comparison of {len(comparison_executions)} executions against baseline"
            )
            comparison.comparison_executions.set(comparison_executions)
            
            # Perform detailed comparison
            comparison_results = self._perform_detailed_comparison(
                baseline_execution, comparison_executions
            )
            
            # Update comparison with results
            comparison.comparison_results = comparison_results
            comparison.performance_improvement = comparison_results.get('overall_performance_improvement', 0.0)
            comparison.quality_improvement = comparison_results.get('overall_quality_improvement', 0.0)
            comparison.save()
            
            logger.info(f"Comparison completed: {comparison.name}")
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing executions: {str(e)}")
            raise
    
    def compare_configurations(self, 
                             query_set_id: int,
                             configurations: List[Dict[str, Any]],
                             execution_name_prefix: str = "Config_Comparison") -> Dict[str, Any]:
        """
        Compare different search configurations on the same query set
        
        Args:
            query_set_id: ID of query set to use
            configurations: List of configuration dictionaries
            execution_name_prefix: Prefix for execution names
            
        Returns:
            Dictionary containing comparison results
        """
        try:
            from .benchmark_collector import BenchmarkCollector
            
            collector = BenchmarkCollector()
            executions = []
            
            # Run benchmark for each configuration
            for i, config in enumerate(configurations):
                execution_name = f"{execution_name_prefix}_{i+1}_{config.get('search_mode', 'hybrid')}_{config.get('ranking_algorithm', 'fast')}"
                
                # Create temporary configuration
                from ..models import BenchmarkConfiguration
                temp_config = BenchmarkConfiguration.objects.create(
                    name=f"temp_config_{i}",
                    search_mode=config.get('search_mode', 'hybrid'),
                    ranking_algorithm=config.get('ranking_algorithm', 'fast_ranking'),
                    ranking_config=config.get('ranking_config', {}),
                    is_active=False  # Temporary config
                )
                
                try:
                    # Execute benchmark
                    execution = collector.collect_benchmark_data(
                        query_set_id=query_set_id,
                        configuration=temp_config,
                        execution_name=execution_name
                    )
                    executions.append(execution)
                    
                finally:
                    # Clean up temporary configuration
                    temp_config.delete()
            
            # Compare all executions
            if len(executions) >= 2:
                baseline = executions[0]
                comparisons = executions[1:]
                
                comparison = self.compare_executions(
                    baseline.id,
                    [e.id for e in comparisons],
                    f"{execution_name_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                return {
                    'comparison_id': comparison.id,
                    'executions': [e.id for e in executions],
                    'results': comparison.comparison_results,
                    'best_configuration': self._identify_best_configuration(executions, comparison.comparison_results)
                }
            else:
                return {'error': 'Need at least 2 configurations to compare'}
                
        except Exception as e:
            logger.error(f"Error comparing configurations: {str(e)}")
            raise
    
    def _perform_detailed_comparison(self, 
                                   baseline_execution: BenchmarkExecution,
                                   comparison_executions: List[BenchmarkExecution]) -> Dict[str, Any]:
        """Perform detailed comparison between executions"""
        
        comparison_results = {
            'baseline_execution': {
                'id': baseline_execution.id,
                'name': baseline_execution.execution_name,
                'search_mode': baseline_execution.search_mode,
                'ranking_algorithm': baseline_execution.ranking_algorithm,
                'metrics': self._extract_execution_metrics(baseline_execution)
            },
            'comparison_executions': [],
            'statistical_comparisons': {},
            'overall_performance_improvement': 0.0,
            'overall_quality_improvement': 0.0,
            'best_execution': None,
            'recommendations': []
        }
        
        # Compare each execution against baseline
        for comparison_execution in comparison_executions:
            comparison_data = self._compare_single_execution(
                baseline_execution, comparison_execution
            )
            comparison_results['comparison_executions'].append(comparison_data)
        
        # Calculate overall improvements
        comparison_results['overall_performance_improvement'] = self._calculate_overall_performance_improvement(
            comparison_results['comparison_executions']
        )
        comparison_results['overall_quality_improvement'] = self._calculate_overall_quality_improvement(
            comparison_results['comparison_executions']
        )
        
        # Identify best execution
        comparison_results['best_execution'] = self._identify_best_execution(
            baseline_execution, comparison_results['comparison_executions']
        )
        
        # Generate recommendations
        comparison_results['recommendations'] = self._generate_comparison_recommendations(
            comparison_results
        )
        
        return comparison_results
    
    def _compare_single_execution(self, 
                                baseline_execution: BenchmarkExecution,
                                comparison_execution: BenchmarkExecution) -> Dict[str, Any]:
        """Compare a single execution against baseline"""
        
        baseline_metrics = self._extract_execution_metrics(baseline_execution)
        comparison_metrics = self._extract_execution_metrics(comparison_execution)
        
        comparison_data = {
            'execution_id': comparison_execution.id,
            'execution_name': comparison_execution.execution_name,
            'search_mode': comparison_execution.search_mode,
            'ranking_algorithm': comparison_execution.ranking_algorithm,
            'metrics': comparison_metrics,
            'improvements': {},
            'degradations': {},
            'statistical_significance': {},
            'overall_score': 0.0
        }
        
        # Compare key metrics
        metrics_to_compare = [
            'average_latency_ms',
            'average_precision_at_10',
            'average_recall_at_10',
            'average_mrr',
            'average_ndcg_at_10',
            'success_rate',
            'total_execution_time'
        ]
        
        improvements = []
        degradations = []
        
        for metric in metrics_to_compare:
            baseline_val = baseline_metrics.get(metric, 0)
            comparison_val = comparison_metrics.get(metric, 0)
            
            if baseline_val != 0:
                percent_change = ((comparison_val - baseline_val) / baseline_val) * 100
                
                # Determine if this is an improvement or degradation
                is_improvement = self._is_metric_improvement(metric, percent_change)
                
                if is_improvement and abs(percent_change) > 5:  # 5% threshold
                    improvements.append(percent_change)
                    comparison_data['improvements'][metric] = percent_change
                elif not is_improvement and abs(percent_change) > 5:
                    degradations.append(percent_change)
                    comparison_data['degradations'][metric] = percent_change
        
        # Calculate overall score
        improvement_score = sum(improvements) / len(improvements) if improvements else 0
        degradation_score = sum(degradations) / len(degradations) if degradations else 0
        comparison_data['overall_score'] = improvement_score - degradation_score
        
        # Statistical significance testing
        comparison_data['statistical_significance'] = self._test_statistical_significance(
            baseline_execution, comparison_execution
        )
        
        return comparison_data
    
    def _extract_execution_metrics(self, execution: BenchmarkExecution) -> Dict[str, Any]:
        """Extract key metrics from an execution"""
        return {
            'total_queries': execution.total_queries,
            'successful_queries': execution.successful_queries,
            'failed_queries': execution.failed_queries,
            'success_rate': execution.success_rate,
            'average_latency_ms': execution.average_latency_ms,
            'min_latency_ms': execution.min_latency_ms,
            'max_latency_ms': execution.max_latency_ms,
            'average_precision_at_10': execution.average_precision_at_10,
            'average_recall_at_10': execution.average_recall_at_10,
            'average_mrr': execution.average_mrr,
            'average_ndcg_at_10': execution.average_ndcg_at_10,
            'total_execution_time': execution.total_execution_time,
            'memory_usage_mb': execution.memory_usage_mb,
            'cpu_usage_percent': execution.cpu_usage_percent
        }
    
    def _is_metric_improvement(self, metric: str, percent_change: float) -> bool:
        """Determine if a percent change represents an improvement for a metric"""
        # Metrics where lower is better
        lower_is_better = [
            'average_latency_ms',
            'min_latency_ms',
            'max_latency_ms',
            'total_execution_time',
            'memory_usage_mb',
            'cpu_usage_percent'
        ]
        
        # Metrics where higher is better
        higher_is_better = [
            'average_precision_at_10',
            'average_recall_at_10',
            'average_mrr',
            'average_ndcg_at_10',
            'success_rate'
        ]
        
        if metric in lower_is_better:
            return percent_change < 0  # Negative change is improvement
        elif metric in higher_is_better:
            return percent_change > 0  # Positive change is improvement
        else:
            return False  # Unknown metric
    
    def _test_statistical_significance(self, 
                                     baseline_execution: BenchmarkExecution,
                                     comparison_execution: BenchmarkExecution) -> Dict[str, Any]:
        """Test statistical significance of differences"""
        
        # Get results for both executions
        baseline_results = list(baseline_execution.results.all())
        comparison_results = list(comparison_execution.results.all())
        
        if len(baseline_results) < self.minimum_sample_size or len(comparison_results) < self.minimum_sample_size:
            return {'error': 'Insufficient sample size for statistical testing'}
        
        # Extract quality scores
        baseline_scores = [r.ranking_quality_score for r in baseline_results if r.ranking_quality_score is not None]
        comparison_scores = [r.ranking_quality_score for r in comparison_results if r.ranking_quality_score is not None]
        
        if not baseline_scores or not comparison_scores:
            return {'error': 'No quality scores available for testing'}
        
        # Perform t-test (simplified version)
        significance_results = self._perform_t_test(baseline_scores, comparison_scores)
        
        return significance_results
    
    def _perform_t_test(self, baseline_scores: List[float], comparison_scores: List[float]) -> Dict[str, Any]:
        """Perform simplified t-test"""
        
        # Calculate means and standard deviations
        baseline_mean = statistics.mean(baseline_scores)
        comparison_mean = statistics.mean(comparison_scores)
        baseline_std = statistics.stdev(baseline_scores) if len(baseline_scores) > 1 else 0
        comparison_std = statistics.stdev(comparison_scores) if len(comparison_scores) > 1 else 0
        
        # Calculate pooled standard error
        n1, n2 = len(baseline_scores), len(comparison_scores)
        pooled_se = ((baseline_std**2 / n1) + (comparison_std**2 / n2)) ** 0.5
        
        if pooled_se == 0:
            return {'error': 'Cannot calculate standard error'}
        
        # Calculate t-statistic
        t_statistic = (comparison_mean - baseline_mean) / pooled_se
        
        # Simplified significance test (|t| > 2 is roughly p < 0.05)
        is_significant = abs(t_statistic) > 2.0
        p_value_approx = 0.05 if is_significant else 0.1  # Rough approximation
        
        return {
            't_statistic': t_statistic,
            'p_value_approx': p_value_approx,
            'is_significant': is_significant,
            'baseline_mean': baseline_mean,
            'comparison_mean': comparison_mean,
            'difference': comparison_mean - baseline_mean,
            'effect_size': (comparison_mean - baseline_mean) / baseline_std if baseline_std > 0 else 0,
            'sample_sizes': {'baseline': n1, 'comparison': n2}
        }
    
    def _calculate_overall_performance_improvement(self, comparisons: List[Dict[str, Any]]) -> float:
        """Calculate overall performance improvement across all comparisons"""
        if not comparisons:
            return 0.0
        
        # Weight different metrics
        performance_metrics = ['average_latency_ms', 'total_execution_time', 'memory_usage_mb', 'cpu_usage_percent']
        weights = {'average_latency_ms': 0.4, 'total_execution_time': 0.3, 'memory_usage_mb': 0.2, 'cpu_usage_percent': 0.1}
        
        total_improvement = 0.0
        total_weight = 0.0
        
        for comparison in comparisons:
            for metric, weight in weights.items():
                if metric in comparison.get('improvements', {}):
                    # For performance metrics, negative change is improvement
                    improvement = -comparison['improvements'][metric]  # Flip sign
                    total_improvement += improvement * weight
                    total_weight += weight
        
        return total_improvement / total_weight if total_weight > 0 else 0.0
    
    def _calculate_overall_quality_improvement(self, comparisons: List[Dict[str, Any]]) -> float:
        """Calculate overall quality improvement across all comparisons"""
        if not comparisons:
            return 0.0
        
        # Weight different quality metrics
        quality_metrics = ['average_precision_at_10', 'average_recall_at_10', 'average_mrr', 'average_ndcg_at_10']
        weights = {'average_precision_at_10': 0.3, 'average_recall_at_10': 0.3, 'average_mrr': 0.2, 'average_ndcg_at_10': 0.2}
        
        total_improvement = 0.0
        total_weight = 0.0
        
        for comparison in comparisons:
            for metric, weight in weights.items():
                if metric in comparison.get('improvements', {}):
                    improvement = comparison['improvements'][metric]
                    total_improvement += improvement * weight
                    total_weight += weight
        
        return total_improvement / total_weight if total_weight > 0 else 0.0
    
    def _identify_best_execution(self, 
                               baseline_execution: BenchmarkExecution,
                               comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify the best execution based on overall scores"""
        
        # Include baseline in comparison
        all_executions = [
            {
                'execution_id': baseline_execution.id,
                'execution_name': baseline_execution.execution_name,
                'search_mode': baseline_execution.search_mode,
                'ranking_algorithm': baseline_execution.ranking_algorithm,
                'overall_score': 0.0  # Baseline score
            }
        ]
        
        # Add comparison executions
        all_executions.extend(comparisons)
        
        # Find execution with highest overall score
        best_execution = max(all_executions, key=lambda x: x['overall_score'])
        
        return {
            'execution_id': best_execution['execution_id'],
            'execution_name': best_execution['execution_name'],
            'search_mode': best_execution['search_mode'],
            'ranking_algorithm': best_execution['ranking_algorithm'],
            'overall_score': best_execution['overall_score'],
            'is_baseline': best_execution['execution_id'] == baseline_execution.id
        }
    
    def _identify_best_configuration(self, 
                                   executions: List[BenchmarkExecution],
                                   comparison_results: Dict[str, Any]) -> Dict[str, Any]:
        """Identify the best configuration from comparison results"""
        
        best_execution_info = comparison_results.get('best_execution', {})
        
        if not best_execution_info:
            return {'error': 'No best execution identified'}
        
        best_execution_id = best_execution_info['execution_id']
        best_execution = next((e for e in executions if e.id == best_execution_id), None)
        
        if not best_execution:
            return {'error': 'Best execution not found'}
        
        return {
            'execution_id': best_execution.id,
            'execution_name': best_execution.execution_name,
            'search_mode': best_execution.search_mode,
            'ranking_algorithm': best_execution.ranking_algorithm,
            'ranking_config': best_execution.ranking_config,
            'overall_score': best_execution_info['overall_score'],
            'key_metrics': {
                'average_latency_ms': best_execution.average_latency_ms,
                'average_precision_at_10': best_execution.average_precision_at_10,
                'average_recall_at_10': best_execution.average_recall_at_10,
                'average_mrr': best_execution.average_mrr,
                'average_ndcg_at_10': best_execution.average_ndcg_at_10,
                'success_rate': best_execution.success_rate
            }
        }
    
    def _generate_comparison_recommendations(self, comparison_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison results"""
        recommendations = []
        
        best_execution = comparison_results.get('best_execution', {})
        if best_execution and not best_execution.get('is_baseline', True):
            recommendations.append(f"Consider adopting the configuration from '{best_execution['execution_name']}' - it shows the best overall performance")
        
        # Check for significant improvements
        for comparison in comparison_results.get('comparison_executions', []):
            if comparison.get('statistical_significance', {}).get('is_significant', False):
                recommendations.append(f"'{comparison['execution_name']}' shows statistically significant improvements over baseline")
        
        # Check for performance improvements
        if comparison_results.get('overall_performance_improvement', 0) > 10:
            recommendations.append("Significant performance improvements detected - consider implementing the best performing configuration")
        
        # Check for quality improvements
        if comparison_results.get('overall_quality_improvement', 0) > 5:
            recommendations.append("Quality improvements detected - review the best performing configuration for quality metrics")
        
        return recommendations

