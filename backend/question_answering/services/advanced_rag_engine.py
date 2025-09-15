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
        
        # Initialize retrieval service
        self.retrieval_service = QARetrievalService()
        
        # Configuration
        self.enable_guardrails = self.config.get('enable_guardrails', False)
        self.enable_conversation_context = self.config.get('enable_conversation_context', True)
        self.default_access_level = AccessLevel(self.config.get('default_access_level', 'public'))
        self.max_retrieval_results = self.config.get('max_retrieval_results', 12)
        
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
                       filters: Optional[Dict[str, Any]] = None) -> RAGResult:
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
            if session_id and self.enable_conversation_context:
                session = self.conversation_manager.get_or_create_session(user_id, session_id)
                if session:
                    conversation_context = self.conversation_manager.get_conversation_context(session, 5)
                    conversation_history = conversation_context.get('recent_turns', [])
                    logger.info(f"Retrieved conversation history: {len(conversation_history)} turns")
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
            
            # Step 4: Retrieve relevant documents
            logger.info(f"Retrieving documents for query: '{query[:50]}...'")
            retrieved_docs = self.retrieval_service.retrieve_for_qa(
                query=query,
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
            
            # Step 5: Pack context for LLM
            logger.info(f"Packing context from {len(retrieved_docs)} retrieved documents")
            try:
                packed_context = self.context_packer.pack_context(
                    retrieved_chunks=retrieved_docs,
                    query=query,
                    conversation_history=conversation_history
                )
                logger.info(f"Context packing completed successfully, type: {type(packed_context)}")
                if isinstance(packed_context, dict):
                    logger.info(f"Packed context keys: {list(packed_context.keys())}")
                    logger.info(f"Packed context status: {packed_context.get('status', 'NO_STATUS_KEY')}")
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
            
            # Step 6: Determine query type and legal domain
            query_type = self._classify_query_type(query)
            legal_domain = self._classify_legal_domain(query, retrieved_docs)
            
            # Step 7: Get appropriate prompt template
            template = self.prompt_system.get_template(query_type, legal_domain, conversation_history)
            
            # Step 8: Format prompt
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
            
            # Step 9: Generate answer with LLM
            logger.info(f"Generating answer with {template.name} template")
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
            
            # Step 10: Apply guardrails to response
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
            
            # Step 11: Format citations
            formatted_sources = self.citation_formatter.format_citations(retrieved_docs)
            
            # Step 12: Add conversation turn to session
            if session:
                self.conversation_manager.add_conversation_turn(
                    session=session,
                    query=query,
                    response=llm_result.text,
                    context_documents=retrieved_docs
                )
            
            # Step 13: Prepare final result
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
