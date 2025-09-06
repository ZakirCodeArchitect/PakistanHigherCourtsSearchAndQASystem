"""
Report Generator Service
Generates comprehensive benchmark reports in various formats.
"""

import logging
import json
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

from search_benchmarking.models import BenchmarkExecution, BenchmarkComparison, BenchmarkReport

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Service for generating benchmark reports"""
    
    def __init__(self):
        self.report_templates_dir = os.path.join(settings.BASE_DIR, 'search_benchmarking', 'templates', 'reports')
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'benchmark_reports')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be safe for filesystem"""
        # Remove or replace invalid characters for Windows/Linux filesystems
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[,;]', '_', filename)
        # Remove multiple consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def generate_execution_report(self, 
                                execution_id: int,
                                report_type: str = 'detailed',
                                format: str = 'html') -> BenchmarkReport:
        """
        Generate a comprehensive report for a benchmark execution
        
        Args:
            execution_id: ID of the benchmark execution
            report_type: Type of report ('summary', 'detailed', 'performance', 'quality')
            format: Output format ('html', 'json', 'pdf')
            
        Returns:
            BenchmarkReport object
        """
        try:
            execution = BenchmarkExecution.objects.get(id=execution_id)
            
            # Generate report data
            report_data = self._collect_execution_data(execution)
            
            # Create report record
            raw_report_name = f"{execution.execution_name}_{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            report_name = self._sanitize_filename(raw_report_name)
            report = BenchmarkReport.objects.create(
                execution=execution,
                report_name=report_name,
                report_type=report_type
            )
            
            # Generate content based on format
            if format == 'html':
                content = self._generate_html_report(report_data, report_type)
                report.report_html = content
            elif format == 'json':
                content = json.dumps(report_data, indent=2, cls=DjangoJSONEncoder)
                report.report_data = report_data
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Save report file
            filename = f"{report_name}.{format}"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            report.report_data = report_data
            report.report_pdf_path = filepath if format == 'pdf' else ''
            report.is_generated = True
            report.generated_at = timezone.now()
            report.save()
            
            logger.info(f"Report generated: {report_name}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating execution report: {str(e)}")
            raise
    
    def generate_comparison_report(self, 
                                 comparison_id: int,
                                 report_type: str = 'comparison',
                                 format: str = 'html') -> BenchmarkReport:
        """
        Generate a comparison report
        
        Args:
            comparison_id: ID of the benchmark comparison
            report_type: Type of report
            format: Output format
            
        Returns:
            BenchmarkReport object
        """
        try:
            comparison = BenchmarkComparison.objects.get(id=comparison_id)
            
            # Generate comparison data
            report_data = self._collect_comparison_data(comparison)
            
            # Create report record (use baseline execution)
            raw_report_name = f"{comparison.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            report_name = self._sanitize_filename(raw_report_name)
            report = BenchmarkReport.objects.create(
                execution=comparison.baseline_execution,
                report_name=report_name,
                report_type=report_type
            )
            
            # Generate content
            if format == 'html':
                content = self._generate_comparison_html_report(report_data)
                report.report_html = content
            elif format == 'json':
                content = json.dumps(report_data, indent=2, cls=DjangoJSONEncoder)
                report.report_data = report_data
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Save report file
            filename = f"{report_name}.{format}"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            report.report_data = report_data
            report.is_generated = True
            report.generated_at = timezone.now()
            report.save()
            
            logger.info(f"Comparison report generated: {report_name}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating comparison report: {str(e)}")
            raise
    
    def _collect_execution_data(self, execution: BenchmarkExecution) -> Dict[str, Any]:
        """Collect all data needed for execution report"""
        
        # Get execution results
        results = list(execution.results.all())
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_statistics(execution, results)
        
        # Performance analysis
        performance_analysis = self._analyze_performance_metrics(execution, results)
        
        # Quality analysis
        quality_analysis = self._analyze_quality_metrics(execution, results)
        
        # Query analysis
        query_analysis = self._analyze_query_performance(results)
        
        return {
            'execution_info': {
                'id': execution.id,
                'name': execution.execution_name,
                'description': execution.description,
                'search_mode': execution.search_mode,
                'ranking_algorithm': execution.ranking_algorithm,
                'ranking_config': execution.ranking_config,
                'status': execution.status,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration': execution.duration
            },
            'query_set_info': {
                'id': execution.query_set.id,
                'name': execution.query_set.name,
                'description': execution.query_set.description,
                'category': execution.query_set.category,
                'version': execution.query_set.version
            },
            'summary_statistics': summary_stats,
            'performance_analysis': performance_analysis,
            'quality_analysis': quality_analysis,
            'query_analysis': query_analysis,
            'generated_at': timezone.now().isoformat(),
            'report_metadata': {
                'total_queries': len(results),
                'successful_queries': len([r for r in results if r.status == 'success']),
                'failed_queries': len([r for r in results if r.status != 'success']),
                'data_collection_time': timezone.now().isoformat()
            }
        }
    
    def _collect_comparison_data(self, comparison: BenchmarkComparison) -> Dict[str, Any]:
        """Collect all data needed for comparison report"""
        
        baseline_execution = comparison.baseline_execution
        comparison_executions = list(comparison.comparison_executions.all())
        
        # Get execution data for all
        baseline_data = self._collect_execution_data(baseline_execution)
        comparison_data = []
        
        for execution in comparison_executions:
            execution_data = self._collect_execution_data(execution)
            comparison_data.append(execution_data)
        
        return {
            'comparison_info': {
                'id': comparison.id,
                'name': comparison.name,
                'description': comparison.description,
                'performance_improvement': comparison.performance_improvement,
                'quality_improvement': comparison.quality_improvement,
                'created_at': comparison.created_at
            },
            'baseline_execution': baseline_data,
            'comparison_executions': comparison_data,
            'comparison_results': comparison.comparison_results,
            'generated_at': timezone.now()
        }
    
    def _calculate_summary_statistics(self, 
                                    execution: BenchmarkExecution,
                                    results: List) -> Dict[str, Any]:
        """Calculate summary statistics for the execution"""
        
        successful_results = [r for r in results if r.status == 'success']
        
        if not successful_results:
            return {'error': 'No successful results to analyze'}
        
        # Performance statistics
        latencies = [r.execution_time_ms for r in successful_results if r.execution_time_ms > 0]
        memory_usage = [r.memory_usage_mb for r in successful_results if r.memory_usage_mb > 0]
        cpu_usage = [r.cpu_usage_percent for r in successful_results if r.cpu_usage_percent > 0]
        
        # Quality statistics
        precisions = [r.precision_at_10 for r in successful_results if r.precision_at_10 is not None]
        recalls = [r.recall_at_10 for r in successful_results if r.recall_at_10 is not None]
        mrrs = [r.mrr for r in successful_results if r.mrr is not None]
        ndcgs = [r.ndcg_at_10 for r in successful_results if r.ndcg_at_10 is not None]
        
        return {
            'performance': {
                'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
                'min_latency_ms': min(latencies) if latencies else 0,
                'max_latency_ms': max(latencies) if latencies else 0,
                'avg_memory_mb': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'avg_cpu_percent': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                'total_execution_time': execution.total_execution_time
            },
            'quality': {
                'avg_precision_at_10': sum(precisions) / len(precisions) if precisions else 0,
                'avg_recall_at_10': sum(recalls) / len(recalls) if recalls else 0,
                'avg_mrr': sum(mrrs) / len(mrrs) if mrrs else 0,
                'avg_ndcg_at_10': sum(ndcgs) / len(ndcgs) if ndcgs else 0,
                'success_rate': execution.success_rate
            },
            'counts': {
                'total_queries': execution.total_queries,
                'successful_queries': execution.successful_queries,
                'failed_queries': execution.failed_queries
            }
        }
    
    def _analyze_performance_metrics(self, 
                                   execution: BenchmarkExecution,
                                   results: List) -> Dict[str, Any]:
        """Analyze performance metrics in detail"""
        
        successful_results = [r for r in results if r.status == 'success']
        
        if not successful_results:
            return {'error': 'No successful results to analyze'}
        
        latencies = [r.execution_time_ms for r in successful_results if r.execution_time_ms > 0]
        
        # Performance categories
        excellent = len([l for l in latencies if l < 500])
        good = len([l for l in latencies if 500 <= l < 1000])
        acceptable = len([l for l in latencies if 1000 <= l < 2000])
        poor = len([l for l in latencies if l >= 2000])
        
        return {
            'latency_distribution': {
                'excellent': excellent,
                'good': good,
                'acceptable': acceptable,
                'poor': poor,
                'total': len(latencies)
            },
            'latency_percentiles': {
                'p50': self._percentile(latencies, 50),
                'p90': self._percentile(latencies, 90),
                'p95': self._percentile(latencies, 95),
                'p99': self._percentile(latencies, 99)
            },
            'throughput': {
                'queries_per_second': execution.total_queries / execution.duration if execution.duration else 0,
                'successful_queries_per_second': execution.successful_queries / execution.duration if execution.duration else 0
            }
        }
    
    def _analyze_quality_metrics(self, 
                               execution: BenchmarkExecution,
                               results: List) -> Dict[str, Any]:
        """Analyze quality metrics in detail"""
        
        successful_results = [r for r in results if r.status == 'success']
        
        if not successful_results:
            return {'error': 'No successful results to analyze'}
        
        quality_scores = [r.ranking_quality_score for r in successful_results if r.ranking_quality_score is not None]
        
        # Quality distribution
        excellent = len([s for s in quality_scores if s >= 0.8])
        good = len([s for s in quality_scores if 0.6 <= s < 0.8])
        fair = len([s for s in quality_scores if 0.4 <= s < 0.6])
        poor = len([s for s in quality_scores if s < 0.4])
        
        return {
            'quality_distribution': {
                'excellent': excellent,
                'good': good,
                'fair': fair,
                'poor': poor,
                'total': len(quality_scores)
            },
            'quality_percentiles': {
                'p50': self._percentile(quality_scores, 50),
                'p90': self._percentile(quality_scores, 90),
                'p95': self._percentile(quality_scores, 95),
                'p99': self._percentile(quality_scores, 99)
            },
            'overall_quality': {
                'mean': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                'median': self._percentile(quality_scores, 50),
                'std': self._standard_deviation(quality_scores)
            }
        }
    
    def _analyze_query_performance(self, results: List) -> Dict[str, Any]:
        """Analyze individual query performance"""
        
        successful_results = [r for r in results if r.status == 'success']
        
        if not successful_results:
            return {'error': 'No successful results to analyze'}
        
        # Find best and worst performing queries
        best_queries = sorted(successful_results, key=lambda x: x.ranking_quality_score, reverse=True)[:5]
        worst_queries = sorted(successful_results, key=lambda x: x.ranking_quality_score)[:5]
        slowest_queries = sorted(successful_results, key=lambda x: x.execution_time_ms, reverse=True)[:5]
        
        # Query type analysis
        query_types = {}
        for result in successful_results:
            query_type = result.query.query_type
            if query_type not in query_types:
                query_types[query_type] = {
                    'count': 0,
                    'avg_latency': 0,
                    'avg_quality': 0,
                    'total_latency': 0,
                    'total_quality': 0
                }
            
            query_types[query_type]['count'] += 1
            query_types[query_type]['total_latency'] += result.execution_time_ms
            query_types[query_type]['total_quality'] += result.ranking_quality_score
        
        # Calculate averages
        for query_type in query_types:
            count = query_types[query_type]['count']
            query_types[query_type]['avg_latency'] = query_types[query_type]['total_latency'] / count
            query_types[query_type]['avg_quality'] = query_types[query_type]['total_quality'] / count
        
        return {
            'best_queries': [
                {
                    'query_text': r.query.query_text[:100],
                    'quality_score': r.ranking_quality_score,
                    'execution_time_ms': r.execution_time_ms,
                    'query_type': r.query.query_type
                }
                for r in best_queries
            ],
            'worst_queries': [
                {
                    'query_text': r.query.query_text[:100],
                    'quality_score': r.ranking_quality_score,
                    'execution_time_ms': r.execution_time_ms,
                    'query_type': r.query.query_type
                }
                for r in worst_queries
            ],
            'slowest_queries': [
                {
                    'query_text': r.query.query_text[:100],
                    'execution_time_ms': r.execution_time_ms,
                    'quality_score': r.ranking_quality_score,
                    'query_type': r.query.query_type
                }
                for r in slowest_queries
            ],
            'query_type_analysis': query_types
        }
    
    def _generate_html_report(self, report_data: Dict[str, Any], report_type: str) -> str:
        """Generate HTML report content"""
        
        # Simple HTML template (in production, you'd use proper Django templates)
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Benchmark Report - {execution_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #f9f9f9; border-radius: 3px; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .poor {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Benchmark Report: {execution_name}</h1>
                <p><strong>Generated:</strong> {generated_at}</p>
                <p><strong>Search Mode:</strong> {search_mode}</p>
                <p><strong>Ranking Algorithm:</strong> {ranking_algorithm}</p>
            </div>
            
            <div class="section">
                <h2>Summary Statistics</h2>
                <div class="metric">
                    <strong>Total Queries:</strong> {total_queries}<br>
                    <strong>Successful:</strong> {successful_queries}<br>
                    <strong>Failed:</strong> {failed_queries}<br>
                    <strong>Success Rate:</strong> {success_rate}%
                </div>
                <div class="metric">
                    <strong>Avg Latency:</strong> {avg_latency_ms}ms<br>
                    <strong>Avg Precision@10:</strong> {avg_precision}<br>
                    <strong>Avg Recall@10:</strong> {avg_recall}<br>
                    <strong>Avg MRR:</strong> {avg_mrr}
                </div>
            </div>
            
            <div class="section">
                <h2>Performance Analysis</h2>
                <p>Performance distribution across query latencies:</p>
                <ul>
                    <li class="good">Excellent (&lt;500ms): {excellent_count}</li>
                    <li class="good">Good (500-1000ms): {good_count}</li>
                    <li class="warning">Acceptable (1000-2000ms): {acceptable_count}</li>
                    <li class="poor">Poor (&gt;2000ms): {poor_count}</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>Quality Analysis</h2>
                <p>Quality score distribution:</p>
                <ul>
                    <li class="good">Excellent (≥0.8): {excellent_quality}</li>
                    <li class="good">Good (0.6-0.8): {good_quality}</li>
                    <li class="warning">Fair (0.4-0.6): {fair_quality}</li>
                    <li class="poor">Poor (&lt;0.4): {poor_quality}</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Extract data for template
        execution_info = report_data.get('execution_info', {})
        summary_stats = report_data.get('summary_statistics', {})
        performance_analysis = report_data.get('performance_analysis', {})
        quality_analysis = report_data.get('quality_analysis', {})
        
        # Format the HTML
        html_content = html_template.format(
            execution_name=execution_info.get('name', 'Unknown'),
            generated_at=report_data.get('generated_at', datetime.now()),
            search_mode=execution_info.get('search_mode', 'Unknown'),
            ranking_algorithm=execution_info.get('ranking_algorithm', 'Unknown'),
            total_queries=summary_stats.get('counts', {}).get('total_queries', 0),
            successful_queries=summary_stats.get('counts', {}).get('successful_queries', 0),
            failed_queries=summary_stats.get('counts', {}).get('failed_queries', 0),
            success_rate=round(summary_stats.get('counts', {}).get('successful_queries', 0) / max(1, summary_stats.get('counts', {}).get('total_queries', 1)) * 100, 1),
            avg_latency_ms=round(summary_stats.get('performance', {}).get('avg_latency_ms', 0), 1),
            avg_precision=round(summary_stats.get('quality', {}).get('avg_precision_at_10', 0), 3),
            avg_recall=round(summary_stats.get('quality', {}).get('avg_recall_at_10', 0), 3),
            avg_mrr=round(summary_stats.get('quality', {}).get('avg_mrr', 0), 3),
            excellent_count=performance_analysis.get('latency_distribution', {}).get('excellent', 0),
            good_count=performance_analysis.get('latency_distribution', {}).get('good', 0),
            acceptable_count=performance_analysis.get('latency_distribution', {}).get('acceptable', 0),
            poor_count=performance_analysis.get('latency_distribution', {}).get('poor', 0),
            excellent_quality=quality_analysis.get('quality_distribution', {}).get('excellent', 0),
            good_quality=quality_analysis.get('quality_distribution', {}).get('good', 0),
            fair_quality=quality_analysis.get('quality_distribution', {}).get('fair', 0),
            poor_quality=quality_analysis.get('quality_distribution', {}).get('poor', 0)
        )
        
        return html_content
    
    def _generate_comparison_html_report(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML report for comparison"""
        
        # Similar to execution report but for comparisons
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Benchmark Comparison Report - {comparison_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .comparison-table {{ width: 100%; border-collapse: collapse; }}
                .comparison-table th, .comparison-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .comparison-table th {{ background-color: #f2f2f2; }}
                .improvement {{ color: green; }}
                .degradation {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Benchmark Comparison Report: {comparison_name}</h1>
                <p><strong>Generated:</strong> {generated_at}</p>
                <p><strong>Baseline:</strong> {baseline_name}</p>
                <p><strong>Comparisons:</strong> {comparison_count}</p>
            </div>
            
            <div class="section">
                <h2>Comparison Summary</h2>
                <p><strong>Performance Improvement:</strong> {performance_improvement}%</p>
                <p><strong>Quality Improvement:</strong> {quality_improvement}%</p>
            </div>
            
            <div class="section">
                <h2>Detailed Comparison</h2>
                <table class="comparison-table">
                    <tr>
                        <th>Execution</th>
                        <th>Search Mode</th>
                        <th>Ranking Algorithm</th>
                        <th>Avg Latency (ms)</th>
                        <th>Avg Precision@10</th>
                        <th>Success Rate (%)</th>
                    </tr>
                    {comparison_rows}
                </table>
            </div>
        </body>
        </html>
        """
        
        comparison_info = report_data.get('comparison_info', {})
        baseline_execution = report_data.get('baseline_execution', {})
        comparison_executions = report_data.get('comparison_executions', [])
        
        # Generate comparison rows
        comparison_rows = ""
        
        # Baseline row
        baseline_data = baseline_execution.get('summary_statistics', {})
        baseline_info = baseline_execution.get('execution_info', {})
        comparison_rows += f"""
        <tr style="background-color: #e6f3ff;">
            <td><strong>{baseline_info.get('name', 'Baseline')}</strong></td>
            <td>{baseline_info.get('search_mode', 'Unknown')}</td>
            <td>{baseline_info.get('ranking_algorithm', 'Unknown')}</td>
            <td>{baseline_data.get('performance', {}).get('avg_latency_ms', 0):.1f}</td>
            <td>{baseline_data.get('quality', {}).get('avg_precision_at_10', 0):.3f}</td>
            <td>{baseline_data.get('counts', {}).get('successful_queries', 0) / max(1, baseline_data.get('counts', {}).get('total_queries', 1)) * 100:.1f}</td>
        </tr>
        """
        
        # Comparison rows
        for execution_data in comparison_executions:
            exec_info = execution_data.get('execution_info', {})
            exec_stats = execution_data.get('summary_statistics', {})
            comparison_rows += f"""
            <tr>
                <td>{exec_info.get('name', 'Unknown')}</td>
                <td>{exec_info.get('search_mode', 'Unknown')}</td>
                <td>{exec_info.get('ranking_algorithm', 'Unknown')}</td>
                <td>{exec_stats.get('performance', {}).get('avg_latency_ms', 0):.1f}</td>
                <td>{exec_stats.get('quality', {}).get('avg_precision_at_10', 0):.3f}</td>
                <td>{exec_stats.get('counts', {}).get('successful_queries', 0) / max(1, exec_stats.get('counts', {}).get('total_queries', 1)) * 100:.1f}</td>
            </tr>
            """
        
        html_content = html_template.format(
            comparison_name=comparison_info.get('name', 'Unknown'),
            generated_at=report_data.get('generated_at', datetime.now()),
            baseline_name=baseline_info.get('name', 'Unknown'),
            comparison_count=len(comparison_executions),
            performance_improvement=comparison_info.get('performance_improvement', 0),
            quality_improvement=comparison_info.get('quality_improvement', 0),
            comparison_rows=comparison_rows
        )
        
        return html_content
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of values"""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]
    
    def _standard_deviation(self, data: List[float]) -> float:
        """Calculate standard deviation of a list of values"""
        if len(data) < 2:
            return 0.0
        
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        return variance ** 0.5

