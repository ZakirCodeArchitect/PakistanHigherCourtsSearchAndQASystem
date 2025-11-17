"""
Django management command for processing QA Knowledge Base
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.apps import apps

from pathlib import Path
import sys

# Ensure backend/search_module is on sys.path so we can import Case models
search_module_dir = Path(__file__).resolve().parents[5] / "search_module"
project_root = search_module_dir.parent.parent  # backend/search_module -> backend

for path in (project_root, search_module_dir):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from qa_app.services.qa_knowledge_base import QAKnowledgeBaseService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process QA Knowledge Base with enhanced chunking, enrichment, and normalization for RAG'

    def add_arguments(self, parser):
        parser.add_argument(
            '--case-id',
            type=int,
            help='Process specific case ID for QA'
        )
        parser.add_argument(
            '--case-range',
            type=str,
            help='Process range of cases for QA (e.g., "1-100")'
        )
        parser.add_argument(
            '--all-cases',
            action='store_true',
            help='Process all cases for QA'
        )
        parser.add_argument(
            '--force-reprocess',
            action='store_true',
            help='Force reprocessing of already processed cases for QA'
        )
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Show QA processing statistics only'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )

    def handle(self, *args, **options):
        # Configure logging
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
            self.stdout.write(self.style.SUCCESS('Verbose logging enabled'))
        
        self.case_model = apps.get_model('cases', 'Case')
        
        # Initialize QA service
        qa_kb_service = QAKnowledgeBaseService()
        
        # Show stats only
        if options['stats_only']:
            self.show_qa_processing_stats(qa_kb_service)
            return
        
        # Process cases for QA
        if options['case_id']:
            self.process_single_case_for_qa(qa_kb_service, options['case_id'], options['force_reprocess'])
        elif options['case_range']:
            self.process_case_range_for_qa(qa_kb_service, options['case_range'], options['force_reprocess'])
        elif options['all_cases']:
            self.process_all_cases_for_qa(qa_kb_service, options['force_reprocess'])
        else:
            self.stdout.write(
                self.style.WARNING('Please specify --case-id, --case-range, or --all-cases')
            )
            self.show_qa_processing_stats(qa_kb_service)

    def process_single_case_for_qa(self, qa_kb_service, case_id, force_reprocess):
        """Process a single case for QA"""
        self.stdout.write(f'Processing case {case_id} for QA...')
        
        try:
            result = qa_kb_service.process_case_for_qa(case_id, force_reprocess)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully processed case {case_id} for QA: '
                        f'{result["qa_entries_created"]} QA entries created, '
                        f'{result["documents_processed"]} documents processed, '
                        f'{result["processing_time"]:.3f}s'
                    )
                )
                
                # Show QA metrics
                qa_metrics = result.get('qa_metrics', {})
                if qa_metrics.get('total_references', 0) > 0:
                    self.stdout.write(
                        f'  Normalized {qa_metrics["normalized_references"]} law references for QA'
                    )
                    self.stdout.write(
                        f'  Average AI context score: {qa_metrics["avg_ai_context_score"]:.3f}'
                    )
                    self.stdout.write(
                        f'  Average QA relevance: {qa_metrics["avg_qa_relevance"]:.3f}'
                    )
                
                # Show errors if any
                if result.get('errors'):
                    for error in result['errors']:
                        self.stdout.write(self.style.ERROR(f'  Error: {error}'))
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to process case {case_id} for QA: {result.get("error", "Unknown error")}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing case {case_id} for QA: {str(e)}')
            )

    def process_case_range_for_qa(self, qa_kb_service, case_range, force_reprocess):
        """Process a range of cases for QA"""
        try:
            start_id, end_id = map(int, case_range.split('-'))
            self.stdout.write(f'Processing cases {start_id} to {end_id} for QA...')
            
            total_processed = 0
            total_qa_entries = 0
            total_errors = 0
            
            for case_id in range(start_id, end_id + 1):
                try:
                    result = qa_kb_service.process_case_for_qa(case_id, force_reprocess)
                    
                    if result['success']:
                        total_processed += 1
                        total_qa_entries += result.get('qa_entries_created', 0)
                        total_errors += len(result.get('errors', []))
                        
                        if case_id % 10 == 0:  # Progress update every 10 cases
                            self.stdout.write(f'  Processed {case_id}/{end_id} cases for QA...')
                    else:
                        total_errors += 1
                        self.stdout.write(
                            self.style.WARNING(f'  Failed case {case_id}: {result.get("error", "Unknown error")}')
                        )
                        
                except Exception as e:
                    total_errors += 1
                    self.stdout.write(
                        self.style.WARNING(f'  Error processing case {case_id} for QA: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'QA range processing completed: {total_processed} cases processed, '
                    f'{total_qa_entries} QA entries created, {total_errors} errors'
                )
            )
            
        except ValueError:
            self.stdout.write(
                self.style.ERROR('Invalid case range format. Use "start-end" (e.g., "1-100")')
            )

    def process_all_cases_for_qa(self, qa_kb_service, force_reprocess):
        """Process all cases for QA"""
        self.stdout.write('Processing all cases for QA...')
        
        # Get all case IDs
        case_ids = list(self.case_model.objects.values_list('id', flat=True))
        total_cases = len(case_ids)
        
        self.stdout.write(f'Found {total_cases} cases to process for QA')
        
        total_processed = 0
        total_qa_entries = 0
        total_errors = 0
        
        for i, case_id in enumerate(case_ids, 1):
            try:
                result = qa_kb_service.process_case_for_qa(case_id, force_reprocess)
                
                if result['success']:
                    total_processed += 1
                    total_qa_entries += result.get('qa_entries_created', 0)
                    total_errors += len(result.get('errors', []))
                else:
                    total_errors += 1
                
                # Progress update
                if i % 50 == 0 or i == total_cases:
                    progress = (i / total_cases) * 100
                    self.stdout.write(
                        f'  Progress: {i}/{total_cases} ({progress:.1f}%) - '
                        f'{total_processed} processed, {total_qa_entries} QA entries, {total_errors} errors'
                    )
                    
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.WARNING(f'  Error processing case {case_id} for QA: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'All cases QA processing completed: {total_processed}/{total_cases} cases processed, '
                f'{total_qa_entries} QA entries created, {total_errors} errors'
            )
        )

    def show_qa_processing_stats(self, qa_kb_service):
        """Show QA processing statistics"""
        self.stdout.write('QA Knowledge Base Processing Statistics:')
        self.stdout.write('=' * 50)
        
        try:
            stats = qa_kb_service.get_qa_processing_stats()
            
            if 'error' in stats:
                self.stdout.write(self.style.ERROR(f'Error getting QA stats: {stats["error"]}'))
                return
            
            # QA Knowledge Base statistics
            qa_kb_stats = stats['qa_knowledge_base']
            self.stdout.write(f'QA Knowledge Base Statistics:')
            self.stdout.write(f'  Total QA entries: {qa_kb_stats["total_entries"]:,}')
            self.stdout.write(f'  Indexed QA entries: {qa_kb_stats["indexed_entries"]:,}')
            self.stdout.write(f'  Indexing coverage: {qa_kb_stats["indexing_coverage"]:.1f}%')
            
            # Case processing statistics
            case_stats = stats['case_processing']
            self.stdout.write(f'\nCase Processing Statistics:')
            self.stdout.write(f'  Total cases: {case_stats["total_cases"]:,}')
            self.stdout.write(f'  Processed cases: {case_stats["processed_cases"]:,}')
            self.stdout.write(f'  Processing coverage: {case_stats["processing_coverage"]:.1f}%')
            
            # Legal domain distribution
            self.stdout.write(f'\nLegal Domain Distribution:')
            for domain, count in stats['legal_domains'].items():
                self.stdout.write(f'  {domain}: {count:,} entries')
            
            # Quality metrics
            quality_stats = stats['quality_metrics']
            self.stdout.write(f'\nQuality Metrics:')
            self.stdout.write(f'  Average content quality: {quality_stats["avg_content_quality"]:.3f}')
            self.stdout.write(f'  Average legal relevance: {quality_stats["avg_legal_relevance"]:.3f}')
            
            self.stdout.write(f'\nLast updated: {stats["timestamp"]}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting QA processing stats: {str(e)}')
            )
