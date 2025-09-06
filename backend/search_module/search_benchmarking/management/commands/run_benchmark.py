"""
Django management command to run benchmark executions
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import json
import time
from datetime import datetime

from search_benchmarking.models import (
    BenchmarkQuerySet, BenchmarkConfiguration, BenchmarkExecution
)
from search_benchmarking.services.benchmark_collector import BenchmarkCollector
from search_benchmarking.services.report_generator import ReportGenerator


class Command(BaseCommand):
    help = 'Run benchmark executions on query sets'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--query-set-id',
            type=int,
            help='ID of the benchmark query set to run'
        )
        parser.add_argument(
            '--query-set-name',
            type=str,
            help='Name of the benchmark query set to run'
        )
        parser.add_argument(
            '--configuration-id',
            type=int,
            help='ID of the benchmark configuration to use'
        )
        parser.add_argument(
            '--execution-name',
            type=str,
            help='Custom name for the execution'
        )
        parser.add_argument(
            '--search-mode',
            type=str,
            choices=['lexical', 'semantic', 'hybrid'],
            default='hybrid',
            help='Search mode to use'
        )
        parser.add_argument(
            '--ranking-algorithm',
            type=str,
            choices=['fast_ranking', 'advanced_ranking'],
            default='fast_ranking',
            help='Ranking algorithm to use'
        )
        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate a report after execution'
        )
        parser.add_argument(
            '--report-format',
            type=str,
            choices=['html', 'json'],
            default='html',
            help='Format for the generated report'
        )
        parser.add_argument(
            '--list-query-sets',
            action='store_true',
            help='List available query sets'
        )
        parser.add_argument(
            '--list-configurations',
            action='store_true',
            help='List available configurations'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        try:
            # List query sets if requested
            if options['list_query_sets']:
                self.list_query_sets()
                return
            
            # List configurations if requested
            if options['list_configurations']:
                self.list_configurations()
                return
            
            # Get query set
            query_set = self.get_query_set(options)
            if not query_set:
                raise CommandError('No valid query set specified')
            
            # Get configuration
            configuration = self.get_configuration(options)
            
            # Create execution name
            execution_name = options.get('execution_name')
            if not execution_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                execution_name = f"{query_set.name}_{timestamp}"
            
            # Run benchmark
            self.run_benchmark(query_set, configuration, execution_name, options)
            
        except Exception as e:
            raise CommandError(f'Error running benchmark: {str(e)}')
    
    def list_query_sets(self):
        """List available query sets"""
        self.stdout.write(self.style.SUCCESS('Available Query Sets:'))
        self.stdout.write('-' * 50)
        
        query_sets = BenchmarkQuerySet.objects.filter(is_active=True).order_by('name')
        
        if not query_sets:
            self.stdout.write(self.style.WARNING('No active query sets found'))
            return
        
        for qs in query_sets:
            query_count = qs.queries.filter(is_active=True).count()
            execution_count = qs.executions.count()
            
            self.stdout.write(f"ID: {qs.id}")
            self.stdout.write(f"Name: {qs.name}")
            self.stdout.write(f"Category: {qs.category}")
            self.stdout.write(f"Description: {qs.description}")
            self.stdout.write(f"Queries: {query_count}")
            self.stdout.write(f"Executions: {execution_count}")
            self.stdout.write(f"Version: {qs.version}")
            self.stdout.write('-' * 50)
    
    def list_configurations(self):
        """List available configurations"""
        self.stdout.write(self.style.SUCCESS('Available Configurations:'))
        self.stdout.write('-' * 50)
        
        configurations = BenchmarkConfiguration.objects.filter(is_active=True).order_by('name')
        
        if not configurations:
            self.stdout.write(self.style.WARNING('No active configurations found'))
            return
        
        for config in configurations:
            query_sets_count = config.query_sets.count()
            
            self.stdout.write(f"ID: {config.id}")
            self.stdout.write(f"Name: {config.name}")
            self.stdout.write(f"Description: {config.description}")
            self.stdout.write(f"Search Mode: {config.search_mode}")
            self.stdout.write(f"Ranking Algorithm: {config.ranking_algorithm}")
            self.stdout.write(f"Query Sets: {query_sets_count}")
            self.stdout.write(f"Is Default: {config.is_default}")
            self.stdout.write('-' * 50)
    
    def get_query_set(self, options):
        """Get query set from options"""
        query_set_id = options.get('query_set_id')
        query_set_name = options.get('query_set_name')
        
        if query_set_id:
            try:
                return BenchmarkQuerySet.objects.get(id=query_set_id, is_active=True)
            except BenchmarkQuerySet.DoesNotExist:
                raise CommandError(f'Query set with ID {query_set_id} not found or inactive')
        
        elif query_set_name:
            try:
                return BenchmarkQuerySet.objects.get(name=query_set_name, is_active=True)
            except BenchmarkQuerySet.DoesNotExist:
                raise CommandError(f'Query set with name "{query_set_name}" not found or inactive')
        
        return None
    
    def get_configuration(self, options):
        """Get configuration from options"""
        configuration_id = options.get('configuration_id')
        
        if configuration_id:
            try:
                return BenchmarkConfiguration.objects.get(id=configuration_id, is_active=True)
            except BenchmarkConfiguration.DoesNotExist:
                raise CommandError(f'Configuration with ID {configuration_id} not found or inactive')
        
        # Create temporary configuration from command line options
        if options.get('search_mode') or options.get('ranking_algorithm'):
            from search_benchmarking.models import BenchmarkConfiguration
            
            temp_config = BenchmarkConfiguration(
                name=f"temp_config_{int(time.time())}",
                search_mode=options.get('search_mode', 'hybrid'),
                ranking_algorithm=options.get('ranking_algorithm', 'fast_ranking'),
                is_active=False  # Temporary config
            )
            temp_config.save()
            return temp_config
        
        return None
    
    def run_benchmark(self, query_set, configuration, execution_name, options):
        """Run the benchmark execution"""
        verbose = options.get('verbose', False)
        
        self.stdout.write(self.style.SUCCESS(f'Starting benchmark execution: {execution_name}'))
        self.stdout.write(f'Query Set: {query_set.name} ({query_set.category})')
        self.stdout.write(f'Queries: {query_set.queries.filter(is_active=True).count()}')
        
        if configuration:
            self.stdout.write(f'Configuration: {configuration.name}')
            self.stdout.write(f'Search Mode: {configuration.search_mode}')
            self.stdout.write(f'Ranking Algorithm: {configuration.ranking_algorithm}')
        else:
            self.stdout.write('Using default configuration')
        
        self.stdout.write('-' * 50)
        
        # Run benchmark
        start_time = time.time()
        
        try:
            collector = BenchmarkCollector()
            execution = collector.collect_benchmark_data(
                query_set_id=query_set.id,
                configuration=configuration,
                execution_name=execution_name
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Display results
            self.stdout.write(self.style.SUCCESS('Benchmark execution completed!'))
            self.stdout.write('-' * 50)
            self.stdout.write(f'Execution ID: {execution.id}')
            self.stdout.write(f'Status: {execution.status}')
            self.stdout.write(f'Total Queries: {execution.total_queries}')
            self.stdout.write(f'Successful: {execution.successful_queries}')
            self.stdout.write(f'Failed: {execution.failed_queries}')
            self.stdout.write(f'Success Rate: {execution.success_rate:.1f}%')
            self.stdout.write(f'Total Time: {execution_time:.2f} seconds')
            self.stdout.write(f'Average Latency: {execution.average_latency_ms:.2f} ms')
            self.stdout.write(f'Average Precision@10: {execution.average_precision_at_10:.3f}')
            self.stdout.write(f'Average Recall@10: {execution.average_recall_at_10:.3f}')
            self.stdout.write(f'Average MRR: {execution.average_mrr:.3f}')
            self.stdout.write(f'Average NDCG@10: {execution.average_ndcg_at_10:.3f}')
            
            # Generate report if requested
            if options.get('generate_report'):
                self.stdout.write('-' * 50)
                self.stdout.write('Generating report...')
                
                report_generator = ReportGenerator()
                report = report_generator.generate_execution_report(
                    execution_id=execution.id,
                    report_type='detailed',
                    format=options.get('report_format', 'html')
                )
                
                self.stdout.write(self.style.SUCCESS(f'Report generated: {report.report_name}'))
                self.stdout.write(f'Report ID: {report.id}')
                self.stdout.write(f'Generated at: {report.generated_at}')
            
            # Clean up temporary configuration
            if configuration and not configuration.is_active:
                configuration.delete()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Benchmark execution failed: {str(e)}'))
            raise

