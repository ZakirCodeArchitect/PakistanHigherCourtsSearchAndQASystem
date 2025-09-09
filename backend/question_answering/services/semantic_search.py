"""
Simplified Search Service
Uses keyword-based search with enhanced matching
"""

import os
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class SemanticSearchService:
    """Simplified search service with keyword-based search"""
    
    def __init__(self):
        """Initialize the search service"""
        self.model_name = "keyword-based"
        self.similarity_threshold = 0.3
        self.top_k = 5
        self.enabled = True
        logger.info("Simplified search service initialized")
    
    def search_documents(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        document_embeddings: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search documents using enhanced keyword matching
        
        Args:
            query: The search query
            documents: List of documents to search through
            document_embeddings: Not used in simplified version
            
        Returns:
            List of documents ranked by relevance score
        """
        if not documents:
            return []
        
        try:
            return self._enhanced_keyword_search(query, documents)
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return []
    
    def _enhanced_keyword_search(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced keyword-based search with better scoring"""
        query_lower = query.lower()
        results = []
        
        # Extract key terms from query
        query_terms = query_lower.split()
        
        for i, doc in enumerate(documents):
            score = 0
            doc_text = self._prepare_document_text(doc).lower()
            
            # Check for exact phrase match
            if query_lower in doc_text:
                score += 5
            
            # Check for individual word matches
            for term in query_terms:
                if len(term) > 2:  # Only consider words longer than 2 characters
                    if term in doc.get('title', '').lower():
                        score += 3
                    if term in doc.get('content', '').lower():
                        score += 2
                    if term in ' '.join(doc.get('keywords', [])).lower():
                        score += 1
            
            # Special handling for common legal terms
            legal_terms = {
                'writ': ['writ petition', 'article 199'],
                'bail': ['bail', 'liberty'],
                'constitution': ['constitutional', 'fundamental rights'],
                'appeal': ['criminal appeal', 'appellate'],
                'property': ['property rights', 'transfer'],
                'family': ['family law', 'marriage', 'divorce']
            }
            
            for term, synonyms in legal_terms.items():
                if term in query_lower:
                    for synonym in synonyms:
                        if synonym in doc_text:
                            score += 2
            
            if score > 0:
                # Normalize score to 0-1 range
                normalized_score = min(score / 8, 1.0)
                results.append({
                    'document': doc,
                    'similarity_score': normalized_score,
                    'relevance': normalized_score,
                    'rank': i + 1
                })
        
        # Sort by score
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:self.top_k]
    
    def _prepare_document_text(self, doc: Dict[str, Any]) -> str:
        """Prepare document text for search"""
        title = doc.get('title', '')
        content = doc.get('content', '')
        keywords = ' '.join(doc.get('keywords', []))
        
        text_parts = [title, content, keywords]
        return ' '.join(filter(None, text_parts))
    
    def create_embeddings(self, texts: List[str]) -> List[float]:
        """Mock embeddings for compatibility"""
        return [0.0] * len(texts)
    
    def create_query_embedding(self, query: str) -> List[float]:
        """Mock query embedding for compatibility"""
        return [0.0]
    
    def calculate_similarity(self, query_embedding: List[float], doc_embeddings: List[List[float]]) -> List[float]:
        """Mock similarity calculation for compatibility"""
        return [0.0] * len(doc_embeddings)
    
    def precompute_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Mock precomputed embeddings for compatibility"""
        return [[0.0]] * len(documents)