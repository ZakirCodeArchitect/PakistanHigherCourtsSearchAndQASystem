"""
QA Knowledge Base API Views
"""

import logging
import time
from typing import Dict, Any, List

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone

from qa_app.services.qa_knowledge_base import (
    QAKnowledgeBaseService,
    QALawReferenceNormalizer,
    QAEnhancedChunkingService
)
from apps.cases.models import Case
from qa_app.models import QAKnowledgeBase

logger = logging.getLogger(__name__)


class QAKnowledgeBaseProcessingView(APIView):
    """API view for QA Knowledge Base processing operations"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.qa_kb_service = QAKnowledgeBaseService()
    
    def post(self, request):
        """Process QA Knowledge Base for specific cases or all cases"""
        try:
            start_time = time.time()
            
            # Parse request parameters
            case_id = request.data.get('case_id')
            case_range = request.data.get('case_range')  # "1-100"
            process_all = request.data.get('process_all', False)
            force_reprocess = request.data.get('force_reprocess', False)
            
            results = {
                'success': False,
                'processing_time': 0,
                'cases_processed': 0,
                'total_qa_entries_created': 0,
                'total_errors': 0,
                'details': []
            }
            
            if case_id:
                # Process single case for QA
                result = self.qa_kb_service.process_case_for_qa(case_id, force_reprocess)
                results['details'].append(result)
                results['cases_processed'] = 1 if result['success'] else 0
                results['total_qa_entries_created'] = result.get('qa_entries_created', 0)
                results['total_errors'] = len(result.get('errors', []))
                
            elif case_range:
                # Process case range for QA
                start_id, end_id = map(int, case_range.split('-'))
                for case_id in range(start_id, end_id + 1):
                    result = self.qa_kb_service.process_case_for_qa(case_id, force_reprocess)
                    results['details'].append(result)
                    
                    if result['success']:
                        results['cases_processed'] += 1
                        results['total_qa_entries_created'] += result.get('qa_entries_created', 0)
                        results['total_errors'] += len(result.get('errors', []))
                    else:
                        results['total_errors'] += 1
                        
            elif process_all:
                # Process all cases for QA
                case_ids = list(Case.objects.values_list('id', flat=True))
                for case_id in case_ids:
                    result = self.qa_kb_service.process_case_for_qa(case_id, force_reprocess)
                    results['details'].append(result)
                    
                    if result['success']:
                        results['cases_processed'] += 1
                        results['total_qa_entries_created'] += result.get('qa_entries_created', 0)
                        results['total_errors'] += len(result.get('errors', []))
                    else:
                        results['total_errors'] += 1
                        
                    # Progress logging
                    if results['cases_processed'] % 50 == 0:
                        logger.info(f"Processed {results['cases_processed']} cases for QA...")
            else:
                return Response({
                    'error': 'Please specify case_id, case_range, or process_all'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            results['processing_time'] = time.time() - start_time
            results['success'] = results['total_errors'] == 0
            
            logger.info(f"QA KB processing completed: {results['cases_processed']} cases, "
                       f"{results['total_qa_entries_created']} QA entries, {results['total_errors']} errors")
            
            return Response(results, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in QA KB processing API: {str(e)}")
            return Response({
                'error': str(e),
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAKnowledgeBaseStatsView(APIView):
    """API view for QA Knowledge Base statistics and monitoring"""
    
    def get(self, request):
        """Get QA Knowledge Base processing statistics"""
        try:
            qa_kb_service = QAKnowledgeBaseService()
            stats = qa_kb_service.get_qa_processing_stats()
            
            if 'error' in stats:
                return Response({
                    'error': stats['error']
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting QA KB stats: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QALawReferenceNormalizationView(APIView):
    """API view for QA law reference normalization testing"""
    
    def post(self, request):
        """Normalize law references in provided text for QA context"""
        try:
            text = request.data.get('text', '')
            if not text:
                return Response({
                    'error': 'Text is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            normalizer = QALawReferenceNormalizer()
            result = normalizer.normalize_reference(text)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error normalizing law references for QA: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAChunkingTestView(APIView):
    """API view for testing QA chunking functionality"""
    
    def post(self, request):
        """Test QA chunking on provided text"""
        try:
            text = request.data.get('text', '')
            case_id = request.data.get('case_id', 1)
            document_type = request.data.get('document_type', 'judgment')
            
            if not text:
                return Response({
                    'error': 'Text is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            chunking_service = QAEnhancedChunkingService()
            chunks = chunking_service.chunk_document_for_qa(
                case_id=case_id,
                text=text,
                document_type=document_type
            )
            
            return Response({
                'text_length': len(text),
                'chunks_created': len(chunks),
                'chunks': chunks
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error testing QA chunking: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAKnowledgeBaseHealthView(APIView):
    """API view for QA Knowledge Base health monitoring"""
    
    def get(self, request):
        """Get QA Knowledge Base health status"""
        try:
            start_time = time.time()
            
            # Get basic statistics
            qa_kb_service = QAKnowledgeBaseService()
            stats = qa_kb_service.get_qa_processing_stats()
            
            # Check database connectivity
            db_healthy = True
            try:
                QAKnowledgeBase.objects.count()
            except Exception:
                db_healthy = False
            
            # Check QA processing health
            qa_healthy = True
            try:
                # Check if we have QA entries
                qa_count = QAKnowledgeBase.objects.count()
                if qa_count == 0:
                    qa_healthy = False
            except Exception:
                qa_healthy = False
            
            health_status = {
                'status': 'healthy' if db_healthy and qa_healthy else 'degraded',
                'timestamp': timezone.now().isoformat(),
                'response_time': time.time() - start_time,
                'components': {
                    'database': {
                        'status': 'healthy' if db_healthy else 'unhealthy',
                        'message': 'Database connection working' if db_healthy else 'Database connection failed'
                    },
                    'qa_knowledge_base': {
                        'status': 'healthy' if qa_healthy else 'unhealthy',
                        'message': 'QA Knowledge Base working' if qa_healthy else 'QA Knowledge Base needs processing'
                    }
                },
                'statistics': stats if 'error' not in stats else None
            }
            
            return Response(health_status, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error checking QA KB health: {str(e)}")
            return Response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAKnowledgeBaseSearchView(APIView):
    """API view for searching QA Knowledge Base"""
    
    def post(self, request):
        """Search QA Knowledge Base entries"""
        try:
            query = request.data.get('query', '')
            limit = request.data.get('limit', 10)
            legal_domain = request.data.get('legal_domain', None)
            
            if not query:
                return Response({
                    'error': 'Query is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            start_time = time.time()
            
            # Search QA Knowledge Base
            qa_entries = QAKnowledgeBase.objects.filter(
                content_text__icontains=query
            )
            
            if legal_domain:
                qa_entries = qa_entries.filter(legal_domain=legal_domain)
            
            qa_entries = qa_entries.order_by('-content_quality_score', '-legal_relevance_score')[:limit]
            
            results = []
            for entry in qa_entries:
                results.append({
                    'id': entry.id,
                    'title': entry.title,
                    'content_preview': entry.content_text[:200] + '...',
                    'court': entry.court,
                    'case_number': entry.case_number,
                    'legal_domain': entry.legal_domain,
                    'content_quality_score': entry.content_quality_score,
                    'legal_relevance_score': entry.legal_relevance_score,
                    'legal_concepts': entry.legal_concepts,
                    'citations': entry.citations,
                    'created_at': entry.created_at.isoformat()
                })
            
            processing_time = time.time() - start_time
            
            return Response({
                'query': query,
                'results': results,
                'result_count': len(results),
                'processing_time': processing_time,
                'search_type': 'qa_knowledge_base'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error searching QA Knowledge Base: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
