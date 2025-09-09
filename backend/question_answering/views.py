"""
Question-Answering System Views
API endpoints and views for the QA system
"""

import logging
import time
import json
from typing import Dict, Any, List
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from models import (
    QASession, QAQuery, QAResponse, QAKnowledgeBase, 
    QAFeedback, QAConfiguration, QAMetrics
)
from services.qa_engine import QAEngine
from services.knowledge_retriever import KnowledgeRetriever

logger = logging.getLogger(__name__)


# ============================================================================
# API VIEWS
# ============================================================================

class QASessionListCreateView(APIView):
    """List and create QA sessions"""
    
    def get(self, request):
        """Get user's QA sessions"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get query parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            is_active = request.GET.get('is_active')
            
            # Build query
            sessions_query = QASession.objects.filter(user=user)
            
            if is_active is not None:
                sessions_query = sessions_query.filter(is_active=is_active.lower() == 'true')
            
            # Order by last activity
            sessions_query = sessions_query.order_by('-last_activity')
            
            # Paginate
            paginator = Paginator(sessions_query, page_size)
            sessions_page = paginator.get_page(page)
            
            # Serialize sessions
            sessions_data = []
            for session in sessions_page:
                sessions_data.append({
                    'session_id': session.session_id,
                    'title': session.title,
                    'description': session.description,
                    'total_queries': session.total_queries,
                    'success_rate': session.success_rate,
                    'user_satisfaction_score': session.user_satisfaction_score,
                    'is_active': session.is_active,
                    'created_at': session.created_at.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'duration': session.duration.total_seconds() if session.duration else 0
                })
            
            return Response({
                'sessions': sessions_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': sessions_page.has_next(),
                    'has_previous': sessions_page.has_previous()
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting QA sessions: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new QA session"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get request data
            title = request.data.get('title', '')
            description = request.data.get('description', '')
            
            # Create QA engine and session
            qa_engine = QAEngine()
            session = qa_engine.create_session(user, title, description)
            
            return Response({
                'session_id': session.session_id,
                'title': session.title,
                'description': session.description,
                'created_at': session.created_at.isoformat(),
                'message': 'QA session created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating QA session: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QASessionDetailView(APIView):
    """Get, update, or delete a specific QA session"""
    
    def get(self, request, session_id):
        """Get session details and history"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get session
            session = get_object_or_404(QASession, session_id=session_id, user=user)
            
            # Get conversation history
            qa_engine = QAEngine()
            history = qa_engine.get_session_history(session_id)
            
            return Response({
                'session': {
                    'session_id': session.session_id,
                    'title': session.title,
                    'description': session.description,
                    'context_data': session.context_data,
                    'total_queries': session.total_queries,
                    'successful_queries': session.successful_queries,
                    'success_rate': session.success_rate,
                    'user_satisfaction_score': session.user_satisfaction_score,
                    'is_active': session.is_active,
                    'created_at': session.created_at.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'duration': session.duration.total_seconds() if session.duration else 0
                },
                'conversation_history': history
            })
            
        except Exception as e:
            logger.error(f"Error getting session details: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, session_id):
        """Update session"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get session
            session = get_object_or_404(QASession, session_id=session_id, user=user)
            
            # Update fields
            if 'title' in request.data:
                session.title = request.data['title']
            if 'description' in request.data:
                session.description = request.data['description']
            if 'is_active' in request.data:
                session.is_active = request.data['is_active']
            
            session.save()
            
            return Response({
                'session_id': session.session_id,
                'title': session.title,
                'description': session.description,
                'is_active': session.is_active,
                'message': 'Session updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, session_id):
        """Delete session"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get session
            session = get_object_or_404(QASession, session_id=session_id, user=user)
            
            # Archive instead of delete
            session.is_active = False
            session.is_archived = True
            session.save()
            
            return Response({'message': 'Session archived successfully'})
            
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAAskView(APIView):
    """Main endpoint for asking questions"""
    
    def post(self, request):
        """Ask a question and get an answer"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get request data
            session_id = request.data.get('session_id')
            question = request.data.get('question', '').strip()
            context = request.data.get('context', {})
            
            if not question:
                return Response({'error': 'Question is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not session_id:
                return Response({'error': 'Session ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Process question
            qa_engine = QAEngine()
            result = qa_engine.ask_question(session_id, question, user, context)
            
            return Response(result)
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAAskStreamView(APIView):
    """Streaming endpoint for asking questions"""
    
    def post(self, request):
        """Ask a question with streaming response"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get request data
            session_id = request.data.get('session_id')
            question = request.data.get('question', '').strip()
            context = request.data.get('context', {})
            
            if not question:
                return Response({'error': 'Question is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not session_id:
                return Response({'error': 'Session ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create streaming response
            def generate_stream():
                try:
                    qa_engine = QAEngine()
                    for chunk in qa_engine.ask_question_stream(session_id, question, user, context):
                        yield f"data: {json.dumps(chunk)}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            
            response = StreamingHttpResponse(
                generate_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['Connection'] = 'keep-alive'
            
            return response
            
        except Exception as e:
            logger.error(f"Error in streaming question: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAQueryListCreateView(APIView):
    """List queries for a session"""
    
    def get(self, request, session_id):
        """Get queries for a session"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get session
            session = get_object_or_404(QASession, session_id=session_id, user=user)
            
            # Get query parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            
            # Get queries
            queries = QAQuery.objects.filter(session=session).order_by('-created_at')
            
            # Paginate
            paginator = Paginator(queries, page_size)
            queries_page = paginator.get_page(page)
            
            # Serialize queries
            queries_data = []
            for query in queries_page:
                query_data = {
                    'id': query.id,
                    'query_text': query.query_text,
                    'query_type': query.query_type,
                    'status': query.status,
                    'processing_time': query.processing_time,
                    'created_at': query.created_at.isoformat(),
                    'processed_at': query.processed_at.isoformat() if query.processed_at else None
                }
                
                # Add response if available
                if hasattr(query, 'response'):
                    response = query.response
                    query_data['response'] = {
                        'id': response.id,
                        'answer_text': response.answer_text,
                        'answer_type': response.answer_type,
                        'confidence_score': response.confidence_score,
                        'user_rating': response.user_rating,
                        'created_at': response.created_at.isoformat()
                    }
                
                queries_data.append(query_data)
            
            return Response({
                'queries': queries_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': queries_page.has_next(),
                    'has_previous': queries_page.has_previous()
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting queries: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAQueryDetailView(APIView):
    """Get specific query details"""
    
    def get(self, request, query_id):
        """Get query details"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get query
            query = get_object_or_404(QAQuery, id=query_id, session__user=user)
            
            query_data = {
                'id': query.id,
                'session_id': query.session.session_id,
                'query_text': query.query_text,
                'processed_query': query.processed_query,
                'query_type': query.query_type,
                'query_intent': query.query_intent,
                'query_confidence': query.query_confidence,
                'context_window': query.context_window,
                'user_context': query.user_context,
                'status': query.status,
                'processing_time': query.processing_time,
                'retrieval_time': query.retrieval_time,
                'generation_time': query.generation_time,
                'error_message': query.error_message,
                'created_at': query.created_at.isoformat(),
                'processed_at': query.processed_at.isoformat() if query.processed_at else None
            }
            
            # Add response if available
            if hasattr(query, 'response'):
                response = query.response
                query_data['response'] = {
                    'id': response.id,
                    'answer_text': response.answer_text,
                    'answer_type': response.answer_type,
                    'confidence_score': response.confidence_score,
                    'source_documents': response.source_documents,
                    'source_cases': response.source_cases,
                    'source_citations': response.source_citations,
                    'reasoning_chain': response.reasoning_chain,
                    'answer_metadata': response.answer_metadata,
                    'relevance_score': response.relevance_score,
                    'completeness_score': response.completeness_score,
                    'accuracy_score': response.accuracy_score,
                    'user_rating': response.user_rating,
                    'user_feedback': response.user_feedback,
                    'created_at': response.created_at.isoformat()
                }
            
            return Response(query_data)
            
        except Exception as e:
            logger.error(f"Error getting query details: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAResponseDetailView(APIView):
    """Get response details"""
    
    def get(self, request, query_id):
        """Get response details for a query"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get query and response
            query = get_object_or_404(QAQuery, id=query_id, session__user=user)
            response = get_object_or_404(QAResponse, query=query)
            
            response_data = {
                'id': response.id,
                'query_id': query.id,
                'answer_text': response.answer_text,
                'answer_type': response.answer_type,
                'confidence_score': response.confidence_score,
                'source_documents': response.source_documents,
                'source_cases': response.source_cases,
                'source_citations': response.source_citations,
                'reasoning_chain': response.reasoning_chain,
                'answer_metadata': response.answer_metadata,
                'limitations': response.limitations,
                'relevance_score': response.relevance_score,
                'completeness_score': response.completeness_score,
                'accuracy_score': response.accuracy_score,
                'user_rating': response.user_rating,
                'user_feedback': response.user_feedback,
                'feedback_timestamp': response.feedback_timestamp.isoformat() if response.feedback_timestamp else None,
                'created_at': response.created_at.isoformat(),
                'updated_at': response.updated_at.isoformat()
            }
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error getting response details: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAFeedbackView(APIView):
    """Submit feedback for a response"""
    
    def post(self, request, response_id):
        """Submit feedback"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get response
            response = get_object_or_404(QAResponse, id=response_id)
            
            # Get feedback data
            rating = request.data.get('rating')
            feedback_text = request.data.get('feedback_text', '')
            accuracy_rating = request.data.get('accuracy_rating')
            relevance_rating = request.data.get('relevance_rating')
            completeness_rating = request.data.get('completeness_rating')
            clarity_rating = request.data.get('clarity_rating')
            is_helpful = request.data.get('is_helpful')
            would_recommend = request.data.get('would_recommend')
            
            if not rating:
                return Response({'error': 'Rating is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create or update feedback
            feedback, created = QAFeedback.objects.get_or_create(
                response=response,
                user=user,
                defaults={
                    'rating': rating,
                    'feedback_text': feedback_text,
                    'accuracy_rating': accuracy_rating,
                    'relevance_rating': relevance_rating,
                    'completeness_rating': completeness_rating,
                    'clarity_rating': clarity_rating,
                    'is_helpful': is_helpful,
                    'would_recommend': would_recommend
                }
            )
            
            if not created:
                # Update existing feedback
                feedback.rating = rating
                feedback.feedback_text = feedback_text
                feedback.accuracy_rating = accuracy_rating
                feedback.relevance_rating = relevance_rating
                feedback.completeness_rating = completeness_rating
                feedback.clarity_rating = clarity_rating
                feedback.is_helpful = is_helpful
                feedback.would_recommend = would_recommend
                feedback.save()
            
            # Update response with user rating
            response.user_rating = rating
            response.user_feedback = feedback_text
            response.feedback_timestamp = timezone.now()
            response.save()
            
            return Response({
                'feedback_id': feedback.id,
                'rating': feedback.rating,
                'message': 'Feedback submitted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAKnowledgeBaseView(APIView):
    """Knowledge base management"""
    
    def get(self, request):
        """Get knowledge base statistics"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get statistics
            total_items = QAKnowledgeBase.objects.count()
            indexed_items = QAKnowledgeBase.objects.filter(is_indexed=True).count()
            
            # Get by source type
            source_type_stats = QAKnowledgeBase.objects.values('source_type').annotate(
                count=Count('id'),
                indexed_count=Count('id', filter=Q(is_indexed=True))
            )
            
            # Get by court
            court_stats = QAKnowledgeBase.objects.values('court').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            # Get by legal domain
            domain_stats = QAKnowledgeBase.objects.values('legal_domain').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            return Response({
                'total_items': total_items,
                'indexed_items': indexed_items,
                'indexing_coverage': (indexed_items / total_items * 100) if total_items > 0 else 0,
                'source_type_distribution': list(source_type_stats),
                'court_distribution': list(court_stats),
                'legal_domain_distribution': list(domain_stats)
            })
            
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAKnowledgeSearchView(APIView):
    """Search knowledge base"""
    
    def get(self, request):
        """Search knowledge base"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get search parameters
            query = request.GET.get('q', '').strip()
            source_type = request.GET.get('source_type')
            court = request.GET.get('court')
            legal_domain = request.GET.get('legal_domain')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            
            if not query:
                return Response({'error': 'Search query is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Build search query
            search_query = QAKnowledgeBase.objects.filter(is_indexed=True)
            
            if source_type:
                search_query = search_query.filter(source_type=source_type)
            if court:
                search_query = search_query.filter(court__icontains=court)
            if legal_domain:
                search_query = search_query.filter(legal_domain=legal_domain)
            
            # Text search
            search_query = search_query.filter(
                Q(title__icontains=query) |
                Q(content_text__icontains=query) |
                Q(case_number__icontains=query) |
                Q(case_title__icontains=query)
            )
            
            # Order by relevance (simple scoring)
            search_query = search_query.order_by('-content_quality_score', '-legal_relevance_score')
            
            # Paginate
            paginator = Paginator(search_query, page_size)
            results_page = paginator.get_page(page)
            
            # Serialize results
            results_data = []
            for item in results_page:
                results_data.append({
                    'id': item.id,
                    'source_type': item.source_type,
                    'title': item.title,
                    'content_preview': item.content_text[:200] + '...' if len(item.content_text) > 200 else item.content_text,
                    'court': item.court,
                    'case_number': item.case_number,
                    'case_title': item.case_title,
                    'legal_domain': item.legal_domain,
                    'content_quality_score': item.content_quality_score,
                    'legal_relevance_score': item.legal_relevance_score,
                    'is_indexed': item.is_indexed,
                    'created_at': item.created_at.isoformat()
                })
            
            return Response({
                'results': results_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': results_page.has_next(),
                    'has_previous': results_page.has_previous()
                }
            })
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAStatusView(APIView):
    """Get QA system status"""
    
    def get(self, request):
        """Get system status"""
        try:
            qa_engine = QAEngine()
            status_data = qa_engine.get_system_status()
            
            return Response(status_data)
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAHealthView(APIView):
    """Health check endpoint"""
    
    def get(self, request):
        """Health check"""
        try:
            qa_engine = QAEngine()
            status_data = qa_engine.get_system_status()
            
            is_healthy = status_data.get('status') == 'healthy'
            
            return Response({
                'status': 'healthy' if is_healthy else 'unhealthy',
                'timestamp': timezone.now().isoformat(),
                'services': status_data.get('services', {}),
                'metrics': status_data.get('metrics', {})
            }, status=status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class QAAnalyticsView(APIView):
    """Get QA system analytics"""
    
    def get(self, request):
        """Get analytics data"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get time range
            days = int(request.GET.get('days', 30))
            start_date = timezone.now() - timedelta(days=days)
            
            # Get user's sessions
            user_sessions = QASession.objects.filter(user=user, created_at__gte=start_date)
            
            # Calculate metrics
            total_sessions = user_sessions.count()
            total_queries = QAQuery.objects.filter(session__in=user_sessions).count()
            successful_queries = QAQuery.objects.filter(
                session__in=user_sessions, 
                status='completed'
            ).count()
            
            # Average response time
            avg_response_time = QAQuery.objects.filter(
                session__in=user_sessions,
                status='completed'
            ).aggregate(avg_time=Avg('processing_time'))['avg_time'] or 0
            
            # Query type distribution
            query_type_dist = QAQuery.objects.filter(
                session__in=user_sessions
            ).values('query_type').annotate(count=Count('id'))
            
            # Average confidence
            avg_confidence = QAResponse.objects.filter(
                query__session__in=user_sessions
            ).aggregate(avg_conf=Avg('confidence_score'))['avg_conf'] or 0
            
            # User satisfaction
            avg_satisfaction = user_sessions.aggregate(
                avg_sat=Avg('user_satisfaction_score')
            )['avg_sat'] or 0
            
            return Response({
                'period_days': days,
                'total_sessions': total_sessions,
                'total_queries': total_queries,
                'successful_queries': successful_queries,
                'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                'average_response_time': avg_response_time,
                'average_confidence': avg_confidence,
                'average_satisfaction': avg_satisfaction,
                'query_type_distribution': list(query_type_dist),
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QAMetricsView(APIView):
    """Get system metrics"""
    
    def get(self, request):
        """Get system metrics"""
        try:
            user = request.user
            if not user.is_authenticated:
                return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get time range
            days = int(request.GET.get('days', 7))
            start_date = timezone.now() - timedelta(days=days)
            
            # Get metrics
            metrics = QAMetrics.objects.filter(
                recorded_at__gte=start_date
            ).order_by('-recorded_at')
            
            # Group by metric name
            metrics_data = {}
            for metric in metrics:
                metric_name = metric.metric_name
                if metric_name not in metrics_data:
                    metrics_data[metric_name] = []
                
                metrics_data[metric_name].append({
                    'value': metric.metric_value,
                    'unit': metric.metric_unit,
                    'recorded_at': metric.recorded_at.isoformat(),
                    'metric_type': metric.metric_type
                })
            
            return Response({
                'metrics': metrics_data,
                'period_days': days,
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# FRONTEND VIEWS
# ============================================================================

@method_decorator(login_required, name='dispatch')
class QAInterfaceView(View):
    """Main QA interface view"""
    
    def get(self, request):
        """Render QA interface"""
        return render(request, 'question_answering/qa_interface.html')


@method_decorator(login_required, name='dispatch')
class QAChatView(View):
    """QA chat interface view"""
    
    def get(self, request, session_id=None):
        """Render chat interface"""
        context = {}
        if session_id:
            try:
                session = QASession.objects.get(session_id=session_id, user=request.user)
                context['session'] = session
            except QASession.DoesNotExist:
                pass
        
        return render(request, 'question_answering/qa_chat.html', context)


@method_decorator(login_required, name='dispatch')
class QASessionsView(View):
    """QA sessions management view"""
    
    def get(self, request):
        """Render sessions management"""
        return render(request, 'question_answering/qa_sessions.html')


@method_decorator(login_required, name='dispatch')
class QAAnalyticsDashboardView(View):
    """QA analytics dashboard view"""
    
    def get(self, request):
        """Render analytics dashboard"""
        return render(request, 'question_answering/qa_analytics.html')
