from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
import time
import logging

from apps.cases.services.legal_vocabulary_extractor import VocabularyExtractor
from apps.cases.models import Case, Term, TermOccurrence, VocabularyProcessingLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Extract legal vocabulary from case documents using high-precision rules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rules-version',
            default='1.0',
            help='Version of extraction rules (default: 1.0)'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.85,
            help='Minimum confidence threshold (default: 0.85)'
        )
        parser.add_argument(
            '--only-new',
            action='store_true',
            help='Only process cases not already processed with current rules version'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing of all cases (overrides --only-new)'
        )
        parser.add_argument(
            '--case-number',
            help='Process specific case by case number'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of cases to process'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate existing extractions, do not extract new terms'
        )
        parser.add_argument(
            '--sample-size',
            type=int,
            default=25,
            help='Sample size for validation (default: 25)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )

    def handle(self, *args, **options):
        """Handle the command execution"""
        
        if options['verbose']:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Initialize extractor
        extractor = VocabularyExtractor(
            rules_version=options['rules_version'],
            min_confidence=options['min_confidence']
        )
        
        if options['validate_only']:
            self._validate_extraction(extractor, options)
        else:
            self._extract_vocabulary(extractor, options)
    
    def _extract_vocabulary(self, extractor, options):
        """Extract vocabulary from case documents"""
        self.stdout.write(
            self.style.SUCCESS('[SYSTEM] Legal Vocabulary Extraction System')
        )
        self.stdout.write('=' * 60)
        self.stdout.write(f"Rules Version: {options['rules_version']}")
        self.stdout.write(f"Min Confidence: {options['min_confidence']}")
        self.stdout.write(f"Only New: {options['only_new']}")
        self.stdout.write(f"Force: {options['force']}")
        
        if options['case_number']:
            self.stdout.write(f"Case Number: {options['case_number']}")
        if options['limit']:
            self.stdout.write(f"Limit: {options['limit']}")
        
        self.stdout.write('')
        
        # Determine processing mode
        only_new = options['only_new'] and not options['force']
        
        if only_new:
            self.stdout.write('Processing only new cases...')
        elif options['force']:
            self.stdout.write('Force processing all cases...')
        else:
            self.stdout.write('Processing all cases...')
        
        # Get cases to process
        if options['case_number']:
            cases = Case.objects.filter(case_number=options['case_number'])
            if not cases.exists():
                raise CommandError(f"Case with number '{options['case_number']}' not found")
        else:
            if only_new:
                # Get cases not processed with current rules version
                processed_cases = VocabularyProcessingLog.objects.filter(
                    rules_version=options['rules_version']
                ).values_list('case_id', flat=True)
                cases = Case.objects.exclude(id__in=processed_cases)
            else:
                cases = Case.objects.all()
            
            if options['limit']:
                cases = cases[:options['limit']]
        
        total_cases = cases.count()
        self.stdout.write(f"Total cases to process: {total_cases}")
        
        if total_cases == 0:
            self.stdout.write(self.style.WARNING('No cases to process'))
            return
        
        # Process cases using the unified views method
        start_time = time.time()
        
        try:
            # Use the existing method that works
            stats = extractor.extract_from_unified_views(only_new=only_new)
            
            execution_time = time.time() - start_time
            
            # Display results
            self.stdout.write('')
            self.stdout.write('[STATS] Extraction Statistics:')
            self.stdout.write(f"  Total Cases: {stats.get('total_cases', 0)}")
            self.stdout.write(f"  Processed: {stats.get('processed_cases', 0)}")
            self.stdout.write(f"  Skipped: {stats.get('skipped_cases', 0)}")
            self.stdout.write(f"  Total Terms: {stats.get('total_terms', 0)}")
            self.stdout.write(f"  Execution Time: {execution_time:.2f} seconds")
            
            if stats.get('errors'):
                self.stdout.write('')
                self.stdout.write(f"[ERROR] Errors ({len(stats['errors'])}):")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    self.stdout.write(f"  - {error}")
                if len(stats['errors']) > 5:
                    self.stdout.write(f"  ... and {len(stats['errors']) - 5} more errors")
            
            # Display success message
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('[SUCCESS] Vocabulary extraction completed successfully!'))
            self.stdout.write(f"Your legal vocabulary database now contains {stats.get('total_terms', 0)} terms!")
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f"[ERROR] Extraction failed: {str(e)}"))
            raise CommandError(f'Vocabulary extraction failed: {str(e)}')
    
    def _validate_extraction(self, extractor, options):
        """Validate existing vocabulary extractions"""
        self.stdout.write(self.style.SUCCESS('[CHECK] Vocabulary Extraction Validation'))
        self.stdout.write('=' * 60)
        
        # Get sample of processed cases
        sample_size = options['sample_size']
        processed_cases = VocabularyProcessingLog.objects.filter(
            is_successful=True
        ).values_list('case_id', flat=True)[:sample_size]
        
        if not processed_cases:
            self.stdout.write(self.style.WARNING('No processed cases found for validation'))
            return
        
        cases = Case.objects.filter(id__in=processed_cases)
        self.stdout.write(f"Validating {cases.count()} cases...")
        
        # Validate extraction quality using the correct method
        validation_results = extractor.validate_extraction(sample_size=sample_size)
        
        if validation_results:
            self.stdout.write('')
            self.stdout.write('[STATS] Validation Statistics:')
            self.stdout.write(f"  Sample Size: {validation_results.get('total_occurrences', 0)}")
            self.stdout.write(f"  Mean Confidence: {validation_results.get('mean_confidence', 0):.3f}")
            
            if 'by_type' in validation_results:
                self.stdout.write('')
                self.stdout.write('[DETAILS] By Type:')
                for term_type, count in validation_results['by_type'].items():
                    self.stdout.write(f"  {term_type.title()}: {count}")
            
            if 'top_sections' in validation_results:
                self.stdout.write('')
                self.stdout.write('[TOP] Top Sections:')
                for section, count in validation_results['top_sections'][:5]:
                    self.stdout.write(f"  {section}: {count}")
            
            if 'validation_checks' in validation_results:
                self.stdout.write('')
                self.stdout.write('[CHECKS] Validation Checks:')
                checks = validation_results['validation_checks']
                for check, status in checks.items():
                    if status:
                        self.stdout.write(f"  [OK] {check.replace('_', ' ').title()}")
                    else:
                        self.style.ERROR(f"  [ERROR] {check.replace('_', ' ').title()}")
            
            if 'issues' in validation_results:
                self.stdout.write('')
                self.stdout.write(f"[ISSUES] Issues ({len(validation_results['issues'])}):")
                for issue in validation_results['issues'][:3]:
                    self.stdout.write(f"  - {issue}")
                if len(validation_results['issues']) > 3:
                    self.stdout.write(f"  ... and {len(validation_results['issues']) - 3} more")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Validation completed successfully!'))
