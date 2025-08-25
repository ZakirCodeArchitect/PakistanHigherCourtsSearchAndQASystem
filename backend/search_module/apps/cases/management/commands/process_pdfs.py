from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import logging

from apps.cases.services.pdf_processor import PDFLinkExtractor, PDFProcessor
from apps.cases.services.unified_case_service import UnifiedCaseService
from apps.cases.models import Document, CaseDocument, DocumentText

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process PDFs from case data: download, extract text, clean, and create unified views'

    def add_arguments(self, parser):
        parser.add_argument(
            '--step',
            type=str,
            choices=['download', 'extract', 'clean', 'unified', 'all'],
            default='all',
            help='Which step to run (default: all)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of cases to process'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if already done'
        )
        parser.add_argument(
            '--case-number',
            type=str,
            help='Process specific case by case number'
        )

    def handle(self, *args, **options):
        step = options['step']
        limit = options['limit']
        force = options['force']
        case_number = options['case_number']

        self.stdout.write(
            self.style.SUCCESS(f'Starting PDF processing pipeline - Step: {step}')
        )

        try:
            if step in ['download', 'all']:
                self._download_pdfs(limit, force, case_number)

            if step in ['extract', 'all']:
                self._extract_text(limit, force, case_number)

            if step in ['clean', 'all']:
                self._clean_text(limit, force, case_number)

            if step in ['unified', 'all']:
                self._create_unified_views(limit, force, case_number)

            self.stdout.write(
                self.style.SUCCESS('PDF processing pipeline completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error in PDF processing pipeline: {str(e)}')
            )
            raise CommandError(str(e))

    def _download_pdfs(self, limit=None, force=False, case_number=None):
        """Step 1: Download PDFs from case data"""
        self.stdout.write('Step 1: Downloading PDFs...')

        extractor = PDFLinkExtractor()
        
        if case_number:
            # Process specific case
            from apps.cases.models import Case
            case = Case.objects.filter(case_number=case_number).first()
            if not case:
                raise CommandError(f"Case not found: {case_number}")
            
            # Extract PDFs for this specific case
            stats = extractor.extract_pdf_links_from_cases(limit=1)
        else:
            # Process all cases
            stats = extractor.extract_pdf_links_from_cases(limit=limit)

        self.stdout.write(
            self.style.SUCCESS(
                f'Download completed: {stats["total_documents_created"]} documents created, '
                f'{stats["total_case_documents_created"]} case-document relationships created'
            )
        )

    def _extract_text(self, limit=None, force=False, case_number=None):
        """Step 2: Extract text from downloaded PDFs"""
        self.stdout.write('Step 2: Extracting text from PDFs...')

        processor = PDFProcessor()
        
        # Get documents to process
        queryset = Document.objects.filter(is_downloaded=True)
        
        if not force:
            queryset = queryset.filter(is_processed=False)
        
        if case_number:
            # Process documents for specific case
            queryset = queryset.filter(case_documents__case__case_number=case_number)
        
        if limit:
            queryset = queryset[:limit]

        total_docs = queryset.count()
        processed_count = 0
        error_count = 0

        for document in queryset:
            try:
                if processor.extract_text_from_pdf(document):
                    processed_count += 1
                    self.stdout.write(f'✓ Extracted text from: {document.file_name}')
                else:
                    error_count += 1
                    self.stdout.write(f'✗ Failed to extract text from: {document.file_name}')
            except Exception as e:
                error_count += 1
                self.stdout.write(f'✗ Error processing {document.file_name}: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Text extraction completed: {processed_count} processed, {error_count} errors'
            )
        )

    def _clean_text(self, limit=None, force=False, case_number=None):
        """Step 3: Clean extracted text"""
        self.stdout.write('Step 3: Cleaning extracted text...')

        processor = PDFProcessor()
        
        # Get documents to clean
        queryset = Document.objects.filter(is_processed=True)
        
        if not force:
            queryset = queryset.filter(is_cleaned=False)
        
        if case_number:
            # Process documents for specific case
            queryset = queryset.filter(case_documents__case__case_number=case_number)
        
        if limit:
            queryset = queryset[:limit]

        total_docs = queryset.count()
        cleaned_count = 0
        error_count = 0

        for document in queryset:
            try:
                if processor.clean_text(document):
                    cleaned_count += 1
                    self.stdout.write(f'✓ Cleaned text from: {document.file_name}')
                else:
                    error_count += 1
                    self.stdout.write(f'✗ Failed to clean text from: {document.file_name}')
            except Exception as e:
                error_count += 1
                self.stdout.write(f'✗ Error cleaning {document.file_name}: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Text cleaning completed: {cleaned_count} cleaned, {error_count} errors'
            )
        )

    def _create_unified_views(self, limit=None, force=False, case_number=None):
        """Step 4: Create unified case views"""
        self.stdout.write('Step 4: Creating unified case views...')

        service = UnifiedCaseService()
        
        if case_number:
            # Process specific case
            from apps.cases.models import Case
            case = Case.objects.filter(case_number=case_number).first()
            if not case:
                raise CommandError(f"Case not found: {case_number}")
            
            unified_view = service.create_unified_view_for_case(case)
            self.stdout.write(
                self.style.SUCCESS(f'Created unified view for case: {case_number}')
            )
        else:
            # Process all cases
            stats = service.create_unified_views_batch(limit=limit)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Unified views completed: {stats["total_views_created"]} created, '
                    f'{stats["total_views_updated"]} updated, {stats["errors"]} errors'
                )
            )
