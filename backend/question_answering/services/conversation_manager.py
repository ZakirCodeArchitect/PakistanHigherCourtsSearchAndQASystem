"""
Conversation Manager Service
Handles conversation memory, context retention, and follow-up query processing
"""

import uuid
import json
from typing import Dict, List, Any, Optional, Tuple
from django.contrib.auth.models import User
from django.utils import timezone
from qa_app.models import QASession, QAQuery, QAResponse
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation sessions and context retention"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, user_id: str, title: str = None, description: str = None) -> QASession:
        """Create a new conversation session"""
        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create session
            session = QASession.objects.create(
                session_id=session_id,
                user_id=user_id,
                title=title or f"Legal QA Session {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                description=description or "Legal question-answering session",
                context_data={},
                conversation_history=[],
                is_active=True
            )
            
            self.logger.info(f"Created new session: {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            raise
    
    def get_or_create_session(self, user_id: str, session_id: str = None) -> QASession:
        """Get existing session or create new one"""
        try:
            if session_id:
                try:
                    session = QASession.objects.get(session_id=session_id, is_active=True)
                    return session
                except QASession.DoesNotExist:
                    pass
            
            # Create new session
            return self.create_session(user_id)
            
        except Exception as e:
            self.logger.error(f"Error getting/creating session: {str(e)}")
            raise
    
    def add_conversation_turn(self, session: QASession, query: str, response: str, 
                            context_documents: List[Dict] = None, 
                            query_id: int = None, response_id: int = None) -> None:
        """Add a conversation turn to the session"""
        try:
            session.add_conversation_turn(
                query=query,
                response=response,
                context_documents=context_documents or [],
                query_id=query_id,
                response_id=response_id
            )
            
            self.logger.info(f"Added conversation turn to session: {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Error adding conversation turn: {str(e)}")
            raise
    
    def get_conversation_context(self, session: QASession, max_turns: int = 5) -> Dict[str, Any]:
        """Get conversation context for follow-up queries"""
        try:
            context = {
                'recent_turns': session.get_recent_context(max_turns),
                'context_summary': session.get_context_summary(3),
                'topics': session.get_conversation_topics(),
                'session_info': {
                    'session_id': session.session_id,
                    'total_queries': session.total_queries,
                    'success_rate': session.success_rate,
                    'duration': str(session.duration),
                    'last_activity': session.last_activity.isoformat() if session.last_activity else None
                }
            }
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return {}
    
    def process_follow_up_query(self, session: QASession, query: str) -> Dict[str, Any]:
        """Process a follow-up query with conversation context"""
        try:
            # Get conversation context
            context = self.get_conversation_context(session)
            
            # Analyze query for follow-up indicators
            follow_up_indicators = self._detect_follow_up_indicators(query)
            
            # Enhance query with context
            enhanced_query = self._enhance_query_with_context(query, context)
            
            return {
                'original_query': query,
                'enhanced_query': enhanced_query,
                'follow_up_indicators': follow_up_indicators,
                'conversation_context': context,
                'is_follow_up': len(follow_up_indicators) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Error processing follow-up query: {str(e)}")
            return {
                'original_query': query,
                'enhanced_query': query,
                'follow_up_indicators': [],
                'conversation_context': {},
                'is_follow_up': False
            }
    
    def _detect_follow_up_indicators(self, query: str) -> List[str]:
        """Detect follow-up query indicators"""
        indicators = []
        query_lower = query.lower()
        
        # Pronouns and references
        if any(word in query_lower for word in ['it', 'this', 'that', 'these', 'those']):
            indicators.append('pronoun_reference')
        
        # Follow-up phrases
        follow_up_phrases = [
            'what about', 'how about', 'what if', 'can you explain more',
            'tell me more', 'give me more details', 'elaborate',
            'what else', 'anything else', 'further information'
        ]
        
        for phrase in follow_up_phrases:
            if phrase in query_lower:
                indicators.append('follow_up_phrase')
                break
        
        # Question words without context
        if query_lower.startswith(('what', 'how', 'when', 'where', 'why', 'who')) and len(query.split()) < 5:
            indicators.append('incomplete_question')
        
        # Comparative questions
        if any(word in query_lower for word in ['compare', 'difference', 'similar', 'versus', 'vs']):
            indicators.append('comparative_question')
        
        return indicators
    
    def _enhance_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
        """Enhance query with conversation context"""
        try:
            recent_turns = context.get('recent_turns', [])
            topics = context.get('topics', [])
            
            if not recent_turns:
                return query
            
            # Get the most recent query and response
            last_turn = recent_turns[-1]
            last_query = last_turn.get('query', '')
            last_response = last_turn.get('response', '')
            
            # Enhance query based on context
            enhanced_query = query
            
            # Add context for pronoun references
            if 'it' in query.lower() or 'this' in query.lower():
                enhanced_query = f"{query} (referring to: {last_query})"
            
            # Add topic context
            if topics:
                topic_context = f" (topics: {', '.join(topics)})"
                enhanced_query += topic_context
            
            return enhanced_query
            
        except Exception as e:
            self.logger.error(f"Error enhancing query with context: {str(e)}")
            return query
    
    def get_session_history(self, session: QASession) -> List[Dict[str, Any]]:
        """Get formatted session history"""
        try:
            history = []
            for turn in session.conversation_history:
                history.append({
                    'timestamp': turn.get('timestamp'),
                    'query': turn.get('query'),
                    'response': turn.get('response'),
                    'context_documents': turn.get('context_documents', []),
                    'query_id': turn.get('query_id'),
                    'response_id': turn.get('response_id')
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Error getting session history: {str(e)}")
            return []
    
    def archive_session(self, session: QASession) -> None:
        """Archive a conversation session"""
        try:
            session.is_active = False
            session.is_archived = True
            session.save()
            
            self.logger.info(f"Archived session: {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Error archiving session: {str(e)}")
            raise
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[QASession]:
        """Get user's conversation sessions"""
        try:
            sessions = QASession.objects.filter(user_id=user_id)
            
            if active_only:
                sessions = sessions.filter(is_active=True)
            
            return sessions.order_by('-last_activity')
            
        except Exception as e:
            self.logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    def get_session_statistics(self, session: QASession) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            stats = {
                'session_id': session.session_id,
                'total_queries': session.total_queries,
                'successful_queries': session.successful_queries,
                'success_rate': session.success_rate,
                'average_response_time': session.average_response_time,
                'user_satisfaction_score': session.user_satisfaction_score,
                'duration': str(session.duration),
                'topics': session.get_conversation_topics(),
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat() if session.last_activity else None
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting session statistics: {str(e)}")
            return {}


class CitationFormatter:
    """Formats legal citations in responses"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def format_citations(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format legal citations from source documents"""
        try:
            formatted_sources = []
            
            for source in sources:
                formatted_source = self._format_single_citation(source)
                formatted_sources.append(formatted_source)
            
            return formatted_sources
            
        except Exception as e:
            self.logger.error(f"Error formatting citations: {str(e)}")
            return sources
    
    def _format_single_citation(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single legal citation"""
        try:
            citation = {
                'title': source.get('title', 'Unknown Case'),
                'case_number': source.get('case_number', 'N/A'),
                'court': source.get('court', 'Unknown Court'),
                'date': source.get('date_decided', 'N/A'),
                'judge': source.get('judge_name', 'Unknown Judge'),
                'relevance_score': source.get('score', 0.0),
                'legal_domain': source.get('legal_domain', 'General'),
                'formatted_citation': self._create_formatted_citation(source),
                'download_link': self._create_download_link(source),
                'metadata': {
                    'case_id': source.get('case_id'),
                    'document_id': source.get('document_id'),
                    'content_type': source.get('content_type', 'unknown')
                }
            }
            
            return citation
            
        except Exception as e:
            self.logger.error(f"Error formatting single citation: {str(e)}")
            return source
    
    def _create_formatted_citation(self, source: Dict[str, Any]) -> str:
        """Create a properly formatted legal citation"""
        try:
            case_title = source.get('case_title', source.get('title', 'Unknown Case'))
            case_number = source.get('case_number', 'N/A')
            court = source.get('court', 'Unknown Court')
            date = source.get('date_decided', 'N/A')
            
            # Format: Case Title v. Case Title, Case Number (Court Year)
            citation = f"{case_title}, {case_number} ({court} {date})"
            
            return citation
            
        except Exception as e:
            self.logger.error(f"Error creating formatted citation: {str(e)}")
            return "Citation format error"
    
    def _create_download_link(self, source: Dict[str, Any]) -> str:
        """Create download link for document"""
        try:
            case_id = source.get('case_id')
            document_id = source.get('document_id')
            
            if document_id:
                return f"/api/qa/download/{document_id}/"
            elif case_id:
                return f"/api/qa/download/case/{case_id}/"
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Error creating download link: {str(e)}")
            return ""
