"""
Django management command to index the knowledge base for QA system
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from question_answering.services.knowledge_retriever import KnowledgeRetriever
from question_answering.models import QAKnowledgeBase, QAConfiguration
from apps.cases.models import Case, Document, DocumentText, UnifiedCaseView
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Index the knowledge base for the QA system using Pinecone'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reindexing of all knowledge items',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of items to process',
        )
        parser.add_argument(
            '--source-type',
            type=str,
            choices=['case_document', 'case_metadata', 'legal_text', 'judgment', 'order', 'comment'],
            help='Index only specific source type',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be indexed without actually indexing',
        )
    
    def handle(self, *args, **options):
        """Handle the command"""
        try:
            self.stdout.write(
                self.style.SUCCESS('Starting knowledge base indexing...')
            )
            
            # Initialize knowledge retriever
            knowledge_retriever = KnowledgeRetriever()
            
            # Check if Pinecone is available
            if not knowledge_retriever.pinecone_index:
                self.stdout.write(
                    self.style.WARNING('Pinecone not available, using database fallback')
                )
            
            # Get knowledge items to index
            if options['force']:
                knowledge_items = QAKnowledgeBase.objects.all()
                self.stdout.write('Force reindexing all items...')
            else:
                knowledge_items = QAKnowledgeBase.objects.filter(is_indexed=False)
                self.stdout.write('Indexing only unindexed items...')
            
            # Filter by source type if specified
            if options['source_type']:
                knowledge_items = knowledge_items.filter(source_type=options['source_type'])
                self.stdout.write(f'Filtering by source type: {options["source_type"]}')
            
            # Apply limit if specified
            if options['limit']:
                knowledge_items = knowledge_items[:options['limit']]
                self.stdout.write(f'Limited to {options["limit"]} items')
            
            total_items = knowledge_items.count()
            self.stdout.write(f'Total items to process: {total_items}')
            
            if total_items == 0:
                self.stdout.write(
                    self.style.SUCCESS('No items to index.')
                )
                return
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN - No actual indexing will be performed')
                )
                self._show_dry_run_info(knowledge_items)
                return
            
            # Start indexing
            start_time = timezone.now()
            
            # Process items in batches
            batch_size = 100
            processed_count = 0
            indexed_count = 0
            error_count = 0
            
            for i in range(0, total_items, batch_size):
                batch = knowledge_items[i:i + batch_size]
                self.stdout.write(f'Processing batch {i//batch_size + 1} ({len(batch)} items)...')
                
                for item in batch:
                    try:
                        # Generate embedding
                        embedding = knowledge_retriever.embedding_model.encode([item.content_text])[0]
                        
                        # Prepare metadata
                        metadata = {
                            'source_type': item.source_type,
                            'source_id': item.source_id,
                            'title': item.title,
                            'content': item.content_text[:1000],  # Limit content length
                            'court': item.court,
                            'case_number': item.case_number,
                            'legal_domain': item.legal_domain,
                            'case_id': item.source_case_id,
                            'document_id': item.source_document_id,
                        }
                        
                        # Prepare vector for Pinecone
                        vector_id = f"{item.source_type}_{item.source_id}"
                        
                        if knowledge_retriever.pinecone_index:
                            # Upsert to Pinecone
                            knowledge_retriever.pinecone_index.upsert(
                                vectors=[{
                                    'id': vector_id,
                                    'values': embedding.tolist(),
                                    'metadata': metadata
                                }]
                            )
                        
                        # Update item
                        item.vector_id = vector_id
                        item.is_indexed = True
                        item.indexed_at = timezone.now()
                        item.save()
                        
                        indexed_count += 1
                        
                        if indexed_count % 10 == 0:
                            self.stdout.write(f'Indexed {indexed_count} items...')
                        
                    except Exception as e:
                        logger.error(f"Error processing item {item.id}: {e}")
                        item.processing_error = str(e)
                        item.save()
                        error_count += 1
                    
                    processed_count += 1
                
                # Progress update
                progress = (processed_count / total_items) * 100
                self.stdout.write(f'Progress: {progress:.1f}% ({processed_count}/{total_items})')
            
            # Calculate results
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            success_rate = (indexed_count / total_items * 100) if total_items > 0 else 0
            
            # Display results
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('Indexing completed!'))
            self.stdout.write(f'Total items processed: {processed_count}')
            self.stdout.write(f'Successfully indexed: {indexed_count}')
            self.stdout.write(f'Errors: {error_count}')
            self.stdout.write(f'Success rate: {success_rate:.1f}%')
            self.stdout.write(f'Duration: {duration:.1f} seconds')
            self.stdout.write(f'Average time per item: {duration/processed_count:.2f} seconds')
            
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Warning: {error_count} items failed to index')
                )
            
            # Update configuration
            config, created = QAConfiguration.objects.get_or_create(
                config_name='knowledge_indexing',
                defaults={
                    'config_type': 'system',
                    'config_data': {
                        'last_indexed': end_time.isoformat(),
                        'total_items': total_items,
                        'indexed_items': indexed_count,
                        'error_count': error_count,
                        'success_rate': success_rate,
                        'duration_seconds': duration
                    }
                }
            )
            
            if not created:
                config.config_data.update({
                    'last_indexed': end_time.isoformat(),
                    'total_items': total_items,
                    'indexed_items': indexed_count,
                    'error_count': error_count,
                    'success_rate': success_rate,
                    'duration_seconds': duration
                })
                config.save()
            
        except Exception as e:
            logger.error(f"Error in knowledge base indexing: {e}")
            raise CommandError(f'Indexing failed: {e}')
    
    def _show_dry_run_info(self, knowledge_items):
        """Show dry run information"""
        self.stdout.write('\nDry run information:')
        self.stdout.write('-' * 30)
        
        # Group by source type
        source_types = {}
        for item in knowledge_items:
            source_type = item.source_type
            if source_type not in source_types:
                source_types[source_type] = 0
            source_types[source_type] += 1
        
        for source_type, count in source_types.items():
            self.stdout.write(f'{source_type}: {count} items')
        
        # Show sample items
        self.stdout.write('\nSample items to be indexed:')
        for i, item in enumerate(knowledge_items[:5]):
            self.stdout.write(f'{i+1}. {item.title[:50]}... ({item.source_type})')
        
        if len(knowledge_items) > 5:
            self.stdout.write(f'... and {len(knowledge_items) - 5} more items')
