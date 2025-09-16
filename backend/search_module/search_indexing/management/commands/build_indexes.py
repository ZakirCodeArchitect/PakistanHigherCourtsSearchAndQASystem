"""
Django management command for building search indexes
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import time

from search_indexing.services.hybrid_indexing import HybridIndexingService
from search_indexing.models import VectorIndex, KeywordIndex, SearchMetadata

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build and manage hybrid search indexes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vector-only',
            action='store_true',
            help='Build only vector indexes'
        )
        parser.add_argument(
            '--keyword-only',
            action='store_true',
            help='Build only keyword indexes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild of existing indexes'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current index status'
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
        
        # Show status if requested
        if options['status']:
            self._show_index_status()
            return
        
        # Build indexes
        if options['vector_only']:
            self._build_vector_indexes(options)
        elif options['keyword_only']:
            self._build_keyword_indexes(options)
        else:
            self._build_hybrid_indexes(options)
    
    def _show_index_status(self):
        """Display current index status"""
        self.stdout.write(
            '\n[CHECK] HYBRID INDEXING SYSTEM\n'
            '========================================'
        )
        
        # Vector index status
        vector_indexes = VectorIndex.objects.filter(is_active=True)
        if vector_indexes.exists():
            vector = vector_indexes.first()
            self.stdout.write('\n[STATS] INDEX STATUS\n----------------------------------------')
            self.stdout.write(f'Vector Index: {vector.index_name}')
            self.stdout.write(f'   Model: {vector.embedding_model}')
            self.stdout.write(f'   Built: {"[OK] Yes" if vector.is_built else "[ERROR] No"}')
            self.stdout.write(f'   Vectors: {vector.total_vectors}')
            self.stdout.write(f'   Active: {"Yes" if vector.is_active else "No"}')
        else:
            self.stdout.write('\n[ERROR] No active vector indexes found')
        
        # Keyword index status
        keyword_indexes = KeywordIndex.objects.filter(is_active=True)
        if keyword_indexes.exists():
            keyword = keyword_indexes.first()
            self.stdout.write(f'\nKeyword Index: {keyword.index_name}')
            self.stdout.write(f'   Documents: {keyword.total_documents}')
            self.stdout.write(f'   Built: {"[OK] Yes" if keyword.is_built else "[ERROR] No"}')
            self.stdout.write(f'   Active: {"Yes" if keyword.is_active else "No"}')
        else:
            self.stdout.write('\n[ERROR] No active keyword indexes found')
        
        # Search metadata status
        metadata_count = SearchMetadata.objects.count()
        self.stdout.write(f'\n[DETAILS] Search Metadata:')
        self.stdout.write(f'   Total Records: {metadata_count}')
        
        # Overall system status
        vector_ready = vector_indexes.filter(is_built=True).exists()
        keyword_ready = keyword_indexes.filter(is_built=True).exists()
        hybrid_ready = vector_ready and keyword_ready
        
        self.stdout.write(f'\n[STATUS] System Status:')
        self.stdout.write(f'   Vector Ready: {"[OK] Yes" if vector_ready else "[ERROR] No"}')
        self.stdout.write(f'   Keyword Ready: {"[OK] Yes" if keyword_ready else "[ERROR] No"}')
        self.stdout.write(f'   Hybrid Ready: {"[OK] Yes" if hybrid_ready else "[ERROR] No"}')
        
        if hybrid_ready:
            self.stdout.write(
                self.style.SUCCESS('\n[SUCCESS] Index refresh completed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n[WARNING] Some indexes are not ready. Run build command to fix.')
            )
    
    def _build_vector_indexes(self, options):
        """Build vector indexes only"""
        self.stdout.write('\n[START] Building vector indexes...')
        
        try:
            service = HybridIndexingService(use_pinecone=False)  # Use FAISS for local testing
            
            if options['force']:
                self.stdout.write('Force rebuild requested - clearing existing indexes...')
                VectorIndex.objects.filter(is_active=True).update(is_built=False)
            
            # Build vector index
            stats = service.build_hybrid_index(vector_only=True, force=options['force'])
            
            self.stdout.write(
                self.style.SUCCESS('[SUCCESS] Vector indexes built successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Failed to build vector indexes: {str(e)}')
            )
            raise CommandError(f'Vector index build failed: {str(e)}')
    
    def _build_keyword_indexes(self, options):
        """Build keyword indexes only"""
        self.stdout.write('\n[START] Building keyword indexes...')
        
        try:
            service = HybridIndexingService(use_pinecone=False)
            
            if options['force']:
                self.stdout.write('Force rebuild requested - clearing existing indexes...')
                KeywordIndex.objects.filter(is_active=True).update(is_built=False)
            
            # Build keyword index
            stats = service.build_hybrid_index(keyword_only=True, force=options['force'])
            
            self.stdout.write(
                self.style.SUCCESS('[SUCCESS] Keyword indexes built successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Failed to build keyword indexes: {str(e)}')
            )
            raise CommandError(f'Keyword index build failed: {str(e)}')
    
    def _build_hybrid_indexes(self, options):
        """Build complete hybrid indexing system"""
        self.stdout.write('\n[START] Building hybrid indexes...\n')
        
        start_time = time.time()
        
        try:
            service = HybridIndexingService(use_pinecone=False)  # Use FAISS for local testing
            
            if options['force']:
                self.stdout.write('Force rebuild requested - clearing existing indexes...')
                VectorIndex.objects.filter(is_active=True).update(is_built=False)
                KeywordIndex.objects.filter(is_active=True).update(is_built=False)
            
            # Build hybrid indexes
            stats = service.build_hybrid_index(force=options['force'])
            
            execution_time = time.time() - start_time
            
            # Display results
            self.stdout.write('\n[STATS] HYBRID INDEXING RESULTS\n----------------------------------------')
            
            if stats:
                self.stdout.write(f'   Vector Index: {"[OK] Yes" if stats.get("vector_indexed", False) else "[ERROR] No"}')
                self.stdout.write(f'   Keyword Index: {"[OK] Yes" if stats.get("keyword_indexed", False) else "[ERROR] No"}')
                self.stdout.write(f'   Hybrid Index: {"[OK] Yes" if stats.get("hybrid_indexed", False) else "[ERROR] No"}')
                self.stdout.write(f'   Processing Time: {execution_time:.2f} seconds')
            
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('\n[SUCCESS] Hybrid indexing completed successfully!')
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.stdout.write('')
            self.stdout.write(
                self.style.ERROR(f'[ERROR] Failed to build hybrid indexes: {str(e)}')
            )
            
            logger.error(f'Failed to build hybrid indexes: {str(e)}')
            raise CommandError(f'Hybrid index build failed: {str(e)}')
