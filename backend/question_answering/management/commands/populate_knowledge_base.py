"""
Django management command to populate the knowledge base from crawled data
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from question_answering.models import QAKnowledgeBase
from apps.cases.models import Case, Document, DocumentText, UnifiedCaseView, OrdersData, CommentsData, JudgementData
import logging
import hashlib

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate the QA knowledge base from crawled case data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force repopulation of all knowledge items',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of cases to process',
        )
        parser.add_argument(
            '--case-id',
            type=int,
            help='Process only specific case ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be populated without actually populating',
        )
        parser.add_argument(
            '--source-types',
            nargs='+',
            choices=['case_metadata', 'case_document', 'judgment', 'order', 'comment'],
            default=['case_metadata', 'case_document', 'judgment', 'order', 'comment'],
            help='Types of knowledge to populate',
        )
    
    def handle(self, *args, **options):
        """Handle the command"""
        try:
            self.stdout.write(
                self.style.SUCCESS('Starting knowledge base population...')
            )
            
            # Get cases to process
            if options['case_id']:
                cases = Case.objects.filter(id=options['case_id'])
                self.stdout.write(f'Processing specific case ID: {options["case_id"]}')
            else:
                cases = Case.objects.all()
                if options['limit']:
                    cases = cases[:options['limit']]
                    self.stdout.write(f'Limited to {options["limit"]} cases')
            
            total_cases = cases.count()
            self.stdout.write(f'Total cases to process: {total_cases}')
            
            if total_cases == 0:
                self.stdout.write(
                    self.style.SUCCESS('No cases to process.')
                )
                return
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('DRY RUN - No actual population will be performed')
                )
                self._show_dry_run_info(cases, options['source_types'])
                return
            
            # Start population
            start_time = timezone.now()
            
            processed_cases = 0
            created_items = 0
            updated_items = 0
            error_count = 0
            
            for case in cases:
                try:
                    self.stdout.write(f'Processing case: {case.case_number}')
                    
                    # Process different source types
                    for source_type in options['source_types']:
                        if source_type == 'case_metadata':
                            items_created, items_updated = self._populate_case_metadata(case, options['force'])
                        elif source_type == 'case_document':
                            items_created, items_updated = self._populate_case_documents(case, options['force'])
                        elif source_type == 'judgment':
                            items_created, items_updated = self._populate_judgments(case, options['force'])
                        elif source_type == 'order':
                            items_created, items_updated = self._populate_orders(case, options['force'])
                        elif source_type == 'comment':
                            items_created, items_updated = self._populate_comments(case, options['force'])
                        
                        created_items += items_created
                        updated_items += items_updated
                    
                    processed_cases += 1
                    
                    if processed_cases % 10 == 0:
                        self.stdout.write(f'Processed {processed_cases} cases...')
                
                except Exception as e:
                    logger.error(f"Error processing case {case.id}: {e}")
                    error_count += 1
            
            # Calculate results
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            # Display results
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('Population completed!'))
            self.stdout.write(f'Total cases processed: {processed_cases}')
            self.stdout.write(f'Knowledge items created: {created_items}')
            self.stdout.write(f'Knowledge items updated: {updated_items}')
            self.stdout.write(f'Errors: {error_count}')
            self.stdout.write(f'Duration: {duration:.1f} seconds')
            self.stdout.write(f'Average time per case: {duration/processed_cases:.2f} seconds')
            
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Warning: {error_count} cases failed to process')
                )
            
        except Exception as e:
            logger.error(f"Error in knowledge base population: {e}")
            raise CommandError(f'Population failed: {e}')
    
    def _populate_case_metadata(self, case, force=False):
        """Populate case metadata knowledge"""
        created_count = 0
        updated_count = 0
        
        try:
            # Create case metadata entry
            content_text = f"Case: {case.case_title}\n"
            content_text += f"Case Number: {case.case_number}\n"
            content_text += f"Court: {case.court.name if case.court else 'Unknown'}\n"
            content_text += f"Status: {case.status}\n"
            content_text += f"Bench: {case.bench}\n"
            content_text += f"Hearing Date: {case.hearing_date}\n"
            content_text += f"Institution Date: {case.institution_date}\n"
            
            # Add case details if available
            if hasattr(case, 'case_detail'):
                detail = case.case_detail
                content_text += f"Case Description: {detail.case_description or ''}\n"
                content_text += f"Advocates Petitioner: {detail.advocates_petitioner or ''}\n"
                content_text += f"Advocates Respondent: {detail.advocates_respondent or ''}\n"
            
            # Create or update knowledge item
            knowledge_item, created = QAKnowledgeBase.objects.get_or_create(
                source_type='case_metadata',
                source_id=str(case.id),
                defaults={
                    'source_case_id': case.id,
                    'title': f"Case Metadata: {case.case_number}",
                    'content_text': content_text,
                    'content_summary': f"Metadata for case {case.case_number}",
                    'court': case.court.name if case.court else '',
                    'case_number': case.case_number,
                    'case_title': case.case_title,
                    'legal_domain': self._determine_legal_domain(case),
                    'content_quality_score': 0.8,
                    'legal_relevance_score': 0.9,
                    'completeness_score': 0.7,
                    'is_processed': True
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
                # Update existing item
                knowledge_item.content_text = content_text
                knowledge_item.case_title = case.case_title
                knowledge_item.status = case.status
                knowledge_item.save()
        
        except Exception as e:
            logger.error(f"Error populating case metadata for case {case.id}: {e}")
        
        return created_count, updated_count
    
    def _populate_case_documents(self, case, force=False):
        """Populate case document knowledge"""
        created_count = 0
        updated_count = 0
        
        try:
            # Get case documents
            case_documents = case.case_documents.all()
            
            for case_doc in case_documents:
                document = case_doc.document
                
                # Get document text
                document_texts = document.document_texts.all()
                if not document_texts.exists():
                    continue
                
                # Combine all pages
                full_text = '\n'.join([dt.clean_text or dt.raw_text for dt in document_texts])
                
                if not full_text.strip():
                    continue
                
                # Create knowledge item
                knowledge_item, created = QAKnowledgeBase.objects.get_or_create(
                    source_type='case_document',
                    source_id=f"{case.id}_{document.id}",
                    defaults={
                        'source_case_id': case.id,
                        'source_document_id': document.id,
                        'title': f"Document: {document.file_name}",
                        'content_text': full_text,
                        'content_summary': full_text[:500] + '...' if len(full_text) > 500 else full_text,
                        'court': case.court.name if case.court else '',
                        'case_number': case.case_number,
                        'case_title': case.case_title,
                        'legal_domain': self._determine_legal_domain(case),
                        'content_quality_score': 0.7,
                        'legal_relevance_score': 0.8,
                        'completeness_score': 0.6,
                        'is_processed': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        except Exception as e:
            logger.error(f"Error populating case documents for case {case.id}: {e}")
        
        return created_count, updated_count
    
    def _populate_judgments(self, case, force=False):
        """Populate judgment knowledge"""
        created_count = 0
        updated_count = 0
        
        try:
            # Get judgment data
            if hasattr(case, 'judgement_data'):
                judgment = case.judgement_data
                
                # Get judgment document if available
                if judgment.document:
                    document_texts = judgment.document.document_texts.all()
                    if document_texts.exists():
                        full_text = '\n'.join([dt.clean_text or dt.raw_text for dt in document_texts])
                        
                        if full_text.strip():
                            knowledge_item, created = QAKnowledgeBase.objects.get_or_create(
                                source_type='judgment',
                                source_id=f"{case.id}_judgment",
                                defaults={
                                    'source_case_id': case.id,
                                    'source_document_id': judgment.document.id,
                                    'title': f"Judgment: {case.case_number}",
                                    'content_text': full_text,
                                    'content_summary': full_text[:500] + '...' if len(full_text) > 500 else full_text,
                                    'court': case.court.name if case.court else '',
                                    'case_number': case.case_number,
                                    'case_title': case.case_title,
                                    'legal_domain': self._determine_legal_domain(case),
                                    'content_quality_score': 0.9,
                                    'legal_relevance_score': 0.95,
                                    'completeness_score': 0.8,
                                    'is_processed': True
                                }
                            )
                            
                            if created:
                                created_count += 1
                            else:
                                updated_count += 1
        
        except Exception as e:
            logger.error(f"Error populating judgments for case {case.id}: {e}")
        
        return created_count, updated_count
    
    def _populate_orders(self, case, force=False):
        """Populate orders knowledge"""
        created_count = 0
        updated_count = 0
        
        try:
            # Get orders data
            orders = case.orders_data.all()
            
            for order in orders:
                content_text = f"Order Details:\n"
                content_text += f"SR Number: {order.sr_number}\n"
                content_text += f"Hearing Date: {order.hearing_date}\n"
                content_text += f"Bench: {order.bench}\n"
                content_text += f"List Type: {order.list_type}\n"
                content_text += f"Case Stage: {order.case_stage}\n"
                content_text += f"Short Order: {order.short_order}\n"
                content_text += f"Disposal Date: {order.disposal_date}\n"
                
                knowledge_item, created = QAKnowledgeBase.objects.get_or_create(
                    source_type='order',
                    source_id=f"{case.id}_order_{order.sr_number}",
                    defaults={
                        'source_case_id': case.id,
                        'title': f"Order: {case.case_number} - SR {order.sr_number}",
                        'content_text': content_text,
                        'content_summary': order.short_order or content_text[:200],
                        'court': case.court.name if case.court else '',
                        'case_number': case.case_number,
                        'case_title': case.case_title,
                        'legal_domain': self._determine_legal_domain(case),
                        'content_quality_score': 0.8,
                        'legal_relevance_score': 0.85,
                        'completeness_score': 0.7,
                        'is_processed': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        except Exception as e:
            logger.error(f"Error populating orders for case {case.id}: {e}")
        
        return created_count, updated_count
    
    def _populate_comments(self, case, force=False):
        """Populate comments knowledge"""
        created_count = 0
        updated_count = 0
        
        try:
            # Get comments data
            comments = case.comments_data.all()
            
            for comment in comments:
                content_text = f"Comment Details:\n"
                content_text += f"Compliance Date: {comment.compliance_date}\n"
                content_text += f"Case Number: {comment.case_no}\n"
                content_text += f"Case Title: {comment.case_title}\n"
                content_text += f"Document Type: {comment.doc_type}\n"
                content_text += f"Parties: {comment.parties}\n"
                content_text += f"Description: {comment.description}\n"
                
                knowledge_item, created = QAKnowledgeBase.objects.get_or_create(
                    source_type='comment',
                    source_id=f"{case.id}_comment_{comment.compliance_date}",
                    defaults={
                        'source_case_id': case.id,
                        'title': f"Comment: {case.case_number} - {comment.compliance_date}",
                        'content_text': content_text,
                        'content_summary': comment.description or content_text[:200],
                        'court': case.court.name if case.court else '',
                        'case_number': case.case_number,
                        'case_title': case.case_title,
                        'legal_domain': self._determine_legal_domain(case),
                        'content_quality_score': 0.6,
                        'legal_relevance_score': 0.7,
                        'completeness_score': 0.5,
                        'is_processed': True
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        except Exception as e:
            logger.error(f"Error populating comments for case {case.id}: {e}")
        
        return created_count, updated_count
    
    def _determine_legal_domain(self, case):
        """Determine legal domain for a case"""
        case_title_lower = (case.case_title or '').lower()
        case_number_lower = (case.case_number or '').lower()
        
        if any(word in case_title_lower for word in ['criminal', 'bail', 'arrest', 'police', 'fir']):
            return 'criminal'
        elif any(word in case_title_lower for word in ['civil', 'contract', 'property', 'damages']):
            return 'civil'
        elif any(word in case_title_lower for word in ['constitutional', 'fundamental rights', 'writ']):
            return 'constitutional'
        elif any(word in case_title_lower for word in ['family', 'marriage', 'divorce', 'custody']):
            return 'family'
        elif any(word in case_title_lower for word in ['commercial', 'business', 'company']):
            return 'commercial'
        elif any(word in case_title_lower for word in ['tax', 'revenue', 'customs']):
            return 'tax'
        else:
            return 'general'
    
    def _show_dry_run_info(self, cases, source_types):
        """Show dry run information"""
        self.stdout.write('\nDry run information:')
        self.stdout.write('-' * 30)
        self.stdout.write(f'Source types to populate: {", ".join(source_types)}')
        self.stdout.write(f'Total cases: {cases.count()}')
        
        # Show sample cases
        self.stdout.write('\nSample cases to be processed:')
        for i, case in enumerate(cases[:5]):
            self.stdout.write(f'{i+1}. {case.case_number} - {case.case_title[:50]}...')
        
        if cases.count() > 5:
            self.stdout.write(f'... and {cases.count() - 5} more cases')
        
        # Show estimated knowledge items
        estimated_items = 0
        for case in cases[:10]:  # Sample first 10 cases
            if 'case_metadata' in source_types:
                estimated_items += 1
            if 'case_document' in source_types:
                estimated_items += case.case_documents.count()
            if 'judgment' in source_types and hasattr(case, 'judgement_data'):
                estimated_items += 1
            if 'order' in source_types:
                estimated_items += case.orders_data.count()
            if 'comment' in source_types:
                estimated_items += case.comments_data.count()
        
        # Extrapolate
        if cases.count() > 10:
            estimated_items = (estimated_items / 10) * cases.count()
        
        self.stdout.write(f'\nEstimated knowledge items to be created: {int(estimated_items)}')
