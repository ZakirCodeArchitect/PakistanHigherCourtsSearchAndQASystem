import json
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class SimpleAISnippetService:
    """
    Simplified AI-powered snippet generation service
    This version works without external AI dependencies and can be easily upgraded
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = {
            'max_snippet_length': 200,
            'temperature': 0.3,
            'max_tokens': 150,
            'timeout': 10,
        }
        
        # Update with custom config
        if config:
            self.config.update(config)
    
    def generate_ai_snippet(self, 
                           case_data: Dict[str, Any], 
                           query: str,
                           document_chunks: List[str] = None,
                           max_snippets: int = 3) -> List[Dict[str, Any]]:
        """
        Generate AI-powered snippets from case data
        This is a simplified version that creates intelligent snippets without external AI
        """
        try:
            # Prepare context for snippet generation
            context = self._prepare_context(case_data, query, document_chunks)
            
            # Generate intelligent snippets
            snippets = self._generate_intelligent_snippets(context, query, max_snippets)
            
            return snippets
            
        except Exception as e:
            logger.error(f"Error generating AI snippets: {str(e)}")
            # Fallback to simple extraction
            return self._fallback_snippet_generation(case_data, document_chunks)
    
    def _prepare_context(self, 
                        case_data: Dict[str, Any], 
                        query: str, 
                        document_chunks: List[str]) -> Dict[str, Any]:
        """Prepare context for snippet generation"""
        
        # Extract key information
        case_title = case_data.get('case_title', 'Unknown Case')
        court = case_data.get('court', 'Unknown Court')
        status = case_data.get('status', 'Unknown Status')
        case_number = case_data.get('case_number', 'N/A')
        
        # Prepare document content
        document_content = ""
        if document_chunks:
            # Take first few chunks with most relevant content
            relevant_chunks = self._select_relevant_chunks(document_chunks, query)
            document_content = "\n\n".join(relevant_chunks[:3])  # Max 3 chunks
        
        return {
            'case_title': case_title,
            'court': court,
            'status': status,
            'case_number': case_number,
            'document_content': document_content,
            'query': query
        }
    
    def _select_relevant_chunks(self, chunks: List[str], query: str) -> List[str]:
        """Select most relevant chunks based on query terms"""
        query_terms = query.lower().split()
        scored_chunks = []
        
        for chunk in chunks:
            if not chunk or len(chunk.strip()) < 50:
                continue
                
            # Simple relevance scoring
            chunk_lower = chunk.lower()
            score = sum(1 for term in query_terms if term in chunk_lower)
            
            # Boost score for legal terms
            legal_terms = ['court', 'judge', 'order', 'judgment', 'law', 'legal', 'case', 'petition', 'appeal']
            score += sum(0.5 for term in legal_terms if term in chunk_lower)
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by relevance and return top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_chunks]
    
    def _generate_intelligent_snippets(self, context: Dict[str, Any], query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate intelligent snippets using rule-based approach"""
        snippets = []
        
        case_title = context['case_title']
        court = context['court']
        status = context['status']
        case_number = context['case_number']
        document_content = context['document_content']
        
        # Generate snippet 1: Case overview
        if case_title and court:
            snippet1 = f"This case involves {case_title} in {court}. "
            if status:
                snippet1 += f"The case status is {status}. "
            if case_number and case_number != 'N/A':
                snippet1 += f"Case number: {case_number}."
            
            snippets.append(self._create_snippet_object(snippet1.strip(), query, 'case_overview'))
        
        # Generate snippet 2: Legal content analysis
        if document_content:
            legal_content = self._extract_legal_content(document_content, query)
            if legal_content:
                snippet2 = f"Legal proceedings: {legal_content}"
                snippets.append(self._create_snippet_object(snippet2, query, 'legal_content'))
        
        # Generate snippet 3: Query relevance
        relevance_snippet = self._generate_relevance_snippet(context, query)
        if relevance_snippet:
            snippets.append(self._create_snippet_object(relevance_snippet, query, 'relevance'))
        
        return snippets[:max_snippets]
    
    def _extract_legal_content(self, document_content: str, query: str) -> str:
        """Extract relevant legal content from document"""
        if not document_content:
            return ""
        
        # Look for legal terms and proceedings
        legal_indicators = [
            'death sentence', 'jail appeal', 'conviction', 'bail', 'petition',
            'order', 'judgment', 'hearing', 'trial', 'proceedings', 'court order',
            'legal', 'law', 'statute', 'regulation', 'act', 'section'
        ]
        
        # Find sentences with legal content
        sentences = document_content.split('. ')
        legal_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            # Check if sentence contains legal terms
            sentence_lower = sentence.lower()
            if any(term in sentence_lower for term in legal_indicators):
                legal_sentences.append(sentence)
        
        # Return the most relevant legal sentence
        if legal_sentences:
            # Prioritize sentences with query terms
            query_terms = query.lower().split()
            for sentence in legal_sentences:
                if any(term in sentence.lower() for term in query_terms):
                    return sentence[:150] + "..." if len(sentence) > 150 else sentence
            
            # Fallback to first legal sentence
            return legal_sentences[0][:150] + "..." if len(legal_sentences[0]) > 150 else legal_sentences[0]
        
        return ""
    
    def _generate_relevance_snippet(self, context: Dict[str, Any], query: str) -> str:
        """Generate snippet explaining relevance to query"""
        query_lower = query.lower()
        
        # Murder-related queries
        if any(term in query_lower for term in ['murder', 'killing', 'homicide', 'death']):
            if 'death sentence' in context['document_content'].lower():
                return "This case involves a death sentence, making it highly relevant to murder-related legal proceedings."
            elif 'conviction' in context['document_content'].lower():
                return "This case involves a criminal conviction, which may be related to violent crimes including murder."
        
        # Bail-related queries
        elif any(term in query_lower for term in ['bail', 'bond', 'release']):
            if 'bail' in context['document_content'].lower():
                return "This case involves bail proceedings, directly relevant to your search for bail-related legal matters."
        
        # Appeal-related queries
        elif any(term in query_lower for term in ['appeal', 'revision', 'petition']):
            if 'appeal' in context['document_content'].lower():
                return "This case involves an appeal, making it relevant to appellate court proceedings."
        
        # General case relevance
        return f"This case from {context['court']} may contain relevant legal principles for your research on {query}."
    
    def _create_snippet_object(self, text: str, query: str, snippet_type: str) -> Dict[str, Any]:
        """Create a snippet object from text"""
        # Clean up the text
        text = text.strip()
        if text.endswith('.'):
            text = text[:-1]
        
        return {
            'text': text,
            'type': snippet_type,
            'relevance_score': 0.9,  # High relevance for intelligent snippets
            'matched_term': query,
            'length': len(text),
            'source': 'intelligent_generation'
        }
    
    def _fallback_snippet_generation(self, case_data: Dict[str, Any], document_chunks: List[str]) -> List[Dict[str, Any]]:
        """Fallback snippet generation when intelligent generation fails"""
        snippets = []
        
        # Create simple snippets from case data
        case_title = case_data.get('case_title', 'Unknown Case')
        court = case_data.get('court', 'Unknown Court')
        status = case_data.get('status', 'Unknown Status')
        
        snippet_text = f"This case involves {case_title} in {court}. Status: {status}."
        snippets.append({
            'text': snippet_text,
            'type': 'fallback',
            'relevance_score': 0.5,
            'matched_term': 'case_info',
            'length': len(snippet_text),
            'source': 'fallback'
        })
        
        return snippets
