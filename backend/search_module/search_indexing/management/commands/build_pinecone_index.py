"""
Django management command to build Pinecone vector indexes
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os

from search_indexing.services.pinecone_indexing import PineconeIndexingService


class Command(BaseCommand):
    help = 'Build Pinecone vector index for legal cases'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild of existing index',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='Pinecone API key (optional, can use environment variable)',
        )
        parser.add_argument(
            '--environment',
            type=str,
            default='gcp-starter',
            help='Pinecone environment (default: gcp-starter)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('[START] Starting Pinecone Index Building...')
        )

        # Check for API key - try command line first, then Django settings, then environment
        api_key = options['api_key']
        if not api_key:
            # Try Django settings first
            api_key = getattr(settings, 'PINECONE_API_KEY', None)
            if not api_key:
                # Fallback to environment variable
                api_key = os.getenv('PINECONE_API_KEY')
                if not api_key:
                    raise CommandError(
                        'Pinecone API key not found. Set PINECONE_API_KEY in Django settings, environment variable, or use --api-key option.'
                    )

        self.stdout.write(f'[INFO] Using Pinecone API key: {api_key[:10]}...{api_key[-10:]}')

        # Initialize Pinecone service
        pinecone_service = PineconeIndexingService()
        
        # Initialize Pinecone connection
        if not pinecone_service.initialize_pinecone(api_key, options['environment']):
            raise CommandError('Failed to initialize Pinecone connection')

        # Build index
        force = options['force']
        if force:
            self.stdout.write(
                self.style.WARNING('[WARNING] Force rebuild requested - existing vectors will be cleared')
            )

        self.stdout.write('[BUILD] Building Pinecone index...')
        
        stats = pinecone_service.build_pinecone_index(force=force)
        
        if stats['index_built']:
            self.stdout.write(
                self.style.SUCCESS('[SUCCESS] Pinecone index built successfully!')
            )
            
            # Display statistics
            self.stdout.write('\n[STATS] Indexing Statistics:')
            self.stdout.write(f'   Cases Processed: {stats["cases_processed"]}')
            self.stdout.write(f'   Chunks Created: {stats["chunks_created"]}')
            self.stdout.write(f'   Embeddings Created: {stats["embeddings_created"]}')
            self.stdout.write(f'   Vectors Uploaded: {stats["vectors_uploaded"]}')
            self.stdout.write(f'   Processing Time: {stats.get("processing_time", 0):.2f} seconds')
            
            if stats['errors']:
                self.stdout.write('\n[WARNING] Warnings/Errors:')
                for error in stats['errors']:
                    self.stdout.write(f'   • {error}')
            
            # Get index stats
            index_stats = pinecone_service.get_index_stats()
            if index_stats:
                self.stdout.write('\n[PINECONE] Pinecone Index Stats:')
                self.stdout.write(f'   Index Name: {index_stats["index_name"]}')
                self.stdout.write(f'   Dimension: {index_stats["dimension"]}')
                self.stdout.write(f'   Metric: {index_stats["metric"]}')
                self.stdout.write(f'   Total Vectors: {index_stats["total_vector_count"]}')
                self.stdout.write(f'   Index Fullness: {index_stats["index_fullness"]}')
                self.stdout.write(f'   Status: {index_stats["status"]}')
            
        else:
            self.stdout.write(
                self.style.ERROR('[ERROR] Failed to build Pinecone index')
            )
            if stats['errors']:
                for error in stats['errors']:
                    self.stdout.write(f'   • {error}')
