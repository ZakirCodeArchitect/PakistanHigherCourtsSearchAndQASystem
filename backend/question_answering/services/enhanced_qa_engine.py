"""
Enhanced QA Engine
Combines semantic search and AI answer generation for intelligent question answering
Now integrated with Advanced RAG Engine for complete RAG pipeline
"""

import logging
from typing import List, Dict, Any, Optional
from .ai_answer_generator import AIAnswerGenerator
from .knowledge_retriever import KnowledgeRetriever
from .rag_service import RAGService
from .conversation_manager import ConversationManager, CitationFormatter
from .advanced_embeddings import AdvancedEmbeddingService
from .advanced_rag_engine import AdvancedRAGEngine
from qa_app.services.qa_retrieval_service import QARetrievalService
from .topic_classifier import TopicClassifier

logger = logging.getLogger(__name__)

class EnhancedQAEngine:
    """Enhanced QA engine combining semantic search and AI generation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the enhanced QA engine"""
        self.config = config or {}
        
        # Legacy components (kept for backward compatibility)
        self.ai_generator = AIAnswerGenerator()
        self.knowledge_retriever = KnowledgeRetriever()
        self.rag_service = RAGService()
        self.conversation_manager = ConversationManager()
        self.citation_formatter = CitationFormatter()
        self.advanced_embeddings = AdvancedEmbeddingService()
        
        # NEW: Advanced QA retrieval with two-stage process
        self.qa_retrieval_service = QARetrievalService()
        
        # NEW: Advanced RAG Engine with all components
        self.advanced_rag_engine = AdvancedRAGEngine(self.config.get('advanced_rag', {}))
        self.topic_classifier = TopicClassifier()
        
        # Configuration
        self.use_advanced_rag = self.config.get('use_advanced_rag', True)
        
        # Log integration status
        logger.info(f"Enhanced QA Engine initialized with Advanced RAG: {self.use_advanced_rag}")
        if self.use_advanced_rag:
            logger.info("Advanced RAG Engine is ENABLED - using full RAG pipeline")
        else:
            logger.info("Advanced RAG Engine is DISABLED - using legacy implementation")
        
        # In-memory fallback to persist active case across turns when session model
        # does not store extra metadata fields (e.g., extra_data not available)
        self._active_case_by_session: Dict[str, int] = {}

    # ----------------------------
    # Helpers for follow-up logic
    # ----------------------------
    def _is_procedural_query(self, text: str) -> bool:
        """Detect procedural/how-to queries where case lock should be OFF."""
        if not text:
            return False
        tl = text.lower()
        keywords = [
            'how to', 'procedure', 'process', 'steps', 'file a writ', 'file writ',
            'petition filing', 'submit', 'timeline', 'fees', 'documents required',
            'format', 'template', 'draft', 'where to file', 'jurisdiction'
        ]
        return any(k in tl for k in keywords)

    def _is_case_field_request(self, text: str) -> bool:
        """Detect simple field-asks about a case (advocates/order/fir etc.)."""
        if not text:
            return False
        tl = text.lower()
        field_terms = [
            'advocat', 'lawyer', 'counsel', 'court order', 'short order', 'order',
            'bench', 'judge', 'status', 'fir', 'police station', 'under section',
            'hearing date', 'date of hearing', 'date of fir', 'sr number',
            'institution date', 'case stage', 'description', 'summary of the case'
        ]
        return any(t in tl for t in field_terms)

    def _has_explicit_case_in_text(self, text: str) -> bool:
        import re
        if not text:
            return False
        return re.search(r'[A-Z][a-z]?\.?\s*\d+/\d+\s+[A-Za-z]+', text) is not None

    def _is_related_followup(self, current_q: str, previous_q: str) -> bool:
        """
        Lightweight relatedness check:
        - If current_q contains pronouns like 'this case', treat as related
        - Else use a simple token-overlap heuristic with previous_q
        """
        if not current_q or not previous_q:
            return False
        cur = current_q.lower()
        if any(p in cur for p in ['this case', 'that case', 'this', 'it']):
            return True
        import re
        tokens_a = set(re.findall(r'[a-z0-9]+', cur))
        tokens_b = set(re.findall(r'[a-z0-9]+', previous_q.lower()))
        if not tokens_a or not tokens_b:
            return False
        overlap = len(tokens_a & tokens_b) / max(1, len(tokens_a | tokens_b))
        return overlap >= 0.25

    def _attempt_structured_answer(self, question: str, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Try to answer using structured metadata before invoking the full RAG pipeline."""
        try:
            requested_fields = self._detect_requested_fields(question)
            if not requested_fields:
                return None

            retrieval_results = self.qa_retrieval_service.retrieve_for_qa(question, top_k=5)
            if not retrieval_results:
                return None

            for result in retrieval_results:
                structured = result.get('structured_data') or {}
                metadata = result.get('metadata', {})

                pieces: List[str] = []

                # Advocates (petitioner/respondent)
                petitioner_adv = structured.get('advocates_petitioner') or []
                respondent_adv = structured.get('advocates_respondent') or []

                if isinstance(petitioner_adv, str):
                    petitioner_adv = [petitioner_adv]
                if isinstance(respondent_adv, str):
                    respondent_adv = [respondent_adv]

                if 'advocates_petitioner' in requested_fields and petitioner_adv:
                    pieces.append(f"Petitioner's advocates: {self._join_names(petitioner_adv)}")
                if 'advocates_respondent' in requested_fields and respondent_adv:
                    pieces.append(f"Respondent's advocates: {self._join_names(respondent_adv)}")

                # Bench / court / status
                if 'bench' in requested_fields:
                    bench_value = structured.get('bench') or result.get('bench') or metadata.get('bench')
                    bench_text = self._render_structured_value(bench_value)
                    if bench_text:
                        pieces.append(f"Bench: {bench_text}")

                if 'status' in requested_fields:
                    status_value = structured.get('status') or result.get('status') or metadata.get('status')
                    status_text = self._render_structured_value(status_value)
                    if status_text:
                        pieces.append(f"Case status: {status_text}")

                if 'short_order' in requested_fields:
                    short_order_value = structured.get('short_order') or result.get('short_order') or metadata.get('short_order')
                    short_order_text = self._render_structured_value(short_order_value)
                    if short_order_text:
                        pieces.append(f"Short order: {short_order_text}")

                if 'orders' in requested_fields:
                    orders_value = structured.get('order') or structured.get('orders')
                    if orders_value:
                        formatted_orders = self._format_order_list(orders_value)
                        if formatted_orders:
                            orders_text = "; ".join(item.lstrip(" -") for item in formatted_orders if item)
                            orders_text = orders_text.strip()
                            if orders_text:
                                pieces.append(f"Orders: {orders_text}")

                if 'fir_number' in requested_fields:
                    fir_value = structured.get('fir_number') or metadata.get('fir_number')
                    fir_text = self._render_structured_value(fir_value)
                    if fir_text:
                        pieces.append(f"FIR number: {fir_text}")

                if 'fir_date' in requested_fields:
                    fir_date_value = structured.get('fir_date') or metadata.get('fir_date')
                    fir_date_text = self._render_structured_value(fir_date_value)
                    if fir_date_text:
                        pieces.append(f"FIR date: {fir_date_text}")

                if 'police_station' in requested_fields:
                    station_value = structured.get('police_station') or metadata.get('police_station')
                    station_text = self._render_structured_value(station_value)
                    if station_text:
                        pieces.append(f"Police station: {station_text}")

                if 'under_section' in requested_fields:
                    section_value = structured.get('under_section') or metadata.get('under_section')
                    section_text = self._render_structured_value(section_value)
                    if section_text:
                        pieces.append(f"Under section: {section_text}")

                if not pieces:
                    continue

                case_title = result.get('case_title') or metadata.get('case_title') or 'the case'
                answer_lines = [f"In {case_title}:"]
                answer_lines.extend(pieces)
                answer = "\n".join(answer_lines)

                source_entry = {
                    'title': case_title,
                    'case_number': result.get('case_number'),
                    'court': metadata.get('court'),
                    'metadata': metadata
                }

                return {
                    'answer': answer,
                    'sources': [source_entry],
                    'answer_type': 'structured_lookup',
                    'confidence': 0.95,
                    'filters': filters or {},
                }

            return None

        except Exception as exc:
            logger.warning(f"Structured answer shortcut failed: {exc}")
            return None

    @staticmethod
    def _join_names(names: List[str]) -> str:
        clean = [name.strip() for name in names if name and isinstance(name, str)]
        if not clean:
            return "unknown"
        if len(clean) == 1:
            return clean[0]
        return ", ".join(clean[:-1]) + f" and {clean[-1]}"

    def _detect_requested_fields(self, question: str) -> set:
        lowered = question.lower()
        requested = set()

        if 'advocate' in lowered or 'counsel' in lowered:
            has_petitioner = 'petitioner' in lowered or 'appellant' in lowered or 'plaintiff' in lowered
            has_respondent = 'respondent' in lowered or 'defendant' in lowered or 'opponent' in lowered

            if has_petitioner:
                requested.add('advocates_petitioner')
            if has_respondent:
                requested.add('advocates_respondent')
            if not has_petitioner and not has_respondent:
                requested.update({'advocates_petitioner', 'advocates_respondent'})

        if 'bench' in lowered:
            requested.add('bench')

        if 'status' in lowered or 'disposed' in lowered or 'decision' in lowered:
            requested.add('status')

        if 'short order' in lowered:
            requested.add('short_order')
        elif 'order' in lowered:
            requested.add('orders')

        if 'fir' in lowered:
            requested.add('fir_number')
            if 'date' in lowered:
                requested.add('fir_date')

        if 'police station' in lowered:
            requested.add('police_station')

        if 'under section' in lowered or 'u/s' in lowered or ('section' in lowered and 'under' in lowered):
            requested.add('under_section')

        return requested

    def _render_structured_value(self, value: Any) -> str:
        if value is None:
            return ''
        text = self._format_structured_value(value)
        if not text:
            return ''
        normalized = text.strip()
        if normalized.lower() in {'', 'n/a', 'not available', 'unknown', 'none'}:
            return ''
        return normalized
    
    def _precompute_embeddings(self):
        """Precompute embeddings for all documents"""
        # This method is now handled by the RAG service
        pass
    
    def _serialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize metadata to ensure all values are JSON serializable"""
        if not metadata:
            return {}
        
        serialized = {}
        for key, value in metadata.items():
            if hasattr(value, 'value'):  # Handle enums
                serialized[key] = value.value
            elif isinstance(value, (list, tuple)):
                serialized[key] = [v.value if hasattr(v, 'value') else v for v in value]
            elif isinstance(value, dict):
                serialized[key] = self._serialize_metadata(value)
            else:
                serialized[key] = value
        
        return serialized
    
    def ask_question(
        self, 
        question: str, 
        conversation_history: Optional[List[Dict]] = None,
        use_ai: bool = True,
        use_advanced_rag: Optional[bool] = None,
        session_id: Optional[str] = None,
        user_id: str = "anonymous",
        access_level: str = "public",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ask a question and get an intelligent answer with conversation management
        
        Args:
            question: The user's question
            conversation_history: Previous conversation context
            use_ai: Whether to use AI generation (True) or simple retrieval (False)
            use_advanced_rag: Whether to use Advanced RAG Engine (None = use default)
            session_id: Session ID for conversation management
            user_id: User ID for session tracking
            access_level: User access level (public, lawyer, judge, admin)
            filters: Retrieval filters (court, year, legal_domain, etc.)
            
        Returns:
            Dictionary containing the answer and metadata
        """
        try:
            # Ensure session exists early so we can decide routing (structured vs advanced) using context
            session = None
            if session_id:
                session = self.conversation_manager.get_or_create_session(user_id, session_id)
            else:
                # New chat without a session_id always gets a fresh session to avoid cross-chat bleed
                session = self.conversation_manager.create_session(user_id)
                session_id = session.session_id

            # If we already have an active case and the user didn't explicitly name a different case,
            # bypass structured lookup and use advanced path with strict locking.
            bypass_structured = False
            active_case_context = {}
            if session:
                try:
                    active_case_context = self.conversation_manager.get_active_case_context(session) or {}
                except Exception:
                    active_case_context = {}
            if active_case_context.get('case_id') and not self._has_explicit_case_in_text(question):
                bypass_structured = True

            # DISABLED: Structured lookup - always use RAG for now
            # Check for structured lookup data, but send it to LLM for formatting
            structured_data = None
            structured_sources = None
            # Skip structured lookup - always use RAG
            bypass_structured = True
            # if not bypass_structured:
            #     structured_lookup = self._attempt_structured_answer(question, filters)
            #     if structured_lookup:
            #         # Extract structured data to pass to LLM
            #         structured_data = structured_lookup.get('answer')  # Raw structured answer
            #         structured_sources = structured_lookup.get('sources', [])
            #         # Continue to LLM formatting instead of returning early

            # Determine whether to use Advanced RAG Engine
            should_use_advanced_rag = use_advanced_rag if use_advanced_rag is not None else self.use_advanced_rag
            
            # Use Advanced RAG Engine if enabled
            if should_use_advanced_rag:
                logger.info("Using Advanced RAG Engine for question answering")
                
                # Convert access level string to enum
                from .guardrails import AccessLevel
                access_level_enum = AccessLevel(access_level.lower())
                
                # Ensure we have a session to maintain context
                session = None
                if session_id:
                    session = self.conversation_manager.get_or_create_session(user_id, session_id)
                else:
                    # Always create a fresh session if none supplied (UI “new chat”)
                    session = self.conversation_manager.create_session(user_id)
                # Ensure we propagate session_id back to caller
                if session and not session_id:
                    session_id = session.session_id
                # refresh conversation history if we have a session
                if session:
                    conversation_history = session.get_recent_context(5)
                
                # Generate answer using Advanced RAG Engine
                # Attempt to lock to explicit case or active case for follow-ups
                forced_case_id = None
                # Determine intent for locking rules
                q_lower = (question or "").lower()
                is_procedural = self._is_procedural_query(q_lower)
                is_case_field = self._is_case_field_request(q_lower)
                is_general_opinion = any(k in q_lower for k in ['what do you think', 'your opinion', 'do you think'])
                # 0) If we have a remembered case for this session, take it first
                if session_id and session_id in self._active_case_by_session:
                    forced_case_id = self._active_case_by_session[session_id]
                # If pronoun follow-up and an active case exists, force lock
                active_case_context = {}
                if self.use_advanced_rag and session:
                    active_case_context = self.conversation_manager.get_active_case_context(session) or {}
                if active_case_context.get('case_id') and not is_procedural and not is_general_opinion:
                    # Lock only for case field asks or non-explicit case follow-ups
                    import re
                    if is_case_field or not re.search(r'[A-Z][a-z]?\.?\s*\d+/\d+\s+[A-Za-z]+', question):
                        forced_case_id = active_case_context['case_id']
                # Also consult in-memory cache
                # Final fallback: if we have a remembered case for this session, lock to it
                if not forced_case_id and session_id and session_id in self._active_case_by_session:
                    forced_case_id = self._active_case_by_session[session_id]
                # Early topic shift detection: if user starts a new case/topic, release lock
                try:
                    summary = (session.context_data or {}).get('conversation_summary', '') if session else ''
                    decision = self.topic_classifier.classify(summary, question, active_case_context.get('case_number'))
                    if decision == 'new' or is_procedural or is_general_opinion:
                        forced_case_id = None
                except Exception:
                    pass

                # If still no lock and we have a previous query, treat as related follow-up
                if not forced_case_id and session:
                    try:
                        ctx = session.context_data or {}
                        last_query_text = ctx.get('last_query')
                    except Exception:
                        last_query_text = None
                    if last_query_text:
                        # Prefer explicit case from last query
                        try:
                            prev_exact = self.qa_retrieval_service._find_exact_case_match(last_query_text)
                            if prev_exact:
                                forced_case_id = prev_exact[0].get('case_id')
                        except Exception:
                            pass
                        # If still not locked and related without explicit case, use active/in-memory case
                        if not forced_case_id and (not self._has_explicit_case_in_text(question)) and self._is_related_followup(question, last_query_text):
                            if active_case_context.get('case_id'):
                                forced_case_id = active_case_context['case_id']
                            elif session_id and session_id in self._active_case_by_session:
                                forced_case_id = self._active_case_by_session[session_id]
                # Try to detect explicit case in current query; if present but not found, release old lock
                try:
                    explicit_hint = self.qa_retrieval_service._extract_case_title_from_question(question)
                except Exception:
                    explicit_hint = None
                if explicit_hint:
                    try:
                        exact = self.qa_retrieval_service._find_exact_case_match(explicit_hint)
                        if exact:
                            forced_case_id = exact[0].get('case_id')
                        else:
                            forced_case_id = None
                    except Exception:
                        forced_case_id = None
                
                # Persist forced case id immediately in in-memory cache so follow-ups lock
                if forced_case_id and session_id:
                    self._active_case_by_session[session_id] = forced_case_id

                # Build an effective retrieval query that always includes the previous query when appropriate
                retrieval_query = question
                try:
                    if session:
                        ctx = session.context_data or {}
                        last_query_text = ctx.get('last_query')
                        # Only chain for case-related follow-ups
                        if last_query_text and not self._has_explicit_case_in_text(question) and not is_procedural and not is_general_opinion:
                            # Always include the previous query to disambiguate the follow-up
                            retrieval_query = f"{last_query_text} THEN: {question}"
                except Exception:
                    pass

                # DEBUG: log follow-up resolution inputs
                try:
                    logger.info(f"[DEBUG] session_id: {session_id}")
                    logger.info(f"[DEBUG] forced_case_id: {forced_case_id}")
                    logger.info(f"[DEBUG] retrieval_query: {retrieval_query[:200]}")
                except Exception:
                    pass

                # Convert structured data to retrieved document format if available
                pre_retrieved_docs = None
                if structured_data and structured_sources:
                    # Format structured data as a retrieved document for LLM processing
                    source = structured_sources[0] if structured_sources else {}
                    # Format the structured data as context that LLM can convert to conversational answer
                    pre_retrieved_docs = [{
                        'text': structured_data,  # Structured data to be formatted conversationally by LLM
                        'metadata': source.get('metadata', {}),
                        'case_title': source.get('title', ''),
                        'case_number': source.get('case_number', ''),
                        'court': source.get('court', ''),
                        'score': 0.95,  # High confidence for structured lookup
                        'source': 'structured_lookup',
                        'structured_data': {}  # Already formatted in text
                    }]
                    logger.info(f"Passing structured lookup data to LLM for conversational formatting")

                rag_result = self.advanced_rag_engine.generate_answer(
                    query=retrieval_query,
                    user_id=user_id,
                    session_id=session_id,
                    access_level=access_level_enum,
                    conversation_history=conversation_history,
                    filters=filters,
                    forced_case_id=forced_case_id,
                    pre_retrieved_docs=pre_retrieved_docs
                )
                
                # Persist active case context only for case-related queries:
                # 1) when we locked to a specific case, or
                # 2) when the top source clearly contains a case_id even if not forced
                try:
                    if session and rag_result.sources and not is_procedural and not is_general_opinion:
                        meta = rag_result.sources[0] if isinstance(rag_result.sources[0], dict) else {}
                        meta_md = meta.get('metadata', {}) if meta else {}
                        detected_case_id = meta_md.get('case_id')
                        if forced_case_id or detected_case_id:
                            case_context = {
                                'case_id': detected_case_id or forced_case_id,
                                'case_number': meta.get('case_number') if meta else None,
                                'case_title': meta.get('title') if meta else None,
                                'court': meta.get('court') if meta else None,
                                'bench': meta_md.get('bench'),
                                'status': meta_md.get('status'),
                                'advocates_petitioner': meta_md.get('advocates_petitioner'),
                                'advocates_respondent': meta_md.get('advocates_respondent'),
                                'short_order': meta_md.get('short_order'),
                                'case_stage': meta_md.get('case_stage'),
                                'summary': (rag_result.answer or '')[:220],
                                'sources': rag_result.sources,
                            }
                            try:
                                self.conversation_manager.set_active_case_context(session, case_context)
                            except Exception:
                                pass
                            if session_id and case_context.get('case_id'):
                                self._active_case_by_session[session_id] = case_context.get('case_id')
                except Exception as e:
                    logger.warning(f"Failed to persist active case context (adv path): {e}")
                
                # Convert RAG result to legacy format
                # Mark as structured_lookup_llm if it came from structured lookup but was LLM-formatted
                answer_type = 'structured_lookup_llm' if (structured_data and structured_sources) else 'advanced_rag'
                answer_data = {
                    'answer': rag_result.answer,
                    'answer_type': answer_type,
                    'confidence': rag_result.confidence,
                    'model_used': rag_result.metadata.get('llm_model', 'unknown'),
                    'tokens_used': rag_result.metadata.get('tokens_used', 0),
                    'sources': rag_result.sources,
                    'citations': rag_result.citations,
                    'status': rag_result.status,
                    'question': question,
                    'session_id': session_id,
                    'generation_time': rag_result.generation_time,
                    'metadata': self._serialize_metadata(rag_result.metadata),
                    'guardrail_result': {
                        'risk_level': rag_result.guardrail_result.risk_level.value if rag_result.guardrail_result and hasattr(rag_result.guardrail_result, 'risk_level') else None,
                        'allowed': rag_result.guardrail_result.allowed if rag_result.guardrail_result else None,
                        'warnings': rag_result.guardrail_result.warnings if rag_result.guardrail_result else None,
                        'errors': rag_result.guardrail_result.errors if rag_result.guardrail_result else None
                    } if rag_result.guardrail_result else None
                }
                
                if rag_result.error:
                    answer_data['error'] = rag_result.error
                
                # DEBUG: log sources returned
                try:
                    srcs = [
                        f"{(s.get('title') if isinstance(s, dict) else str(s))} | {(s.get('case_number') if isinstance(s, dict) else '')}"
                        for s in (rag_result.sources or [])
                    ]
                    logger.info(f"[DEBUG] sources returned: {srcs}")
                except Exception:
                    pass

                # Store this question as last_query for follow-up awareness
                try:
                    if session:
                        data = session.context_data or {}
                        data['last_query'] = question
                        session.context_data = data
                        session.save(update_fields=['context_data'])
                except Exception as e:
                    logger.warning(f"Failed to persist last_query: {e}")
                
                return answer_data
            
            # Fallback to legacy implementation
            logger.info("Using legacy QA engine for question answering")
            
            # Step 1: Get or create session for conversation management (already done above)
            
            # Step 2: Process follow-up query if session exists
            enhanced_query_info = None
            if session:
                enhanced_query_info = self.conversation_manager.process_follow_up_query(session, question)
                original_question = question
                question = enhanced_query_info.get('enhanced_query', question)
                conversation_history = session.get_recent_context(5)
                
                # Log if query was enhanced
                if question != original_question:
                    logger.info(f"[CONTEXT] Follow-up query enhanced: '{original_question}' -> '{question}'")
                    logger.info(f"[CONTEXT] Is follow-up: {enhanced_query_info.get('is_follow_up', False)}")
            
            # Step 3: Use advanced QA retrieval (two-stage with cross-encoder)
            # Context-aware: lock to active case for pronoun-based follow-ups
            active_case_context = {}
            if session:
                active_case_context = self.conversation_manager.get_active_case_context(session) or {}
            def _has_explicit_case_number(q: str) -> bool:
                import re
                return re.search(r'[A-Z][a-z]?\.?\s*\d+/\d+\s+[A-Za-z]+', q) is not None
            is_pronoun_followup = any(w in question.lower() for w in ['this case', 'that case', 'this', 'it'])
            search_results = None
            if active_case_context.get('case_id') and is_pronoun_followup and not _has_explicit_case_number(question):
                # Lock to active case
                search_results = self.qa_retrieval_service.get_case_by_id(active_case_context['case_id'])
                logger.info(f"Using active case lock for follow-up (case_id={active_case_context['case_id']}); results={len(search_results)}")
            if not search_results:
                search_results = self._advanced_qa_retrieval(question, top_k=5)
            
            # If we got an exact case or by_case_id, clamp to single result and store as active case
            if search_results:
                top = search_results[0]
                meta = top.get('metadata', {})
                if meta.get('match_type') in ('exact_case_number', 'by_case_id'):
                    search_results = [top]
                    # Persist active case context
                    case_context = {
                        'case_id': meta.get('case_id'),
                        'case_number': meta.get('case_number'),
                        'case_title': meta.get('case_title'),
                        'court': meta.get('court'),
                        'bench': meta.get('bench'),
                        'status': meta.get('status'),
                        'advocates_petitioner': meta.get('advocates_petitioner'),
                        'advocates_respondent': meta.get('advocates_respondent'),
                        'short_order': meta.get('short_order'),
                        'case_stage': meta.get('case_stage'),
                        'summary': (top.get('text') or '')[:220],
                        'sources': [{'case_number': meta.get('case_number'), 'title': meta.get('case_title'), 'court': meta.get('court')}],
                    }
                    if session:
                        self.conversation_manager.set_active_case_context(session, case_context)
                else:
                    # If user explicitly mentioned a case number, try to lock to the matching result even without match_type
                    if _has_explicit_case_number(question):
                        q_lower = question.lower()
                        # Find first result whose case_number string appears in the query
                        best = None
                        for res in search_results:
                            m = (res.get('metadata') or {})
                            cn = (m.get('case_number') or '')
                            if cn and cn.lower() in q_lower:
                                best = res
                                break
                        if best:
                            search_results = [best]
                            m = best.get('metadata', {})
                            case_context = {
                                'case_id': m.get('case_id'),
                                'case_number': m.get('case_number'),
                                'case_title': m.get('case_title'),
                                'court': m.get('court'),
                                'bench': m.get('bench'),
                                'status': m.get('status'),
                                'advocates_petitioner': m.get('advocates_petitioner'),
                                'advocates_respondent': m.get('advocates_respondent'),
                                'short_order': m.get('short_order'),
                                'case_stage': m.get('case_stage'),
                                'summary': (best.get('text') or '')[:220],
                                'sources': [{'case_number': m.get('case_number'), 'title': m.get('case_title'), 'court': m.get('court')}],
                            }
                            if session:
                                self.conversation_manager.set_active_case_context(session, case_context)
            
            # Step 4: Extract case information for context
            # If we have active case context, prepend a concise context document
            if active_case_context:
                summary_lines = []
                if active_case_context.get('case_number'):
                    summary_lines.append(f"Case Number: {active_case_context.get('case_number')}")
                if active_case_context.get('case_title'):
                    summary_lines.append(f"Case Title: {active_case_context.get('case_title')}")
                if active_case_context.get('court'):
                    summary_lines.append(f"Court: {active_case_context.get('court')}")
                if active_case_context.get('status'):
                    summary_lines.append(f"Status: {active_case_context.get('status')}")
                if active_case_context.get('bench'):
                    summary_lines.append(f"Bench: {active_case_context.get('bench')}")
                if active_case_context.get('advocates_petitioner'):
                    summary_lines.append(f"Petitioner's Advocates: {active_case_context.get('advocates_petitioner')}")
                if active_case_context.get('advocates_respondent'):
                    summary_lines.append(f"Respondent's Advocates: {active_case_context.get('advocates_respondent')}")
                if active_case_context.get('short_order'):
                    summary_lines.append(f"Short Order: {active_case_context.get('short_order')}")
                prior_doc = {
                    'id': 'active_case_context',
                    'text': "\n".join(summary_lines),
                    'metadata': {
                        'case_id': active_case_context.get('case_id'),
                        'case_number': active_case_context.get('case_number'),
                        'case_title': active_case_context.get('case_title'),
                        'court': active_case_context.get('court'),
                        'status': active_case_context.get('status'),
                        'bench': active_case_context.get('bench'),
                        'match_type': 'active_case_context'
                    },
                    'score': 1.0
                }
                search_results = [prior_doc] + (search_results or [])
            relevant_documents = self._prepare_case_context(search_results)
            
            # Step 5: Generate answer using AI or simple retrieval
            if use_ai and self.ai_generator.enabled:
                answer_data = self.ai_generator.generate_answer(
                    question=question,
                    context_documents=relevant_documents,
                    conversation_history=conversation_history
                )
            else:
                answer_data = self._generate_simple_answer(question, relevant_documents)
            
            # Step 6: Format citations
            if answer_data.get('sources'):
                formatted_sources = self.citation_formatter.format_citations(answer_data['sources'])
                answer_data['sources'] = formatted_sources
            
            # Step 7: Add conversation and search metadata
            answer_data.update({
                'search_method': 'legacy',
                'documents_found': len(relevant_documents),
                'search_results': search_results,
                'question': question,
                'session_id': session.session_id if session else None,
                'is_follow_up': enhanced_query_info.get('is_follow_up', False) if enhanced_query_info else False,
                'conversation_context': enhanced_query_info.get('conversation_context', {}) if enhanced_query_info else {}
            })
            
            # Step 8: Add conversation turn to session
            if session:
                self.conversation_manager.add_conversation_turn(
                    session=session,
                    query=question,
                    response=answer_data.get('answer', ''),
                    context_documents=relevant_documents
                )
            
            return answer_data
            
        except Exception as e:
            logger.error(f"Error in enhanced QA engine: {str(e)}")
            return self._error_response(question, str(e))
    
    def _prepare_case_context(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare case context for AI generation"""
        context_documents = []
        
        for result in search_results:
            # Merge result with its metadata for complete information
            metadata = result.get('metadata', {})
            merged_result = {**result, **metadata}  # Merge metadata into result
            
            # Create a structured document for AI context
            context_doc = {
                'title': merged_result.get('case_title', result.get('case_title', 'Legal Case')),
                'content': self._format_case_content(merged_result),
                'court': merged_result.get('court', result.get('court_name', 'Unknown Court')),
                'case_number': merged_result.get('case_number', result.get('case_number', 'N/A')),
                'category': 'Legal Case',
                'keywords': self._extract_keywords(merged_result),
                'score': result.get('score', 0.0),
                'case_id': merged_result.get('case_id', result.get('case_id')),
                'status': merged_result.get('status', result.get('status')),
                'bench': merged_result.get('bench', result.get('bench')),
                'hearing_date': result.get('hearing_date'),
                'structured_data': result.get('structured_data', {}),
                'text_excerpt': result.get('text', ''),
                'metadata': metadata,  # Include metadata for reference
            }
            context_documents.append(context_doc)
        
        return context_documents
    
    def _format_case_content(self, case_data: Dict[str, Any]) -> str:
        """Format case data into readable content"""
        # If text field already contains formatted content (from exact match), use it
        text_content = case_data.get('text', '')
        if text_content and ('Petitioner\'s Advocates:' in text_content or 'Advocates:' in text_content or 'Petitioner Advocates:' in text_content):
            # Text already has advocates, use it directly
            logger.info(f"Using pre-formatted text content (length: {len(text_content)})")
            return text_content
        
        content_parts = []
        
        # Case title
        if case_data.get('case_title'):
            content_parts.append(f"Case Title: {case_data['case_title']}")
        
        # Case description
        if case_data.get('case_description'):
            content_parts.append(f"Description: {case_data['case_description']}")
        
        # Short order
        if case_data.get('short_order'):
            content_parts.append(f"Order: {case_data['short_order']}")
        
        # Case stage
        if case_data.get('case_stage'):
            content_parts.append(f"Stage: {case_data['case_stage']}")
        
        # Status
        if case_data.get('status'):
            content_parts.append(f"Status: {case_data['status']}")
        
        # Advocates information - check metadata first (from exact match), then structured data
        metadata = case_data.get('metadata', {})
        if metadata.get('advocates_petitioner'):
            content_parts.append(f"Petitioner's Advocates: {metadata['advocates_petitioner']}")
        elif case_data.get('advocates_petitioner'):
            content_parts.append(f"Petitioner's Advocates: {case_data['advocates_petitioner']}")
        
        if metadata.get('advocates_respondent'):
            content_parts.append(f"Respondent's Advocates: {metadata['advocates_respondent']}")
        elif case_data.get('advocates_respondent'):
            content_parts.append(f"Respondent's Advocates: {case_data['advocates_respondent']}")
        
        # FIR information (for criminal cases)
        if case_data.get('fir_number'):
            content_parts.append(f"FIR Number: {case_data['fir_number']}")
        
        if case_data.get('incident'):
            content_parts.append(f"Incident: {case_data['incident']}")
        
        if case_data.get('under_section'):
            content_parts.append(f"Under Section: {case_data['under_section']}")

        structured = case_data.get('structured_data') or {}
        if structured:
            # Only add if not already added from metadata
            if not metadata.get('advocates_petitioner') and not case_data.get('advocates_petitioner'):
                petitioner_adv = structured.get('advocates_petitioner')
                if petitioner_adv:
                    content_parts.append(f"Petitioner Advocates: {self._format_structured_value(petitioner_adv)}")
            
            if not metadata.get('advocates_respondent') and not case_data.get('advocates_respondent'):
                respondent_adv = structured.get('advocates_respondent')
                if respondent_adv:
                    content_parts.append(f"Respondent Advocates: {self._format_structured_value(respondent_adv)}")
            
            fir_details = structured.get('fir_number') or structured.get('fir_info')
            police_station = structured.get('police_station')
            sections = structured.get('under_section')
            parties = structured.get('parties')
            orders = structured.get('order') or structured.get('orders')
            if fir_details and not case_data.get('fir_number'):
                content_parts.append(f"FIR Number: {self._format_structured_value(fir_details)}")
            if police_station and not case_data.get('police_station'):
                content_parts.append(f"Police Station: {self._format_structured_value(police_station)}")
            if sections and not case_data.get('under_section'):
                content_parts.append(f"Under Section: {self._format_structured_value(sections)}")
            if parties:
                formatted_parties = self._format_structured_value(parties)
                content_parts.append(f"Parties: {formatted_parties}")
            if orders:
                formatted_orders = self._format_order_list(orders)
                if formatted_orders:
                    content_parts.append("Orders:\n" + "\n".join(formatted_orders))

        text_excerpt = case_data.get('text') or case_data.get('text_excerpt')
        if text_excerpt and text_excerpt not in content_parts:
            excerpt = text_excerpt if len(text_excerpt) <= 500 else f"{text_excerpt[:500].rstrip()}..."
            content_parts.append(f"Excerpt: {excerpt}")
        
        return "\n".join(content_parts)
    
    def _format_structured_value(self, value: Any) -> str:
        """Format structured values (lists/dicts) into readable strings."""
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            formatted_items = [self._format_structured_value(item) for item in value if item]
            return ", ".join(filter(None, formatted_items))
        if isinstance(value, dict):
            parts = []
            for key, val in value.items():
                if val in (None, '', []):
                    continue
                parts.append(f"{key.replace('_', ' ').title()}: {self._format_structured_value(val)}")
            return "; ".join(parts)
        return str(value)

    def _format_order_list(self, orders: Any) -> List[str]:
        """Create readable summaries for order metadata."""
        if orders is None:
            return []
        if not isinstance(orders, list):
            orders = [orders]
        formatted = []
        for order in orders[:5]:
            if isinstance(order, dict):
                parts = []
                if order.get('sr_number'):
                    parts.append(f"SR {order['sr_number']}")
                if order.get('hearing_date'):
                    parts.append(str(order['hearing_date']))
                if order.get('case_stage'):
                    parts.append(order['case_stage'])
                if order.get('short_order'):
                    parts.append(self._format_structured_value(order['short_order']))
                if parts:
                    formatted.append(" - " + " | ".join(parts))
            else:
                formatted.append(f" - {self._format_structured_value(order)}")
        return formatted
    
    def _extract_keywords(self, case_data: Dict[str, Any]) -> List[str]:
        """Extract keywords from case data"""
        keywords = []
        
        # Add status as keyword
        if case_data.get('status'):
            keywords.append(case_data['status'].lower())
        
        # Add case stage as keyword
        if case_data.get('case_stage'):
            keywords.append(case_data['case_stage'].lower())
        
        # Add court name as keyword
        if case_data.get('court_name'):
            keywords.append(case_data['court_name'].lower())
        
        # Add document type as keyword
        if case_data.get('document_type'):
            keywords.append(case_data['document_type'].lower())
        
        structured = case_data.get('structured_data') or {}
        for key in ['advocates_petitioner', 'advocates_respondent', 'under_section', 'police_station']:
            value = structured.get(key)
            if not value:
                continue
            if isinstance(value, list):
                keywords.extend([str(item).lower() for item in value if item])
            else:
                keywords.append(str(value).lower())
        
        return keywords
    
    def _generate_simple_answer(self, question: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a simple answer without AI"""
        if documents:
            # Use the best matching document
            best_doc = documents[0]
            answer = f"Based on {best_doc.get('title', 'Legal Document')} ({best_doc.get('court', 'Unknown Court')}):\n\n{best_doc.get('content', 'No content available')}"
            confidence = 0.7
        else:
            answer = f"I couldn't find specific information about '{question}' in the current knowledge base. However, I can help you with questions about Pakistani law, including bail procedures, writ petitions, constitutional rights, criminal appeals, property rights, and family law. Please try rephrasing your question or ask about a specific legal topic."
            confidence = 0.1
        
        return {
            'answer': answer,
            'answer_type': 'simple_retrieval',
            'confidence': confidence,
            'model_used': 'simple_retrieval',
            'tokens_used': 0,
            'sources': self._extract_sources(documents),
            'status': 'success'
        }
    
    def _extract_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract source information from documents"""
        sources = []
        for doc in documents:
            sources.append({
                'title': doc.get('title', 'Legal Document'),
                'court': doc.get('court', 'Unknown Court'),
                'case_number': doc.get('case_number', 'N/A'),
                'category': doc.get('category', 'General')
            })
        return sources
    
    def _error_response(self, question: str, error_message: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            'question': question,
            'answer': f"I apologize, but I encountered an error while processing your question: {error_message}. Please try again or rephrase your question.",
            'answer_type': 'error',
            'confidence': 0.0,
            'model_used': 'error',
            'tokens_used': 0,
            'sources': [],
            'status': 'error',
            'error': error_message
        }
    
    def ask_question_streaming(self, 
                              question: str, 
                              user_id: str = "anonymous",
                              session_id: Optional[str] = None,
                              access_level: str = "public",
                              filters: Optional[Dict[str, Any]] = None):
        """Ask a question and get streaming answer"""
        
        if self.use_advanced_rag:
            # Convert access level string to enum
            from .guardrails import AccessLevel
            access_level_enum = AccessLevel(access_level.lower())
            
            # Generate streaming answer using Advanced RAG Engine
            for chunk in self.advanced_rag_engine.generate_streaming_answer(
                query=question,
                user_id=user_id,
                session_id=session_id,
                access_level=access_level_enum,
                filters=filters
            ):
                yield chunk
        else:
            # Fallback to non-streaming for legacy implementation
            result = self.ask_question(
                question=question,
                user_id=user_id,
                session_id=session_id,
                access_level=access_level,
                filters=filters
            )
            
            # Simulate streaming by yielding the result
            yield {
                'type': 'complete',
                'answer': result.get('answer', ''),
                'sources': result.get('sources', []),
                'metadata': result.get('metadata', {})
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get the status of all system components"""
        # Get database statistics
        db_stats = self.knowledge_retriever.get_statistics()
        
        # Get RAG service status
        rag_status = self.rag_service.get_system_status()
        
        # Get Advanced RAG Engine status
        advanced_rag_status = {}
        if self.use_advanced_rag:
            try:
                advanced_rag_status = self.advanced_rag_engine.get_system_status()
            except Exception as e:
                advanced_rag_status = {'error': str(e)}
        
        return {
            'engine_type': 'advanced_rag' if self.use_advanced_rag else 'legacy',
            'ai_generator': {
                'enabled': self.ai_generator.enabled,
                'model': self.ai_generator.model if self.ai_generator.enabled else 'disabled'
            },
            'rag_service': rag_status,
            'advanced_rag_engine': advanced_rag_status,
            'knowledge_base': {
                'total_cases': db_stats.get('total_cases', 0),
                'total_documents': db_stats.get('total_documents', 0),
                'court_distribution': db_stats.get('court_distribution', {}),
                'status_distribution': db_stats.get('status_distribution', {})
            }
        }
    
    def add_document(self, document: Dict[str, Any]) -> bool:
        """Add a new document to the knowledge base"""
        try:
            self.documents.append(document)
            # Recompute embeddings
            self._precompute_embeddings()
            logger.info(f"Added new document: {document.get('title', 'Untitled')}")
            return True
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return False
    
    def _advanced_qa_retrieval(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Advanced QA retrieval using two-stage process with cross-encoder reranking
        
        Args:
            question: User's question
            top_k: Number of results to return
            
        Returns:
            List of high-quality results optimized for QA
        """
        try:
            logger.info(f"Using advanced QA retrieval for: '{question[:50]}...'")
            
            # Try advanced QA retrieval first
            if self.qa_retrieval_service:
                qa_results = self.qa_retrieval_service.retrieve_for_qa(
                    query=question,
                    top_k=top_k
                )
                
                if qa_results:
                    logger.info(f"Advanced QA retrieval found {len(qa_results)} results")
                    return qa_results
                else:
                    logger.info("Advanced QA retrieval returned no results, falling back to knowledge retriever")
            
            # Fallback to original knowledge retriever
            return self.knowledge_retriever.search_legal_cases(question, top_k=top_k)
            
        except Exception as e:
            logger.error(f"Error in advanced QA retrieval: {str(e)}")
            # Fallback to original method
            return self.knowledge_retriever.search_legal_cases(question, top_k=top_k)
    
    def search_only(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search documents without generating an answer"""
        try:
            # Use advanced QA retrieval for search-only as well
            return self._advanced_qa_retrieval(query, top_k)
        except Exception as e:
            logger.error(f"Error in search only: {str(e)}")
            return []
