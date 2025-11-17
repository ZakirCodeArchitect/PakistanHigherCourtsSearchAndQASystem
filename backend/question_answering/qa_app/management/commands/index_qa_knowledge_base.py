"""
Django management command to index QA knowledge base entries into the vector store.
"""

import logging
from django.core.management.base import BaseCommand
from django.db.models import Q

from qa_app.models import QAKnowledgeBase
from qa_app.services.qa_indexing_service import QAIndexingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Index QA knowledge base entries into the Pinecone vector store."

    def add_arguments(self, parser):
        parser.add_argument(
            '--case-id',
            type=int,
            help='Limit indexing to a specific case ID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-index entries even if already marked as indexed'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit the number of entries processed'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for queryset iteration'
        )
        parser.add_argument(
            '--include-processed',
            action='store_true',
            help='Include entries marked as processing errors'
        )

    def handle(self, *args, **options):
        case_id = options.get('case_id')
        force = options.get('force', False)
        limit = options.get('limit', 0)
        batch_size = options.get('batch_size', 50)
        include_processed = options.get('include_processed', False)

        self.stdout.write(self.style.SUCCESS("Initializing QA indexing service..."))
        indexing_service = QAIndexingService()

        if not indexing_service.rag_service.pinecone_index:
            self.stdout.write(self.style.ERROR(
                "Pinecone index is not available. Set PINECONE_API_KEY and ensure the index exists."
            ))
            return

        queryset = QAKnowledgeBase.objects.all().order_by('id')

        if case_id:
            queryset = queryset.filter(source_case_id=case_id)
            self.stdout.write(f"Filtering entries for case ID {case_id}")
        else:
            if not force:
                queryset = queryset.filter(is_indexed=False)
            if not include_processed:
                queryset = queryset.filter(Q(processing_error__isnull=True) | Q(processing_error=''))

        total_candidates = queryset.count()
        if limit and limit > 0:
            queryset = queryset[:limit]
            total_candidates = min(total_candidates, limit)

        if total_candidates == 0:
            self.stdout.write(self.style.WARNING("No QA knowledge base entries matched the criteria."))
            return

        self.stdout.write(f"Processing {total_candidates} QA entries (force={force})...")

        stats = indexing_service.index_queryset(queryset, force=force, batch_size=batch_size)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("QA Indexing Summary"))
        self.stdout.write("----------------------------------")
        self.stdout.write(f"Total evaluated : {stats['total']}")
        self.stdout.write(f"Successfully indexed : {stats['indexed']}")
        self.stdout.write(f"Skipped (already indexed) : {stats['skipped']}")
        self.stdout.write(f"Failed : {stats['failed']}")

        if stats['failed'] > 0:
            self.stdout.write(self.style.WARNING(
                "Some entries failed to index. Check logs for details or rerun with --force."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("All requested entries indexed successfully."))

