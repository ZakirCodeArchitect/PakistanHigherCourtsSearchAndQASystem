"""
Context Manager Service
Manages conversation context and session state for QA system
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone

from ..models import QASession, QAQuery, QAResponse

logger = logging.getLogger(__name__)


class ContextManager:
    """Service for managing conversation context and session state"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Configuration
        self.max_context_length = self.config.get('max_context_length', 4000)
        self.max_history_items = self.config.get('max_history_items', 10)
        self.context_decay_factor = self.config.get('context_decay_factor', 0.9)
        
        logger.info("Context Manager initialized successfully")
    
    def get_session_context(self, session: QASession) -> Dict[str, Any]:
        """Get current session context"""
        try:
            # Get conversation history
            conversation_history = self._get_conversation_history(session)
            
            # Get user preferences and context
            user_context = session.context_data or {}
            
            # Get recent queries for context
            recent_queries = self._get_recent_queries(session)
            
            # Build context
            context = {
                'session_id': session.session_id,
                'user_context': user_context,
                'conversation_history': conversation_history,
                'recent_queries': recent_queries,
                'legal_domain_focus': user_context.get('legal_domain', 'general'),
                'court_focus': user_context.get('court_focus', 'all'),
                'language': user_context.get('language', 'en'),
                'session_metrics': {
                    'total_queries': session.total_queries,
                    'success_rate': session.success_rate,
                    'average_response_time': session.average_response_time
                }
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return {
                'session_id': session.session_id,
                'user_context': {},
                'conversation_history': [],
                'recent_queries': [],
                'legal_domain_focus': 'general',
                'court_focus': 'all',
                'language': 'en',
                'session_metrics': {}
            }
    
    def update_session_context(self, 
                              session: QASession, 
                              question: str, 
                              answer_result: Dict[str, Any]):
        """Update session context with new question and answer"""
        try:
            # Get current conversation history
            conversation_history = session.conversation_history or []
            
            # Add new conversation turn
            conversation_turn = {
                'timestamp': timezone.now().isoformat(),
                'question': question,
                'answer': answer_result.get('answer', ''),
                'answer_type': answer_result.get('answer_type', 'explanation'),
                'confidence': answer_result.get('confidence', 0.0),
                'sources_count': len(answer_result.get('sources', [])),
                'query_type': self._classify_query_type(question)
            }
            
            conversation_history.append(conversation_turn)
            
            # Limit history length
            if len(conversation_history) > self.max_history_items:
                conversation_history = conversation_history[-self.max_history_items:]
            
            # Update legal domain focus based on recent queries
            legal_domain_focus = self._update_legal_domain_focus(conversation_history)
            
            # Update court focus based on recent sources
            court_focus = self._update_court_focus(answer_result.get('sources', []))
            
            # Update session context data
            context_data = session.context_data or {}
            context_data.update({
                'legal_domain': legal_domain_focus,
                'court_focus': court_focus,
                'last_activity': timezone.now().isoformat(),
                'conversation_turns': len(conversation_history)
            })
            
            # Update session
            session.conversation_history = conversation_history
            session.context_data = context_data
            session.last_activity = timezone.now()
            session.save()
            
            logger.info(f"Updated session context for session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Error updating session context: {e}")
    
    def get_context_window(self, session: QASession, max_items: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation context for query processing"""
        try:
            conversation_history = session.conversation_history or []
            
            # Get recent conversation turns
            recent_turns = conversation_history[-max_items:] if conversation_history else []
            
            # Format for query processing
            context_window = []
            for turn in recent_turns:
                context_window.append({
                    'question': turn.get('question', ''),
                    'answer': turn.get('answer', ''),
                    'query_type': turn.get('query_type', 'general_legal'),
                    'timestamp': turn.get('timestamp', ''),
                    'confidence': turn.get('confidence', 0.0)
                })
            
            return context_window
            
        except Exception as e:
            logger.error(f"Error getting context window: {e}")
            return []
    
    def _get_conversation_history(self, session: QASession) -> List[Dict[str, Any]]:
        """Get formatted conversation history"""
        try:
            conversation_history = session.conversation_history or []
            
            # Apply decay factor to older conversations
            decayed_history = []
            for i, turn in enumerate(conversation_history):
                decay_factor = self.context_decay_factor ** (len(conversation_history) - i - 1)
                turn_copy = turn.copy()
                turn_copy['relevance_weight'] = decay_factor
                decayed_history.append(turn_copy)
            
            return decayed_history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def _get_recent_queries(self, session: QASession) -> List[Dict[str, Any]]:
        """Get recent queries for context"""
        try:
            recent_queries = QAQuery.objects.filter(
                session=session
            ).order_by('-created_at')[:5]
            
            query_context = []
            for query in recent_queries:
                query_context.append({
                    'query_text': query.query_text,
                    'query_type': query.query_type,
                    'status': query.status,
                    'created_at': query.created_at.isoformat(),
                    'processing_time': query.processing_time
                })
            
            return query_context
            
        except Exception as e:
            logger.error(f"Error getting recent queries: {e}")
            return []
    
    def _classify_query_type(self, question: str) -> str:
        """Classify query type for context"""
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
    
    def _update_legal_domain_focus(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Update legal domain focus based on conversation history"""
        try:
            if not conversation_history:
                return 'general'
            
            # Count query types
            query_type_counts = {}
            for turn in conversation_history:
                query_type = turn.get('query_type', 'general_legal')
                query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1
            
            # Determine dominant domain
            if not query_type_counts:
                return 'general'
            
            dominant_type = max(query_type_counts, key=query_type_counts.get)
            
            # Map query types to legal domains
            domain_mapping = {
                'case_inquiry': 'case_law',
                'law_research': 'statutory_law',
                'judge_inquiry': 'judicial_analysis',
                'lawyer_inquiry': 'legal_practice',
                'court_procedure': 'procedural_law',
                'citation_lookup': 'legal_research',
                'general_legal': 'general'
            }
            
            return domain_mapping.get(dominant_type, 'general')
            
        except Exception as e:
            logger.error(f"Error updating legal domain focus: {e}")
            return 'general'
    
    def _update_court_focus(self, sources: List[Dict[str, Any]]) -> str:
        """Update court focus based on recent sources"""
        try:
            if not sources:
                return 'all'
            
            # Count court mentions
            court_counts = {}
            for source in sources:
                court = source.get('court', '')
                if court:
                    court_counts[court] = court_counts.get(court, 0) + 1
            
            if not court_counts:
                return 'all'
            
            # Return most frequent court
            dominant_court = max(court_counts, key=court_counts.get)
            
            # Normalize court names
            court_mapping = {
                'Islamabad High Court': 'IHC',
                'Lahore High Court': 'LHC',
                'Sindh High Court': 'SHC',
                'Balochistan High Court': 'BHC',
                'Peshawar High Court': 'PHC',
                'Supreme Court': 'SC',
                'Federal Shariat Court': 'FSC'
            }
            
            return court_mapping.get(dominant_court, dominant_court)
            
        except Exception as e:
            logger.error(f"Error updating court focus: {e}")
            return 'all'
    
    def get_session_summary(self, session: QASession) -> Dict[str, Any]:
        """Get session summary for analytics"""
        try:
            conversation_history = session.conversation_history or []
            
            # Analyze conversation patterns
            query_types = [turn.get('query_type', 'general_legal') for turn in conversation_history]
            query_type_counts = {}
            for query_type in query_types:
                query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1
            
            # Calculate average confidence
            confidences = [turn.get('confidence', 0.0) for turn in conversation_history]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Get most common legal domain
            legal_domain = session.context_data.get('legal_domain', 'general')
            court_focus = session.context_data.get('court_focus', 'all')
            
            return {
                'session_id': session.session_id,
                'total_queries': session.total_queries,
                'success_rate': session.success_rate,
                'average_confidence': avg_confidence,
                'query_type_distribution': query_type_counts,
                'legal_domain_focus': legal_domain,
                'court_focus': court_focus,
                'session_duration': session.duration.total_seconds() if session.duration else 0,
                'last_activity': session.last_activity.isoformat() if session.last_activity else None
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            return {
                'session_id': session.session_id,
                'error': str(e)
            }
    
    def clear_session_context(self, session: QASession):
        """Clear session context (for privacy or reset)"""
        try:
            session.conversation_history = []
            session.context_data = {
                'legal_domain': 'general',
                'court_focus': 'all',
                'language': 'en',
                'cleared_at': timezone.now().isoformat()
            }
            session.save()
            
            logger.info(f"Cleared context for session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Error clearing session context: {e}")
    
    def export_session_context(self, session: QASession) -> Dict[str, Any]:
        """Export session context for analysis or backup"""
        try:
            return {
                'session_id': session.session_id,
                'user_id': session.user.id if session.user else None,
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat() if session.last_activity else None,
                'context_data': session.context_data,
                'conversation_history': session.conversation_history,
                'session_metrics': {
                    'total_queries': session.total_queries,
                    'successful_queries': session.successful_queries,
                    'success_rate': session.success_rate,
                    'average_response_time': session.average_response_time,
                    'user_satisfaction_score': session.user_satisfaction_score
                }
            }
            
        except Exception as e:
            logger.error(f"Error exporting session context: {e}")
            return {'error': str(e)}
    
    def is_healthy(self) -> bool:
        """Check if context manager is healthy"""
        try:
            # Simple health check
            return True
        except Exception as e:
            logger.error(f"Context manager health check failed: {e}")
            return False
