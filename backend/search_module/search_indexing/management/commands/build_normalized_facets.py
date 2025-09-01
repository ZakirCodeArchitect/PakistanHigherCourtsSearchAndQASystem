"""
Django management command to build normalized facet tables
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q
import time
import logging

from search_indexing.services.normalized_facet_service import NormalizedFacetService
from search_indexing.models import FacetTerm, FacetMapping

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build normalized facet tables for improved search performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--facet-type',
            help='Build only specific facet type (e.g., court, judge, section)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild of existing facets'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up orphaned mappings after building'
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
        
        # Initialize service
        facet_service = NormalizedFacetService()
        
        # Display header
        self.stdout.write(
            self.style.SUCCESS('[START] Starting normalized facet table build...')
        )
        self.stdout.write('=' * 60)
        
        # Check if facets already exist
        existing_facets = FacetTerm.objects.values('facet_type').distinct().count()
        if existing_facets > 0 and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_facets} existing facet types. Use --force to rebuild.'
                )
            )
            return
        
        # Build facets
        start_time = time.time()
        
        try:
            if options['facet_type']:
                # Build specific facet type
                self.stdout.write(f"Building facet type: {options['facet_type']}")
                stats = facet_service.build_specific_facet(options['facet_type'])
            else:
                # Build all facets
                self.stdout.write("Building all facet types...")
                stats = facet_service.build_normalized_facets()
            
            execution_time = time.time() - start_time
            
            # Display results
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'[SUCCESS] Normalized facets built successfully!\n'
                    f'Execution time: {execution_time:.2f} seconds'
                )
            )
            
            # Display statistics
            if stats:
                self.stdout.write('')
                self.stdout.write(
                    f'\n[STATS] Facet Statistics:\n'
                    f'  Total Facet Terms: {stats.get("total_terms", 0)}\n'
                    f'  Total Mappings: {stats.get("total_mappings", 0)}\n'
                    f'  Facet Types: {stats.get("facet_types", 0)}\n'
                    f'  Processing Time: {execution_time:.2f}s'
                )
                
                # Show breakdown by facet type
                if 'by_type' in stats:
                    self.stdout.write('')
                    self.stdout.write('  By Facet Type:')
                    for facet_type, count in stats['by_type'].items():
                        self.stdout.write(f"    {facet_type}: {count} terms")
            
            # Cleanup if requested
            if options['cleanup']:
                self.stdout.write('')
                self.stdout.write('Cleaning up orphaned mappings...')
                
                cleanup_stats = facet_service.cleanup_old_mappings()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[SUCCESS] Cleanup completed: {cleanup_stats["orphaned_mappings_removed"]} '
                        f'orphaned mappings removed'
                    )
                )
            
            # Final status
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    '[SUCCESS] Normalized facet system is ready for use!'
                )
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(
                    f'[ERROR] Failed to build normalized facets:\n'
                    f'Error: {str(e)}\n'
                    f'Execution time: {execution_time:.2f} seconds'
                )
            )
            
            # Log error
            logger.error(f'Failed to build normalized facets: {str(e)}')
            
            # Re-raise for proper error handling
            raise CommandError(f'[ERROR] Unexpected error: {str(e)}')
