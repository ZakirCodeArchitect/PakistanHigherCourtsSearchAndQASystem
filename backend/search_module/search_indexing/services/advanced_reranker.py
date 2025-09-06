"""
Advanced Result Re-ranking System
Multi-stage re-ranking with legal domain expertise and learning mechanisms
"""

import logging
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg
from apps.cases.models import Case

logger = logging.getLogger(__name__)


class AdvancedReranker:
    """Advanced multi-stage result re-ranking system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Re-ranking configuration
        self.default_config = {
            'citation_boost': 3.0,
            'exact_match_boost': 2.5,
            'legal_term_boost': 1.8,
            'recency_weight': 0.15,
            'court_hierarchy_weight': 1.5,
            'case_importance_weight': 1.3,
            'semantic_threshold': 0.3,
            'diversity_penalty': 0.1,
            'quality_threshold': 0.2,
            'max_rerank_results': 50,
            'learning_rate': 0.1
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
        
        # Court hierarchy scoring
        self.court_hierarchy = {
            'supreme court': 1.0,
            'high court': 0.8,
            'district court': 0.6,
            'sessions court': 0.4,
            'magistrate': 0.3,
            'tribunal': 0.5
        }
        
        # Legal importance indicators
        self.importance_indicators = {
            'constitutional': 2.0,
            'landmark': 1.8,
            'precedent': 1.6,
            'leading case': 1.5,
            'binding': 1.4,
            'authoritative': 1.3
        }
    
    def rerank_results(self, 
                      search_results: List[Dict[str, Any]], 
                      query: str,
                      query_analysis: Dict[str, Any] = None,
                      user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Advanced multi-stage re-ranking of search results
        
        Args:
            search_results: Initial search results
            query: Original search query
            query_analysis: Query analysis from expansion service
            user_context: User context for personalization
            
        Returns:
            Re-ranked search results
        """
        try:
            logger.info(f"Starting advanced re-ranking for {len(search_results)} results")
            
            if not search_results:
                return []
            
            # Stage 1: Quality filtering
            quality_filtered = self._filter_by_quality(search_results)
            
            # Stage 2: Legal relevance scoring
            relevance_scored = self._score_legal_relevance(quality_filtered, query, query_analysis)
            
            # Stage 3: Authority and importance scoring
            authority_scored = self._score_authority_importance(relevance_scored)
            
            # Stage 4: Recency and temporal relevance
            temporal_scored = self._apply_temporal_scoring(authority_scored)
            
            # Stage 5: Diversity optimization
            diversity_optimized = self._optimize_diversity(temporal_scored, query)
            
            # Stage 6: Final fusion and normalization
            final_ranked = self._final_score_fusion(diversity_optimized)
            
            # Stage 7: Learning-based adjustments (if user context available)
            if user_context:
                final_ranked = self._apply_learning_adjustments(final_ranked, query, user_context)
            
            # Limit results and add ranking metadata
            limited_results = final_ranked[:self.default_config['max_rerank_results']]
            
            for i, result in enumerate(limited_results):
                result['rerank_position'] = i + 1
                result['reranking_applied'] = True
                result['rerank_confidence'] = self._calculate_confidence(result)
            
            logger.info(f"Advanced re-ranking completed: {len(limited_results)} results")
            return limited_results
            
        except Exception as e:
            logger.error(f"Error in advanced re-ranking: {str(e)}")
            return search_results  # Fallback to original results
    
    def _filter_by_quality(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results by quality thresholds"""
        quality_results = []
        quality_threshold = self.default_config['quality_threshold']
        
        for result in results:
            # Quality indicators
            quality_score = 0.0
            
            # Basic data completeness
            case_data = result.get('result_data', result)
            if case_data.get('case_title'):
                quality_score += 0.3
            if case_data.get('case_number'):
                quality_score += 0.3
            if case_data.get('court'):
                quality_score += 0.2
            if case_data.get('status'):
                quality_score += 0.1
            if case_data.get('institution_date'):
                quality_score += 0.1
            
            # Content quality
            title_length = len(case_data.get('case_title', ''))
            if title_length > 10:  # Reasonable title length
                quality_score += 0.1
            
            if quality_score >= quality_threshold:
                result['quality_score'] = quality_score
                quality_results.append(result)
        
        logger.info(f"Quality filtering: {len(results)} -> {len(quality_results)} results")
        return quality_results
    
    def _score_legal_relevance(self, 
                              results: List[Dict[str, Any]], 
                              query: str,
                              query_analysis: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Score results based on legal relevance"""
        query_lower = query.lower()
        
        for result in results:
            relevance_score = result.get('similarity', result.get('rank', 0.5))
            case_data = result.get('result_data', result)
            
            # Citation matching boost
            if self._has_citation_match(query, case_data):
                relevance_score *= self.default_config['citation_boost']
            
            # Exact term matching
            exact_matches = self._count_exact_matches(query_lower, case_data)
            if exact_matches > 0:
                boost = 1.0 + (exact_matches * 0.2)
                relevance_score *= min(boost, self.default_config['exact_match_boost'])
            
            # Legal term relevance
            legal_term_score = self._calculate_legal_term_relevance(query, case_data)
            relevance_score *= (1.0 + legal_term_score * self.default_config['legal_term_boost'])
            
            # Query type specific boosting
            if query_analysis:
                type_boost = self._get_query_type_boost(query_analysis, case_data)
                relevance_score *= type_boost
            
            result['legal_relevance_score'] = relevance_score
        
        return results
    
    def _score_authority_importance(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score results based on legal authority and case importance"""
        for result in results:
            case_data = result.get('result_data', result)
            authority_score = 1.0
            
            # Court hierarchy scoring
            court_name = case_data.get('court', '').lower()
            for court_type, score in self.court_hierarchy.items():
                if court_type in court_name:
                    authority_score *= (1.0 + score * self.default_config['court_hierarchy_weight'])
                    break
            
            # Case importance indicators
            case_title = case_data.get('case_title', '').lower()
            case_text = f"{case_title} {case_data.get('case_number', '')}".lower()
            
            for indicator, boost in self.importance_indicators.items():
                if indicator in case_text:
                    authority_score *= (1.0 + boost * self.default_config['case_importance_weight'])
            
            # Judicial precedent indicators
            precedent_indicators = ['leading case', 'landmark', 'binding precedent', 'authoritative']
            for indicator in precedent_indicators:
                if indicator in case_text:
                    authority_score *= 1.2
            
            result['authority_score'] = authority_score
        
        return results
    
    def _apply_temporal_scoring(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply temporal relevance scoring"""
        current_date = timezone.now().date()
        
        for result in results:
            case_data = result.get('result_data', result)
            temporal_score = 1.0
            
            # Recency scoring
            institution_date = case_data.get('institution_date')
            if institution_date:
                try:
                    if isinstance(institution_date, str):
                        case_date = datetime.strptime(institution_date[:10], '%Y-%m-%d').date()
                    else:
                        case_date = institution_date
                    
                    days_old = (current_date - case_date).days
                    
                    # Recency boost (more recent cases get slight preference)
                    if days_old < 365:  # Less than 1 year
                        temporal_score *= (1.0 + self.default_config['recency_weight'])
                    elif days_old < 1825:  # Less than 5 years
                        temporal_score *= (1.0 + self.default_config['recency_weight'] * 0.5)
                    
                except (ValueError, TypeError):
                    pass  # Skip temporal scoring for invalid dates
            
            result['temporal_score'] = temporal_score
        
        return results
    
    def _optimize_diversity(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Optimize result diversity to avoid redundancy"""
        if len(results) <= 10:
            return results  # Skip diversity optimization for small result sets
        
        diverse_results = []
        seen_titles = set()
        seen_parties = set()
        
        # Sort by current scores first
        sorted_results = sorted(results, 
                              key=lambda x: x.get('legal_relevance_score', 0) * 
                                          x.get('authority_score', 1) * 
                                          x.get('temporal_score', 1), 
                              reverse=True)
        
        for result in sorted_results:
            case_data = result.get('result_data', result)
            case_title = case_data.get('case_title', '').lower()
            
            # Check title similarity
            is_diverse = True
            for seen_title in seen_titles:
                similarity = self._calculate_title_similarity(case_title, seen_title)
                if similarity > 0.8:  # High similarity threshold
                    is_diverse = False
                    # Apply diversity penalty
                    result['diversity_penalty'] = self.default_config['diversity_penalty']
                    break
            
            if is_diverse or len(diverse_results) < 5:  # Always include top 5
                diverse_results.append(result)
                seen_titles.add(case_title)
                result['diversity_penalty'] = 0.0
            else:
                diverse_results.append(result)  # Include with penalty
        
        return diverse_results
    
    def _final_score_fusion(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fuse all scores into final ranking score"""
        for result in results:
            # Get component scores
            relevance = result.get('legal_relevance_score', 0.5)
            authority = result.get('authority_score', 1.0)
            temporal = result.get('temporal_score', 1.0)
            quality = result.get('quality_score', 0.5)
            diversity_penalty = result.get('diversity_penalty', 0.0)
            
            # Weighted fusion
            final_score = (
                relevance * authority * temporal * quality * (1.0 - diversity_penalty)
            )
            
            result['final_rerank_score'] = final_score
            
            # Store component scores for analysis
            result['score_components'] = {
                'relevance': relevance,
                'authority': authority,
                'temporal': temporal,
                'quality': quality,
                'diversity_penalty': diversity_penalty
            }
        
        # Sort by final score
        sorted_results = sorted(results, key=lambda x: x['final_rerank_score'], reverse=True)
        return sorted_results
    
    def _apply_learning_adjustments(self, 
                                   results: List[Dict[str, Any]], 
                                   query: str,
                                   user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply learning-based adjustments based on user behavior"""
        # This is a placeholder for future machine learning integration
        # Could include:
        # - Click-through rate adjustments
        # - User preference learning
        # - Query pattern recognition
        # - Collaborative filtering
        
        learning_rate = self.default_config['learning_rate']
        
        for result in results:
            # Example: boost results similar to previously clicked items
            if 'preferred_courts' in user_context:
                case_data = result.get('result_data', result)
                court = case_data.get('court', '').lower()
                
                for preferred_court in user_context['preferred_courts']:
                    if preferred_court.lower() in court:
                        adjustment = 1.0 + learning_rate
                        result['final_rerank_score'] *= adjustment
                        break
        
        return results
    
    def _has_citation_match(self, query: str, case_data: Dict[str, Any]) -> bool:
        """Check for citation matches"""
        import re
        
        citation_patterns = [
            r'\b\d{4}\s*[A-Z]+\s*\d+\b',
            r'\b[A-Z]+\s*\d{4}\s*\d+\b',
            r'\b\d+\s*of\s*\d{4}\b'
        ]
        
        query_citations = []
        case_citations = []
        
        case_text = f"{case_data.get('case_number', '')} {case_data.get('case_title', '')}"
        
        for pattern in citation_patterns:
            query_citations.extend(re.findall(pattern, query, re.IGNORECASE))
            case_citations.extend(re.findall(pattern, case_text, re.IGNORECASE))
        
        return bool(set(query_citations).intersection(set(case_citations)))
    
    def _count_exact_matches(self, query: str, case_data: Dict[str, Any]) -> int:
        """Count exact word matches between query and case data"""
        query_words = set(query.lower().split())
        case_text = f"{case_data.get('case_title', '')} {case_data.get('case_number', '')}".lower()
        case_words = set(case_text.split())
        
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'of', 'in', 'at', 'to', 'for', 'vs', 'versus'}
        query_words -= stop_words
        case_words -= stop_words
        
        return len(query_words.intersection(case_words))
    
    def _calculate_legal_term_relevance(self, query: str, case_data: Dict[str, Any]) -> float:
        """Calculate legal term relevance score"""
        legal_terms = [
            'appeal', 'petition', 'bail', 'writ', 'civil', 'criminal',
            'constitutional', 'contract', 'property', 'family',
            'commercial', 'tax', 'court', 'judge', 'justice'
        ]
        
        query_lower = query.lower()
        case_text = f"{case_data.get('case_title', '')} {case_data.get('case_number', '')}".lower()
        
        relevance_score = 0.0
        for term in legal_terms:
            if term in query_lower and term in case_text:
                relevance_score += 0.1
        
        return min(1.0, relevance_score)
    
    def _get_query_type_boost(self, query_analysis: Dict[str, Any], case_data: Dict[str, Any]) -> float:
        """Get boost based on query type analysis"""
        query_type = query_analysis.get('type', 'general')
        boost = 1.0
        
        case_text = f"{case_data.get('case_title', '')} {case_data.get('case_number', '')}".lower()
        
        if query_type == 'citation':
            # Boost cases with citation patterns
            import re
            if re.search(r'\b\d{4}\s*[A-Z]+\s*\d+\b', case_text):
                boost = 1.3
        elif query_type == 'case_parties':
            # Boost cases with party names
            if ' vs ' in case_text or ' v ' in case_text:
                boost = 1.2
        elif query_type == 'legal_concept':
            # Boost based on legal concepts
            legal_concepts = query_analysis.get('legal_concepts', [])
            for concept in legal_concepts:
                if concept in case_text:
                    boost *= 1.1
        
        return boost
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between case titles"""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for the ranking"""
        score_components = result.get('score_components', {})
        
        # High confidence if multiple strong signals
        confidence = 0.5  # Base confidence
        
        if score_components.get('relevance', 0) > 1.5:
            confidence += 0.2
        if score_components.get('authority', 1) > 1.2:
            confidence += 0.15
        if score_components.get('quality', 0) > 0.7:
            confidence += 0.15
        
        return min(1.0, confidence)
