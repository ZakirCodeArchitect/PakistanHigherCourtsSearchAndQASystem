"""
Conversation Manager Service
Handles conversation memory, context retention, and follow-up query processing
"""

import uuid
import json
import re
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
                    # Create new session with the provided session_id
                    session = QASession.objects.create(
                        session_id=session_id,
                        user_id=user_id,
                        is_active=True
                    )
                    self.logger.info(f"Created new session with provided ID: {session_id}")
                    return session
            
            # Create new session with generated ID
            return self.create_session(user_id)
            
        except Exception as e:
            self.logger.error(f"Error getting/creating session: {str(e)}")
            raise
    
    def get_or_create_active_session_for_user(self, user_id: str) -> QASession:
        """
        Return the most recent active session for a user, or create a new one.
        Enables context persistence when clients don't pass session_id.
        """
        try:
            try:
                session = QASession.objects.filter(user_id=user_id, is_active=True).order_by('-created_at').first()
                if session:
                    return session
            except Exception:
                pass
            return self.create_session(user_id)
        except Exception as e:
            self.logger.error(f"Error getting/creating active session for user {user_id}: {e}")
            return self.create_session(user_id)
    
    def add_conversation_turn(self, session: QASession, query: str, response: str, 
                            context_documents: List[Dict] = None, 
                            query_id: int = None, response_id: int = None) -> None:
        """Add a conversation turn to the session"""
        try:
            # Create QAQuery if not provided
            if not query_id:
                qa_query = QAQuery.objects.create(
                    session=session,
                    query_text=query,
                    query_type="general"
                )
                query_id = qa_query.id
            else:
                qa_query = QAQuery.objects.get(id=query_id)
            
            # Create QAResponse if not provided
            if not response_id:
                qa_response = QAResponse.objects.create(
                    query=qa_query,
                    answer_text=response,
                    confidence_score=1.0,
                    answer_type="advanced_rag"
                )
                response_id = qa_response.id
            
            # Update session counters
            session.total_queries = session.queries.count()
            session.save()
            
            self.logger.info(f"Added conversation turn to session: {session.session_id}")
            
        except Exception as e:
            self.logger.error(f"Error adding conversation turn: {str(e)}")
            raise
    
    def get_conversation_context(self, session: QASession, max_turns: int = 5) -> Dict[str, Any]:
        """Get conversation context for follow-up queries"""
        try:
            # Get recent queries and responses
            recent_queries = session.queries.order_by('-created_at')[:max_turns]
            recent_responses = QAResponse.objects.filter(query__session=session).order_by('-created_at')[:max_turns]
            
            self.logger.info(f"Found {len(recent_queries)} queries and {len(recent_responses)} responses for session {session.session_id}")
            
            # Build recent turns
            recent_turns = []
            for query, response in zip(reversed(recent_queries), reversed(recent_responses)):
                recent_turns.append({
                    'query': query.query_text,
                    'response': response.answer_text,
                    'timestamp': query.created_at.isoformat(),
                    'query_type': query.query_type
                })
            
            context = {
                'recent_turns': recent_turns,
                'context_summary': f"Session with {session.total_queries} queries",
                'topics': [q.query_type for q in recent_queries[:3]],
                'session_info': {
                    'session_id': session.session_id,
                    'total_queries': session.total_queries,
                    'total_responses': QAResponse.objects.filter(query__session=session).count(),
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat()
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
            active_case = context.get('active_case_context', {})
            
            if not recent_turns:
                return query
            
            # Get the most recent query and response
            last_turn = recent_turns[-1]
            last_query = last_turn.get('query', '')
            last_response = last_turn.get('response', '')
            
            # Extract case number from previous conversation
            case_number = self._extract_case_number_from_conversation(recent_turns)
            if not case_number and isinstance(active_case, dict):
                case_number = active_case.get('case_number')
            
            # Enhance query based on context
            enhanced_query = query
            
            # If query references "this case" or similar, and we found a case number, use it
            if ('this' in query.lower() or 'that' in query.lower() or 'it' in query.lower()) and case_number:
                # Replace pronoun references with actual case number
                enhanced_query = f"{query.replace('this case', case_number).replace('that case', case_number).replace('it', case_number)} {case_number}"
            elif case_number and any(word in query.lower() for word in ['details', 'information', 'about', 'tell me', 'give me']):
                # For general follow-up questions, append the case number
                enhanced_query = f"{query} {case_number}"
            elif 'it' in query.lower() or 'this' in query.lower():
                # Fallback: add context reference
                enhanced_query = f"{query} (referring to: {last_query})"
            
            # Add topic context
            if topics:
                topic_context = f" (topics: {', '.join(topics)})"
                enhanced_query += topic_context
            
            return enhanced_query
            
        except Exception as e:
            self.logger.error(f"Error enhancing query with context: {str(e)}")
            return query
    
    # ==== Active Case Context storage ====
    def set_active_case_context(self, session: QASession, case_context: Dict[str, Any]) -> None:
        """Persist active case context (case_id/number/title + extracted fields and short summary)"""
        try:
            data = session.context_data or {}
            data['active_case_context'] = {
                'case_id': case_context.get('case_id'),
                'case_number': case_context.get('case_number'),
                'case_title': case_context.get('case_title'),
                'court': case_context.get('court'),
                'bench': case_context.get('bench'),
                'status': case_context.get('status'),
                'advocates_petitioner': case_context.get('advocates_petitioner'),
                'advocates_respondent': case_context.get('advocates_respondent'),
                'short_order': case_context.get('short_order'),
                'case_stage': case_context.get('case_stage'),
                'summary': case_context.get('summary'),
                'sources': case_context.get('sources', []),
            }
            session.context_data = data
            session.save(update_fields=['context_data'])
        except Exception as e:
            self.logger.warning(f"Failed to set active_case_context: {e}")
    
    def clear_active_case_context(self, session: QASession) -> None:
        try:
            data = session.context_data or {}
            if 'active_case_context' in data:
                del data['active_case_context']
                session.context_data = data
                session.save(update_fields=['context_data'])
        except Exception as e:
            self.logger.warning(f"Failed to clear active_case_context: {e}")
    
    def get_active_case_context(self, session: QASession) -> Dict[str, Any]:
        try:
            data = session.context_data or {}
            return data.get('active_case_context', {}) or {}
        except Exception:
            return {}
    
    def _extract_case_number_from_conversation(self, recent_turns: List[Dict]) -> Optional[str]:
        """Extract case number from conversation history"""
        
        # Check all recent turns for case numbers
        for turn in reversed(recent_turns):  # Start from most recent
            query = turn.get('query', '')
            response = turn.get('response', '')
            
            # Pattern to match case numbers like:
            # "T.A. 2/2023 Civil (SB)"
            # "Crl. Org. 5/2025 Writ (SB)"
            # "C.O. 1/2025 Others (SB)"
            # More flexible pattern: [Letters][.] [Number]/[Number] [Word] [(Letters)]
            case_pattern = r'([A-Z][a-z]?\.?\s*\d+/\d+\s+[A-Za-z]+(?:\s*\([A-Z]+\))?)'
            
            # Also check for case numbers in sources metadata
            sources = turn.get('sources', [])
            if sources:
                for source in sources:
                    if isinstance(source, dict):
                        case_num = source.get('case_number') or source.get('case')
                        if case_num:
                            return str(case_num).strip()
            
            # Check query first
            matches = re.findall(case_pattern, query)
            if matches:
                return matches[0].strip()
            
            # Check response
            matches = re.findall(case_pattern, response)
            if matches:
                return matches[0].strip()
        
        return None
    
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
            
            # Filter and prioritize sources
            filtered_sources = self._filter_and_prioritize_sources(sources)
            
            for source in filtered_sources:
                formatted_source = self._format_single_citation(source)
                formatted_sources.append(formatted_source)
            
            return formatted_sources
            
        except Exception as e:
            self.logger.error(f"Error formatting citations: {str(e)}")
            return sources
    
    def _filter_and_prioritize_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and prioritize sources to show the best ones first"""
        try:
            if not sources:
                return sources
            
            # Separate high-quality and low-quality sources
            high_quality_sources = []
            low_quality_sources = []
            
            for source in sources:
                # Check if it's a high-quality source (has proper case title, court, etc.)
                case_title = source.get('case_title', '')
                court = source.get('court', '')
                case_number = source.get('case_number', '')
                
                # High quality if it has proper case information
                if (case_title and case_title not in ['Unknown Case', 'N/A', ''] and 
                    court and court not in ['Unknown Court', 'N/A', ''] and
                    case_number and case_number not in ['N/A', '']):
                    high_quality_sources.append(source)
                else:
                    low_quality_sources.append(source)
            
            # Sort high-quality sources by relevance score
            high_quality_sources.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Sort low-quality sources by relevance score
            low_quality_sources.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Combine: high-quality first, then low-quality (but limit low-quality)
            combined_sources = high_quality_sources.copy()
            
            # Only add low-quality sources if we have very few high-quality sources
            # And only if they have some meaningful content
            if len(high_quality_sources) < 2:
                # Only add low-quality sources that have some meaningful content
                meaningful_low_quality = []
                for source in low_quality_sources[:3]:
                    text_content = source.get('text', '')
                    if text_content and len(text_content) > 100:
                        # Check if it has some legal content
                        if any(keyword in text_content.lower() for keyword in ['court', 'case', 'petition', 'law', 'legal', 'judge', 'order']):
                            meaningful_low_quality.append(source)
                
                combined_sources.extend(meaningful_low_quality[:2])
            
            # If we still have no sources, add the best available
            if len(combined_sources) == 0 and len(sources) > 0:
                combined_sources = sources[:3]  # Take top 3 as fallback
            
            # Limit total sources to 5 for better UI
            return combined_sources[:5]
            
        except Exception as e:
            self.logger.error(f"Error filtering sources: {str(e)}")
            return sources
    
    def _format_single_citation(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single legal citation"""
        try:
            # Get metadata if available (handle both dict and list cases)
            metadata = source.get('metadata', {})
            if isinstance(metadata, list):
                metadata = {}
            
            # Use the best available score (prioritize normalized scores)
            # Ensure all scores are Python floats to avoid JSON serialization issues
            relevance_score = float(
                source.get('normalized_rerank_score') or 
                source.get('combined_score') or 
                source.get('rerank_score') or 
                source.get('score', 0.0)
            )
            
            # Generate better title based on available information
            title = self._generate_better_title(source, metadata)
            
            # Enhanced metadata extraction
            enhanced_metadata = self._extract_enhanced_metadata(source, metadata)
            
            citation = {
            'title': title,
            'case_number': enhanced_metadata.get('case_number', 'N/A'),
            'court': enhanced_metadata.get('court', 'Unknown Court'),
            'date': enhanced_metadata.get('date', 'N/A'),
            'judge': enhanced_metadata.get('judge', 'Unknown Judge'),
            'relevance_score': relevance_score,  # Use the best available normalized score
            'score': relevance_score,  # Preserve the main score field
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
    
    def _generate_better_title(self, source: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Generate a better title for the source based on available information"""
        try:
            # Get source type to determine formatting strategy
            source_type = source.get('source_type', '') or metadata.get('source_type', '')
            
            # Get case title from BOTH source and metadata (retrieval service puts it in both places)
            case_title = source.get('case_title') or metadata.get('case_title')
            
            # SIMPLE APPROACH: Just show the original case title and document info
            
            # For document chunks and document texts, show case title + document info
            if source_type in ['document_chunk', 'document_text']:
                return self._format_simple_document_title(source, metadata, case_title)
            
            # For unified_case_view and case_metadata, use case title directly
            if source_type in ['unified_case_view', 'case_metadata']:
                if case_title and case_title not in ['Unknown Case', 'N/A', '', 'Document Content']:
                    return case_title
            
            # FALLBACK: If we have a proper case title but no source type, use the case title
            if case_title and case_title not in ['Unknown Case', 'N/A', '', 'Document Content']:
                return case_title
            
            # Final fallback to generic title
            return "Legal Document"
            
        except Exception as e:
            self.logger.error(f"Error generating better title: {str(e)}")
            return "Legal Document"
    
    def _format_simple_document_title(self, source: Dict[str, Any], metadata: Dict[str, Any], case_title: str) -> str:
        """Simple formatting: show original case title + document info"""
        try:
            source_type = source.get('source_type', '') or metadata.get('source_type', '')
            
            # Check if case_title is generic (like "Document 133 - Text Content")
            is_generic_title = (case_title and case_title != '' and
                              ('Document' in case_title and 'Text Content' in case_title) or
                              case_title.startswith('Document ') or
                              case_title == 'Document Content')
            
            # Get document information
            document_info = self._get_document_info(source, metadata)
            
            # SIMPLE LOGIC: Just show the case title if we have it!
            if case_title and case_title not in ['Unknown Case', 'N/A', ''] and not is_generic_title:
                # We have a proper case title - just show it (don't worry about file names)
                return case_title
            else:
                # No proper case title - try to get case number as fallback (check both locations)
                case_number = source.get('case_number') or metadata.get('case_number')
                if case_number and case_number not in ['N/A', '']:
                    return f"Legal Document - Case {case_number}"
                else:
                    return "Legal Document"
                    
        except Exception as e:
            self.logger.error(f"Error formatting simple document title: {str(e)}")
            return "Legal Document"
    
    def _get_document_info(self, source: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Get document information for formatting"""
        try:
            # Try to get document info from metadata
            document_id = source.get('document_id') or metadata.get('document_id')
            file_name = source.get('file_name') or metadata.get('file_name')
            page_number = source.get('page_number') or metadata.get('page_number')
            
            # If we have document info, format it nicely
            if file_name and file_name != 'N/A':
                # Clean up the file name
                clean_filename = file_name.replace('_', ' ').replace('.pdf', '').title()
                if page_number and page_number != 'N/A':
                    return f"{clean_filename} (Page {page_number})"
                else:
                    return clean_filename
            
            # Try to get chunk/page info
            chunk_index = source.get('chunk_index') or metadata.get('chunk_index')
            if chunk_index is not None:
                return f"Document (Chunk {chunk_index})"
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error getting document info: {str(e)}")
            return ""
    
    
    def _clean_case_title(self, title: str) -> str:
        """Clean and format case titles"""
        try:
            # Remove common prefixes and suffixes
            clean_title = title.strip()
            
            # Remove common legal prefixes
            prefixes_to_remove = [
                'IN THE MATTER OF:',
                'IN RE:',
                'IN THE CASE OF:',
                'CASE NO:',
                'CASE NUMBER:',
                'PETITION NO:',
                'PETITION NUMBER:',
                'APPLICATION NO:',
                'APPLICATION NUMBER:'
            ]
            
            for prefix in prefixes_to_remove:
                if clean_title.upper().startswith(prefix):
                    clean_title = clean_title[len(prefix):].strip()
            
            # Remove common suffixes
            suffixes_to_remove = [
                'PETITION',
                'APPLICATION',
                'CASE',
                'MATTER'
            ]
            
            for suffix in suffixes_to_remove:
                if clean_title.upper().endswith(suffix):
                    clean_title = clean_title[:-len(suffix)].strip()
            
            # Clean up extra spaces and special characters
            clean_title = ' '.join(clean_title.split())
            
            # Limit length
            if len(clean_title) > 120:
                clean_title = clean_title[:120].strip()
            
            return clean_title if len(clean_title) > 5 else None
            
        except Exception as e:
            self.logger.error(f"Error cleaning case title: {str(e)}")
            return None
    
    def _extract_enhanced_metadata(self, source: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, str]:
        """Extract enhanced metadata from source and content"""
        try:
            enhanced_metadata = {
                'case_number': 'N/A',
                'court': 'Unknown Court',
                'date': 'N/A',
                'judge': 'Unknown Judge',
                'document_id': 'N/A',
                'file_name': 'N/A',
                'page_number': 'N/A',
                'chunk_index': 'N/A'
            }
            
            # Try to get metadata from source first
            case_number = source.get('case_number') or metadata.get('case_number')
            court = source.get('court') or metadata.get('court')
            date = source.get('date_decided') or metadata.get('institution_date') or source.get('institution_date')
            judge = source.get('judge_name') or metadata.get('judge')
            
            # Document-specific metadata
            document_id = source.get('document_id') or metadata.get('document_id')
            file_name = source.get('file_name') or metadata.get('file_name')
            page_number = source.get('page_number') or metadata.get('page_number')
            chunk_index = source.get('chunk_index') or metadata.get('chunk_index')
            
            # If we have good metadata, use it
            if case_number and case_number not in ['N/A', '']:
                enhanced_metadata['case_number'] = case_number
            if court and court not in ['Unknown Court', 'N/A', '']:
                enhanced_metadata['court'] = court
            if date and date not in ['N/A', '']:
                enhanced_metadata['date'] = date
            if judge and judge not in ['Unknown Judge', 'N/A', '']:
                enhanced_metadata['judge'] = judge
            
            # Document metadata
            if document_id and document_id not in ['N/A', '']:
                enhanced_metadata['document_id'] = document_id
            if file_name and file_name not in ['N/A', '']:
                enhanced_metadata['file_name'] = file_name
            if page_number and page_number not in ['N/A', '']:
                enhanced_metadata['page_number'] = page_number
            if chunk_index is not None and chunk_index != 'N/A':
                enhanced_metadata['chunk_index'] = chunk_index
            
            # If metadata is missing, try to extract from content
            text_content = source.get('text', '')
            if text_content and len(text_content) > 100:
                content_metadata = self._extract_metadata_from_content(text_content)
                
                # Use content metadata if source metadata is missing
                if enhanced_metadata['case_number'] == 'N/A' and content_metadata.get('case_number'):
                    enhanced_metadata['case_number'] = content_metadata['case_number']
                
                if enhanced_metadata['court'] == 'Unknown Court' and content_metadata.get('court'):
                    enhanced_metadata['court'] = content_metadata['court']
                
                if enhanced_metadata['date'] == 'N/A' and content_metadata.get('date'):
                    enhanced_metadata['date'] = content_metadata['date']
                
                if enhanced_metadata['judge'] == 'Unknown Judge' and content_metadata.get('judge'):
                    enhanced_metadata['judge'] = content_metadata['judge']
            
            return enhanced_metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting enhanced metadata: {str(e)}")
            return {
                'case_number': 'N/A',
                'court': 'Unknown Court',
                'date': 'N/A',
                'judge': 'Unknown Judge',
                'document_id': 'N/A',
                'file_name': 'N/A',
                'page_number': 'N/A',
                'chunk_index': 'N/A'
            }
    
    def _extract_metadata_from_content(self, text_content: str) -> Dict[str, str]:
        """Extract metadata from document content"""
        try:
            import re
            metadata = {}
            lines = text_content.split('\n')
            
            # Look for case numbers
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                if any(pattern in line.lower() for pattern in ['case no', 'case number', 'petition no', 'application no']):
                    # Extract case number
                    import re
                    case_patterns = [
                        r'case\s+no[.:]?\s*([A-Z0-9/\-]+)',
                        r'case\s+number[.:]?\s*([A-Z0-9/\-]+)',
                        r'petition\s+no[.:]?\s*([A-Z0-9/\-]+)',
                        r'application\s+no[.:]?\s*([A-Z0-9/\-]+)'
                    ]
                    
                    for pattern in case_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            metadata['case_number'] = match.group(1).strip()
                            break
            
            # Look for court information
            for line in lines[:20]:
                line = line.strip()
                if any(court in line.lower() for court in ['high court', 'supreme court', 'district court', 'session court']):
                    # Extract court name
                    court_patterns = [
                        r'([A-Za-z\s]+High Court)',
                        r'([A-Za-z\s]+Supreme Court)',
                        r'([A-Za-z\s]+District Court)',
                        r'([A-Za-z\s]+Session Court)'
                    ]
                    
                    for pattern in court_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            metadata['court'] = match.group(1).strip()
                            break
            
            # Look for dates
            for line in lines[:20]:
                line = line.strip()
                # Look for date patterns
                date_patterns = [
                    r'(\d{1,2}[-\/]\d{1,2}[-\/]\d{4})',
                    r'(\d{4}[-\/]\d{1,2}[-\/]\d{1,2})',
                    r'(\d{1,2}\s+\w+\s+\d{4})'
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        metadata['date'] = match.group(1).strip()
                        break
            
            # Look for judge names
            for line in lines[:20]:
                line = line.strip()
                if any(keyword in line.lower() for keyword in ['justice', 'judge', 'honourable']):
                    # Extract judge name
                    judge_patterns = [
                        r'justice\s+([A-Za-z\s]+)',
                        r'judge\s+([A-Za-z\s]+)',
                        r'honourable\s+([A-Za-z\s]+)'
                    ]
                    
                    for pattern in judge_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            judge_name = match.group(1).strip()
                            if len(judge_name) > 3:  # Valid name length
                                metadata['judge'] = judge_name
                                break
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting metadata from content: {str(e)}")
            return {}
    
    def _extract_court_from_filename(self, filename: str) -> str:
        """Extract court information from filename"""
        try:
            if not filename or filename == 'Unknown Court':
                return 'Unknown Court'
            
            # Common court patterns in Pakistani legal documents
            if 'lahore' in filename.lower():
                return 'Lahore High Court'
            elif 'karachi' in filename.lower():
                return 'Karachi High Court'
            elif 'islamabad' in filename.lower():
                return 'Islamabad High Court'
            elif 'peshawar' in filename.lower():
                return 'Peshawar High Court'
            elif 'quetta' in filename.lower():
                return 'Balochistan High Court'
            elif 'sindh' in filename.lower():
                return 'Sindh High Court'
            elif 'punjab' in filename.lower():
                return 'Punjab High Court'
            elif 'kpk' in filename.lower() or 'khyber' in filename.lower():
                return 'Khyber Pakhtunkhwa High Court'
            else:
                # Try to extract from case number patterns
                if 'SB' in filename:
                    return 'Supreme Court (Single Bench)'
                elif 'DB' in filename:
                    return 'Supreme Court (Division Bench)'
                elif 'FB' in filename:
                    return 'Supreme Court (Full Bench)'
                else:
                    return 'High Court'
        except Exception:
            return 'Unknown Court'
    
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
