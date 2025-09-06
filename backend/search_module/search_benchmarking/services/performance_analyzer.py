"""
Performance Analyzer Service
Analyzes search system performance metrics and identifies bottlenecks.
"""

import logging
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from search_benchmarking.models import BenchmarkExecution, BenchmarkResult

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """Service for analyzing search system performance"""
    
    def __init__(self):
        self.performance_thresholds = {
            'excellent_latency_ms': 500,
            'good_latency_ms': 1000,
            'acceptable_latency_ms': 2000,
            'poor_latency_ms': 5000,
            'excellent_memory_mb': 100,
            'good_memory_mb': 200,
            'acceptable_memory_mb': 500,
            'poor_memory_mb': 1000,
            'excellent_cpu_percent': 10,
            'good_cpu_percent': 25,
            'acceptable_cpu_percent': 50,
            'poor_cpu_percent': 80
        }
    
    def analyze_execution_performance(self, 
                                    execution: BenchmarkExecution) -> Dict[str, Any]:
        """
        Analyze performance of a benchmark execution
        
        Args:
            execution: Benchmark execution to analyze
            
        Returns:
            Dictionary containing performance analysis
        """
        try:
            results = execution.results.all()
            if not results:
                return self._empty_analysis()
            
            analysis = {
                'execution_summary': self._analyze_execution_summary(execution),
                'latency_analysis': self._analyze_latency(results),
                'memory_analysis': self._analyze_memory_usage(results),
                'cpu_analysis': self._analyze_cpu_usage(results),
                'throughput_analysis': self._analyze_throughput(execution, results),
                'performance_trends': self._analyze_performance_trends(results),
                'bottleneck_analysis': self._identify_bottlenecks(results),
                'recommendations': []
            }
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_performance_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing execution performance: {str(e)}")
            return self._empty_analysis()
    
    def compare_performance(self, 
                          baseline_execution: BenchmarkExecution,
                          comparison_execution: BenchmarkExecution) -> Dict[str, Any]:
        """
        Compare performance between two executions
        
        Args:
            baseline_execution: Baseline execution
            comparison_execution: Execution to compare against baseline
            
        Returns:
            Dictionary containing performance comparison
        """
        try:
            baseline_analysis = self.analyze_execution_performance(baseline_execution)
            comparison_analysis = self.analyze_execution_performance(comparison_execution)
            
            comparison = {
                'baseline_performance': baseline_analysis,
                'comparison_performance': comparison_analysis,
                'performance_differences': {},
                'improvements': {},
                'degradations': {},
                'overall_assessment': {}
            }
            
            # Compare key metrics
            self._compare_metrics(baseline_analysis, comparison_analysis, comparison)
            
            # Overall assessment
            comparison['overall_assessment'] = self._assess_overall_performance_change(
                baseline_analysis, comparison_analysis
            )
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing performance: {str(e)}")
            return {}
    
    def analyze_performance_trends(self, 
                                 executions: List[BenchmarkExecution],
                                 days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze performance trends over time
        
        Args:
            executions: List of benchmark executions
            days_back: Number of days to look back
            
        Returns:
            Dictionary containing trend analysis
        """
        try:
            # Filter executions by date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_executions = [
                e for e in executions 
                if e.started_at.replace(tzinfo=None) >= cutoff_date
            ]
            
            if len(recent_executions) < 2:
                return {'error': 'Insufficient data for trend analysis'}
            
            # Sort by date
            recent_executions.sort(key=lambda x: x.started_at)
            
            trends = {
                'time_period': f"Last {days_back} days",
                'total_executions': len(recent_executions),
                'latency_trends': self._analyze_latency_trends(recent_executions),
                'memory_trends': self._analyze_memory_trends(recent_executions),
                'throughput_trends': self._analyze_throughput_trends(recent_executions),
                'quality_trends': self._analyze_quality_trends(recent_executions),
                'performance_regressions': self._identify_performance_regressions(recent_executions),
                'recommendations': []
            }
            
            # Generate trend-based recommendations
            trends['recommendations'] = self._generate_trend_recommendations(trends)
            
            return trends
            
        except Exception as e:
            logger.error(f"Error analyzing performance trends: {str(e)}")
            return {}
    
    def _analyze_execution_summary(self, execution: BenchmarkExecution) -> Dict[str, Any]:
        """Analyze execution summary"""
        return {
            'execution_name': execution.execution_name,
            'search_mode': execution.search_mode,
            'ranking_algorithm': execution.ranking_algorithm,
            'total_queries': execution.total_queries,
            'successful_queries': execution.successful_queries,
            'failed_queries': execution.failed_queries,
            'success_rate': execution.success_rate,
            'total_execution_time': execution.total_execution_time,
            'average_latency_ms': execution.average_latency_ms,
            'started_at': execution.started_at,
            'completed_at': execution.completed_at,
            'duration': execution.duration
        }
    
    def _analyze_latency(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze query latency"""
        latencies = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        
        if not latencies:
            return {'error': 'No latency data available'}
        
        analysis = {
            'count': len(latencies),
            'mean_ms': statistics.mean(latencies),
            'median_ms': statistics.median(latencies),
            'min_ms': min(latencies),
            'max_ms': max(latencies),
            'std_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
            'percentiles': {
                'p50': statistics.median(latencies),
                'p90': self._percentile(latencies, 90),
                'p95': self._percentile(latencies, 95),
                'p99': self._percentile(latencies, 99)
            },
            'performance_categories': self._categorize_latency_performance(latencies),
            'slow_queries': self._identify_slow_queries(results, latencies)
        }
        
        return analysis
    
    def _analyze_memory_usage(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze memory usage"""
        memory_usage = [r.memory_usage_mb for r in results if r.memory_usage_mb > 0]
        
        if not memory_usage:
            return {'error': 'No memory usage data available'}
        
        analysis = {
            'count': len(memory_usage),
            'mean_mb': statistics.mean(memory_usage),
            'median_mb': statistics.median(memory_usage),
            'min_mb': min(memory_usage),
            'max_mb': max(memory_usage),
            'std_mb': statistics.stdev(memory_usage) if len(memory_usage) > 1 else 0,
            'total_memory_mb': sum(memory_usage),
            'performance_categories': self._categorize_memory_performance(memory_usage),
            'memory_efficiency': self._calculate_memory_efficiency(results)
        }
        
        return analysis
    
    def _analyze_cpu_usage(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze CPU usage"""
        cpu_usage = [r.cpu_usage_percent for r in results if r.cpu_usage_percent > 0]
        
        if not cpu_usage:
            return {'error': 'No CPU usage data available'}
        
        analysis = {
            'count': len(cpu_usage),
            'mean_percent': statistics.mean(cpu_usage),
            'median_percent': statistics.median(cpu_usage),
            'min_percent': min(cpu_usage),
            'max_percent': max(cpu_usage),
            'std_percent': statistics.stdev(cpu_usage) if len(cpu_usage) > 1 else 0,
            'performance_categories': self._categorize_cpu_performance(cpu_usage),
            'cpu_efficiency': self._calculate_cpu_efficiency(results)
        }
        
        return analysis
    
    def _analyze_throughput(self, execution: BenchmarkExecution, 
                          results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze system throughput"""
        if not execution.duration or execution.duration <= 0:
            return {'error': 'Invalid execution duration'}
        
        total_queries = len(results)
        successful_queries = len([r for r in results if r.status == 'success'])
        
        analysis = {
            'queries_per_second': total_queries / execution.duration,
            'successful_queries_per_second': successful_queries / execution.duration,
            'total_queries': total_queries,
            'successful_queries': successful_queries,
            'execution_duration_seconds': execution.duration,
            'average_query_time_ms': execution.average_latency_ms,
            'throughput_efficiency': successful_queries / total_queries if total_queries > 0 else 0
        }
        
        return analysis
    
    def _analyze_performance_trends(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze performance trends within a single execution"""
        if len(results) < 2:
            return {'error': 'Insufficient data for trend analysis'}
        
        # Sort results by execution order (assuming they're in order)
        sorted_results = sorted(results, key=lambda x: x.executed_at)
        
        # Calculate moving averages
        window_size = min(10, len(sorted_results) // 4)  # 25% of results or 10, whichever is smaller
        
        latencies = [r.execution_time_ms for r in sorted_results if r.execution_time_ms > 0]
        memory_usage = [r.memory_usage_mb for r in sorted_results if r.memory_usage_mb > 0]
        
        trends = {
            'latency_trend': self._calculate_moving_average(latencies, window_size),
            'memory_trend': self._calculate_moving_average(memory_usage, window_size),
            'performance_degradation': self._detect_performance_degradation(sorted_results),
            'consistency_score': self._calculate_consistency_score(sorted_results)
        }
        
        return trends
    
    def _identify_bottlenecks(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Identify performance bottlenecks"""
        bottlenecks = {
            'latency_bottlenecks': [],
            'memory_bottlenecks': [],
            'cpu_bottlenecks': [],
            'error_patterns': [],
            'overall_assessment': {}
        }
        
        # Identify slow queries
        latencies = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        if latencies:
            slow_threshold = self._percentile(latencies, 95)  # Top 5% slowest
            slow_queries = [r for r in results if r.execution_time_ms >= slow_threshold]
            bottlenecks['latency_bottlenecks'] = [
                {
                    'query_id': r.query.id,
                    'query_text': r.query.query_text[:100],
                    'execution_time_ms': r.execution_time_ms,
                    'percentile': 95
                }
                for r in slow_queries
            ]
        
        # Identify memory-intensive queries
        memory_usage = [r.memory_usage_mb for r in results if r.memory_usage_mb > 0]
        if memory_usage:
            memory_threshold = self._percentile(memory_usage, 95)
            memory_intensive = [r for r in results if r.memory_usage_mb >= memory_threshold]
            bottlenecks['memory_bottlenecks'] = [
                {
                    'query_id': r.query.id,
                    'query_text': r.query.query_text[:100],
                    'memory_usage_mb': r.memory_usage_mb,
                    'percentile': 95
                }
                for r in memory_intensive
            ]
        
        # Identify error patterns
        error_queries = [r for r in results if r.status != 'success']
        if error_queries:
            bottlenecks['error_patterns'] = [
                {
                    'query_id': r.query.id,
                    'query_text': r.query.query_text[:100],
                    'status': r.status,
                    'error_message': r.error_message[:200] if r.error_message else ''
                }
                for r in error_queries
            ]
        
        # Overall assessment
        bottlenecks['overall_assessment'] = self._assess_bottleneck_severity(bottlenecks)
        
        return bottlenecks
    
    def _categorize_latency_performance(self, latencies: List[float]) -> Dict[str, int]:
        """Categorize latency performance"""
        categories = {
            'excellent': 0,  # < 500ms
            'good': 0,       # 500-1000ms
            'acceptable': 0, # 1000-2000ms
            'poor': 0        # > 2000ms
        }
        
        for latency in latencies:
            if latency < self.performance_thresholds['excellent_latency_ms']:
                categories['excellent'] += 1
            elif latency < self.performance_thresholds['good_latency_ms']:
                categories['good'] += 1
            elif latency < self.performance_thresholds['acceptable_latency_ms']:
                categories['acceptable'] += 1
            else:
                categories['poor'] += 1
        
        return categories
    
    def _categorize_memory_performance(self, memory_usage: List[float]) -> Dict[str, int]:
        """Categorize memory performance"""
        categories = {
            'excellent': 0,  # < 100MB
            'good': 0,       # 100-200MB
            'acceptable': 0, # 200-500MB
            'poor': 0        # > 500MB
        }
        
        for memory in memory_usage:
            if memory < self.performance_thresholds['excellent_memory_mb']:
                categories['excellent'] += 1
            elif memory < self.performance_thresholds['good_memory_mb']:
                categories['good'] += 1
            elif memory < self.performance_thresholds['acceptable_memory_mb']:
                categories['acceptable'] += 1
            else:
                categories['poor'] += 1
        
        return categories
    
    def _categorize_cpu_performance(self, cpu_usage: List[float]) -> Dict[str, int]:
        """Categorize CPU performance"""
        categories = {
            'excellent': 0,  # < 10%
            'good': 0,       # 10-25%
            'acceptable': 0, # 25-50%
            'poor': 0        # > 50%
        }
        
        for cpu in cpu_usage:
            if cpu < self.performance_thresholds['excellent_cpu_percent']:
                categories['excellent'] += 1
            elif cpu < self.performance_thresholds['good_cpu_percent']:
                categories['good'] += 1
            elif cpu < self.performance_thresholds['acceptable_cpu_percent']:
                categories['acceptable'] += 1
            else:
                categories['poor'] += 1
        
        return categories
    
    def _identify_slow_queries(self, results: List[BenchmarkResult], 
                             latencies: List[float]) -> List[Dict[str, Any]]:
        """Identify slow queries"""
        if not latencies:
            return []
        
        slow_threshold = self._percentile(latencies, 90)  # Top 10% slowest
        
        slow_queries = []
        for result in results:
            if result.execution_time_ms >= slow_threshold:
                slow_queries.append({
                    'query_id': result.query.id,
                    'query_text': result.query.query_text[:100] + '...',
                    'execution_time_ms': result.execution_time_ms,
                    'percentile': 90,
                    'query_type': result.query.query_type,
                    'difficulty_level': result.query.difficulty_level
                })
        
        return slow_queries
    
    def _calculate_memory_efficiency(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate memory efficiency metrics"""
        memory_usage = [r.memory_usage_mb for r in results if r.memory_usage_mb > 0]
        latencies = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        
        if not memory_usage or not latencies:
            return {}
        
        # Memory per query
        total_memory = sum(memory_usage)
        total_queries = len(memory_usage)
        
        # Memory efficiency (lower is better)
        avg_memory_per_query = total_memory / total_queries
        memory_per_second = total_memory / (sum(latencies) / 1000) if latencies else 0
        
        return {
            'avg_memory_per_query_mb': avg_memory_per_query,
            'total_memory_usage_mb': total_memory,
            'memory_per_second_mb': memory_per_second,
            'memory_efficiency_score': 1.0 / (1.0 + avg_memory_per_query / 100)  # Normalized score
        }
    
    def _calculate_cpu_efficiency(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Calculate CPU efficiency metrics"""
        cpu_usage = [r.cpu_usage_percent for r in results if r.cpu_usage_percent > 0]
        latencies = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        
        if not cpu_usage or not latencies:
            return {}
        
        # CPU efficiency metrics
        avg_cpu_per_query = sum(cpu_usage) / len(cpu_usage)
        total_cpu_time = sum(cpu_usage) * (sum(latencies) / 1000) / len(latencies)
        
        return {
            'avg_cpu_per_query_percent': avg_cpu_per_query,
            'total_cpu_time_seconds': total_cpu_time,
            'cpu_efficiency_score': 1.0 / (1.0 + avg_cpu_per_query / 50)  # Normalized score
        }
    
    def _calculate_moving_average(self, values: List[float], window_size: int) -> List[float]:
        """Calculate moving average"""
        if len(values) < window_size:
            return values
        
        moving_avg = []
        for i in range(len(values) - window_size + 1):
            window = values[i:i + window_size]
            moving_avg.append(statistics.mean(window))
        
        return moving_avg
    
    def _detect_performance_degradation(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Detect performance degradation within execution"""
        if len(results) < 10:
            return {'detected': False, 'reason': 'Insufficient data'}
        
        # Split into first half and second half
        mid_point = len(results) // 2
        first_half = results[:mid_point]
        second_half = results[mid_point:]
        
        first_half_latencies = [r.execution_time_ms for r in first_half if r.execution_time_ms > 0]
        second_half_latencies = [r.execution_time_ms for r in second_half if r.execution_time_ms > 0]
        
        if not first_half_latencies or not second_half_latencies:
            return {'detected': False, 'reason': 'No latency data'}
        
        first_half_avg = statistics.mean(first_half_latencies)
        second_half_avg = statistics.mean(second_half_latencies)
        
        degradation_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        
        return {
            'detected': degradation_percent > 20,  # 20% degradation threshold
            'degradation_percent': degradation_percent,
            'first_half_avg_ms': first_half_avg,
            'second_half_avg_ms': second_half_avg,
            'severity': 'high' if degradation_percent > 50 else 'medium' if degradation_percent > 20 else 'low'
        }
    
    def _calculate_consistency_score(self, results: List[BenchmarkResult]) -> float:
        """Calculate performance consistency score"""
        latencies = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        
        if len(latencies) < 2:
            return 1.0
        
        mean_latency = statistics.mean(latencies)
        std_latency = statistics.stdev(latencies)
        
        # Consistency score (lower coefficient of variation = higher consistency)
        cv = std_latency / mean_latency if mean_latency > 0 else 1.0
        consistency_score = max(0.0, 1.0 - cv)
        
        return consistency_score
    
    def _assess_bottleneck_severity(self, bottlenecks: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall bottleneck severity"""
        severity_score = 0
        issues = []
        
        # Latency bottlenecks
        if len(bottlenecks['latency_bottlenecks']) > 0:
            severity_score += 2
            issues.append(f"{len(bottlenecks['latency_bottlenecks'])} slow queries detected")
        
        # Memory bottlenecks
        if len(bottlenecks['memory_bottlenecks']) > 0:
            severity_score += 1
            issues.append(f"{len(bottlenecks['memory_bottlenecks'])} memory-intensive queries detected")
        
        # Error patterns
        if len(bottlenecks['error_patterns']) > 0:
            severity_score += 3
            issues.append(f"{len(bottlenecks['error_patterns'])} queries failed")
        
        # Determine severity level
        if severity_score >= 5:
            severity = 'critical'
        elif severity_score >= 3:
            severity = 'high'
        elif severity_score >= 1:
            severity = 'medium'
        else:
            severity = 'low'
        
        return {
            'severity': severity,
            'severity_score': severity_score,
            'issues': issues,
            'recommendation': self._get_bottleneck_recommendation(severity)
        }
    
    def _get_bottleneck_recommendation(self, severity: str) -> str:
        """Get recommendation based on bottleneck severity"""
        recommendations = {
            'critical': 'Immediate attention required. Consider system optimization or scaling.',
            'high': 'Performance issues detected. Review and optimize slow queries.',
            'medium': 'Some performance concerns. Monitor and consider optimizations.',
            'low': 'Performance is generally good. Continue monitoring.'
        }
        return recommendations.get(severity, 'Continue monitoring performance.')
    
    def _generate_performance_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on analysis"""
        recommendations = []
        
        # Latency recommendations
        latency_analysis = analysis.get('latency_analysis', {})
        if latency_analysis.get('mean_ms', 0) > 2000:
            recommendations.append("Consider optimizing slow queries - average latency exceeds 2 seconds")
        
        # Memory recommendations
        memory_analysis = analysis.get('memory_analysis', {})
        if memory_analysis.get('mean_mb', 0) > 500:
            recommendations.append("High memory usage detected - consider memory optimization")
        
        # CPU recommendations
        cpu_analysis = analysis.get('cpu_analysis', {})
        if cpu_analysis.get('mean_percent', 0) > 50:
            recommendations.append("High CPU usage detected - consider load balancing or optimization")
        
        # Bottleneck recommendations
        bottlenecks = analysis.get('bottleneck_analysis', {})
        if bottlenecks.get('overall_assessment', {}).get('severity') in ['high', 'critical']:
            recommendations.append("Performance bottlenecks detected - review bottleneck analysis")
        
        return recommendations
    
    def _compare_metrics(self, baseline: Dict[str, Any], 
                        comparison: Dict[str, Any], 
                        result: Dict[str, Any]):
        """Compare metrics between baseline and comparison"""
        metrics_to_compare = [
            'latency_analysis.mean_ms',
            'memory_analysis.mean_mb',
            'cpu_analysis.mean_percent',
            'throughput_analysis.queries_per_second'
        ]
        
        for metric_path in metrics_to_compare:
            baseline_val = self._get_nested_value(baseline, metric_path)
            comparison_val = self._get_nested_value(comparison, metric_path)
            
            if baseline_val is not None and comparison_val is not None:
                difference = comparison_val - baseline_val
                percent_change = (difference / baseline_val) * 100 if baseline_val != 0 else 0
                
                result['performance_differences'][metric_path] = {
                    'baseline': baseline_val,
                    'comparison': comparison_val,
                    'difference': difference,
                    'percent_change': percent_change
                }
                
                # Categorize as improvement or degradation
                if percent_change > 5:  # 5% threshold
                    result['improvements'][metric_path] = percent_change
                elif percent_change < -5:
                    result['degradations'][metric_path] = percent_change
    
    def _assess_overall_performance_change(self, baseline: Dict[str, Any], 
                                         comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall performance change"""
        improvements = 0
        degradations = 0
        
        # Count improvements and degradations
        for metric_path, data in comparison.get('performance_differences', {}).items():
            if data['percent_change'] > 5:
                improvements += 1
            elif data['percent_change'] < -5:
                degradations += 1
        
        # Determine overall assessment
        if improvements > degradations * 2:
            assessment = 'significant_improvement'
        elif improvements > degradations:
            assessment = 'improvement'
        elif degradations > improvements * 2:
            assessment = 'significant_degradation'
        elif degradations > improvements:
            assessment = 'degradation'
        else:
            assessment = 'no_change'
        
        return {
            'assessment': assessment,
            'improvements_count': improvements,
            'degradations_count': degradations,
            'overall_change_percent': self._calculate_overall_change_percent(baseline, comparison)
        }
    
    def _calculate_overall_change_percent(self, baseline: Dict[str, Any], 
                                        comparison: Dict[str, Any]) -> float:
        """Calculate overall performance change percentage"""
        # Weight different metrics
        weights = {
            'latency_analysis.mean_ms': -0.4,  # Lower is better
            'memory_analysis.mean_mb': -0.2,   # Lower is better
            'cpu_analysis.mean_percent': -0.2, # Lower is better
            'throughput_analysis.queries_per_second': 0.2  # Higher is better
        }
        
        weighted_changes = []
        for metric_path, weight in weights.items():
            baseline_val = self._get_nested_value(baseline, metric_path)
            comparison_val = self._get_nested_value(comparison, metric_path)
            
            if baseline_val is not None and comparison_val is not None and baseline_val != 0:
                change_percent = (comparison_val - baseline_val) / baseline_val * 100
                weighted_changes.append(change_percent * weight)
        
        return sum(weighted_changes) / len(weighted_changes) if weighted_changes else 0.0
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of values"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis dictionary"""
        return {
            'execution_summary': {},
            'latency_analysis': {'error': 'No data available'},
            'memory_analysis': {'error': 'No data available'},
            'cpu_analysis': {'error': 'No data available'},
            'throughput_analysis': {'error': 'No data available'},
            'performance_trends': {'error': 'No data available'},
            'bottleneck_analysis': {'error': 'No data available'},
            'recommendations': []
        }

