"""
QA Engine - Main orchestrator for question-answering system
Coordinates between knowledge retrieval, answer generation, and response management
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from django.utils import timezone
from django.db import transaction

from ..models import QASession, QAQuery, QAResponse, QAConfiguration
from .knowledge_retriever import KnowledgeRetriever
from .answer_generator import AnswerGenerator
from .context_manager import ContextManager
from .query_processor import QueryProcessor

logger = logging.getLogger(__name__)


class QAEngine:
    """Main QA engine that orchestrates the question-answering process"""
    
    def __init__(self, config_name: str = "default"):
        self.config_name = config_name
        self.config = self._load_configuration()
        
        # Initialize services
        self.knowledge_retriever = KnowledgeRetriever(self.config)
        self.answer_generator = AnswerGenerator(self.config)
        self.context_manager = ContextManager(self.config)
        self.query_processor = QueryProcessor(self.config)
        
        logger.info("QA Engine initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load QA system configuration"""
        try:
            config = QAConfiguration.objects.filter(
                config_name=self.config_name,
                is_active=True
            ).first()
            
            if config:
                return config.config_data
        except Exception as e:
            logger.warning(f"Could not load QA configuration: {e}")
        
        # Default configuration
        return {
            'embedding_model': 'all-MiniLM-L6-v2',
            'generation_model': 'gpt-3.5-turbo',
            'max_tokens': 1000,
            'temperature': 0.7,
            'top_k_documents': 5,
            'similarity_threshold': 0.7,
            'max_context_length': 4000,
            'enable_streaming': True,
            'enable_feedback': True,
        }
    
    def create_session(self, user, title: str = "", description: str = "") -> QASession:
        """Create a new QA session"""
        try:
            session_id = str(uuid.uuid4())
            
            session = QASession.objects.create(
                session_id=session_id,
                user=user,
                title=title or f"QA Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description=description,
                context_data={
                    'legal_domain': 'general',
                    'court_focus': 'all',
                    'language': 'en',
                }
            )
            
            logger.info(f"Created QA session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating QA session: {e}")
            raise
    
    def ask_question(self, 
                    session_id: str, 
                    question: str, 
                    user=None,
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a question and generate an answer
        
        Args:
            session_id: QA session ID
            question: User's question
            user: User object (optional)
            context: Additional context (optional)
            
        Returns:
            Dictionary containing answer and metadata
        """
        start_time = time.time()
        
        try:
            # Get or create session
            session = self._get_or_create_session(session_id, user)
            
            # Create query record
            query = self._create_query(session, question, context)
            
            # Process the question
            processed_question = self.query_processor.process_query(question, context)
            
            # Update query with processed information
            query.processed_query = processed_question['processed_text']
            query.query_intent = processed_question['intent']
            query.query_confidence = processed_question['confidence']
            query.status = 'processing'
            query.save()
            
            # Retrieve relevant knowledge
            retrieval_start = time.time()
            knowledge_results = self.knowledge_retriever.retrieve_knowledge(
                processed_question['processed_text'],
                top_k=self.config.get('top_k_documents', 5),
                similarity_threshold=self.config.get('similarity_threshold', 0.7)
            )
            query.retrieval_time = time.time() - retrieval_start
            
            # Generate answer
            generation_start = time.time()
            answer_result = self.answer_generator.generate_answer(
                question=processed_question['processed_text'],
                knowledge_context=knowledge_results,
                session_context=self.context_manager.get_session_context(session),
                query_intent=processed_question['intent']
            )
            query.generation_time = time.time() - generation_start
            
            # Create response record
            response = self._create_response(query, answer_result, knowledge_results)
            
            # Update session context
            self.context_manager.update_session_context(session, question, answer_result)
            
            # Update session metrics
            self._update_session_metrics(session, query, response)
            
            # Calculate total processing time
            query.processing_time = time.time() - start_time
            query.status = 'completed'
            query.processed_at = timezone.now()
            query.save()
            
            # Prepare response
            result = {
                'session_id': session.session_id,
                'query_id': query.id,
                'response_id': response.id,
                'question': question,
                'answer': answer_result['answer'],
                'answer_type': answer_result['answer_type'],
                'confidence_score': answer_result['confidence'],
                'sources': answer_result['sources'],
                'reasoning': answer_result.get('reasoning', []),
                'processing_time': query.processing_time,
                'retrieval_time': query.retrieval_time,
                'generation_time': query.generation_time,
                'metadata': {
                    'query_intent': processed_question['intent'],
                    'query_confidence': processed_question['confidence'],
                    'knowledge_retrieved': len(knowledge_results),
                    'context_used': len(self.context_manager.get_session_context(session))
                }
            }
            
            logger.info(f"Successfully processed question in {query.processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            
            # Update query with error
            if 'query' in locals():
                query.status = 'failed'
                query.error_message = str(e)
                query.save()
            
            # Update session metrics
            if 'session' in locals():
                session.total_queries += 1
                session.save()
            
            raise
    
    def ask_question_stream(self, 
                           session_id: str, 
                           question: str, 
                           user=None,
                           context: Dict[str, Any] = None):
        """
        Process a question with streaming response
        
        Yields:
            Dictionary containing streaming response chunks
        """
        try:
            # Get or create session
            session = self._get_or_create_session(session_id, user)
            
            # Create query record
            query = self._create_query(session, question, context)
            query.status = 'processing'
            query.save()
            
            # Process the question
            processed_question = self.query_processor.process_query(question, context)
            
            # Update query with processed information
            query.processed_query = processed_question['processed_text']
            query.query_intent = processed_question['intent']
            query.query_confidence = processed_question['confidence']
            query.save()
            
            # Retrieve relevant knowledge
            knowledge_results = self.knowledge_retriever.retrieve_knowledge(
                processed_question['processed_text'],
                top_k=self.config.get('top_k_documents', 5),
                similarity_threshold=self.config.get('similarity_threshold', 0.7)
            )
            
            # Stream answer generation
            for chunk in self.answer_generator.generate_answer_stream(
                question=processed_question['processed_text'],
                knowledge_context=knowledge_results,
                session_context=self.context_manager.get_session_context(session),
                query_intent=processed_question['intent']
            ):
                yield chunk
            
            # Create final response record
            response = self._create_response(query, chunk, knowledge_results)
            
            # Update session context
            self.context_manager.update_session_context(session, question, chunk)
            
            # Update session metrics
            self._update_session_metrics(session, query, response)
            
            query.status = 'completed'
            query.processed_at = timezone.now()
            query.save()
            
        except Exception as e:
            logger.error(f"Error in streaming question processing: {e}")
            
            if 'query' in locals():
                query.status = 'failed'
                query.error_message = str(e)
                query.save()
            
            yield {
                'type': 'error',
                'error': str(e),
                'session_id': session_id
            }
    
    def _get_or_create_session(self, session_id: str, user=None) -> QASession:
        """Get existing session or create new one"""
        try:
            session = QASession.objects.get(session_id=session_id)
            return session
        except QASession.DoesNotExist:
            if user:
                return self.create_session(user)
            else:
                raise ValueError("Session not found and no user provided for creation")
    
    def _create_query(self, session: QASession, question: str, context: Dict[str, Any] = None) -> QAQuery:
        """Create a new query record"""
        return QAQuery.objects.create(
            session=session,
            query_text=question,
            query_type=self._classify_query_type(question),
            context_window=self.context_manager.get_context_window(session),
            user_context=context or {}
        )
    
    def _create_response(self, query: QAQuery, answer_result: Dict[str, Any], knowledge_results: List[Dict]) -> QAResponse:
        """Create a response record"""
        return QAResponse.objects.create(
            query=query,
            answer_text=answer_result['answer'],
            answer_type=answer_result['answer_type'],
            confidence_score=answer_result['confidence'],
            source_documents=[doc.get('document_id') for doc in knowledge_results if doc.get('document_id')],
            source_cases=[doc.get('case_id') for doc in knowledge_results if doc.get('case_id')],
            source_citations=answer_result.get('citations', []),
            reasoning_chain=answer_result.get('reasoning', []),
            answer_metadata=answer_result.get('metadata', {}),
            relevance_score=answer_result.get('relevance_score', 0.0),
            completeness_score=answer_result.get('completeness_score', 0.0),
            accuracy_score=answer_result.get('accuracy_score', 0.0)
        )
    
    def _classify_query_type(self, question: str) -> str:
        """Classify the type of query"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['case', 'judgment', 'order', 'decision']):
            return 'case_inquiry'
        elif any(word in question_lower for word in ['law', 'statute', 'section', 'act']):
            return 'law_research'
        elif any(word in question_lower for word in ['judge', 'justice', 'bench']):
            return 'judge_inquiry'
        elif any(word in question_lower for word in ['lawyer', 'advocate', 'counsel']):
            return 'lawyer_inquiry'
        elif any(word in question_lower for word in ['procedure', 'process', 'how to']):
            return 'court_procedure'
        elif any(word in question_lower for word in ['cite', 'citation', 'reference']):
            return 'citation_lookup'
        else:
            return 'general_legal'
    
    def _update_session_metrics(self, session: QASession, query: QAQuery, response: QAResponse):
        """Update session performance metrics"""
        session.total_queries += 1
        if query.status == 'completed':
            session.successful_queries += 1
        
        # Update average response time
        if session.total_queries == 1:
            session.average_response_time = query.processing_time
        else:
            session.average_response_time = (
                (session.average_response_time * (session.total_queries - 1) + query.processing_time) 
                / session.total_queries
            )
        
        session.last_activity = timezone.now()
        session.save()
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            session = QASession.objects.get(session_id=session_id)
            queries = QAQuery.objects.filter(session=session).order_by('created_at')
            
            history = []
            for query in queries:
                if hasattr(query, 'response'):
                    history.append({
                        'query_id': query.id,
                        'question': query.query_text,
                        'answer': query.response.answer_text,
                        'answer_type': query.response.answer_type,
                        'confidence_score': query.response.confidence_score,
                        'sources': query.response.source_documents,
                        'created_at': query.created_at.isoformat(),
                        'processing_time': query.processing_time
                    })
            
            return history
            
        except QASession.DoesNotExist:
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get QA system status and health"""
        try:
            # Get configuration
            config = QAConfiguration.objects.filter(is_active=True).first()
            
            # Get recent metrics
            recent_sessions = QASession.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=1)
            ).count()
            
            recent_queries = QAQuery.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=1)
            ).count()
            
            # Get knowledge base status
            total_knowledge = QAKnowledgeBase.objects.count()
            indexed_knowledge = QAKnowledgeBase.objects.filter(is_indexed=True).count()
            
            return {
                'status': 'healthy',
                'configuration': config.config_name if config else 'default',
                'services': {
                    'knowledge_retriever': self.knowledge_retriever.is_healthy(),
                    'answer_generator': self.answer_generator.is_healthy(),
                    'context_manager': self.context_manager.is_healthy(),
                    'query_processor': self.query_processor.is_healthy(),
                },
                'metrics': {
                    'recent_sessions_24h': recent_sessions,
                    'recent_queries_24h': recent_queries,
                    'total_knowledge_items': total_knowledge,
                    'indexed_knowledge_items': indexed_knowledge,
                    'knowledge_coverage': (indexed_knowledge / total_knowledge * 100) if total_knowledge > 0 else 0
                },
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
