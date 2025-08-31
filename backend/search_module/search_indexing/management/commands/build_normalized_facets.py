"""
Django management command to build normalized facet tables
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import logging

from search_indexing.services.normalized_facet_service import NormalizedFacetService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build normalized facet tables for optimized search performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--facet-type',
            type=str,
            help='Specific facet type to build (e.g., section, judge, court)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild all facets',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up orphaned mappings after building',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting normalized facet table build...')
        )
        
        try:
            # Initialize service
            service = NormalizedFacetService()
            
            # Build normalized facets
            facet_type = options.get('facet_type')
            force = options.get('force')
            
            if force:
                self.stdout.write('🔄 Force rebuild requested - clearing existing data...')
                from search_indexing.models import FacetTerm, FacetMapping
                FacetTerm.objects.all().delete()
                FacetMapping.objects.all().delete()
            
            # Build facets
            stats = service.build_normalized_facets(facet_type=facet_type)
            
            if stats['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Normalized facets built successfully!\n'
                        f'   Facet Type: {stats["facet_type"]}\n'
                        f'   Terms Processed: {stats["terms_processed"]}\n'
                        f'   Mappings Created: {stats["mappings_created"]}'
                    )
                )
                
                # Show facet statistics
                facet_stats = service.get_facet_stats(facet_type)
                if facet_stats:
                    self.stdout.write(
                        f'\n📊 Facet Statistics:\n'
                        f'   Total Terms: {facet_stats["total_terms"]}\n'
                        f'   Total Mappings: {facet_stats["total_mappings"]}\n'
                        f'   Facet Types: {", ".join(facet_stats["facet_types"])}'
                    )
                    
                    if facet_stats['top_terms']:
                        self.stdout.write('\n🏆 Top Terms by Case Count:')
                        for i, term in enumerate(facet_stats['top_terms'][:5], 1):
                            self.stdout.write(
                                f'   {i}. {term["term"]} ({term["facet_type"]}) - '
                                f'{term["case_count"]} cases'
                            )
                
                # Cleanup if requested
                if options.get('cleanup'):
                    self.stdout.write('\n🧹 Cleaning up orphaned mappings...')
                    cleanup_stats = service.cleanup_old_mappings()
                    if cleanup_stats['success']:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ Cleanup completed: {cleanup_stats["orphaned_mappings_removed"]} '
                                f'orphaned mappings removed'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠️ Cleanup failed: {cleanup_stats.get("error", "Unknown error")}'
                            )
                        )
                
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Failed to build normalized facets:\n'
                        f'   Errors: {stats["errors"]}'
                    )
                )
                raise CommandError('Normalized facet build failed')
            
            # Calculate processing time
            processing_time = (timezone.now() - start_time).total_seconds()
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n⏱️ Processing completed in {processing_time:.2f} seconds'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Unexpected error: {str(e)}')
            )
            raise CommandError(f'Normalized facet build failed: {str(e)}')
