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
            self.style.SUCCESS('🏛️ Legal Vocabulary Extraction System')
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
        
        # Get cases to process
        queryset = Case.objects.all()
        
        if options['case_number']:
            queryset = queryset.filter(case_number=options['case_number'])
            if not queryset.exists():
                raise CommandError(f"Case with number '{options['case_number']}' not found")
        
        if only_new:
            # Skip cases already processed with current rules version
            processed_cases = VocabularyProcessingLog.objects.filter(
                rules_version=options['rules_version']
            ).values_list('case_id', flat=True)
            queryset = queryset.exclude(id__in=processed_cases)
        
        if options['limit']:
            queryset = queryset[:options['limit']]
        
        total_cases = queryset.count()
        
        if total_cases == 0:
            self.stdout.write(
                self.style.WARNING('⚠️ No cases to process. All cases may already be processed.')
            )
            return
        
        self.stdout.write(f"Processing {total_cases} cases for vocabulary extraction...")
        self.stdout.write('')
        
        # Extract vocabulary
        start_time = time.time()
        stats = extractor.extract_from_unified_views(only_new=only_new)
        processing_time = time.time() - start_time
        
        # Print results
        self._print_extraction_stats(stats, processing_time)
        
        # Validate extraction
        self.stdout.write('')
        self.stdout.write('🔍 Validating extraction...')
        validation_results = extractor.validate_extraction(sample_size=options['sample_size'])
        self._print_validation_stats(validation_results)
    
    def _validate_extraction(self, extractor, options):
        """Validate existing vocabulary extraction"""
        self.stdout.write(
            self.style.SUCCESS('🔍 Vocabulary Extraction Validation')
        )
        self.stdout.write('=' * 50)
        self.stdout.write(f"Rules Version: {options['rules_version']}")
        self.stdout.write(f"Sample Size: {options['sample_size']}")
        self.stdout.write('')
        
        # Check if any extractions exist
        total_occurrences = TermOccurrence.objects.count()
        if total_occurrences == 0:
            self.stdout.write(
                self.style.WARNING('⚠️ No vocabulary extractions found. Run extraction first.')
            )
            return
        
        self.stdout.write(f"Total occurrences in database: {total_occurrences}")
        self.stdout.write('')
        
        # Validate extraction
        validation_results = extractor.validate_extraction(sample_size=options['sample_size'])
        self._print_validation_stats(validation_results)
    
    def _print_extraction_stats(self, stats, processing_time):
        """Print extraction statistics"""
        self.stdout.write('📊 Extraction Statistics:')
        self.stdout.write('-' * 30)
        self.stdout.write(f"Total Cases: {stats.get('total_cases', 0)}")
        self.stdout.write(f"Processed: {stats.get('processed_cases', 0)}")
        self.stdout.write(f"Skipped: {stats.get('skipped_cases', 0)}")
        self.stdout.write(f"Total Terms Extracted: {stats.get('total_terms', 0)}")
        self.stdout.write(f"Processing Time: {processing_time:.2f} seconds")
        
        if stats.get('errors'):
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(f"❌ Errors ({len(stats['errors'])}):")
            )
            for error in stats['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f"  • {error}")
            if len(stats['errors']) > 5:
                self.stdout.write(f"  ... and {len(stats['errors']) - 5} more")
        
        if stats.get('total_terms', 0) > 0:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('✅ Vocabulary extraction completed successfully!')
            )
            self.stdout.write(f"   Extracted {stats['total_terms']} terms from {stats['processed_cases']} cases")
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('⚠️ No terms extracted. Check if cases have processed text data.')
            )
    
    def _print_validation_stats(self, validation_results):
        """Print validation statistics"""
        self.stdout.write('📊 Validation Statistics:')
        self.stdout.write('-' * 30)
        self.stdout.write(f"Sample Size: {validation_results.get('total_occurrences', 0)}")
        self.stdout.write(f"Mean Confidence: {validation_results.get('mean_confidence', 0):.3f}")
        
        # By type breakdown
        if validation_results.get('by_type'):
            self.stdout.write('')
            self.stdout.write('📋 By Type:')
            for term_type, count in validation_results['by_type'].items():
                self.stdout.write(f"  {term_type.title()}: {count}")
        
        # Top sections
        if validation_results.get('top_sections'):
            self.stdout.write('')
            self.stdout.write('📖 Top Sections:')
            for section, count in validation_results['top_sections'][:5]:
                self.stdout.write(f"  {section}: {count}")
        
        # Validation checks
        if validation_results.get('validation_checks'):
            self.stdout.write('')
            self.stdout.write('✅ Validation Checks:')
            checks = validation_results['validation_checks']
            for check, status in checks.items():
                if status:
                    self.stdout.write(f"  ✅ {check.replace('_', ' ').title()}")
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ {check.replace('_', ' ').title()}")
                    )
        
        # Issues
        if validation_results.get('issues'):
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(f"⚠️ Issues ({len(validation_results['issues'])}):")
            )
            for issue in validation_results['issues'][:3]:
                self.stdout.write(f"  • {issue}")
            if len(validation_results['issues']) > 3:
                self.stdout.write(f"  ... and {len(validation_results['issues']) - 3} more")
        
        # Overall assessment
        all_checks_passed = all(validation_results.get('validation_checks', {}).values())
        if all_checks_passed and not validation_results.get('issues'):
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('🎉 All validation checks passed!')
            )
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING('⚠️ Some validation issues found. Review the results above.')
            )
