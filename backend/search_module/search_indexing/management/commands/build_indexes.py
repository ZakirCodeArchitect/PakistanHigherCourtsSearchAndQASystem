"""
Django management command for building search indexes
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from search_indexing.services.hybrid_indexing import HybridIndexingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build hybrid search indexes (vector + keyword)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild all indexes',
        )
        parser.add_argument(
            '--vector-only',
            action='store_true',
            help='Build only vector indexes',
        )
        parser.add_argument(
            '--keyword-only',
            action='store_true',
            help='Build only keyword indexes',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show index status',
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Refresh indexes incrementally',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                '\n🔍 HYBRID INDEXING SYSTEM\n'
                '===========================================================\n'
                f'\nStarted at: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            )
        )
        
        service = HybridIndexingService()
        
        if options['status']:
            self._show_status(service)
            return
        
        if options['refresh']:
            self._refresh_indexes(service)
            return
        
        self._build_indexes(service, options)
    
    def _show_status(self, service):
        """Show current index status"""
        self.stdout.write('\n📊 INDEX STATUS\n----------------------------------------')
        
        status = service.get_index_status()
        
        # Vector index status
        vector = status.get('vector_index', {})
        self.stdout.write('🧠 Vector Index:')
        self.stdout.write(f'   Built: {"✅ Yes" if vector.get("is_built", False) else "❌ No"}')
        self.stdout.write(f'   Vectors: {vector.get("total_vectors", 0)}')
        if vector.get("last_updated"):
            self.stdout.write(f'   Last Updated: {vector["last_updated"].strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Keyword index status
        keyword = status.get('keyword_index', {})
        self.stdout.write('\n🔤 Keyword Index:')
        self.stdout.write(f'   Built: {"✅ Yes" if keyword.get("is_built", False) else "❌ No"}')
        self.stdout.write(f'   Documents: {keyword.get("total_documents", 0)}')
        if keyword.get("last_updated"):
            self.stdout.write(f'   Last Updated: {keyword["last_updated"].strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Facet indexes status
        facets = status.get('facet_indexes', {})
        self.stdout.write(f'\n🏷️  Facet Indexes: {facets.get("total", 0)}')
        if facets.get("types"):
            self.stdout.write(f'   Types: {", ".join(facets["types"])}')
        
        # Search metadata status
        metadata = status.get('search_metadata', {})
        self.stdout.write(f'\n📋 Search Metadata:')
        self.stdout.write(f'   Total Records: {metadata.get("total_records", 0)}')
        self.stdout.write(f'   Indexed Records: {metadata.get("indexed_records", 0)}')
        
        # Overall status
        hybrid_ready = (
            vector.get("is_built", False) and 
            keyword.get("is_built", False) and 
            metadata.get("indexed_records", 0) > 0
        )
        
        self.stdout.write(f'\n🎯 Overall Status:')
        self.stdout.write(f'   Hybrid Ready: {"✅ Yes" if hybrid_ready else "❌ No"}')
    
    def _refresh_indexes(self, service):
        """Refresh indexes incrementally"""
        self.stdout.write('\n🔄 REFRESHING INDEXES\n----------------------------------------')
        
        stats = service.refresh_indexes(incremental=True)
        
        if stats.get('hybrid_indexed', False):
            self.stdout.write(
                self.style.SUCCESS('✅ Index refresh completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ Index refresh completed with errors')
            )
            if stats.get('errors'):
                for error in stats['errors']:
                    self.stdout.write(f'   Error: {error}')
    
    def _build_indexes(self, service, options):
        """Build indexes"""
        self.stdout.write('\n🚀 Building hybrid indexes...\n')
        
        # Determine build type
        if options['vector_only']:
            self.stdout.write('📝 Vector-only build')
        elif options['keyword_only']:
            self.stdout.write('📝 Keyword-only build')
        else:
            self.stdout.write('📝 Full hybrid build')
        
        if options['force']:
            self.stdout.write('📝 Force rebuild - all data will be reprocessed\n')
        else:
            self.stdout.write('📝 Incremental build - only new/changed data will be processed\n')
        
        # Build indexes
        stats = service.build_hybrid_index(
            force=options['force'],
            vector_only=options['vector_only'],
            keyword_only=options['keyword_only']
        )
        
        # Display results
        self.stdout.write('\n📊 HYBRID INDEXING RESULTS\n----------------------------------------')
        
        # Vector indexing results
        self.stdout.write('🧠 Vector Indexing:')
        self.stdout.write(f'   Cases Processed: {stats.get("total_cases", 0)}')
        self.stdout.write(f'   Chunks Created: {stats.get("total_chunks", 0)}')
        self.stdout.write(f'   Embeddings Created: {stats.get("total_vectors", 0)}')
        self.stdout.write(f'   Index Built: {"✅ Yes" if stats.get("vector_indexed", False) else "❌ No"}')
        
        # Keyword indexing results
        self.stdout.write('\n🔤 Keyword Indexing:')
        self.stdout.write(f'   Cases Processed: {stats.get("total_cases", 0)}')
        self.stdout.write(f'   Metadata Created: {stats.get("total_metadata", 0)}')
        self.stdout.write(f'   Facet Indexes Built: {stats.get("facet_indexes_built", 0)}')
        self.stdout.write(f'   Index Built: {"✅ Yes" if stats.get("keyword_indexed", False) else "❌ No"}')
        
        # Overall results
        self.stdout.write('\n🎯 Overall Results:')
        self.stdout.write(f'   Hybrid Index Built: {"✅ Yes" if stats.get("hybrid_indexed", False) else "❌ No"}')
        self.stdout.write(f'   Total Processing Time: {stats.get("processing_time", 0):.2f}s')
        
        if stats.get('hybrid_indexed', False):
            self.stdout.write(
                self.style.SUCCESS('\n✅ Hybrid indexing completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠️ Hybrid indexing completed with errors')
            )
            if stats.get('errors'):
                self.stdout.write('   Please check the error messages above.')
                for error in stats['errors']:
                    self.stdout.write(f'   Error: {error}')
