"""
Enhanced QA Engine
Combines semantic search and AI answer generation for intelligent question answering
"""

import logging
from typing import List, Dict, Any, Optional
from .ai_answer_generator import AIAnswerGenerator
from .knowledge_retriever import KnowledgeRetriever
from .rag_service import RAGService
from .conversation_manager import ConversationManager, CitationFormatter
from .advanced_embeddings import AdvancedEmbeddingService

logger = logging.getLogger(__name__)

class EnhancedQAEngine:
    """Enhanced QA engine combining semantic search and AI generation"""
    
    def __init__(self):
        """Initialize the enhanced QA engine"""
        self.ai_generator = AIAnswerGenerator()
        self.knowledge_retriever = KnowledgeRetriever()
        self.rag_service = RAGService()
        self.conversation_manager = ConversationManager()
        self.citation_formatter = CitationFormatter()
        self.advanced_embeddings = AdvancedEmbeddingService()
    
    def _precompute_embeddings(self):
        """Precompute embeddings for all documents"""
        # This method is now handled by the RAG service
        pass
    
    def ask_question(
        self, 
        question: str, 
        conversation_history: Optional[List[Dict]] = None,
        use_ai: bool = True,
        session_id: Optional[str] = None,
        user_id: str = "anonymous"
    ) -> Dict[str, Any]:
        """
        Ask a question and get an intelligent answer with conversation management
        
        Args:
            question: The user's question
            conversation_history: Previous conversation context
            use_ai: Whether to use AI generation (True) or simple retrieval (False)
            session_id: Session ID for conversation management
            user_id: User ID for session tracking
            
        Returns:
            Dictionary containing the answer and metadata
        """
        try:
            # Step 1: Get or create session for conversation management
            session = None
            if session_id:
                session = self.conversation_manager.get_or_create_session(user_id, session_id)
            
            # Step 2: Process follow-up query if session exists
            enhanced_query_info = None
            if session:
                enhanced_query_info = self.conversation_manager.process_follow_up_query(session, question)
                question = enhanced_query_info.get('enhanced_query', question)
                conversation_history = session.get_recent_context(5)
            
            # Step 3: Use knowledge retriever to find relevant legal cases
            search_results = self.knowledge_retriever.search_legal_cases(question, top_k=5)
            
            # Step 4: Extract case information for context
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
                'search_method': 'database',  # RAG temporarily disabled
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
            # Create a structured document for AI context
            context_doc = {
                'title': result.get('case_title', 'Legal Case'),
                'content': self._format_case_content(result),
                'court': result.get('court_name', 'Unknown Court'),
                'case_number': result.get('case_number', 'N/A'),
                'category': 'Legal Case',
                'keywords': self._extract_keywords(result),
                'score': result.get('score', 0.0),
                'case_id': result.get('case_id'),
                'status': result.get('status'),
                'bench': result.get('bench'),
                'hearing_date': result.get('hearing_date')
            }
            context_documents.append(context_doc)
        
        return context_documents
    
    def _format_case_content(self, case_data: Dict[str, Any]) -> str:
        """Format case data into readable content"""
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
        
        # FIR information (for criminal cases)
        if case_data.get('fir_number'):
            content_parts.append(f"FIR Number: {case_data['fir_number']}")
        
        if case_data.get('incident'):
            content_parts.append(f"Incident: {case_data['incident']}")
        
        if case_data.get('under_section'):
            content_parts.append(f"Under Section: {case_data['under_section']}")
        
        return "\n".join(content_parts)
    
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
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get the status of all system components"""
        # Get database statistics
        db_stats = self.knowledge_retriever.get_statistics()
        
        # Get RAG service status
        rag_status = self.rag_service.get_system_status()
        
        return {
            'ai_generator': {
                'enabled': self.ai_generator.enabled,
                'model': self.ai_generator.model if self.ai_generator.enabled else 'disabled'
            },
            'rag_service': rag_status,
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
    
    def search_only(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search documents without generating an answer"""
        try:
            results = self.semantic_search.search_documents(
                query=query,
                documents=self.documents,
                document_embeddings=self.document_embeddings
            )
            return results[:top_k]
        except Exception as e:
            logger.error(f"Error in search only: {str(e)}")
            return []
