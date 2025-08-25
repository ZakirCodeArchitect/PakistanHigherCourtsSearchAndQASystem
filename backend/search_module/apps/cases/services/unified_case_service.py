import logging
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone

from ..models import (
    Case, CaseDetail, OrdersData, CommentsData, CaseCmsData, 
    PartiesDetailData, Document, CaseDocument, DocumentText, UnifiedCaseView
)

logger = logging.getLogger(__name__)


class UnifiedCaseService:
    """Service for creating unified case views combining metadata and PDF content"""
    
    def __init__(self):
        self.pdf_processor = None  # Will be imported when needed
    
    def create_unified_view_for_case(self, case: Case) -> UnifiedCaseView:
        """Create unified view for a single case"""
        try:
            # Check if unified view already exists
            existing_view = UnifiedCaseView.objects.filter(case=case).first()
            if existing_view:
                logger.info(f"Unified view already exists for case {case.case_number}")
                return existing_view
            
            # Build case metadata
            case_metadata = self._build_case_metadata(case)
            
            # Build PDF content summary
            pdf_content_summary = self._build_pdf_content_summary(case)
            
            # Determine status flags
            has_pdf = bool(pdf_content_summary.get('total_documents', 0) > 0)
            text_extracted = pdf_content_summary.get('total_pages_with_text', 0) > 0
            text_cleaned = pdf_content_summary.get('total_pages_cleaned', 0) > 0
            metadata_complete = self._is_metadata_complete(case_metadata)
            
            # Create unified view
            unified_view = UnifiedCaseView.objects.create(
                case=case,
                case_metadata=case_metadata,
                pdf_content_summary=pdf_content_summary,
                has_pdf=has_pdf,
                text_extracted=text_extracted,
                text_cleaned=text_cleaned,
                metadata_complete=metadata_complete,
                is_processed=True
            )
            
            logger.info(f"Created unified view for case {case.case_number}")
            return unified_view
            
        except Exception as e:
            logger.error(f"Error creating unified view for case {case.case_number}: {str(e)}")
            # Create view with error
            return UnifiedCaseView.objects.create(
                case=case,
                case_metadata={},
                pdf_content_summary={},
                processing_error=str(e)
            )
    
    def create_unified_views_batch(self, limit: int = None) -> Dict[str, int]:
        """Create unified views for multiple cases"""
        stats = {
            'total_cases_processed': 0,
            'total_views_created': 0,
            'total_views_updated': 0,
            'errors': 0
        }
        
        queryset = Case.objects.all()
        if limit:
            queryset = queryset[:limit]
        
        for case in queryset:
            try:
                stats['total_cases_processed'] += 1
                
                # Check if view exists
                existing_view = UnifiedCaseView.objects.filter(case=case).first()
                
                if existing_view:
                    # Update existing view
                    self._update_unified_view(existing_view)
                    stats['total_views_updated'] += 1
                else:
                    # Create new view
                    self.create_unified_view_for_case(case)
                    stats['total_views_created'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing case {case.case_number}: {str(e)}")
                stats['errors'] += 1
        
        return stats
    
    def _build_case_metadata(self, case: Case) -> Dict:
        """Build comprehensive case metadata from all related tables"""
        metadata = {
            'basic_info': {
                'case_number': case.case_number,
                'sr_number': case.sr_number,
                'case_title': case.case_title,
                'institution_date': case.institution_date,
                'hearing_date': case.hearing_date,
                'status': case.status,
                'bench': case.bench,
                'court': case.court.name if case.court else None,
            },
            'case_detail': {},
            'orders': [],
            'comments': [],
            'case_cms': [],
            'parties': [],
            'documents': []
        }
        
        # Add case detail information
        if hasattr(case, 'case_detail'):
            detail = case.case_detail
            metadata['case_detail'] = {
                'case_status': detail.case_status,
                'hearing_date_detailed': detail.hearing_date_detailed,
                'case_stage': detail.case_stage,
                'tentative_date': detail.tentative_date,
                'short_order': detail.short_order,
                'before_bench': detail.before_bench,
                'case_title_detailed': detail.case_title_detailed,
                'advocates_petitioner': detail.advocates_petitioner,
                'advocates_respondent': detail.advocates_respondent,
                'case_description': detail.case_description,
                'disposed_of_status': detail.disposed_of_status,
                'case_disposal_date': detail.case_disposal_date,
                'disposal_bench': detail.disposal_bench,
                'consigned_date': detail.consigned_date,
                'fir_number': detail.fir_number,
                'fir_date': detail.fir_date,
                'police_station': detail.police_station,
                'under_section': detail.under_section,
                'incident': detail.incident,
                'name_of_accused': detail.name_of_accused,
            }
        
        # Add orders data
        for order in case.orders_data.all():
            order_data = {
                'sr_number': order.sr_number,
                'hearing_date': order.hearing_date,
                'bench': order.bench,
                'list_type': order.list_type,
                'case_stage': order.case_stage,
                'short_order': order.short_order,
                'disposal_date': order.disposal_date,
                'source_type': order.source_type,
                'view_links': order.view_link or []
            }
            metadata['orders'].append(order_data)
        
        # Add comments data
        for comment in case.comments_data.all():
            comment_data = {
                'compliance_date': comment.compliance_date,
                'case_no': comment.case_no,
                'case_title': comment.case_title,
                'doc_type': comment.doc_type,
                'parties': comment.parties,
                'description': comment.description,
                'source_type': comment.source_type,
                'view_links': comment.view_link or []
            }
            metadata['comments'].append(comment_data)
        
        # Add case CMs data
        for cm in case.case_cms_data.all():
            cm_data = {
                'sr_number': cm.sr_number,
                'cm': cm.cm,
                'institution': cm.institution,
                'disposal_date': cm.disposal_date,
                'order_passed': cm.order_passed,
                'description': cm.description,
                'status': cm.status,
                'source_type': cm.source_type,
            }
            metadata['case_cms'].append(cm_data)
        
        # Add parties data
        for party in case.parties_detail_data.all():
            party_data = {
                'party_number': party.party_number,
                'party_name': party.party_name,
                'party_side': party.party_side,
            }
            metadata['parties'].append(party_data)
        
        # Add document information
        for case_doc in case.case_documents.all():
            doc_data = {
                'document_id': case_doc.document.id,
                'file_name': case_doc.document.file_name,
                'file_size': case_doc.document.file_size,
                'total_pages': case_doc.document.total_pages,
                'document_type': case_doc.document_type,
                'document_title': case_doc.document_title,
                'source_table': case_doc.source_table,
                'is_downloaded': case_doc.document.is_downloaded,
                'is_processed': case_doc.document.is_processed,
                'is_cleaned': case_doc.document.is_cleaned,
            }
            metadata['documents'].append(doc_data)
        
        return metadata
    
    def _build_pdf_content_summary(self, case: Case) -> Dict:
        """Build summary of PDF content for the case"""
        summary = {
            'total_documents': 0,
            'total_pages': 0,
            'total_pages_with_text': 0,
            'total_pages_cleaned': 0,
            'documents_by_type': {},
            'text_extraction_stats': {},
            'sample_texts': [],
            'complete_pdf_content': '',
            'total_text_length': 0
        }
        
        # Get all documents for this case
        case_documents = case.case_documents.all()
        summary['total_documents'] = case_documents.count()
        
        for case_doc in case_documents:
            document = case_doc.document
            doc_type = case_doc.document_type
            
            # Update document type stats
            if doc_type not in summary['documents_by_type']:
                summary['documents_by_type'][doc_type] = {
                    'count': 0,
                    'total_pages': 0,
                    'total_size': 0
                }
            
            summary['documents_by_type'][doc_type]['count'] += 1
            summary['documents_by_type'][doc_type]['total_pages'] += document.total_pages or 0
            summary['documents_by_type'][doc_type]['total_size'] += document.file_size or 0
            
            # Get text statistics
            document_texts = document.document_texts.all()
            summary['total_pages'] += document_texts.count()
            summary['total_pages_with_text'] += document_texts.filter(has_text=True).count()
            summary['total_pages_cleaned'] += document_texts.filter(is_cleaned=True).count()
            
            # Add complete text content for each document
            all_pages_text = []
            for doc_text in document_texts.filter(has_text=True, is_cleaned=True).order_by('page_number'):
                if doc_text.clean_text:
                    all_pages_text.append(doc_text.clean_text)
            
            if all_pages_text:
                complete_text = '\n\n--- Page Break ---\n\n'.join(all_pages_text)
                summary['sample_texts'].append({
                    'document_type': doc_type,
                    'file_name': document.file_name,
                    'complete_text': complete_text,
                    'total_pages': len(all_pages_text),
                    'text_length': len(complete_text)
                })
                
                # Add to combined content
                if summary['complete_pdf_content']:
                    summary['complete_pdf_content'] += '\n\n--- Document Break ---\n\n'
                summary['complete_pdf_content'] += f"Document: {document.file_name}\nType: {doc_type}\n\n{complete_text}"
                summary['total_text_length'] += len(complete_text)
        
        # Add extraction statistics
        summary['text_extraction_stats'] = {
            'pymupdf_pages': DocumentText.objects.filter(
                document__case_documents__case=case,
                extraction_method='pymupdf'
            ).count(),
            'ocr_pages': DocumentText.objects.filter(
                document__case_documents__case=case,
                extraction_method='ocr'
            ).count(),
            'pages_needing_ocr': DocumentText.objects.filter(
                document__case_documents__case=case,
                needs_ocr=True
            ).count(),
        }
        
        return summary
    
    def _is_metadata_complete(self, case_metadata: Dict) -> bool:
        """Check if case metadata is complete"""
        basic_info = case_metadata.get('basic_info', {})
        
        # Check essential fields
        essential_fields = ['case_number', 'case_title']
        for field in essential_fields:
            if not basic_info.get(field):
                return False
        
        # Check if we have at least some additional data
        has_orders = len(case_metadata.get('orders', [])) > 0
        has_comments = len(case_metadata.get('comments', [])) > 0
        has_parties = len(case_metadata.get('parties', [])) > 0
        has_detail = any(case_metadata.get('case_detail', {}).values())
        
        return has_orders or has_comments or has_parties or has_detail
    
    def _update_unified_view(self, unified_view: UnifiedCaseView):
        """Update existing unified view with latest data"""
        try:
            case = unified_view.case
            
            # Rebuild metadata and content summary
            case_metadata = self._build_case_metadata(case)
            pdf_content_summary = self._build_pdf_content_summary(case)
            
            # Update status flags
            has_pdf = bool(pdf_content_summary.get('total_documents', 0) > 0)
            text_extracted = pdf_content_summary.get('total_pages_with_text', 0) > 0
            text_cleaned = pdf_content_summary.get('total_pages_cleaned', 0) > 0
            metadata_complete = self._is_metadata_complete(case_metadata)
            
            # Update the view
            unified_view.case_metadata = case_metadata
            unified_view.pdf_content_summary = pdf_content_summary
            unified_view.has_pdf = has_pdf
            unified_view.text_extracted = text_extracted
            unified_view.text_cleaned = text_cleaned
            unified_view.metadata_complete = metadata_complete
            unified_view.is_processed = True
            unified_view.processing_error = ""
            unified_view.save()
            
            logger.info(f"Updated unified view for case {case.case_number}")
            
        except Exception as e:
            logger.error(f"Error updating unified view for case {unified_view.case.case_number}: {str(e)}")
            unified_view.processing_error = str(e)
            unified_view.save()
    
    def get_unified_case_data(self, case: Case) -> Dict:
        """Get complete unified case data for a case"""
        try:
            # Get or create unified view
            unified_view = UnifiedCaseView.objects.filter(case=case).first()
            if not unified_view:
                unified_view = self.create_unified_view_for_case(case)
            
            # Return complete data
            return {
                'case': {
                    'id': case.id,
                    'case_number': case.case_number,
                    'sr_number': case.sr_number,
                    'case_title': case.case_title,
                    'status': case.status,
                    'hearing_date': case.hearing_date,
                    'bench': case.bench,
                    'court': case.court.name if case.court else None,
                },
                'metadata': unified_view.case_metadata,
                'pdf_content': unified_view.pdf_content_summary,
                'status': {
                    'has_pdf': unified_view.has_pdf,
                    'text_extracted': unified_view.text_extracted,
                    'text_cleaned': unified_view.text_cleaned,
                    'metadata_complete': unified_view.metadata_complete,
                    'is_processed': unified_view.is_processed,
                },
                'processing_error': unified_view.processing_error,
                'created_at': unified_view.created_at,
                'updated_at': unified_view.updated_at,
            }
            
        except Exception as e:
            logger.error(f"Error getting unified case data for {case.case_number}: {str(e)}")
            return {
                'error': str(e),
                'case': {
                    'case_number': case.case_number,
                    'case_title': case.case_title,
                }
            }
