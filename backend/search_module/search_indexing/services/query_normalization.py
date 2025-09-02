"""
Query Normalization Service
Handles legal citation canonicalization and query preprocessing
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from django.db.models import Q
from apps.cases.models import Term, TermOccurrence

logger = logging.getLogger(__name__)


class QueryNormalizationService:
    """Service for normalizing legal search queries"""
    
    def __init__(self):
        # Legal citation patterns
        self.citation_patterns = {
            'ppc': r'(?:P\.?P\.?C\.?|Pakistan\s+Penal\s+Code)\s*[:\-]?\s*(\d+(?:[a-z])?)',
            'crpc': r'(?:Cr\.?P\.?C\.?|Criminal\s+Procedure\s+Code)\s*[:\-]?\s*(\d+(?:[a-z])?)',
            'cpc': r'(?:C\.?P\.?C\.?|Civil\s+Procedure\s+Code)\s*[:\-]?\s*(\d+(?:[a-z])?)',
            'plj': r'(?:PLJ|Pakistan\s+Law\s+Journal)\s*[:\-]?\s*(\d+)',
            'pld': r'(?:PLD|Pakistan\s+Legal\s+Decisions)\s*[:\-]?\s*(\d+)',
            'mld': r'(?:MLD|Monthly\s+Law\s+Digest)\s*[:\-]?\s*(\d+)',
            'clc': r'(?:CLC|Civil\s+Law\s+Cases)\s*[:\-]?\s*(\d+)',
            'scmr': r'(?:SCMR|Supreme\s+Court\s+Monthly\s+Review)\s*[:\-]?\s*(\d+)',
            'ylr': r'(?:YLR|Yearly\s+Law\s+Report)\s*[:\-]?\s*(\d+)',
        }
        
        # Legal abbreviations mapping
        self.legal_abbreviations = {
            'cr.p.c.': 'crpc',
            'crpc': 'crpc',
            'p.p.c.': 'ppc',
            'ppc': 'ppc',
            'c.p.c.': 'cpc',
            'cpc': 'cpc',
            'vs': 'vs',
            'pet': 'petition',
            'app': 'appeal',
            'rev': 'revision',
            'misc': 'miscellaneous',
            'const.': 'constitutional',
            'const': 'constitutional',
            'admin': 'administrative',
            'writ': 'writ',
            'habeas': 'habeas corpus',
            'mandamus': 'mandamus',
            'certiorari': 'certiorari',
            'prohibition': 'prohibition',
            'quo warranto': 'quo warranto',
        }
        
        # Precompiled regex patterns for performance
        self.compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE) 
            for key, pattern in self.citation_patterns.items()
        }
    
    def normalize_query(self, query: str) -> Dict[str, Any]:
        """
        Normalize a search query and extract legal citations
        
        Returns:
            Dict containing:
            - normalized_query: processed query string
            - citations: extracted legal citations
            - exact_identifiers: exact case numbers/citations
            - boost_signals: signals for ranking boosts
        """
        try:
            original_query = query.strip()
            if not original_query:
                return self._empty_result()
            
            # Step 1: Extract legal citations
            citations = self._extract_citations(original_query)
            
            # Step 2: Detect exact identifiers
            exact_identifiers = self._detect_exact_identifiers(original_query)
            
            # Step 3: Normalize text
            normalized_text = self._normalize_text(original_query)
            
            # Step 4: Generate boost signals
            boost_signals = self._generate_boost_signals(citations, exact_identifiers)
            
            # Step 5: Build final normalized query
            normalized_query = self._build_normalized_query(normalized_text, citations)
            
            result = {
                'original_query': original_query,
                'normalized_query': normalized_query,
                'citations': citations,
                'exact_identifiers': exact_identifiers,
                'boost_signals': boost_signals,
                'processing_metadata': {
                    'has_citations': len(citations) > 0,
                    'has_exact_matches': len(exact_identifiers) > 0,
                    'citation_count': len(citations),
                    'identifier_count': len(exact_identifiers)
                }
            }
            
            logger.debug(f"Query normalized: {original_query} -> {normalized_query}")
            return result
            
        except Exception as e:
            logger.error(f"Error normalizing query '{query}': {str(e)}")
            return self._empty_result()
    
    def _extract_citations(self, query: str) -> List[Dict[str, Any]]:
        """Extract legal citations from query"""
        citations = []
        
        for citation_type, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(query)
            for match in matches:
                section_num = match.group(1)
                canonical_form = f"{citation_type}:{section_num}"
                
                citations.append({
                    'type': citation_type,
                    'section': section_num,
                    'canonical': canonical_form,
                    'original': match.group(0),
                    'start_pos': match.start(),
                    'end_pos': match.end()
                })
        
        return citations
    
    def _detect_exact_identifiers(self, query: str) -> List[Dict[str, Any]]:
        """Detect exact case numbers and citations"""
        identifiers = []
        
        # Case number patterns (e.g., "Application 2/2025", "Petition 123/2024")
        case_patterns = [
            r'\b(?:Application|Petition|Appeal|Revision|Misc|Const)\s+(\d+/\d{4})\b',
            r'\b(\d+/\d{4})\b',  # Simple number/year pattern
            r'\b([A-Z]{2,}\s+\d+/\d{4})\b',  # Court code + number/year
        ]
        
        for pattern in case_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                identifiers.append({
                    'type': 'case_number',
                    'value': match.group(1),
                    'original': match.group(0),
                    'start_pos': match.start(),
                    'end_pos': match.end()
                })
        
        return identifiers
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for search"""
        # Convert to lowercase
        normalized = text.lower()
        
        # Normalize legal abbreviations
        for abbrev, full in self.legal_abbreviations.items():
            normalized = re.sub(r'\b' + re.escape(abbrev) + r'\b', full, normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove punctuation (keep spaces)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        
        return normalized.strip()
    
    def _generate_boost_signals(self, citations: List[Dict], identifiers: List[Dict]) -> Dict[str, Any]:
        """Generate signals for ranking boosts"""
        boost_signals = {
            'citation_boost': 0.0,
            'exact_match_boost': 0.0,
            'legal_term_boost': 0.0,
            'total_boost': 0.0
        }
        
        # Citation boost
        if citations:
            boost_signals['citation_boost'] = min(2.0, len(citations) * 0.5)
        
        # Exact identifier boost
        if identifiers:
            boost_signals['exact_match_boost'] = min(3.0, len(identifiers) * 1.0)
        
        # Legal term boost (will be calculated during search)
        boost_signals['legal_term_boost'] = 0.0
        
        # Total boost
        boost_signals['total_boost'] = (
            boost_signals['citation_boost'] + 
            boost_signals['exact_match_boost'] + 
            boost_signals['legal_term_boost']
        )
        
        return boost_signals
    
    def _build_normalized_query(self, normalized_text: str, citations: List[Dict]) -> str:
        """Build final normalized query string"""
        query_parts = [normalized_text]
        
        # Add canonical citation forms
        for citation in citations:
            query_parts.append(citation['canonical'])
        
        return ' '.join(query_parts)
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'original_query': '',
            'normalized_query': '',
            'citations': [],
            'exact_identifiers': [],
            'boost_signals': {
                'citation_boost': 0.0,
                'exact_match_boost': 0.0,
                'legal_term_boost': 0.0,
                'total_boost': 0.0
            },
            'processing_metadata': {
                'has_citations': False,
                'has_exact_matches': False,
                'citation_count': 0,
                'identifier_count': 0
            }
        }
    
    def get_canonical_terms(self, query: str) -> List[str]:
        """Get canonical terms for a query to boost relevant cases"""
        try:
            # Extract citations
            citations = self._extract_citations(query)
            
            # Get canonical forms
            canonical_terms = []
            for citation in citations:
                canonical_terms.append(citation['canonical'])
            
            # Also check for general legal terms
            normalized_query = self._normalize_text(query)
            words = normalized_query.split()
            
            # Look for legal terms in the vocabulary
            for word in words:
                if len(word) > 3:  # Skip very short words
                    terms = Term.objects.filter(
                        canonical__icontains=word,
                        type__in=['section', 'statute', 'citation']
                    )[:5]  # Limit results
                    
                    for term in terms:
                        canonical_terms.append(term.canonical)
            
            return list(set(canonical_terms))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error getting canonical terms: {str(e)}")
            return []
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate query and provide suggestions"""
        try:
            if not query or len(query.strip()) < 2:
                return {
                    'is_valid': False,
                    'error': 'Query too short (minimum 2 characters)',
                    'suggestions': []
                }
            
            if len(query.strip()) > 500:
                return {
                    'is_valid': False,
                    'error': 'Query too long (maximum 500 characters)',
                    'suggestions': []
                }
            
            # Check for potentially problematic queries
            warnings = []
            suggestions = []
            
            # Check for very common words
            common_words = ['the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with']
            query_words = query.lower().split()
            if len(query_words) == 1 and query_words[0] in common_words:
                warnings.append('Query contains only common words')
                suggestions.append('Try adding more specific legal terms')
            
            # Check for citation-like patterns that might be incomplete
            incomplete_citations = re.findall(r'\b(?:ppc|crpc|cpc)\s*$', query.lower())
            if incomplete_citations:
                warnings.append('Incomplete citation detected')
                suggestions.append('Complete the citation (e.g., "PPC 302" instead of "PPC")')
            
            return {
                'is_valid': True,
                'warnings': warnings,
                'suggestions': suggestions,
                'query_length': len(query.strip())
            }
            
        except Exception as e:
            logger.error(f"Error validating query: {str(e)}")
            return {
                'is_valid': False,
                'error': 'Query validation failed',
                'suggestions': []
            }
