"""
Django management command to populate QA knowledge base from existing legal data
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from qa_app.models import QAKnowledgeBase, QAConfiguration
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate QA knowledge base with existing legal case data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of cases to process (for testing)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force repopulation even if knowledge base already has data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be populated without actually doing it'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS('Starting QA Knowledge Base Population...')
        )

        # Check if knowledge base already has data
        existing_count = QAKnowledgeBase.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Knowledge base already has {existing_count} entries. '
                    'Use --force to repopulate.'
                )
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be written')
            )

        try:
            # Create default configuration if it doesn't exist
            self.create_default_configuration(dry_run)

            # Populate knowledge base
            total_processed = self.populate_knowledge_base(limit, dry_run)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {total_processed} knowledge base entries'
                )
            )

        except Exception as e:
            logger.error(f"Error populating knowledge base: {str(e)}")
            raise CommandError(f'Failed to populate knowledge base: {str(e)}')

    def create_default_configuration(self, dry_run=False):
        """Create default QA configuration"""
        if QAConfiguration.objects.exists():
            self.stdout.write('Default QA configuration already exists')
            return

        if dry_run:
            self.stdout.write('Would create default QA configuration')
            return

        config = QAConfiguration.objects.create(
            config_name='Default QA Configuration',
            config_type='default',
            description='Default configuration for the QA system',
            config_data={
                'chunk_size': 500,
                'chunk_overlap': 50,
                'version': '1.0'
            },
            embedding_model='all-MiniLM-L6-v2',
            generation_model='gpt-3.5-turbo',
            max_tokens=1000,
            temperature=0.7,
            top_k_documents=5,
            similarity_threshold=0.7,
            max_context_length=4000,
            is_active=True,
            is_default=True
        )

        self.stdout.write(
            self.style.SUCCESS('Created default QA configuration')
        )

    def populate_knowledge_base(self, limit=None, dry_run=False):
        """Populate knowledge base with case data"""
        with connection.cursor() as cursor:
            # Get cases with their details
            query = """
                SELECT 
                    c.id as case_id,
                    c.case_number,
                    c.case_title,
                    c.status,
                    c.bench,
                    c.hearing_date,
                    ct.name as court_name,
                    cd.case_description,
                    cd.case_stage,
                    cd.short_order,
                    cd.disposed_of_status,
                    cd.case_disposal_date,
                    cd.disposal_bench,
                    cd.advocates_petitioner,
                    cd.advocates_respondent,
                    cd.fir_number,
                    cd.fir_date,
                    cd.police_station,
                    cd.under_section,
                    cd.incident,
                    cd.name_of_accused
                FROM cases c
                LEFT JOIN courts ct ON c.court_id = ct.id
                LEFT JOIN case_details cd ON c.id = cd.case_id
                ORDER BY c.id
            """
            
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            cases = cursor.fetchall()

        total_processed = 0

        for case_data in cases:
            try:
                # Extract case information
                case_id = case_data[0]
                case_number = case_data[1] or 'N/A'
                case_title = case_data[2] or 'Untitled Case'
                status = case_data[3] or 'Unknown'
                bench = case_data[4] or 'Unknown'
                hearing_date = case_data[5] or 'Unknown'
                court_name = case_data[6] or 'Unknown Court'
                case_description = case_data[7] or ''
                case_stage = case_data[8] or ''
                short_order = case_data[9] or ''
                disposed_of_status = case_data[10] or ''
                case_disposal_date = case_data[11] or ''
                disposal_bench = case_data[12] or ''
                advocates_petitioner = case_data[13] or ''
                advocates_respondent = case_data[14] or ''
                fir_number = case_data[15] or ''
                fir_date = case_data[16] or ''
                police_station = case_data[17] or ''
                under_section = case_data[18] or ''
                incident = case_data[19] or ''
                name_of_accused = case_data[20] or ''

                # Create content text
                content_parts = []
                
                # Basic case information
                content_parts.append(f"Case Number: {case_number}")
                content_parts.append(f"Case Title: {case_title}")
                content_parts.append(f"Court: {court_name}")
                content_parts.append(f"Status: {status}")
                content_parts.append(f"Bench: {bench}")
                
                if hearing_date != 'Unknown':
                    content_parts.append(f"Hearing Date: {hearing_date}")
                
                # Case description
                if case_description:
                    content_parts.append(f"Description: {case_description}")
                
                # Case stage and order
                if case_stage:
                    content_parts.append(f"Case Stage: {case_stage}")
                
                if short_order:
                    content_parts.append(f"Order: {short_order}")
                
                # Disposal information
                if disposed_of_status:
                    content_parts.append(f"Disposal Status: {disposed_of_status}")
                
                if case_disposal_date:
                    content_parts.append(f"Disposal Date: {case_disposal_date}")
                
                if disposal_bench:
                    content_parts.append(f"Disposal Bench: {disposal_bench}")
                
                # Advocates
                if advocates_petitioner:
                    content_parts.append(f"Petitioner Advocates: {advocates_petitioner}")
                
                if advocates_respondent:
                    content_parts.append(f"Respondent Advocates: {advocates_respondent}")
                
                # FIR information (for criminal cases)
                if fir_number:
                    content_parts.append(f"FIR Number: {fir_number}")
                
                if fir_date:
                    content_parts.append(f"FIR Date: {fir_date}")
                
                if police_station:
                    content_parts.append(f"Police Station: {police_station}")
                
                if under_section:
                    content_parts.append(f"Under Section: {under_section}")
                
                if incident:
                    content_parts.append(f"Incident: {incident}")
                
                if name_of_accused:
                    content_parts.append(f"Accused: {name_of_accused}")

                content_text = "\n".join(content_parts)
                
                # Create summary
                summary_parts = [case_title, status, court_name]
                if case_description:
                    summary_parts.append(case_description[:200] + "..." if len(case_description) > 200 else case_description)
                
                content_summary = " | ".join(summary_parts)

                if not dry_run:
                    # Create knowledge base entry
                    kb_entry = QAKnowledgeBase.objects.create(
                        source_type='case_metadata',
                        source_id=f'case_{case_id}',
                        source_case_id=case_id,
                        title=case_title,
                        content_text=content_text,
                        content_summary=content_summary,
                        court=court_name,
                        case_number=case_number,
                        case_title=case_title,
                        judge_name='Unknown Judge',  # Will be updated when available
                        legal_domain='General Legal',
                        legal_concepts=[],
                        legal_entities=[],
                        citations=[],
                        vector_id=f'vec_case_{case_id}',
                        embedding_model='all-MiniLM-L6-v2',
                        embedding_dimension=384,
                        content_quality_score=0.8,
                        legal_relevance_score=0.9,
                        completeness_score=0.7,
                        is_indexed=False,
                        is_processed=True,
                        processing_error='',
                        content_hash=f'hash_{case_id}'
                    )
                    
                    self.stdout.write(f"Created KB entry for case {case_number}")
                else:
                    self.stdout.write(f"Would create KB entry for case {case_number}")

                total_processed += 1

                # Process documents for this case
                self.process_case_documents(case_id, dry_run)

            except Exception as e:
                logger.error(f"Error processing case {case_id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Error processing case {case_id}: {str(e)}")
                )

        return total_processed

    def process_case_documents(self, case_id, dry_run=False):
        """Process documents associated with a case"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    d.id,
                    d.file_name,
                    dt.page_number,
                    dt.clean_text
                FROM case_documents cdoc
                JOIN documents d ON cdoc.document_id = d.id
                LEFT JOIN document_texts dt ON d.id = dt.document_id
                WHERE cdoc.case_id = %s
                ORDER BY d.id, dt.page_number
            """, [case_id])

            documents = cursor.fetchall()

        for doc_data in documents:
            try:
                doc_id = doc_data[0]
                file_name = doc_data[1]
                page_number = doc_data[2]
                clean_text = doc_data[3]

                if not clean_text:
                    continue

                # Create content for document
                content_text = f"Document: {file_name}\nPage {page_number}\n\n{clean_text}"
                content_summary = f"{file_name} - Page {page_number}"

                if not dry_run:
                    kb_entry = QAKnowledgeBase.objects.create(
                        source_type='document_text',
                        source_id=f'doc_{doc_id}_page_{page_number}',
                        source_case_id=case_id,
                        source_document_id=doc_id,
                        title=f"{file_name} - Page {page_number}",
                        content_text=content_text,
                        content_summary=content_summary,
                        court='Unknown Court',
                        case_number='N/A',
                        case_title='Document Content',
                        judge_name='Unknown Judge',
                        legal_domain='Document',
                        legal_concepts=[],
                        legal_entities=[],
                        citations=[],
                        vector_id=f'vec_doc_{doc_id}_page_{page_number}',
                        embedding_model='all-MiniLM-L6-v2',
                        embedding_dimension=384,
                        content_quality_score=0.7,
                        legal_relevance_score=0.8,
                        completeness_score=0.6,
                        is_indexed=False,
                        is_processed=True,
                        processing_error='',
                        content_hash=f'hash_doc_{doc_id}_{page_number}'
                    )
                else:
                    self.stdout.write(f"Would create document KB entry for {file_name}")

            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {str(e)}")

    def process_case_orders(self, case_id, dry_run=False):
        """Process orders for a case"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    sr_number,
                    hearing_date,
                    bench,
                    case_stage,
                    short_order,
                    disposal_date
                FROM orders_data
                WHERE case_id = %s
                ORDER BY hearing_date DESC
            """, [case_id])

            orders = cursor.fetchall()

        for order_data in orders:
            try:
                sr_number = order_data[0]
                hearing_date = order_data[1] or 'Unknown'
                bench = order_data[2] or 'Unknown'
                case_stage = order_data[3] or 'Unknown'
                short_order = order_data[4] or ''
                disposal_date = order_data[5] or ''

                if not short_order:
                    continue

                content_parts = [
                    f"Order SR Number: {sr_number}",
                    f"Hearing Date: {hearing_date}",
                    f"Bench: {bench}",
                    f"Case Stage: {case_stage}",
                    f"Order: {short_order}"
                ]

                if disposal_date:
                    content_parts.append(f"Disposal Date: {disposal_date}")

                content_text = "\n".join(content_parts)
                content_summary = f"Order {sr_number} - {short_order[:100]}..."

                if not dry_run:
                    kb_entry = QAKnowledgeBase.objects.create(
                        case_id=case_id,
                        content_type='order_text',
                        content_text=content_text,
                        content_summary=content_summary,
                        embedding_model='all-MiniLM-L6-v2',
                        embedding_dimension=384,
                        is_indexed=False,
                        is_processed=True
                    )
                else:
                    self.stdout.write(f"Would create order KB entry for SR {sr_number}")

            except Exception as e:
                logger.error(f"Error processing order {sr_number}: {str(e)}")
