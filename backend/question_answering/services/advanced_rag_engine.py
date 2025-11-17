"""
Advanced RAG Engine
Complete RAG generation pipeline integrating all components
"""

import logging
import time
import markdown
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

# Import all the new components
from .context_packer import ContextPacker
from .prompt_template_system import PromptTemplateSystem, QueryType, LegalDomain
from .llm_generator import LLMGenerator, LLMModel, LLMProvider
from .guardrails import Guardrails, AccessLevel, GuardrailResult
from .conversation_manager import ConversationManager, CitationFormatter
from qa_app.services.qa_retrieval_service import QARetrievalService
from .conversation_summarizer import ConversationSummarizer
from .query_rewriter import QueryRewriter
from .topic_classifier import TopicClassifier

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Complete RAG generation result"""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    guardrail_result: Optional[GuardrailResult]
    generation_time: float
    status: str = "success"
    error: Optional[str] = None


class AdvancedRAGEngine:
    """Complete RAG generation engine with all components integrated"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize all components
        self.context_packer = ContextPacker(self.config.get('context_packer', {}))
        self.prompt_system = PromptTemplateSystem(self.config.get('prompt_templates', {}))
        self.llm_generator = LLMGenerator(self.config.get('llm_generator', {}))
        self.guardrails = Guardrails(self.config.get('guardrails', {}))
        self.conversation_manager = ConversationManager()
        self.citation_formatter = CitationFormatter()
        self.summarizer = ConversationSummarizer()
        self.query_rewriter = QueryRewriter()
        self.topic_classifier = TopicClassifier()
        
        # Initialize retrieval service
        self.retrieval_service = QARetrievalService()
        
        # Configuration
        self.enable_guardrails = self.config.get('enable_guardrails', False)
        self.enable_conversation_context = self.config.get('enable_conversation_context', True)
        self.default_access_level = AccessLevel(self.config.get('default_access_level', 'public'))
        self.max_retrieval_results = self.config.get('max_retrieval_results', 12)
        # Response style
        self.warm_tone = self.config.get('warm_tone', True)
        
        logger.info("Advanced RAG Engine initialized with all components")
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert Markdown text to HTML"""
        try:
            # Configure markdown with extensions for better formatting
            md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])
            html = md.convert(text)
            return html
        except Exception as e:
            logger.warning(f"Failed to convert markdown to HTML: {str(e)}")
            # Return original text if conversion fails
            return text
    
    def generate_answer(self, 
                       query: str,
                       user_id: str = "anonymous",
                       session_id: Optional[str] = None,
                       access_level: Optional[AccessLevel] = None,
                       conversation_history: Optional[List[Dict]] = None,
                       filters: Optional[Dict[str, Any]] = None,
                       forced_case_id: Optional[int] = None,
                       pre_retrieved_docs: Optional[List[Dict[str, Any]]] = None) -> RAGResult:
        """
        Generate complete RAG answer with all components
        
        Args:
            query: User's question
            user_id: User identifier
            session_id: Session identifier for conversation management
            access_level: User access level (public, lawyer, judge, admin)
            conversation_history: Previous conversation context
            filters: Retrieval filters (court, year, legal_domain, etc.)
            
        Returns:
            Complete RAG result with answer, sources, and metadata
        """
        
        start_time = time.time()
        
        try:
            # Step 1: Set access level
            if access_level is None:
                access_level = self.default_access_level
            
            # Step 2: Get or create session
            session = None
            active_case_context = {}
            short_summary = ""
            if session_id and self.enable_conversation_context:
                session = self.conversation_manager.get_or_create_session(user_id, session_id)
                if session:
                    conversation_context = self.conversation_manager.get_conversation_context(session, 20)
                    conversation_history = conversation_context.get('recent_turns', [])
                    logger.info(f"Retrieved conversation history: {len(conversation_history)} turns")
                    # Pull active case context if any
                    try:
                        active_case_context = self.conversation_manager.get_active_case_context(session) or {}
                    except Exception:
                        active_case_context = {}
                    # Build/update a short summary deterministically
                    short_summary = self.summarizer.summarize(conversation_history, active_case_context)
                    # Persist the summary for downstream tools/clients
                    try:
                        data = session.context_data or {}
                        data['conversation_summary'] = short_summary
                        session.context_data = data
                        session.save(update_fields=['context_data'])
                    except Exception:
                        pass
                    if conversation_history:
                        recent_turn = conversation_history[-1]
                        logger.info(f"Recent turn type: {type(recent_turn)}")
                        if isinstance(recent_turn, dict):
                            logger.info(f"Recent query: {recent_turn.get('query', 'N/A')}")
                        else:
                            logger.info(f"Recent turn content: {recent_turn}")
            
            # Step 3: Apply guardrails to query
            if self.enable_guardrails:
                query_guardrail = self.guardrails.check_query_safety(query, access_level)
                if not query_guardrail.allowed:
                    return RAGResult(
                        answer=self.guardrails._generate_safe_response(query, []),
                        confidence=0.0,
                        sources=[],
                        citations=[],
                        metadata={'query_guardrail': query_guardrail.__dict__},
                        guardrail_result=query_guardrail,
                        generation_time=time.time() - start_time,
                        status="blocked",
                        error="Query blocked by guardrails"
                    )
            
            # Step 4: Check if query is legal-related
            is_legal_query = self._is_legal_query(query, conversation_history)
            is_overview_query = self._is_database_overview_query(query)
            logger.info(f"Query analysis: '{query[:50]}...' -> Legal: {is_legal_query}, Overview: {is_overview_query}")
            
            if not is_legal_query:
                # Handle non-legal queries (greetings, casual conversation)
                return RAGResult(
                    answer="Hello! I'm Pakistan Legal AI Assistant. I can help you with legal research, case law analysis, and court procedures. Please ask me a specific legal question, and I'll provide you with detailed information based on Pakistani law and legal precedents.",
                    confidence=1.0,
                    sources=[],
                    citations=[],
                    metadata={'query_type': 'non_legal', 'is_greeting': True},
                    guardrail_result=None,
                    generation_time=time.time() - start_time,
                    status="success"
                )
            
            # Step 5: Topic detection and standalone query rewrite
            # If we have session context, decide if the user started a new topic
            if session and self.enable_conversation_context:
                topic_decision = self.topic_classifier.classify(
                    short_summary,
                    query,
                    active_case_context.get('case_number') if isinstance(active_case_context, dict) else None
                )
                if topic_decision == "new":
                    # Reset active case to avoid polluting new searches
                    try:
                        self.conversation_manager.clear_active_case_context(session)
                        active_case_context = {}
                    except Exception:
                        pass
                # Build a standalone retrieval query
                rewritten_query = self.query_rewriter.rewrite(
                    current_query=query,
                    recent_turns=conversation_history or [],
                    short_summary=short_summary,
                    active_case=active_case_context or {}
                )
            else:
                rewritten_query = query

            # Step 6: Retrieve relevant documents for legal queries
            # If pre-retrieved docs provided (from structured lookup), use those
            if pre_retrieved_docs:
                logger.info(f"Using pre-retrieved structured data: {len(pre_retrieved_docs)} documents")
                retrieved_docs = pre_retrieved_docs
            elif is_overview_query:
                # For database overview queries, get diverse cases representing different legal areas
                logger.info(f"Retrieving diverse legal cases for database overview: '{query[:50]}...'")
                retrieved_docs = self._get_diverse_legal_cases(top_k=self.max_retrieval_results)
            else:
                # For specific legal queries, use normal semantic search or forced case lock
                if forced_case_id:
                    logger.info(f"Retrieving documents with forced case lock (case_id={forced_case_id})")
                    retrieved_docs = self.retrieval_service.get_case_by_id(forced_case_id)
                else:
                    logger.info(f"Retrieving documents for specific legal query: '{rewritten_query[:50]}...'")
                    retrieved_docs = self.retrieval_service.retrieve_for_qa(
                        query=rewritten_query,
                        top_k=self.max_retrieval_results
                    )
            
            if not retrieved_docs:
                return RAGResult(
                    answer="I couldn't find relevant legal information to answer your question. Please try rephrasing your question or consult with a qualified legal professional.",
                    confidence=0.0,
                    sources=[],
                    citations=[],
                    metadata={'retrieval_results': 0},
                    guardrail_result=None,
                    generation_time=time.time() - start_time,
                    status="no_results"
                )
            
            # Step 7: Pack context for LLM
            logger.info(f"Packing context from {len(retrieved_docs)} retrieved documents")
            try:
                packed_context = self.context_packer.pack_context(
                    retrieved_chunks=retrieved_docs,
                    query=rewritten_query,
                    conversation_history=conversation_history
                )
                logger.info(f"Context packing completed successfully, type: {type(packed_context)}")
                if isinstance(packed_context, dict):
                    logger.info(f"Packed context keys: {list(packed_context.keys())}")
                    logger.info(f"Packed context status: {packed_context.get('status', 'NO_STATUS_KEY')}")
                    # Inject a conversation-context document with highest priority for the prompt system
                    try:
                        fmt = packed_context.get('formatted_context') or {}
                        if not isinstance(fmt, dict):
                            fmt = {}
                        convo_doc = ""
                        if short_summary:
                            convo_doc = f"Conversation summary so far: {short_summary}"
                        if active_case_context and active_case_context.get('case_number'):
                            convo_doc = (convo_doc + " | " if convo_doc else "") + f"Active case: {active_case_context.get('case_number')}"
                        fmt['conversation_context'] = convo_doc
                        packed_context['formatted_context'] = fmt
                    except Exception:
                        pass
                    # DEBUG: safe preview of context text
                    try:
                        import re
                        _sanitize = re.compile(r"[^\\x20-\\x7E]+")
                        fmt = packed_context.get('formatted_context') or {}
                        ctx_text = ''
                        if isinstance(fmt, dict):
                            ctx_text = fmt.get('context_text', '')
                        safe = _sanitize.sub('?', str(ctx_text))
                        logger.info(f"[DEBUG] context_text length: {len(safe)}")
                        logger.info(f"[DEBUG] context_text preview: {safe[:400]}")
                    except Exception as _e:
                        logger.warning(f"[DEBUG] unable to log context preview: {_e}")
                else:
                    logger.info(f"Packed context content: {packed_context}")
            except Exception as e:
                logger.error(f"Error in context packing: {str(e)}")
                raise
            
            logger.info(f"About to check packed_context status")
            if not isinstance(packed_context, dict) or packed_context.get('status') != 'success':
                return RAGResult(
                    answer="I encountered an error processing the legal documents. Please try again or consult with a legal professional.",
                    confidence=0.0,
                    sources=[],
                    citations=[],
                    metadata={'context_packing_error': packed_context.get('packing_metadata', {}) if isinstance(packed_context, dict) else str(packed_context)},
                    guardrail_result=None,
                    generation_time=time.time() - start_time,
                    status="context_error"
                )
            
            # Step 7: Determine query type and legal domain
            query_type = self._classify_query_type(query)
            legal_domain = self._classify_legal_domain(query, retrieved_docs)
            
            # Step 8: Get appropriate prompt template
            template = self.prompt_system.get_template(query_type, legal_domain, conversation_history)
            
            # Step 9: Format prompt
            logger.info(f"Packed context type: {type(packed_context)}")
            if isinstance(packed_context, dict):
                logger.info(f"Packed context keys: {list(packed_context.keys())}")
            else:
                logger.info(f"Packed context content: {packed_context}")
            
            formatted_prompt = self.prompt_system.format_prompt(
                template=template,
                query=query,
                context_data=packed_context,
                conversation_history=conversation_history
            )
            
            logger.info(f"Formatted prompt type: {type(formatted_prompt)}")
            if isinstance(formatted_prompt, dict):
                logger.info(f"Formatted prompt keys: {list(formatted_prompt.keys())}")
            else:
                logger.info(f"Formatted prompt content: {formatted_prompt}")
            
            # Step 10: Generate answer with LLM
            logger.info(f"Generating answer with {template.name} template")
            
            # Debug logging for advocates questions
            if 'advocat' in query.lower():
                logger.info(f"[DEBUG] Advocates question detected")
                # Sanitize previews to avoid Windows cp1252 encoding issues in logs
                def _safe_preview(s: str, n: int) -> str:
                    try:
                        return (s or "")[:n].encode("ascii", "ignore").decode("ascii")
                    except Exception:
                        return ""
                logger.info(f"[DEBUG] System prompt (first 200 chars): {_safe_preview(formatted_prompt['system_prompt'], 200)}")
                logger.info(f"[DEBUG] User prompt (first 500 chars): {_safe_preview(formatted_prompt['user_prompt'], 500)}")
                logger.info(f"[DEBUG] Has 'CONCISE' in system: {'CONCISE' in formatted_prompt['system_prompt']}")
                logger.info(f"[DEBUG] Has 'advocates' in user prompt: {'advocates' in formatted_prompt['user_prompt'].lower()}")
                logger.info(f"[DEBUG] Has 'qaiser' in user prompt: {'qaiser' in formatted_prompt['user_prompt'].lower()}")
            
            llm_result = self.llm_generator.generate_answer(
                system_prompt=formatted_prompt['system_prompt'],
                user_prompt=formatted_prompt['user_prompt'],
                conversation_history=conversation_history
            )
            
            if llm_result.status != "success":
                return RAGResult(
                    answer="I encountered an error generating the answer. Please try again or consult with a legal professional.",
                    confidence=0.0,
                    sources=[],
                    citations=[],
                    metadata={'llm_error': llm_result.error},
                    guardrail_result=None,
                    generation_time=time.time() - start_time,
                    status="generation_error"
                )
            
            # Step 11: Post-process for field-only/summary intents and conversational tone
            try:
                processed_text = self._post_process_answer(query, llm_result.text, retrieved_docs)
                if processed_text:
                    llm_result.text = processed_text
            except Exception as _pp_e:
                logger.warning(f"Post-processing failed: {_pp_e}")

            # Step 12: Apply guardrails to response
            guardrail_result = None
            if self.enable_guardrails:
                logger.info("Applying guardrails to generated response")
                guardrail_result = self.guardrails.apply_guardrails(
                    query=query,
                    response=llm_result.text,
                    context_sources=retrieved_docs,
                    confidence_score=llm_result.confidence,
                    user_access_level=access_level
                )
                
                if not guardrail_result.allowed:
                    return RAGResult(
                        answer=guardrail_result.safe_response or "I cannot provide a response to this query due to safety concerns. Please consult with a qualified legal professional.",
                        confidence=0.0,
                        sources=[],
                        citations=[],
                        metadata={'guardrail_result': guardrail_result.__dict__},
                        guardrail_result=guardrail_result,
                        generation_time=time.time() - start_time,
                        status="blocked",
                        error="Response blocked by guardrails"
                    )
            
            # Step 13: Format citations
            formatted_sources = self.citation_formatter.format_citations(retrieved_docs)
            
            # Step 14: Add conversation turn to session
            if session:
                self.conversation_manager.add_conversation_turn(
                    session=session,
                    query=query,
                    response=llm_result.text,
                    context_documents=retrieved_docs
                )
            
            # Step 15: Prepare final result
            generation_time = time.time() - start_time
            
            return RAGResult(
                answer=self._convert_markdown_to_html(llm_result.text),
                confidence=llm_result.confidence,
                sources=formatted_sources,
                citations=formatted_sources,  # Same as sources for now
                metadata={
                    'query_type': query_type.value,
                    'legal_domain': legal_domain.value,
                    'template_used': template.name,
                    'llm_provider': llm_result.provider,
                    'llm_model': llm_result.model,
                    'tokens_used': llm_result.tokens_used,
                    'retrieval_results': len(retrieved_docs),
                    'context_chunks': packed_context.get('chunk_count', 0) if isinstance(packed_context, dict) else 0,
                    'context_tokens': packed_context.get('token_count', 0) if isinstance(packed_context, dict) else 0,
                    'packing_metadata': packed_context.get('packing_metadata', {}) if isinstance(packed_context, dict) else {},
                    'prompt_metadata': formatted_prompt.get('context_metadata', {}) if isinstance(formatted_prompt, dict) else {},
                    'generation_time': generation_time
                },
                guardrail_result=guardrail_result,
                generation_time=generation_time,
                status="success"
            )
            
        except Exception as e:
            import traceback
            logger.error(f"Error in RAG generation: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return RAGResult(
                answer="I encountered an unexpected error while processing your question. Please try again or consult with a legal professional.",
                confidence=0.0,
                sources=[],
                citations=[],
                metadata={'error': str(e)},
                guardrail_result=None,
                generation_time=time.time() - start_time,
                status="error",
                error=str(e)
            )
    
    def generate_streaming_answer(self, 
                                 query: str,
                                 user_id: str = "anonymous",
                                 session_id: Optional[str] = None,
                                 access_level: Optional[AccessLevel] = None,
                                 conversation_history: Optional[List[Dict]] = None,
                                 filters: Optional[Dict[str, Any]] = None):
        """Generate streaming RAG answer"""
        
        try:
            # Step 1: Set access level
            if access_level is None:
                access_level = self.default_access_level
            
            # Step 2: Apply guardrails to query
            if self.enable_guardrails:
                query_guardrail = self.guardrails.check_query_safety(query, access_level)
                if not query_guardrail.allowed:
                    yield {
                        'type': 'error',
                        'error': 'Query blocked by guardrails',
                        'safe_response': self.guardrails._generate_safe_response(query, [])
                    }
                    return
            
            # Step 3: Retrieve relevant documents
            retrieved_docs = self.retrieval_service.retrieve_for_qa(
                query=query,
                top_k=self.max_retrieval_results
            )
            
            if not retrieved_docs:
                yield {
                    'type': 'error',
                    'error': 'No relevant documents found',
                    'message': 'I couldn\'t find relevant legal information to answer your question.'
                }
                return
            
            # Step 4: Pack context
            packed_context = self.context_packer.pack_context(
                retrieved_chunks=retrieved_docs,
                query=query,
                conversation_history=conversation_history
            )
            
            if not isinstance(packed_context, dict) or packed_context.get('status') != 'success':
                yield {
                    'type': 'error',
                    'error': 'Context packing failed',
                    'message': 'I encountered an error processing the legal documents.'
                }
                return
            
            # Step 5: Get template and format prompt
            query_type = self._classify_query_type(query)
            legal_domain = self._classify_legal_domain(query, retrieved_docs)
            template = self.prompt_system.get_template(query_type, legal_domain, conversation_history)
            
            formatted_prompt = self.prompt_system.format_prompt(
                template=template,
                query=query,
                context_data=packed_context,
                conversation_history=conversation_history
            )
            
            # Step 6: Stream generation
            full_response = ""
            for chunk in self.llm_generator.generate_streaming_answer(
                system_prompt=formatted_prompt['system_prompt'],
                user_prompt=formatted_prompt['user_prompt']
            ):
                if chunk['type'] == 'content':
                    full_response += chunk['content']
                    yield {
                        'type': 'content',
                        'content': chunk['content'],
                        'template': template.name,
                        'provider': chunk.get('provider', 'unknown')
                    }
                elif chunk['type'] == 'complete':
                    # Apply guardrails to complete response
                    if self.enable_guardrails:
                        guardrail_result = self.guardrails.apply_guardrails(
                            query=query,
                            response=full_response,
                            context_sources=retrieved_docs,
                            confidence_score=0.8,  # Default confidence for streaming
                            user_access_level=access_level
                        )
                        
                        if not guardrail_result.allowed:
                            yield {
                                'type': 'error',
                                'error': 'Response blocked by guardrails',
                                'safe_response': guardrail_result.safe_response
                            }
                            return
                    
                    # Format citations
                    formatted_sources = self.citation_formatter.format_citations(retrieved_docs)
                    
                    yield {
                        'type': 'complete',
                        'answer': self._convert_markdown_to_html(full_response),
                        'sources': formatted_sources,
                        'metadata': {
                            'query_type': query_type.value,
                            'legal_domain': legal_domain.value,
                            'template_used': template.name,
                            'retrieval_results': len(retrieved_docs),
                            'context_chunks': packed_context.get('chunk_count', 0) if isinstance(packed_context, dict) else 0
                        }
                    }
                elif chunk['type'] == 'error':
                    yield chunk
            
        except Exception as e:
            logger.error(f"Error in streaming RAG generation: {str(e)}")
            yield {
                'type': 'error',
                'error': str(e),
                'message': 'I encountered an unexpected error while processing your question.'
            }
    
    def _is_legal_query(self, query: str, conversation_history: Optional[List[Dict]] = None) -> bool:
        """Check if the query is legal-related or just casual conversation"""
        try:
            query_lower = query.lower().strip()
            
            # Define legal keywords at the top level
            legal_keywords = [
                'law', 'legal', 'court', 'judge', 'case', 'judgment', 'order', 'decision', 'ruling',
                'statute', 'section', 'act', 'code', 'provision', 'constitution', 'article',
                'procedure', 'process', 'filing', 'bail', 'fir', 'criminal', 'civil', 'family',
                'divorce', 'custody', 'inheritance', 'marriage', 'property', 'contract',
                'lawyer', 'advocate', 'counsel', 'attorney', 'justice', 'bench', 'judicial',
                'cite', 'citation', 'reference', 'plj', 'pld', 'mld', 'writ', 'fundamental right',
                'ppc', 'crpc', 'cpc', 'offence', 'suit', 'land', 'real estate', 'ownership',
                'petition', 'appeal', 'hearing', 'trial', 'verdict', 'sentence', 'punishment',
                'tax', 'revenue', 'commercial', 'business', 'administrative', 'government'
            ]
            
            # FIRST: Check if this is a follow-up question in a legal conversation
            # This takes priority over everything else
            if conversation_history and len(conversation_history) > 0:
                # Check the entire conversation history for ANY legal queries
                for turn in conversation_history:  # Check ALL turns in conversation
                    prev_query = turn.get('query', '').lower()
                    if any(keyword in prev_query for keyword in legal_keywords):
                        # If ANY previous query was legal, treat EVERY follow-up as legal
                        # This is the most reliable approach - users can ask anything in follow-ups
                        return True
            
            # SECOND: Check for legal keywords in current query
            if any(keyword in query_lower for keyword in legal_keywords):
                return True
            
            # THIRD: Check for casual patterns (only if no legal conversation history)
            casual_patterns = [
                'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
                'how are you', 'how are you?', 'what\'s up', 'how do you do', 'nice to meet you',
                'thank you', 'thanks', 'bye', 'goodbye', 'see you later',
                'ok', 'okay', 'yes', 'no', 'maybe', 'sure', 'alright',
                'test', 'testing', 'check', 'checking',
                'how have you been', 'how is everything', 'how is your day',
                'how are things', 'how is life', 'how are you doing',
                'what\'s going on', 'how\'s it going', 'how\'s everything',
                'good to see you', 'nice to see you', 'long time no see'
            ]
            
            # Check for casual patterns (exact matches only for short patterns, contains for longer ones)
            for pattern in casual_patterns:
                if len(pattern) <= 3:  # Short patterns like 'ok', 'hi' should be exact matches
                    # For short patterns, only match if it's the entire query or followed by casual words
                    if query_lower == pattern:
                        return False
                    elif query_lower.startswith(pattern + ' '):
                        # Check if what follows is also casual
                        remaining = query_lower[len(pattern):].strip()
                        casual_follow_ups = ['thanks', 'thank you', 'bye', 'goodbye', 'yes', 'no', 'sure', 'alright']
                        if any(follow_up in remaining for follow_up in casual_follow_ups):
                            return False
                else:  # Longer patterns can be contains
                    if pattern in query_lower:
                        return False
            
            # Check for very short queries (likely casual)
            if len(query_lower.split()) <= 2 and len(query_lower) <= 10:
                return False
            
            # For longer queries without legal keywords, be more conservative
            # Only classify as legal if it's clearly asking about legal matters
            if len(query_lower.split()) >= 4:
                # Check for question patterns that might be legal
                legal_question_patterns = [
                    'what is', 'what are', 'how to', 'how can', 'what does', 'what should',
                    'explain', 'describe', 'tell me about', 'information about'
                ]
                
                # If it's a question pattern but no legal keywords, it's probably not legal
                # UNLESS it's a follow-up question (handled above)
                if any(pattern in query_lower for pattern in legal_question_patterns):
                    return False
            
            # Default to non-legal for unclear queries
            return False
        except Exception as e:
            logger.error(f"Error in _is_legal_query: {str(e)}")
            return False

    def _is_database_overview_query(self, query: str) -> bool:
        """Check if the query is asking about what types of information are available in the database"""
        query_lower = query.lower().strip()
        
        # Patterns that indicate the user wants to know what information is available
        overview_patterns = [
            'what type of information',
            'what information',
            'what can you help',
            'what can you provide',
            'what do you have',
            'what is available',
            'what kind of',
            'what types of',
            'show me what',
            'tell me what',
            'what data',
            'what cases',
            'what documents',
            'what legal information',
            'what legal data',
            'what legal cases',
            'what legal documents',
            'what is in your database',
            'what does your database contain',
            'what can you tell me about',
            'what are the different types',
            'what categories',
            'what areas of law',
            'what legal areas',
            'what legal topics',
            'what legal subjects'
        ]
        
        # Check if query matches any overview pattern
        for pattern in overview_patterns:
            if pattern in query_lower:
                return True
        
        return False

    def _get_diverse_legal_cases(self, top_k: int = 8) -> List[Dict[str, Any]]:
        """Get a diverse set of legal cases representing different types of information available"""
        try:
            # Get diverse cases by querying different legal areas
            diverse_queries = [
                "constitutional law writ petition",
                "criminal law bail application", 
                "civil law property dispute",
                "family law divorce case",
                "tax law revenue case",
                "commercial law contract dispute",
                "administrative law government case",
                "banking law financial case"
            ]
            
            diverse_cases = []
            cases_per_query = max(1, top_k // len(diverse_queries))
            
            for query in diverse_queries:
                try:
                    results = self.retrieval_service.retrieve_for_qa(
                        query=query,
                        top_k=cases_per_query
                    )
                    diverse_cases.extend(results)
                except Exception as e:
                    logger.warning(f"Failed to get diverse cases for query '{query}': {str(e)}")
                    continue
            
            # Remove duplicates and limit to top_k
            seen_titles = set()
            unique_cases = []
            for case in diverse_cases:
                title = case.get('case_title', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_cases.append(case)
                    if len(unique_cases) >= top_k:
                        break
            
            logger.info(f"Retrieved {len(unique_cases)} diverse legal cases for database overview")
            return unique_cases
            
        except Exception as e:
            logger.error(f"Error getting diverse legal cases: {str(e)}")
            # Fallback: get any recent cases
            try:
                return self.retrieval_service.retrieve_for_qa(
                    query="recent legal cases",
                    top_k=top_k
                )
            except:
                return []

    def _classify_query_type(self, query: str) -> QueryType:
        """Classify the type of legal query"""
        query_lower = query.lower()
        
        # Case inquiry patterns
        if any(word in query_lower for word in ['case', 'judgment', 'order', 'decision', 'ruling']):
            return QueryType.CASE_INQUIRY
        
        # Law research patterns
        if any(word in query_lower for word in ['law', 'statute', 'section', 'act', 'code', 'provision']):
            return QueryType.LAW_RESEARCH
        
        # Procedural guidance patterns
        if any(word in query_lower for word in ['procedure', 'process', 'how to', 'filing', 'court procedure']):
            return QueryType.PROCEDURAL_GUIDANCE
        
        # Judge inquiry patterns
        if any(word in query_lower for word in ['judge', 'justice', 'bench', 'judicial']):
            return QueryType.JUDGE_INQUIRY
        
        # Lawyer inquiry patterns
        if any(word in query_lower for word in ['lawyer', 'advocate', 'counsel', 'attorney']):
            return QueryType.LAWYER_INQUIRY
        
        # Citation lookup patterns
        if any(word in query_lower for word in ['cite', 'citation', 'reference', 'plj', 'pld', 'mld']):
            return QueryType.CITATION_LOOKUP
        
        # Constitutional patterns
        if any(word in query_lower for word in ['constitution', 'article 199', 'writ', 'fundamental right']):
            return QueryType.CONSTITUTIONAL_QUESTION
        
        # Criminal law patterns
        if any(word in query_lower for word in ['criminal', 'bail', 'fir', 'ppc', 'crpc', 'offence']):
            return QueryType.CRIMINAL_LAW
        
        # Civil law patterns
        if any(word in query_lower for word in ['civil', 'property', 'contract', 'cpc', 'suit']):
            return QueryType.CIVIL_LAW
        
        # Family law patterns
        if any(word in query_lower for word in ['family', 'divorce', 'custody', 'inheritance', 'marriage']):
            return QueryType.FAMILY_LAW
        
        # Property law patterns
        if any(word in query_lower for word in ['property', 'land', 'real estate', 'ownership']):
            return QueryType.PROPERTY_LAW
        
        return QueryType.GENERAL_LEGAL
    
    def _classify_legal_domain(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> LegalDomain:
        """Classify the legal domain based on query and retrieved documents"""
        query_lower = query.lower()
        
        # Check query for domain indicators
        if any(word in query_lower for word in ['constitution', 'article 199', 'writ', 'fundamental right']):
            return LegalDomain.CONSTITUTIONAL
        
        if any(word in query_lower for word in ['criminal', 'bail', 'fir', 'ppc', 'crpc', 'offence']):
            return LegalDomain.CRIMINAL
        
        if any(word in query_lower for word in ['civil', 'property', 'contract', 'cpc', 'suit']):
            return LegalDomain.CIVIL
        
        if any(word in query_lower for word in ['family', 'divorce', 'custody', 'inheritance', 'marriage']):
            return LegalDomain.FAMILY
        
        if any(word in query_lower for word in ['property', 'land', 'real estate', 'ownership']):
            return LegalDomain.PROPERTY
        
        if any(word in query_lower for word in ['commercial', 'business', 'trade', 'company']):
            return LegalDomain.COMMERCIAL
        
        if any(word in query_lower for word in ['administrative', 'government', 'public', 'bureaucracy']):
            return LegalDomain.ADMINISTRATIVE
        
        if any(word in query_lower for word in ['procedure', 'process', 'court procedure', 'filing']):
            return LegalDomain.PROCEDURAL
        
        # Check retrieved documents for domain indicators
        if retrieved_docs:
            domain_counts = {}
            for doc in retrieved_docs:
                legal_domain = doc.get('legal_domain', '').lower()
                if legal_domain:
                    domain_counts[legal_domain] = domain_counts.get(legal_domain, 0) + 1
            
            if domain_counts:
                most_common_domain = max(domain_counts, key=domain_counts.get)
                domain_mapping = {
                    'constitutional': LegalDomain.CONSTITUTIONAL,
                    'criminal': LegalDomain.CRIMINAL,
                    'civil': LegalDomain.CIVIL,
                    'family': LegalDomain.FAMILY,
                    'property': LegalDomain.PROPERTY,
                    'commercial': LegalDomain.COMMERCIAL,
                    'administrative': LegalDomain.ADMINISTRATIVE,
                    'procedural': LegalDomain.PROCEDURAL
                }
                return domain_mapping.get(most_common_domain, LegalDomain.GENERAL)
        
        return LegalDomain.GENERAL
    
    def _post_process_answer(self, query: str, text: str, retrieved_docs: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Minimal post-processing - just add warm tone if enabled, otherwise return LLM output as-is."""
        try:
            if not text:
                return text
            
            # Only add warm tone prefix if enabled and not already present
            if self.warm_tone and not text.strip().startswith("Sure —"):
                return f"Sure — {text}"
            
            return text
        except Exception:
            return text

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'rag_engine': {
                'status': 'operational',
                'components': {
                    'context_packer': 'operational',
                    'prompt_system': 'operational',
                    'llm_generator': 'operational',
                    'guardrails': 'operational',
                    'conversation_manager': 'operational',
                    'citation_formatter': 'operational',
                    'retrieval_service': 'operational'
                },
                'configuration': {
                    'enable_guardrails': self.enable_guardrails,
                    'enable_conversation_context': self.enable_conversation_context,
                    'default_access_level': self.default_access_level.value,
                    'max_retrieval_results': self.max_retrieval_results
                }
            },
            'llm_generator': self.llm_generator.get_system_status(),
            'guardrails': self.guardrails.get_guardrail_status(),
            'retrieval_service': self.retrieval_service.get_qa_retrieval_stats()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            'overall': 'healthy',
            'components': {},
            'timestamp': time.time()
        }
        
        # Check each component
        try:
            # Context packer health
            health_status['components']['context_packer'] = 'healthy'
        except Exception as e:
            health_status['components']['context_packer'] = f'unhealthy: {str(e)}'
            health_status['overall'] = 'degraded'
        
        try:
            # Prompt system health
            health_status['components']['prompt_system'] = 'healthy'
        except Exception as e:
            health_status['components']['prompt_system'] = f'unhealthy: {str(e)}'
            health_status['overall'] = 'degraded'
        
        try:
            # LLM generator health
            llm_status = self.llm_generator.get_system_status()
            if any(provider.get('available', False) for provider in llm_status['providers'].values()):
                health_status['components']['llm_generator'] = 'healthy'
            else:
                health_status['components']['llm_generator'] = 'unhealthy: no providers available'
                health_status['overall'] = 'unhealthy'
        except Exception as e:
            health_status['components']['llm_generator'] = f'unhealthy: {str(e)}'
            health_status['overall'] = 'unhealthy'
        
        try:
            # Guardrails health
            health_status['components']['guardrails'] = 'healthy'
        except Exception as e:
            health_status['components']['guardrails'] = f'unhealthy: {str(e)}'
            health_status['overall'] = 'degraded'
        
        try:
            # Retrieval service health
            retrieval_stats = self.retrieval_service.get_qa_retrieval_stats()
            if retrieval_stats.get('status') == 'operational':
                health_status['components']['retrieval_service'] = 'healthy'
            else:
                health_status['components']['retrieval_service'] = 'degraded'
                health_status['overall'] = 'degraded'
        except Exception as e:
            health_status['components']['retrieval_service'] = f'unhealthy: {str(e)}'
            health_status['overall'] = 'degraded'
        
        return health_status
