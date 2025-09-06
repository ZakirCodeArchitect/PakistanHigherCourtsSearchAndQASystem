"""
Query Expansion Service
Enhances search queries with legal synonyms, variations, and domain knowledge
"""

import logging
import re
from typing import List, Dict, Any, Set, Tuple
from django.db.models import Q
from apps.cases.models import Case, Term

logger = logging.getLogger(__name__)


class QueryExpansionService:
    """Service for expanding queries with legal domain knowledge"""
    
    def __init__(self):
        # Legal terminology mappings
        self.legal_synonyms = {
            # Case types
            'appeal': ['appellate', 'revision', 'review', 'challenge'],
            'petition': ['application', 'plea', 'request', 'motion'],
            'bail': ['custody', 'detention', 'remand', 'release'],
            'writ': ['mandamus', 'certiorari', 'prohibition', 'habeas corpus'],
            'civil': ['suit', 'claim', 'dispute', 'matter'],
            'criminal': ['crl', 'crime', 'offence', 'prosecution'],
            
            # Legal concepts
            'constitutional': ['fundamental rights', 'basic rights', 'charter'],
            'contract': ['agreement', 'covenant', 'deed', 'instrument'],
            'property': ['land', 'real estate', 'possession', 'title'],
            'family': ['matrimonial', 'domestic', 'personal law'],
            'commercial': ['business', 'trade', 'mercantile', 'corporate'],
            'tax': ['revenue', 'customs', 'excise', 'duty'],
            
            # Court terminology
            'court': ['tribunal', 'bench', 'forum', 'judiciary'],
            'judge': ['justice', 'magistrate', 'adjudicator'],
            'judgment': ['order', 'decree', 'ruling', 'decision'],
            'hearing': ['proceeding', 'trial', 'session'],
            
            # Legal actions
            'injunction': ['restraint', 'stay', 'prohibition'],
            'damages': ['compensation', 'reparation', 'restitution'],
            'acquittal': ['discharge', 'exoneration', 'absolution'],
            'conviction': ['sentence', 'punishment', 'penalty'],
        }
        
        # Legal abbreviations
        self.legal_abbreviations = {
            'w.p': 'writ petition',
            'c.p': 'civil petition',
            'cr.p': 'criminal petition',
            'f.a.o': 'first appeal',
            'r.f.a': 'regular first appeal',
            'c.r': 'civil revision',
            'crl.rev': 'criminal revision',
            'crl.a': 'criminal appeal',
            'c.o.s': 'civil original suit',
            'i.c.a': 'intra court appeal',
            'r.a': 'review application',
            't.a': 'transfer application',
            'j.s.a': 'jail sentence appeal',
            'ex.pet': 'execution petition',
            'misc': 'miscellaneous',
        }
        
        # Legal phrase patterns
        self.legal_phrases = {
            'vs': ['versus', 'against', 'v'],
            'through': ['thru', 'via'],
            'and others': ['& others', 'et al', 'and ors'],
            'state': ['government', 'federation', 'province'],
            'secretary': ['secy', 'sec'],
            'ministry': ['min', 'dept', 'department'],
        }
        
        # Citation patterns
        self.citation_patterns = [
            r'\b\d{4}\s*[A-Z]+\s*\d+\b',  # 2023 PLD 123
            r'\b[A-Z]+\s*\d{4}\s*\d+\b',  # PLD 2023 123
            r'\b\d+\s*of\s*\d{4}\b',      # 123 of 2023
            r'\b[A-Z]+\.?\s*No\.?\s*\d+\b',  # W.P No. 123
        ]
    
    def expand_query(self, query: str, expansion_mode: str = 'balanced') -> Dict[str, Any]:
        """
        Expand query with legal domain knowledge
        
        Args:
            query: Original search query
            expansion_mode: 'conservative', 'balanced', 'aggressive'
            
        Returns:
            Dictionary with expanded query components
        """
        try:
            logger.info(f"Expanding query: '{query}' with mode: {expansion_mode}")
            
            # Analyze query structure
            query_analysis = self._analyze_query_structure(query)
            
            # Generate expansions
            expansions = self._generate_expansions(query, query_analysis, expansion_mode)
            
            # Create expanded query variants
            expanded_queries = self._create_query_variants(query, expansions)
            
            result = {
                'original_query': query,
                'query_analysis': query_analysis,
                'expansions': expansions,
                'expanded_queries': expanded_queries,
                'boost_terms': self._identify_boost_terms(query, query_analysis),
                'search_strategy': self._recommend_search_strategy(query_analysis)
            }
            
            logger.info(f"Query expansion generated {len(expanded_queries)} variants")
            return result
            
        except Exception as e:
            logger.error(f"Error in query expansion: {str(e)}")
            return {
                'original_query': query,
                'query_analysis': {'type': 'general'},
                'expansions': {},
                'expanded_queries': [query],
                'boost_terms': [],
                'search_strategy': 'hybrid'
            }
    
    def _analyze_query_structure(self, query: str) -> Dict[str, Any]:
        """Analyze query structure and identify components"""
        analysis = {
            'type': 'general',
            'has_citation': False,
            'has_case_parties': False,
            'has_legal_terms': False,
            'has_court_reference': False,
            'has_abbreviations': False,
            'detected_entities': [],
            'legal_concepts': [],
            'citations': [],
            'abbreviations': []
        }
        
        query_lower = query.lower()
        
        # Detect citations
        for pattern in self.citation_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                analysis['has_citation'] = True
                analysis['type'] = 'citation'
                citations = re.findall(pattern, query, re.IGNORECASE)
                analysis['citations'].extend(citations)
        
        # Detect case parties (vs, versus patterns)
        if ' v ' in query_lower or ' vs ' in query_lower or ' versus ' in query_lower:
            analysis['has_case_parties'] = True
            if analysis['type'] == 'general':
                analysis['type'] = 'case_parties'
        
        # Detect legal terms
        legal_terms_found = []
        for term, synonyms in self.legal_synonyms.items():
            if term in query_lower:
                legal_terms_found.append(term)
                analysis['has_legal_terms'] = True
        analysis['legal_concepts'] = legal_terms_found
        
        # Detect abbreviations
        abbreviations_found = []
        for abbrev, full_form in self.legal_abbreviations.items():
            if abbrev in query_lower:
                abbreviations_found.append((abbrev, full_form))
                analysis['has_abbreviations'] = True
        analysis['abbreviations'] = abbreviations_found
        
        # Detect court references
        court_terms = ['court', 'tribunal', 'bench', 'justice', 'judge']
        if any(term in query_lower for term in court_terms):
            analysis['has_court_reference'] = True
        
        # Set query type based on analysis
        if analysis['has_citation']:
            analysis['type'] = 'citation'
        elif analysis['has_case_parties']:
            analysis['type'] = 'case_parties'
        elif analysis['has_legal_terms']:
            analysis['type'] = 'legal_concept'
        elif analysis['has_court_reference']:
            analysis['type'] = 'court_specific'
        
        return analysis
    
    def _generate_expansions(self, query: str, analysis: Dict[str, Any], mode: str) -> Dict[str, List[str]]:
        """Generate query expansions based on analysis"""
        expansions = {
            'synonyms': [],
            'abbreviations': [],
            'legal_variations': [],
            'contextual_terms': []
        }
        
        # Expansion intensity based on mode
        max_synonyms = {'conservative': 2, 'balanced': 3, 'aggressive': 5}[mode]
        
        # Add synonym expansions
        for concept in analysis['legal_concepts']:
            if concept in self.legal_synonyms:
                synonyms = self.legal_synonyms[concept][:max_synonyms]
                expansions['synonyms'].extend(synonyms)
        
        # Add abbreviation expansions
        for abbrev, full_form in analysis['abbreviations']:
            expansions['abbreviations'].append(full_form)
        
        # Add legal variations based on query type
        if analysis['type'] == 'citation':
            expansions['legal_variations'].extend(['case law', 'precedent', 'authority'])
        elif analysis['type'] == 'case_parties':
            expansions['legal_variations'].extend(['litigation', 'dispute', 'matter'])
        elif analysis['type'] == 'legal_concept':
            expansions['legal_variations'].extend(['law', 'legal principle', 'doctrine'])
        
        # Add contextual terms
        query_words = set(query.lower().split())
        if 'civil' in query_words:
            expansions['contextual_terms'].extend(['suit', 'claim', 'damages'])
        if 'criminal' in query_words:
            expansions['contextual_terms'].extend(['prosecution', 'defence', 'trial'])
        
        return expansions
    
    def _create_query_variants(self, original_query: str, expansions: Dict[str, List[str]]) -> List[str]:
        """Create multiple query variants for search"""
        variants = [original_query]
        
        # Create synonym-enhanced queries
        for synonym in expansions['synonyms'][:2]:  # Limit to top 2
            variant = f"{original_query} {synonym}"
            variants.append(variant)
        
        # Create abbreviation-expanded queries
        expanded_query = original_query
        for abbrev, full_form in self.legal_abbreviations.items():
            if abbrev in expanded_query.lower():
                expanded_query = re.sub(
                    re.escape(abbrev), 
                    full_form, 
                    expanded_query, 
                    flags=re.IGNORECASE
                )
        if expanded_query != original_query:
            variants.append(expanded_query)
        
        # Create contextual variants
        if expansions['contextual_terms']:
            contextual_terms = ' '.join(expansions['contextual_terms'][:2])
            variants.append(f"{original_query} {contextual_terms}")
        
        return list(set(variants))  # Remove duplicates
    
    def _identify_boost_terms(self, query: str, analysis: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Identify terms that should receive boosting"""
        boost_terms = []
        
        # High boost for exact citations
        for citation in analysis['citations']:
            boost_terms.append((citation, 3.0))
        
        # Medium boost for legal concepts
        for concept in analysis['legal_concepts']:
            boost_terms.append((concept, 2.0))
        
        # Boost for case parties
        if analysis['has_case_parties']:
            # Extract party names (simplified)
            parts = re.split(r'\s+v\s+|\s+vs\s+|\s+versus\s+', query, flags=re.IGNORECASE)
            for part in parts:
                if len(part.strip()) > 3:
                    boost_terms.append((part.strip(), 1.5))
        
        return boost_terms
    
    def _recommend_search_strategy(self, analysis: Dict[str, Any]) -> str:
        """Recommend optimal search strategy based on query analysis"""
        if analysis['type'] == 'citation':
            return 'keyword_primary'  # Exact matching is crucial
        elif analysis['type'] == 'case_parties':
            return 'hybrid_balanced'  # Mix of exact and semantic
        elif analysis['type'] == 'legal_concept':
            return 'semantic_primary'  # Concept-based matching
        else:
            return 'hybrid'  # Default balanced approach
    
    def get_legal_context_terms(self, query: str) -> List[str]:
        """Get contextual legal terms that might be relevant"""
        context_terms = []
        query_lower = query.lower()
        
        # Context mapping
        context_map = {
            'appeal': ['appellate court', 'higher court', 'revision'],
            'bail': ['custody', 'arrest', 'detention', 'police'],
            'civil': ['damages', 'injunction', 'contract', 'tort'],
            'criminal': ['prosecution', 'defence', 'evidence', 'trial'],
            'constitutional': ['fundamental rights', 'article', 'constitution'],
            'property': ['title', 'possession', 'ownership', 'transfer'],
            'family': ['marriage', 'divorce', 'custody', 'maintenance'],
            'tax': ['assessment', 'appeal', 'tribunal', 'revenue'],
        }
        
        for key_term, contexts in context_map.items():
            if key_term in query_lower:
                context_terms.extend(contexts[:3])  # Limit context terms
        
        return list(set(context_terms))
    
    def enhance_query_with_legal_knowledge(self, query: str) -> Dict[str, Any]:
        """Enhanced query processing with comprehensive legal knowledge"""
        # Get basic expansion
        expansion_result = self.expand_query(query, 'balanced')
        
        # Add legal context
        legal_context = self.get_legal_context_terms(query)
        
        # Identify must-have terms (exact matches required)
        must_have_terms = []
        if expansion_result['query_analysis']['has_citation']:
            must_have_terms.extend(expansion_result['query_analysis']['citations'])
        
        # Identify should-have terms (boost but not required)
        should_have_terms = [term for term, boost in expansion_result['boost_terms']]
        
        # Create comprehensive query structure
        enhanced_result = {
            **expansion_result,
            'legal_context': legal_context,
            'must_have_terms': must_have_terms,
            'should_have_terms': should_have_terms,
            'query_complexity': self._assess_query_complexity(expansion_result['query_analysis'])
        }
        
        return enhanced_result
    
    def _assess_query_complexity(self, analysis: Dict[str, Any]) -> str:
        """Assess query complexity for search strategy optimization"""
        complexity_score = 0
        
        if analysis['has_citation']: complexity_score += 3
        if analysis['has_case_parties']: complexity_score += 2
        if analysis['has_legal_terms']: complexity_score += 2
        if analysis['has_court_reference']: complexity_score += 1
        if analysis['has_abbreviations']: complexity_score += 1
        
        if complexity_score >= 6:
            return 'high'
        elif complexity_score >= 3:
            return 'medium'
        else:
            return 'low'
