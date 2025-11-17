"""
Django management command to test BM25 implementation
Usage: python manage.py test_bm25
"""

from django.core.management.base import BaseCommand
from search_indexing.services.bm25_indexing import BM25IndexingService
from search_indexing.services.keyword_indexing import KeywordIndexingService


class Command(BaseCommand):
    help = 'Test BM25 implementation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--build-index',
            action='store_true',
            help='Build BM25 index before testing',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild index',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Testing BM25 Implementation'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Test 1: Initialize BM25 service
        self.stdout.write('\n1. Initializing BM25 service...')
        try:
            bm25_service = BM25IndexingService()
            self.stdout.write(self.style.SUCCESS('[OK] BM25 service initialized successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Failed to initialize BM25 service: {e}'))
            return

        # Test 2: Build index
        if options['build_index'] or options['force']:
            self.stdout.write('\n2. Building BM25 index...')
            try:
                build_stats = bm25_service.build_index(force=options['force'])
                if build_stats.get('index_built'):
                    self.stdout.write(self.style.SUCCESS('[OK] BM25 index built successfully'))
                    self.stdout.write(f'  - Documents: {build_stats.get("total_documents", 0)}')
                    self.stdout.write(f'  - Fields: {build_stats.get("total_fields", 0)}')
                    self.stdout.write(f'  - Time: {build_stats.get("processing_time", 0):.2f}s')
                else:
                    self.stdout.write(self.style.ERROR(f'[ERROR] Failed to build index: {build_stats.get("errors", [])}'))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[ERROR] Error building index: {e}'))
                import traceback
                traceback.print_exc()
                return
        else:
            self.stdout.write('\n2. Loading existing BM25 index...')
            # Try to load from cache
            if not bm25_service.index_built:
                self.stdout.write(self.style.WARNING('  Index not loaded. Use --build-index to build it.'))

        # Test 3: Search with BM25
        self.stdout.write('\n3. Testing BM25 search...')
        test_queries = [
            "criminal appeal",
            "PPC section 302",
            "murder case",
            "bail application"
        ]

        for query in test_queries:
            try:
                results = bm25_service.search(query, top_k=5)
                self.stdout.write(f'\n  Query: "{query}"')
                self.stdout.write(f'  Results: {len(results)}')
                if results:
                    for i, result in enumerate(results[:3], 1):
                        title = result.get('case_title', '')[:50]
                        if len(result.get('case_title', '')) > 50:
                            title += '...'
                        self.stdout.write(f'    {i}. Case {result.get("case_id")}: {title}')
                        self.stdout.write(f'       Score: {result.get("bm25_score", 0):.4f}')
                else:
                    self.stdout.write(self.style.WARNING('    No results found'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error searching "{query}": {e}'))

        # Test 4: Integration with KeywordIndexingService
        self.stdout.write('\n4. Testing integration with KeywordIndexingService...')
        try:
            keyword_service = KeywordIndexingService(use_bm25=True)
            results = keyword_service.search("criminal appeal", top_k=5)
            self.stdout.write(self.style.SUCCESS(f'[OK] Keyword service with BM25 returned {len(results)} results'))
            if results:
                self.stdout.write(f'  First result: Case {results[0].get("case_id")}, Score: {results[0].get("rank", 0):.4f}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error in keyword service: {e}'))
            import traceback
            traceback.print_exc()

        # Test 5: Index stats
        self.stdout.write('\n5. BM25 Index Statistics:')
        try:
            stats = bm25_service.get_index_stats()
            self.stdout.write(f'  - Index built: {stats.get("index_built")}')
            self.stdout.write(f'  - Total documents: {stats.get("total_documents", 0)}')
            self.stdout.write(f'  - Total fields: {stats.get("total_fields", 0)}')
            self.stdout.write(f'  - Field names: {", ".join(stats.get("field_names", []))}')
            self.stdout.write(f'  - Parameters: k1={stats.get("k1")}, b={stats.get("b")}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] Error getting stats: {e}'))

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('BM25 Testing Complete!'))
        self.stdout.write('=' * 60)

