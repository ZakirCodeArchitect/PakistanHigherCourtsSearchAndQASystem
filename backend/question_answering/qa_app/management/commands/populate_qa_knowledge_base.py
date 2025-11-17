"""
Django management command to populate QA knowledge base from existing legal data
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from qa_app.models import QAKnowledgeBase, QAConfiguration
import logging
import json

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
                    cd.name_of_accused,
                    ucv.case_metadata,
                    ucv.pdf_content_summary
                FROM cases c
                LEFT JOIN courts ct ON c.court_id = ct.id
                LEFT JOIN case_details cd ON c.id = cd.case_id
                LEFT JOIN unified_case_views ucv ON c.id = ucv.case_id
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
                case_metadata = self._parse_json_field(case_data[21])
                pdf_summary = self._parse_json_field(case_data[22])

                # Prefer values from unified metadata when available
                if case_metadata:
                    basic_info = case_metadata.get('basic_info', {}) or {}
                    case_title = basic_info.get('case_title') or case_title
                    case_number = basic_info.get('case_number') or case_number
                    status = basic_info.get('status') or status
                    bench = basic_info.get('bench') or bench
                    hearing_date = basic_info.get('hearing_date') or hearing_date
                    court_name = basic_info.get('court') or court_name

                    detail_info = case_metadata.get('case_detail', {}) or {}
                    case_description = detail_info.get('case_description') or case_description
                    case_stage = detail_info.get('case_stage') or case_stage
                    short_order = detail_info.get('short_order') or short_order
                    disposed_of_status = detail_info.get('disposed_of_status') or disposed_of_status
                    case_disposal_date = detail_info.get('case_disposal_date') or case_disposal_date
                    disposal_bench = detail_info.get('disposal_bench') or disposal_bench
                    advocates_petitioner = detail_info.get('advocates_petitioner') or advocates_petitioner
                    advocates_respondent = detail_info.get('advocates_respondent') or advocates_respondent
                    fir_number = detail_info.get('fir_number') or fir_number
                    fir_date = detail_info.get('fir_date') or fir_date
                    police_station = detail_info.get('police_station') or police_station
                    under_section = detail_info.get('under_section') or under_section
                    incident = detail_info.get('incident') or incident
                    name_of_accused = detail_info.get('name_of_accused') or name_of_accused

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

                # Unified case metadata (structured sections)
                if case_metadata:
                    content_parts.extend(self._format_case_metadata(case_metadata))

                # PDF summary insights
                if pdf_summary:
                    content_parts.extend(self._format_pdf_summary(pdf_summary))

                content_text = "\n".join(content_parts)
                
                # Create summary
                summary_parts = [case_title, status, court_name]
                if case_description:
                    summary_parts.append(case_description[:200] + "..." if len(case_description) > 200 else case_description)
                if advocates_petitioner:
                    summary_parts.append(f"P.Adv: {advocates_petitioner}")
                if advocates_respondent:
                    summary_parts.append(f"R.Adv: {advocates_respondent}")
                if fir_number:
                    summary_parts.append(f"FIR: {fir_number}")
                if under_section:
                    summary_parts.append(f"Section: {under_section}")
                
                content_summary = " | ".join(summary_parts)
                legal_entities = self._build_legal_entities(
                    court_name=court_name,
                    status=status,
                    bench=bench,
                    advocates_petitioner=advocates_petitioner,
                    advocates_respondent=advocates_respondent,
                    fir_number=fir_number,
                    fir_date=fir_date,
                    police_station=police_station,
                    under_section=under_section,
                    incident=incident,
                    name_of_accused=name_of_accused,
                    case_stage=case_stage,
                    short_order=short_order,
                    case_metadata=case_metadata,
                    pdf_summary=pdf_summary,
                )

                if not dry_run:
                    entry_defaults = {
                        'title': case_title,
                        'content_text': content_text,
                        'content_summary': content_summary,
                        'court': court_name,
                        'case_number': case_number,
                        'case_title': case_title,
                        'judge_name': 'Unknown Judge',  # Will be updated when available
                        'legal_domain': 'General Legal',
                        'legal_concepts': [],
                        'legal_entities': legal_entities,
                        'citations': [],
                        'vector_id': f'vec_case_{case_id}',
                        'embedding_model': 'all-MiniLM-L6-v2',
                        'embedding_dimension': 384,
                        'content_quality_score': 0.8,
                        'legal_relevance_score': 0.9,
                        'completeness_score': 0.7,
                        'is_indexed': False,
                        'is_processed': True,
                        'processing_error': ''
                    }

                    QAKnowledgeBase.objects.update_or_create(
                        source_type='case_metadata',
                        source_id=f'case_{case_id}',
                        defaults=entry_defaults
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
                    entry_defaults = {
                        'source_case_id': case_id,
                        'source_document_id': doc_id,
                        'title': f"{file_name} - Page {page_number}",
                        'content_text': content_text,
                        'content_summary': content_summary,
                        'court': 'Unknown Court',
                        'case_number': 'N/A',
                        'case_title': 'Document Content',
                        'judge_name': 'Unknown Judge',
                        'legal_domain': 'Document',
                        'legal_concepts': [],
                        'legal_entities': [],
                        'citations': [],
                        'vector_id': f'vec_doc_{doc_id}_page_{page_number}',
                        'embedding_model': 'all-MiniLM-L6-v2',
                        'embedding_dimension': 384,
                        'content_quality_score': 0.7,
                        'legal_relevance_score': 0.8,
                        'completeness_score': 0.6,
                        'is_indexed': False,
                        'is_processed': True,
                        'processing_error': ''
                    }

                    QAKnowledgeBase.objects.update_or_create(
                        source_type='document_text',
                        source_id=f'doc_{doc_id}_page_{page_number}',
                        defaults=entry_defaults
                    )
                else:
                    self.stdout.write(f"Would create document KB entry for {file_name}")

            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {str(e)}")

    def _parse_json_field(self, value):
        """Safely parse JSON/JSONB fields returned from the database."""
        if value in (None, '', {}):
            return {}

        try:
            if isinstance(value, memoryview):
                value = value.tobytes().decode('utf-8')
            elif isinstance(value, (bytes, bytearray)):
                value = value.decode('utf-8')

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return {}
                return json.loads(value)

            if isinstance(value, dict):
                return value

            # Attempt to convert via string representation as last resort
            return json.loads(str(value))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Unable to parse JSON field: %s", exc)
            return {}

    def _format_label(self, key: str) -> str:
        """Convert snake_case keys into human-readable labels."""
        if not key:
            return ''
        return key.replace('_', ' ').title()

    def _truncate_text(self, text: str, limit: int = 300) -> str:
        """Truncate lengthy text values for summaries."""
        if not text:
            return ''
        text = str(text)
        return text if len(text) <= limit else f"{text[:limit].rstrip()}..."

    def _format_case_metadata(self, metadata: dict) -> list:
        """Create human-readable sections from unified case metadata."""
        sections = []
        if not metadata:
            return sections

        basic_info = metadata.get('basic_info') or {}
        if basic_info:
            sections.append("Basic Information:")
            for key, value in basic_info.items():
                if value:
                    sections.append(f"- {self._format_label(key)}: {value}")

        case_detail = metadata.get('case_detail') or {}
        detail_lines = []
        for key, value in case_detail.items():
            if value:
                detail_lines.append(f"- {self._format_label(key)}: {value}")
        if detail_lines:
            sections.append("Case Detail:")
            sections.extend(detail_lines)

        orders = metadata.get('orders') or []
        if orders:
            sections.append("Recent Orders:")
            for order in orders[:5]:
                details = []
                if order.get('sr_number'):
                    details.append(f"SR {order['sr_number']}")
                if order.get('hearing_date'):
                    details.append(str(order['hearing_date']))
                if order.get('case_stage'):
                    details.append(order['case_stage'])
                if order.get('short_order'):
                    details.append(self._truncate_text(order['short_order'], 200))
                if details:
                    sections.append(f"- {' | '.join(details)}")

        comments = metadata.get('comments') or []
        if comments:
            sections.append("Recent Comments:")
            for comment in comments[:3]:
                preview = self._truncate_text(comment.get('description') or comment.get('doc_type') or '', 200)
                parts = [
                    comment.get('doc_type') or 'Comment',
                    str(comment.get('compliance_date') or ''),
                    preview
                ]
                sections.append(f"- {' | '.join(filter(None, parts))}")

        parties = metadata.get('parties') or []
        if parties:
            sections.append("Parties Involved:")
            for party in parties[:10]:
                party_parts = [
                    f"#{party.get('party_number')}" if party.get('party_number') else None,
                    party.get('party_side'),
                    party.get('party_name')
                ]
                sections.append(f"- {' | '.join(filter(None, party_parts))}")

        return sections

    def _format_pdf_summary(self, pdf_summary: dict) -> list:
        """Create readable notes from PDF content summary information."""
        sections = []
        if not pdf_summary:
            return sections

        summary_lines = []
        total_documents = pdf_summary.get('total_documents')
        total_pages = pdf_summary.get('total_pages')
        total_pages_with_text = pdf_summary.get('total_pages_with_text')
        total_pages_cleaned = pdf_summary.get('total_pages_cleaned')

        if total_documents:
            summary_lines.append(f"- Documents: {total_documents}")
        if total_pages:
            summary_lines.append(f"- Pages: {total_pages}")
        if total_pages_with_text:
            summary_lines.append(f"- Pages With Text: {total_pages_with_text}")
        if total_pages_cleaned:
            summary_lines.append(f"- Cleaned Pages: {total_pages_cleaned}")

        if summary_lines:
            sections.append("PDF Summary:")
            sections.extend(summary_lines)

        sample_texts = pdf_summary.get('sample_texts') or []
        for sample in sample_texts[:2]:
            file_name = sample.get('file_name') or 'Document Sample'
            doc_type = sample.get('document_type') or 'Unknown Type'
            text_preview = self._truncate_text(sample.get('complete_text', ''), 400)
            if text_preview:
                sections.append(f"PDF Sample ({file_name} | {doc_type}): {text_preview}")

        return sections

    def _is_meaningful(self, value) -> bool:
        """Determine whether a value carries useful information."""
        if value is None:
            return False
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return False
            return stripped.lower() not in {'unknown', 'n/a', 'none'}
        return True

    def _stringify(self, value):
        """Convert values (like dates) to serialisable strings when needed."""
        if value is None:
            return None
        return str(value)

    def _build_legal_entities(
        self,
        court_name: str,
        status: str,
        bench: str,
        advocates_petitioner: str,
        advocates_respondent: str,
        fir_number: str,
        fir_date,
        police_station: str,
        under_section: str,
        incident: str,
        name_of_accused: str,
        case_stage: str,
        short_order: str,
        case_metadata: dict,
        pdf_summary: dict,
    ) -> list:
        """Create structured entities that can be indexed alongside content."""
        entities = []

        def add_entity(entity_type: str, value):
            if not self._is_meaningful(value):
                return
            if isinstance(value, str):
                entities.append({'type': entity_type, 'value': value.strip()})
            else:
                entities.append({'type': entity_type, 'value': value})

        add_entity('court', court_name)
        add_entity('status', status)
        add_entity('bench', bench)
        add_entity('case_stage', case_stage)
        add_entity('short_order', short_order)
        add_entity('advocates_petitioner', advocates_petitioner)
        add_entity('advocates_respondent', advocates_respondent)
        add_entity('fir_number', fir_number)
        add_entity('fir_date', self._stringify(fir_date))
        add_entity('police_station', police_station)
        add_entity('under_section', under_section)
        add_entity('incident', incident)
        add_entity('accused', name_of_accused)

        if case_metadata:
            orders = case_metadata.get('orders') or []
            for order in orders[:5]:
                order_summary = {
                    'sr_number': order.get('sr_number'),
                    'hearing_date': self._stringify(order.get('hearing_date')),
                    'case_stage': order.get('case_stage'),
                    'short_order': self._truncate_text(order.get('short_order'), 250),
                }
                if any(order_summary.values()):
                    add_entity('order', order_summary)

            comments = case_metadata.get('comments') or []
            for comment in comments[:3]:
                comment_summary = {
                    'doc_type': comment.get('doc_type'),
                    'compliance_date': self._stringify(comment.get('compliance_date')),
                    'description': self._truncate_text(comment.get('description'), 250),
                }
                if any(comment_summary.values()):
                    add_entity('comment', comment_summary)

            parties = case_metadata.get('parties') or []
            key_parties = []
            for party in parties[:10]:
                party_summary = {
                    'party_name': party.get('party_name'),
                    'party_side': party.get('party_side'),
                    'party_number': party.get('party_number'),
                }
                if any(party_summary.values()):
                    key_parties.append(party_summary)
            if key_parties:
                add_entity('parties', key_parties)

        if pdf_summary:
            pdf_stats = {
                'total_documents': pdf_summary.get('total_documents'),
                'total_pages': pdf_summary.get('total_pages'),
                'total_pages_with_text': pdf_summary.get('total_pages_with_text'),
                'total_pages_cleaned': pdf_summary.get('total_pages_cleaned'),
            }
            if any(pdf_stats.values()):
                add_entity('pdf_stats', pdf_stats)

        return entities

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
