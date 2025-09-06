"""
Relevance Evaluator Service
Evaluates search result relevance and calculates quality metrics.
"""

import logging
import math
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

from search_benchmarking.models import BenchmarkQuery, BenchmarkResult

logger = logging.getLogger(__name__)


class RelevanceEvaluator:
    """Service for evaluating search result relevance and quality"""
    
    def __init__(self):
        self.metrics_cache = {}
    
    def evaluate_query_relevance(self, 
                               query: BenchmarkQuery, 
                               returned_results: List[Dict]) -> Dict[str, Any]:
        """
        Evaluate relevance of returned results for a query
        
        Args:
            query: Benchmark query with expected results
            returned_results: List of returned search results
            
        Returns:
            Dictionary containing relevance metrics
        """
        try:
            expected_results = query.expected_results
            if not expected_results:
                return self._empty_metrics()
            
            # Extract case IDs and relevance scores
            expected_case_ids = [item['case_id'] for item in expected_results]
            expected_relevance = {item['case_id']: item.get('relevance', 1.0) 
                                for item in expected_results}
            
            returned_case_ids = [item['case_id'] for item in returned_results]
            
            # Calculate various metrics
            metrics = {
                'precision_at_5': self._calculate_precision_at_k(expected_case_ids, returned_case_ids, 5),
                'precision_at_10': self._calculate_precision_at_k(expected_case_ids, returned_case_ids, 10),
                'precision_at_20': self._calculate_precision_at_k(expected_case_ids, returned_case_ids, 20),
                'recall_at_5': self._calculate_recall_at_k(expected_case_ids, returned_case_ids, 5),
                'recall_at_10': self._calculate_recall_at_k(expected_case_ids, returned_case_ids, 10),
                'recall_at_20': self._calculate_recall_at_k(expected_case_ids, returned_case_ids, 20),
                'mrr': self._calculate_mrr(expected_case_ids, returned_case_ids),
                'ndcg_at_5': self._calculate_ndcg(expected_relevance, returned_results, 5),
                'ndcg_at_10': self._calculate_ndcg(expected_relevance, returned_results, 10),
                'ndcg_at_20': self._calculate_ndcg(expected_relevance, returned_results, 20),
                'map': self._calculate_map(expected_relevance, returned_results),
                'f1_at_10': self._calculate_f1_at_k(expected_case_ids, returned_case_ids, 10),
                'coverage': self._calculate_coverage(expected_case_ids, returned_case_ids),
                'ranking_quality': self._calculate_ranking_quality(expected_relevance, returned_results)
            }
            
            # Add detailed analysis
            metrics['detailed_analysis'] = self._detailed_relevance_analysis(
                expected_relevance, returned_results
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating relevance: {str(e)}")
            return self._empty_metrics()
    
    def evaluate_execution_quality(self, 
                                 execution_results: List[BenchmarkResult]) -> Dict[str, Any]:
        """
        Evaluate overall quality of a benchmark execution
        
        Args:
            execution_results: List of benchmark results from an execution
            
        Returns:
            Dictionary containing aggregate quality metrics
        """
        try:
            if not execution_results:
                return self._empty_metrics()
            
            # Aggregate metrics across all queries
            metrics = defaultdict(list)
            
            for result in execution_results:
                if result.status == 'success':
                    metrics['precision_at_10'].append(result.precision_at_10)
                    metrics['recall_at_10'].append(result.recall_at_10)
                    metrics['mrr'].append(result.mrr)
                    metrics['ndcg_at_10'].append(result.ndcg_at_10)
                    metrics['ranking_quality_score'].append(result.ranking_quality_score)
                    metrics['execution_time_ms'].append(result.execution_time_ms)
            
            # Calculate aggregate statistics
            aggregate_metrics = {}
            
            for metric_name, values in metrics.items():
                if values:
                    aggregate_metrics[f'{metric_name}_mean'] = sum(values) / len(values)
                    aggregate_metrics[f'{metric_name}_median'] = self._median(values)
                    aggregate_metrics[f'{metric_name}_std'] = self._standard_deviation(values)
                    aggregate_metrics[f'{metric_name}_min'] = min(values)
                    aggregate_metrics[f'{metric_name}_max'] = max(values)
            
            # Calculate overall quality score
            quality_scores = [result.ranking_quality_score for result in execution_results 
                            if result.ranking_quality_score is not None]
            if quality_scores:
                aggregate_metrics['overall_quality_score'] = sum(quality_scores) / len(quality_scores)
            
            # Performance analysis
            aggregate_metrics['performance_analysis'] = self._analyze_performance(execution_results)
            
            # Quality distribution analysis
            aggregate_metrics['quality_distribution'] = self._analyze_quality_distribution(execution_results)
            
            return dict(aggregate_metrics)
            
        except Exception as e:
            logger.error(f"Error evaluating execution quality: {str(e)}")
            return self._empty_metrics()
    
    def compare_executions(self, 
                         baseline_results: List[BenchmarkResult],
                         comparison_results: List[BenchmarkResult]) -> Dict[str, Any]:
        """
        Compare two benchmark executions
        
        Args:
            baseline_results: Results from baseline execution
            comparison_results: Results from comparison execution
            
        Returns:
            Dictionary containing comparison metrics
        """
        try:
            baseline_quality = self.evaluate_execution_quality(baseline_results)
            comparison_quality = self.evaluate_execution_quality(comparison_results)
            
            comparison = {
                'baseline_metrics': baseline_quality,
                'comparison_metrics': comparison_quality,
                'improvements': {},
                'degradations': {},
                'statistical_significance': {}
            }
            
            # Calculate improvements and degradations
            for metric in ['precision_at_10_mean', 'recall_at_10_mean', 'mrr_mean', 
                          'ndcg_at_10_mean', 'overall_quality_score']:
                if metric in baseline_quality and metric in comparison_quality:
                    baseline_val = baseline_quality[metric]
                    comparison_val = comparison_quality[metric]
                    
                    if baseline_val > 0:
                        improvement = ((comparison_val - baseline_val) / baseline_val) * 100
                        comparison['improvements'][metric] = improvement
                        
                        if improvement > 5:  # Significant improvement
                            comparison['improvements'][f'{metric}_significant'] = True
                        elif improvement < -5:  # Significant degradation
                            comparison['degradations'][metric] = improvement
                            comparison['degradations'][f'{metric}_significant'] = True
            
            # Statistical significance testing (simplified)
            comparison['statistical_significance'] = self._calculate_statistical_significance(
                baseline_results, comparison_results
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing executions: {str(e)}")
            return {}
    
    def _calculate_precision_at_k(self, expected: List[int], returned: List[int], k: int) -> float:
        """Calculate precision at k"""
        if not returned or k <= 0:
            return 0.0
        
        relevant_returned = set(returned[:k]).intersection(set(expected))
        return len(relevant_returned) / min(k, len(returned))
    
    def _calculate_recall_at_k(self, expected: List[int], returned: List[int], k: int) -> float:
        """Calculate recall at k"""
        if not expected or k <= 0:
            return 0.0
        
        relevant_returned = set(returned[:k]).intersection(set(expected))
        return len(relevant_returned) / len(expected)
    
    def _calculate_mrr(self, expected: List[int], returned: List[int]) -> float:
        """Calculate Mean Reciprocal Rank"""
        if not expected or not returned:
            return 0.0
        
        for i, case_id in enumerate(returned):
            if case_id in expected:
                return 1.0 / (i + 1)
        return 0.0
    
    def _calculate_ndcg(self, expected_relevance: Dict[int, float], 
                       returned_results: List[Dict], k: int) -> float:
        """Calculate Normalized Discounted Cumulative Gain at k"""
        if not expected_relevance or not returned_results or k <= 0:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, result in enumerate(returned_results[:k]):
            case_id = result['case_id']
            relevance = expected_relevance.get(case_id, 0.0)
            dcg += relevance / math.log2(i + 2)  # i+2 because log2(1) = 0
        
        # Calculate IDCG (ideal DCG)
        ideal_relevances = sorted(expected_relevance.values(), reverse=True)
        idcg = 0.0
        for i, relevance in enumerate(ideal_relevances[:k]):
            idcg += relevance / math.log2(i + 2)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def _calculate_map(self, expected_relevance: Dict[int, float], 
                      returned_results: List[Dict]) -> float:
        """Calculate Mean Average Precision"""
        if not expected_relevance or not returned_results:
            return 0.0
        
        relevant_count = 0
        precision_sum = 0.0
        
        for i, result in enumerate(returned_results):
            case_id = result['case_id']
            if case_id in expected_relevance:
                relevant_count += 1
                precision_at_i = relevant_count / (i + 1)
                precision_sum += precision_at_i
        
        return precision_sum / len(expected_relevance) if expected_relevance else 0.0
    
    def _calculate_f1_at_k(self, expected: List[int], returned: List[int], k: int) -> float:
        """Calculate F1 score at k"""
        precision = self._calculate_precision_at_k(expected, returned, k)
        recall = self._calculate_recall_at_k(expected, returned, k)
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)
    
    def _calculate_coverage(self, expected: List[int], returned: List[int]) -> float:
        """Calculate coverage (percentage of expected results found)"""
        if not expected:
            return 0.0
        
        found = set(returned).intersection(set(expected))
        return len(found) / len(expected)
    
    def _calculate_ranking_quality(self, expected_relevance: Dict[int, float], 
                                 returned_results: List[Dict]) -> float:
        """Calculate overall ranking quality score"""
        if not expected_relevance or not returned_results:
            return 0.0
        
        # Weighted score based on position and relevance
        total_score = 0.0
        total_weight = 0.0
        
        for i, result in enumerate(returned_results):
            case_id = result['case_id']
            if case_id in expected_relevance:
                relevance = expected_relevance[case_id]
                position_weight = 1.0 / (i + 1)  # Higher weight for better positions
                total_score += relevance * position_weight
                total_weight += position_weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _detailed_relevance_analysis(self, expected_relevance: Dict[int, float], 
                                   returned_results: List[Dict]) -> Dict[str, Any]:
        """Provide detailed analysis of relevance"""
        analysis = {
            'total_expected': len(expected_relevance),
            'total_returned': len(returned_results),
            'relevant_found': 0,
            'relevant_positions': [],
            'missing_relevant': [],
            'irrelevant_returned': 0
        }
        
        found_case_ids = set()
        for i, result in enumerate(returned_results):
            case_id = result['case_id']
            if case_id in expected_relevance:
                analysis['relevant_found'] += 1
                analysis['relevant_positions'].append({
                    'position': i + 1,
                    'case_id': case_id,
                    'relevance': expected_relevance[case_id]
                })
                found_case_ids.add(case_id)
            else:
                analysis['irrelevant_returned'] += 1
        
        # Find missing relevant results
        for case_id, relevance in expected_relevance.items():
            if case_id not in found_case_ids:
                analysis['missing_relevant'].append({
                    'case_id': case_id,
                    'relevance': relevance
                })
        
        return analysis
    
    def _analyze_performance(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze performance characteristics"""
        execution_times = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        
        if not execution_times:
            return {}
        
        return {
            'avg_execution_time_ms': sum(execution_times) / len(execution_times),
            'median_execution_time_ms': self._median(execution_times),
            'min_execution_time_ms': min(execution_times),
            'max_execution_time_ms': max(execution_times),
            'std_execution_time_ms': self._standard_deviation(execution_times),
            'slow_queries_count': len([t for t in execution_times if t > 2000]),  # > 2 seconds
            'fast_queries_count': len([t for t in execution_times if t < 500])   # < 0.5 seconds
        }
    
    def _analyze_quality_distribution(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze quality score distribution"""
        quality_scores = [r.ranking_quality_score for r in results 
                         if r.ranking_quality_score is not None]
        
        if not quality_scores:
            return {}
        
        return {
            'excellent_queries': len([s for s in quality_scores if s >= 0.8]),  # >= 80%
            'good_queries': len([s for s in quality_scores if 0.6 <= s < 0.8]),  # 60-80%
            'fair_queries': len([s for s in quality_scores if 0.4 <= s < 0.6]),  # 40-60%
            'poor_queries': len([s for s in quality_scores if s < 0.4]),  # < 40%
            'quality_distribution': {
                'mean': sum(quality_scores) / len(quality_scores),
                'median': self._median(quality_scores),
                'std': self._standard_deviation(quality_scores)
            }
        }
    
    def _calculate_statistical_significance(self, 
                                          baseline_results: List[BenchmarkResult],
                                          comparison_results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate statistical significance of differences (simplified)"""
        # This is a simplified version - in production, you'd use proper statistical tests
        
        baseline_scores = [r.ranking_quality_score for r in baseline_results 
                          if r.ranking_quality_score is not None]
        comparison_scores = [r.ranking_quality_score for r in comparison_results 
                           if r.ranking_quality_score is not None]
        
        if not baseline_scores or not comparison_scores:
            return {}
        
        baseline_mean = sum(baseline_scores) / len(baseline_scores)
        comparison_mean = sum(comparison_scores) / len(comparison_scores)
        
        # Simple t-test approximation
        baseline_std = self._standard_deviation(baseline_scores)
        comparison_std = self._standard_deviation(comparison_scores)
        
        # Pooled standard error
        n1, n2 = len(baseline_scores), len(comparison_scores)
        pooled_se = math.sqrt((baseline_std**2 / n1) + (comparison_std**2 / n2))
        
        if pooled_se > 0:
            t_statistic = (comparison_mean - baseline_mean) / pooled_se
            # Simplified significance (|t| > 2 is roughly p < 0.05)
            is_significant = abs(t_statistic) > 2.0
        else:
            t_statistic = 0.0
            is_significant = False
        
        return {
            't_statistic': t_statistic,
            'is_significant': is_significant,
            'baseline_mean': baseline_mean,
            'comparison_mean': comparison_mean,
            'difference': comparison_mean - baseline_mean,
            'effect_size': (comparison_mean - baseline_mean) / baseline_mean if baseline_mean > 0 else 0
        }
    
    def _median(self, values: List[float]) -> float:
        """Calculate median of a list of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]
    
    def _standard_deviation(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics dictionary"""
        return {
            'precision_at_5': 0.0,
            'precision_at_10': 0.0,
            'precision_at_20': 0.0,
            'recall_at_5': 0.0,
            'recall_at_10': 0.0,
            'recall_at_20': 0.0,
            'mrr': 0.0,
            'ndcg_at_5': 0.0,
            'ndcg_at_10': 0.0,
            'ndcg_at_20': 0.0,
            'map': 0.0,
            'f1_at_10': 0.0,
            'coverage': 0.0,
            'ranking_quality': 0.0,
            'detailed_analysis': {}
        }

