"""
Precision Optimizer Service
Improves search precision through relevance filtering, query enhancement, and result refinement
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import math

from django.db.models import Q
from apps.cases.models import Case, Term, TermOccurrence
from ..models import SearchMetadata

logger = logging.getLogger(__name__)


class PrecisionOptimizerService:
    """Service to optimize search precision and relevance"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Precision optimization configuration
        self.default_config = {
            'relevance_threshold': 0.3,
            'max_results': 200,  # Increased from 20 to allow more results
            'diversity_threshold': 0.8,
            'legal_term_boost': 2.0,
            'exact_match_boost': 3.0,
            'citation_boost': 2.5,
            'recency_weight': 0.1,
            'court_hierarchy_boost': 1.5,
            'enable_query_expansion': True,
            'enable_result_filtering': True,
            'enable_relevance_scoring': True,
            # New intelligent filtering parameters
            'min_relevance_score': 0.1,   # Higher minimum score for quality
            'score_drop_threshold': 0.45, # Stop when score drops below 45% of top score
            'enable_intelligent_cutoff': True,
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
    
    def optimize_search_results(self, 
                               search_results: List[Dict[str, Any]], 
                               query: str,
                               search_mode: str = 'hybrid',
                               filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Optimize search results for better precision
        
        Args:
            search_results: Raw search results
            query: Original search query
            search_mode: Search mode used
            filters: Applied filters
            
        Returns:
            Optimized and filtered search results
        """
        try:
            logger.info(f"Optimizing {len(search_results)} search results for precision")
            
            # Step 1: Enhance query understanding
            enhanced_query_info = self._enhance_query_understanding(query)
            
            # Step 2: Apply relevance scoring
            scored_results = self._apply_precision_scoring(search_results, enhanced_query_info)
            
            # Step 3: Filter by relevance threshold
            filtered_results = self._filter_by_relevance(scored_results)
            
            # Step 4: Apply legal domain boosting
            boosted_results = self._apply_legal_domain_boosting(filtered_results, enhanced_query_info)
            
            # Step 5: Remove low-quality results
            quality_filtered = self._filter_low_quality_results(boosted_results)
            
            # Step 6: Apply diversity filtering
            diverse_results = self._apply_diversity_filtering(quality_filtered)
            
            # Step 7: Final ranking and limiting
            final_results = self._final_precision_ranking(diverse_results)
            
            logger.info(f"Precision optimization reduced results from {len(search_results)} to {len(final_results)}")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in precision optimization: {str(e)}")
            # Return original results if optimization fails
            return search_results[:self.default_config['max_results']]
    
    def _enhance_query_understanding(self, query: str) -> Dict[str, Any]:
        """Enhanced query analysis for legal domain"""
        query_info = {
            'original_query': query,
            'normalized_query': query.lower().strip(),
            'query_type': 'general',
            'legal_entities': [],
            'citations': [],
            'key_terms': [],
            'boost_factors': {}
        }
        
        # Detect query type
        query_info['query_type'] = self._detect_query_type(query)
        
        # Extract legal entities
        query_info['legal_entities'] = self._extract_legal_entities(query)
        
        # Extract citations
        query_info['citations'] = self._extract_citations(query)
        
        # Extract key legal terms
        query_info['key_terms'] = self._extract_key_legal_terms(query)
        
        # Calculate boost factors
        query_info['boost_factors'] = self._calculate_query_boost_factors(query_info)
        
        return query_info
    
    def _detect_query_type(self, query: str) -> str:
        """Detect the type of legal query"""
        query_lower = query.lower()
        
        # Citation patterns
        citation_patterns = [
            r'\b\d{4}\s*[A-Z]+\s*\d+\b',  # 2023 PLD 123
            r'\b[A-Z]+\s*\d{4}\s*\d+\b',  # PLD 2023 123
            r'\b\d+\s*of\s*\d{4}\b',      # 123 of 2023
        ]
        
        for pattern in citation_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return 'citation'
        
        # Case title patterns
        if ' v ' in query_lower or ' vs ' in query_lower or ' versus ' in query_lower:
            return 'case_title'
        
        # Legal concept patterns
        legal_concepts = [
            'appeal', 'petition', 'bail', 'habeas corpus', 'constitutional',
            'civil suit', 'criminal case', 'writ', 'injunction', 'damages'
        ]
        
        for concept in legal_concepts:
            if concept in query_lower:
                return 'legal_concept'
        
        # Court-specific patterns
        court_terms = ['supreme court', 'high court', 'district court', 'sessions court']
        for term in court_terms:
            if term in query_lower:
                return 'court_specific'
        
        return 'general'
    
    def _extract_legal_entities(self, query: str) -> List[str]:
        """Extract legal entities from query"""
        entities = []
        
        # Common legal entities
        entity_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Person names
            r'\b[A-Z]+\s+(?:Ltd|Limited|Corp|Corporation|Inc)\b',   # Company names
            r'\b(?:State|Government|Ministry|Department)\s+of\s+[A-Z][a-z]+\b',  # Government entities
        ]
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)
        
        return entities[:5]  # Limit to top 5 entities
    
    def _extract_citations(self, query: str) -> List[str]:
        """Extract legal citations from query"""
        citations = []
        
        citation_patterns = [
            r'\b\d{4}\s*[A-Z]+\s*\d+\b',  # 2023 PLD 123
            r'\b[A-Z]+\s*\d{4}\s*\d+\b',  # PLD 2023 123
            r'\b\d+\s*of\s*\d{4}\b',      # 123 of 2023
            r'\b[A-Z]+\s*No\.\s*\d+\b',   # W.P No. 123
        ]
        
        for pattern in citation_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            citations.extend(matches)
        
        return citations
    
    def _extract_key_legal_terms(self, query: str) -> List[str]:
        """Extract key legal terms for boosting"""
        legal_terms = [
            'appeal', 'petition', 'bail', 'habeas corpus', 'constitutional',
            'civil', 'criminal', 'writ', 'injunction', 'damages', 'compensation',
            'contempt', 'review', 'revision', 'acquittal', 'conviction',
            'jurisdiction', 'precedent', 'judgment', 'order', 'decree'
        ]
        
        query_lower = query.lower()
        found_terms = []
        
        for term in legal_terms:
            if term in query_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _calculate_query_boost_factors(self, query_info: Dict[str, Any]) -> Dict[str, float]:
        """Calculate boost factors based on query analysis"""
        boost_factors = {}
        
        # Query type boosts
        type_boosts = {
            'citation': 2.5,
            'case_title': 2.0,
            'legal_concept': 1.8,
            'court_specific': 1.5,
            'general': 1.0
        }
        boost_factors['query_type'] = type_boosts.get(query_info['query_type'], 1.0)
        
        # Entity boost
        boost_factors['entity_boost'] = min(2.0, 1.0 + len(query_info['legal_entities']) * 0.2)
        
        # Citation boost
        boost_factors['citation_boost'] = min(3.0, 1.0 + len(query_info['citations']) * 0.5)
        
        # Legal terms boost
        boost_factors['legal_terms_boost'] = min(2.0, 1.0 + len(query_info['key_terms']) * 0.15)
        
        return boost_factors
    
    def _apply_precision_scoring(self, results: List[Dict[str, Any]], query_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply precision-focused scoring to results"""
        scored_results = []
        
        for result in results:
            precision_score = self._calculate_precision_score(result, query_info)
            result['precision_score'] = precision_score
            result['original_score'] = result.get('similarity', result.get('rank', 0))
            scored_results.append(result)
        
        return scored_results
    
    def _calculate_precision_score(self, result: Dict[str, Any], query_info: Dict[str, Any]) -> float:
        """Calculate precision-focused relevance score"""
        base_score = result.get('similarity', result.get('rank', 0))
        
        # Start with base score
        precision_score = float(base_score)
        
        # Apply query type boost
        precision_score *= query_info['boost_factors'].get('query_type', 1.0)
        
        # Check for exact matches in case data
        case_data = result.get('result_data', result)
        
        # Exact case number match
        if self._has_exact_case_number_match(case_data, query_info):
            precision_score *= self.default_config['exact_match_boost']
        
        # Citation match
        if self._has_citation_match(case_data, query_info):
            precision_score *= self.default_config['citation_boost']
        
        # Legal term matches
        legal_term_matches = self._count_legal_term_matches(case_data, query_info)
        if legal_term_matches > 0:
            precision_score *= (1.0 + legal_term_matches * 0.2)
        
        # Court hierarchy boost
        court_boost = self._get_court_hierarchy_boost(case_data)
        precision_score *= court_boost
        
        # Recency boost (slight)
        recency_boost = self._get_recency_boost(case_data)
        precision_score *= recency_boost
        
        return precision_score
    
    def _has_exact_case_number_match(self, case_data: Dict[str, Any], query_info: Dict[str, Any]) -> bool:
        """Check for exact case number match"""
        case_number = case_data.get('case_number', '').lower()
        query = query_info['normalized_query']
        
        # Extract potential case numbers from query
        for citation in query_info['citations']:
            if citation.lower() in case_number:
                return True
        
        return False
    
    def _has_citation_match(self, case_data: Dict[str, Any], query_info: Dict[str, Any]) -> bool:
        """Check for citation match"""
        return len(query_info['citations']) > 0
    
    def _count_legal_term_matches(self, case_data: Dict[str, Any], query_info: Dict[str, Any]) -> int:
        """Count legal term matches in case data"""
        case_text = f"{case_data.get('case_title', '')} {case_data.get('case_number', '')}".lower()
        matches = 0
        
        for term in query_info['key_terms']:
            if term in case_text:
                matches += 1
        
        return matches
    
    def _get_court_hierarchy_boost(self, case_data: Dict[str, Any]) -> float:
        """Get boost based on court hierarchy"""
        court = case_data.get('court', '').lower()
        
        if 'supreme' in court:
            return 1.5
        elif 'high' in court:
            return 1.3
        elif 'district' in court:
            return 1.1
        else:
            return 1.0
    
    def _get_recency_boost(self, case_data: Dict[str, Any]) -> float:
        """Get boost based on case recency"""
        # Simple recency boost - newer cases get slight preference
        return 1.0 + self.default_config['recency_weight']
    
    def _filter_by_relevance(self, scored_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results by relevance threshold"""
        threshold = self.default_config['relevance_threshold']
        filtered_results = []
        
        for result in scored_results:
            if result['precision_score'] >= threshold:
                filtered_results.append(result)
        
        logger.info(f"Relevance filtering: {len(scored_results)} -> {len(filtered_results)} results")
        return filtered_results
    
    def _apply_legal_domain_boosting(self, results: List[Dict[str, Any]], query_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply legal domain-specific boosting"""
        for result in results:
            # Additional legal domain boosts
            case_data = result.get('result_data', result)
            
            # Boost based on case type alignment
            if self._has_case_type_alignment(case_data, query_info):
                result['precision_score'] *= 1.2
        
        return results
    
    def _has_case_type_alignment(self, case_data: Dict[str, Any], query_info: Dict[str, Any]) -> bool:
        """Check if case type aligns with query intent"""
        case_title = case_data.get('case_title', '').lower()
        query_type = query_info['query_type']
        
        if query_type == 'legal_concept':
            # Check if case title contains legal concepts from query
            for term in query_info['key_terms']:
                if term in case_title:
                    return True
        
        return False
    
    def _filter_low_quality_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove low-quality results"""
        quality_results = []
        
        for result in results:
            case_data = result.get('result_data', result)
            
            # Skip results with missing essential data
            if not case_data.get('case_title') or not case_data.get('case_number'):
                continue
            
            # Skip very short case titles (likely incomplete data)
            if len(case_data.get('case_title', '')) < 10:
                continue
            
            quality_results.append(result)
        
        return quality_results
    
    def _apply_diversity_filtering(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply diversity filtering to avoid duplicate-like results"""
        if len(results) <= 5:
            return results
        
        diverse_results = []
        seen_titles = set()
        
        for result in results:
            case_data = result.get('result_data', result)
            case_title = case_data.get('case_title', '').lower()
            
            # Simple diversity check - avoid very similar case titles
            is_diverse = True
            for seen_title in seen_titles:
                similarity = self._calculate_title_similarity(case_title, seen_title)
                if similarity > self.default_config['diversity_threshold']:
                    is_diverse = False
                    break
            
            if is_diverse:
                diverse_results.append(result)
                seen_titles.add(case_title)
            
            # Limit diverse results
            if len(diverse_results) >= self.default_config['max_results']:
                break
        
        return diverse_results
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple title similarity"""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _final_precision_ranking(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Final ranking with intelligent relevance-based cutoff"""
        if not results:
            return results
            
        # Sort by precision score
        sorted_results = sorted(results, key=lambda x: x['precision_score'], reverse=True)
        
        # Apply intelligent cutoff if enabled
        if self.default_config.get('enable_intelligent_cutoff', True):
            final_results = self._apply_intelligent_cutoff(sorted_results)
        else:
            # Fallback to max results limit
            final_results = sorted_results[:self.default_config['max_results']]
        
        # Add final ranking metadata
        for i, result in enumerate(final_results):
            result['final_rank'] = i + 1
            result['precision_optimized'] = True
        
        return final_results
    
    def _apply_intelligent_cutoff(self, sorted_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply intelligent relevance-based cutoff to results - IMPROVED for partial matches"""
        if not sorted_results:
            return sorted_results
            
        try:
            # Get top score for relative comparison
            top_score = sorted_results[0].get('precision_score', 0)
            min_score = self.default_config['min_relevance_score']
            score_drop_threshold = self.default_config['score_drop_threshold']
            
            intelligent_results = []
            
            for result in sorted_results:
                current_score = result.get('precision_score', 0)
                
                # Apply absolute minimum score threshold
                if current_score < min_score:
                    break  # Stop at first result below minimum
                
                # IMPROVED: More lenient relative score drop threshold for cases with good combined scores
                if top_score > 0:
                    score_ratio = current_score / top_score
                    
                    # If the case has a good combined score (from vector/keyword search), be more lenient
                    combined_score = result.get('combined_score', 0)
                    if combined_score > 0.1:  # If it has a decent combined score
                        # Use a very lenient threshold for cases with good search scores
                        lenient_threshold = max(0.02, score_drop_threshold * 0.1)  # 90% more lenient (0.45 * 0.1 = 0.045)
                        if score_ratio < lenient_threshold:
                            break
                    else:
                        # Use normal threshold for cases without good search scores
                        if score_ratio < score_drop_threshold:
                            break
                
                intelligent_results.append(result)
                
                # Safety limit to prevent infinite results
                if len(intelligent_results) >= self.default_config['max_results']:
                    break
            
            # Ensure we have at least one result if any exist
            if not intelligent_results and sorted_results:
                intelligent_results = [sorted_results[0]]
            
            logger.info(f"Intelligent cutoff: {len(sorted_results)} -> {len(intelligent_results)} results (top_score: {top_score:.3f})")
            return intelligent_results
            
        except Exception as e:
            logger.error(f"Error in intelligent cutoff: {str(e)}")
            # Fallback to max results limit
            return sorted_results[:self.default_config['max_results']]
