from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.utils import timezone
import logging
import time
from typing import Dict, List, Optional

from apps.cases.services.pdf_processor import PDFLinkExtractor, PDFProcessor
from apps.cases.services.unified_case_service import UnifiedCaseService
from apps.cases.models import (
    Case, Document, CaseDocument, DocumentText, UnifiedCaseView,
    OrdersData, CommentsData, CaseCmsData, PartiesDetailData
)

logger = logging.getLogger(__name__)


class CompletePipelineCommand(BaseCommand):
    help = 'Run complete PDF processing pipeline for all cases in database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if already done'
        )
        parser.add_argument(
            '--skip-download',
            action='store_true',
            help='Skip PDF download step'
        )
        parser.add_argument(
            '--skip-extract',
            action='store_true',
            help='Skip text extraction step'
        )
        parser.add_argument(
            '--skip-clean',
            action='store_true',
            help='Skip text cleaning step'
        )
        parser.add_argument(
            '--skip-unified',
            action='store_true',
            help='Skip unified views creation step'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate current state without processing'
        )

    def handle(self, *args, **options):
        self.force = options['force']
        self.skip_download = options['skip_download']
        self.skip_extract = options['skip_extract']
        self.skip_clean = options['skip_clean']
        self.skip_unified = options['skip_unified']
        self.validate_only = options['validate_only']

        self.start_time = time.time()
        self.pipeline_stats = {
            'total_cases': 0,
            'cases_with_pdfs': 0,
            'cases_with_metadata': 0,
            'documents_downloaded': 0,
            'documents_processed': 0,
            'documents_cleaned': 0,
            'text_records_created': 0,
            'unified_views_created': 0,
            'errors': []
        }

        try:
            self.stdout.write(
                self.style.SUCCESS('🚀 Starting Complete PDF Processing Pipeline')
            )
            self.stdout.write('=' * 60)

            # Step 0: Validate and analyze current state
            self._validate_current_state()

            if self.validate_only:
                self._print_final_report()
                return

            # Step 1: Download PDFs
            if not self.skip_download:
                self._download_pdfs()

            # Step 2: Extract text
            if not self.skip_extract:
                self._extract_text()

            # Step 3: Clean text
            if not self.skip_clean:
                self._clean_text()

            # Step 4: Create unified views
            if not self.skip_unified:
                self._create_unified_views()

            # Final report
            self._print_final_report()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Pipeline failed: {str(e)}')
            )
            self.pipeline_stats['errors'].append(str(e))
            self._print_final_report()
            raise CommandError(str(e))

    def _validate_current_state(self):
        """Analyze current database state"""
        self.stdout.write('📊 Analyzing current database state...')

        # Count cases and their data
        self.pipeline_stats['total_cases'] = Case.objects.count()
        self.pipeline_stats['cases_with_pdfs'] = Case.objects.filter(
            case_documents__isnull=False
        ).distinct().count()
        self.pipeline_stats['cases_with_metadata'] = Case.objects.filter(
            orders_data__isnull=False
        ).distinct().count()

        # Count documents
        self.pipeline_stats['documents_downloaded'] = Document.objects.filter(
            is_downloaded=True
        ).count()
        self.pipeline_stats['documents_processed'] = Document.objects.filter(
            is_processed=True
        ).count()
        self.pipeline_stats['documents_cleaned'] = Document.objects.filter(
            is_cleaned=True
        ).count()

        # Count text records
        self.pipeline_stats['text_records_created'] = DocumentText.objects.count()

        # Count unified views
        self.pipeline_stats['unified_views_created'] = UnifiedCaseView.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f'📈 Found {self.pipeline_stats["total_cases"]} cases, '
                f'{self.pipeline_stats["cases_with_pdfs"]} with PDFs, '
                f'{self.pipeline_stats["documents_downloaded"]} documents downloaded'
            )
        )

    def _download_pdfs(self):
        """Step 1: Download PDFs from all cases"""
        self.stdout.write('\n📥 Step 1: Downloading PDFs from case data...')
        
        extractor = PDFLinkExtractor()
        
        # Get all cases that have PDF links
        cases_with_links = Case.objects.filter(
            orders_data__view_link__isnull=False
        ).distinct() | Case.objects.filter(
            comments_data__view_link__isnull=False
        ).distinct() | Case.objects.filter(
            judgement_data__pdf_url__isnull=False
        ).exclude(
            judgement_data__pdf_url=''
        ).distinct()
        
        total_cases = cases_with_links.count()
        self.stdout.write(f'Found {total_cases} cases with PDF links')

        if total_cases == 0:
            self.stdout.write(self.style.WARNING('⚠️ No cases with PDF links found'))
            return

        # Extract PDFs
        stats = extractor.extract_pdf_links_from_cases()
        
        self.pipeline_stats['documents_downloaded'] = Document.objects.filter(
            is_downloaded=True
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Download completed: {stats["total_documents_created"]} documents created, '
                f'{stats["total_case_documents_created"]} case-document relationships created'
            )
        )

    def _extract_text(self):
        """Step 2: Extract text from all downloaded PDFs"""
        self.stdout.write('\n📄 Step 2: Extracting text from PDFs...')
        
        processor = PDFProcessor()
        
        # Get all downloaded documents that need processing
        queryset = Document.objects.filter(is_downloaded=True)
        
        if not self.force:
            queryset = queryset.filter(is_processed=False)
        
        total_docs = queryset.count()
        
        if total_docs == 0:
            self.stdout.write(self.style.WARNING('⚠️ No documents to process for text extraction'))
            return

        self.stdout.write(f'Processing {total_docs} documents for text extraction...')
        
        processed_count = 0
        error_count = 0

        for i, document in enumerate(queryset, 1):
            try:
                self.stdout.write(f'Processing {i}/{total_docs}: {document.file_name}')
                
                if processor.extract_text_from_pdf(document):
                    processed_count += 1
                    self.stdout.write(f'  ✅ Extracted text from: {document.file_name}')
                else:
                    error_count += 1
                    self.stdout.write(f'  ❌ Failed to extract text from: {document.file_name}')
                    
            except Exception as e:
                error_count += 1
                error_msg = f'Error processing {document.file_name}: {str(e)}'
                self.stdout.write(f'  ❌ {error_msg}')
                self.pipeline_stats['errors'].append(error_msg)

        self.pipeline_stats['documents_processed'] = Document.objects.filter(
            is_processed=True
        ).count()
        self.pipeline_stats['text_records_created'] = DocumentText.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Text extraction completed: {processed_count} processed, {error_count} errors'
            )
        )

    def _clean_text(self):
        """Step 3: Clean all extracted text"""
        self.stdout.write('\n🧹 Step 3: Cleaning extracted text...')
        
        processor = PDFProcessor()
        
        # Get all processed documents that need cleaning
        queryset = Document.objects.filter(is_processed=True)
        
        if not self.force:
            queryset = queryset.filter(is_cleaned=False)
        
        total_docs = queryset.count()
        
        if total_docs == 0:
            self.stdout.write(self.style.WARNING('⚠️ No documents to clean'))
            return

        self.stdout.write(f'Cleaning {total_docs} documents...')
        
        cleaned_count = 0
        error_count = 0

        for i, document in enumerate(queryset, 1):
            try:
                self.stdout.write(f'Cleaning {i}/{total_docs}: {document.file_name}')
                
                if processor.clean_text(document):
                    cleaned_count += 1
                    self.stdout.write(f'  ✅ Cleaned text from: {document.file_name}')
                else:
                    error_count += 1
                    self.stdout.write(f'  ❌ Failed to clean text from: {document.file_name}')
                    
            except Exception as e:
                error_count += 1
                error_msg = f'Error cleaning {document.file_name}: {str(e)}'
                self.stdout.write(f'  ❌ {error_msg}')
                self.pipeline_stats['errors'].append(error_msg)

        self.pipeline_stats['documents_cleaned'] = Document.objects.filter(
            is_cleaned=True
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Text cleaning completed: {cleaned_count} cleaned, {error_count} errors'
            )
        )

    def _create_unified_views(self):
        """Step 4: Create unified views for all cases"""
        self.stdout.write('\n🔗 Step 4: Creating unified case views...')
        
        service = UnifiedCaseService()
        
        # Get all cases
        total_cases = Case.objects.count()
        
        if total_cases == 0:
            self.stdout.write(self.style.WARNING('⚠️ No cases found in database'))
            return

        self.stdout.write(f'Creating unified views for {total_cases} cases...')
        
        # Process all cases
        stats = service.create_unified_views_batch()
        
        self.pipeline_stats['unified_views_created'] = UnifiedCaseView.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Unified views completed: {stats["total_views_created"]} created, '
                f'{stats["total_views_updated"]} updated, {stats["errors"]} errors'
            )
        )

    def _print_final_report(self):
        """Print comprehensive final report"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📊 COMPLETE PIPELINE REPORT'))
        self.stdout.write('=' * 60)
        
        # Update final statistics
        self._validate_current_state()
        
        # Calculate processing time
        processing_time = time.time() - self.start_time
        
        # Print statistics
        self.stdout.write(f'\n📈 DATABASE STATISTICS:')
        self.stdout.write(f'  • Total cases: {self.pipeline_stats["total_cases"]}')
        self.stdout.write(f'  • Cases with PDFs: {self.pipeline_stats["cases_with_pdfs"]}')
        self.stdout.write(f'  • Cases with metadata: {self.pipeline_stats["cases_with_metadata"]}')
        self.stdout.write(f'  • Documents downloaded: {self.pipeline_stats["documents_downloaded"]}')
        self.stdout.write(f'  • Documents processed: {self.pipeline_stats["documents_processed"]}')
        self.stdout.write(f'  • Documents cleaned: {self.pipeline_stats["documents_cleaned"]}')
        self.stdout.write(f'  • Text records created: {self.pipeline_stats["text_records_created"]}')
        self.stdout.write(f'  • Unified views created: {self.pipeline_stats["unified_views_created"]}')
        
        # Print processing time
        self.stdout.write(f'\n⏱️ PROCESSING TIME: {processing_time:.2f} seconds')
        
        # Print errors if any
        if self.pipeline_stats['errors']:
            self.stdout.write(f'\n❌ ERRORS ENCOUNTERED ({len(self.pipeline_stats["errors"])}):')
            for i, error in enumerate(self.pipeline_stats['errors'], 1):
                self.stdout.write(f'  {i}. {error}')
        else:
            self.stdout.write(f'\n✅ No errors encountered')
        
        # Print completion status
        if self.pipeline_stats['unified_views_created'] == self.pipeline_stats['total_cases']:
            self.stdout.write(f'\n🎉 PIPELINE COMPLETED SUCCESSFULLY!')
            self.stdout.write(f'   All {self.pipeline_stats["total_cases"]} cases have unified views')
        else:
            self.stdout.write(f'\n⚠️ PIPELINE COMPLETED WITH PARTIAL SUCCESS')
            self.stdout.write(f'   {self.pipeline_stats["unified_views_created"]}/{self.pipeline_stats["total_cases"]} cases have unified views')
        
        self.stdout.write('=' * 60)


class Command(CompletePipelineCommand):
    """Django management command wrapper"""
    pass
