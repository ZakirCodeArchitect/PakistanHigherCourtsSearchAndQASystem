"""
Fast Ranking Service
Simplified ranking for high-performance search
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FastRankingService:
    """Fast ranking service optimized for performance"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Simple, fast configuration
        self.default_config = {
            'vector_weight': 0.6,
            'keyword_weight': 0.4,
            'exact_match_boost': 2.0,
            'max_boost': 3.0,
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
    
    def rank_results(self, 
                    vector_results: List[Dict], 
                    keyword_results: List[Dict],
                    query: str,
                    exact_case_match: Dict[str, Any] = None,
                    filters: Dict[str, Any] = None,
                    top_k: int = None) -> List[Dict[str, Any]]:
        """
        Fast ranking without complex database queries
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            query_info: Query information
            filters: Applied search filters
            top_k: Number of top results to return
        
        Returns:
            Ranked list of results
        """
        try:
            logger.info(f"Starting fast ranking for {len(vector_results)} vector + {len(keyword_results)} keyword results")
            
            # Step 1: Combine results by case ID (fast in-memory operation)
            combined_results = self._combine_results_fast(vector_results, keyword_results)
            
            # Step 2: Calculate simple scores (no database queries)
            scored_results = self._calculate_simple_scores(combined_results, query)
            
            # Step 3: Sort by final score
            ranked_results = sorted(scored_results, key=lambda x: x['final_score'], reverse=True)
            
            # Step 4: Limit to top results (use provided top_k or reasonable default)
            limit = top_k if top_k is not None else 10
            final_results = ranked_results[:limit]
            
            # Step 5: Add ranking metadata
            for i, result in enumerate(final_results):
                result['rank'] = i + 1
                result['ranking_method'] = 'fast_ranking'
            
            if final_results:
                logger.info(f"Fast ranking completed. Top result score: {final_results[0]['final_score']:.4f}")
            else:
                logger.warning("Fast ranking completed with no results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in fast ranking: {str(e)}")
            # Fallback to simple ranking
            limit = top_k if top_k is not None else 10
            return self._fallback_ranking(vector_results, keyword_results, limit)
    
    def _combine_results_fast(self, vector_results: List[Dict], keyword_results: List[Dict]) -> Dict[int, Dict]:
        """Combine results by case ID - fast in-memory operation"""
        combined = {}
        
        # Process vector results
        for result in vector_results:
            case_id = result.get('case_id')
            if case_id:
                if case_id not in combined:
                    combined[case_id] = {
                        'case_id': case_id,
                        'vector_score': result.get('similarity', 0),
                        'keyword_score': 0,
                        'result_data': result
                    }
                else:
                    # Take the best vector score
                    combined[case_id]['vector_score'] = max(
                        combined[case_id]['vector_score'],
                        result.get('similarity', 0)
                    )
                    # Merge result_data to preserve all fields, especially dates
                    combined[case_id]['result_data'].update(result)
                    # Ensure date fields are preserved
                    if result.get('institution_date'):
                        combined[case_id]['result_data']['institution_date'] = result['institution_date']
                    if result.get('hearing_date'):
                        combined[case_id]['result_data']['hearing_date'] = result['hearing_date']
        
        # Process keyword results
        for result in keyword_results:
            case_id = result.get('case_id')
            if case_id:
                if case_id not in combined:
                    combined[case_id] = {
                        'case_id': case_id,
                        'vector_score': 0,
                        'keyword_score': result.get('rank', 0),
                        'result_data': result
                    }
                else:
                    # Take the best keyword score
                    combined[case_id]['keyword_score'] = max(
                        combined[case_id]['keyword_score'],
                        result.get('rank', 0)
                    )
                    # Merge result_data to preserve all fields, especially dates
                    combined[case_id]['result_data'].update(result)
                    # Ensure date fields are preserved
                    if result.get('institution_date'):
                        combined[case_id]['result_data']['institution_date'] = result['institution_date']
                    if result.get('hearing_date'):
                        combined[case_id]['result_data']['hearing_date'] = result['hearing_date']
        
        return combined
    
    def _calculate_simple_scores(self, combined_results: Dict[int, Dict], query: str) -> List[Dict]:
        """Calculate simple scores without database queries"""
        scored_results = []
        
        for case_id, result in combined_results.items():
            # Normalize scores to 0-1 range
            vector_score = min(1.0, result['vector_score'])
            
            # Keyword score normalization (PostgreSQL ranks are typically 0.001-1.0)
            # Use logarithmic scaling for very small ranks
            if result['keyword_score'] > 0:
                if result['keyword_score'] < 0.01:  # Very small ranks (1e-20, etc.)
                    keyword_score = min(1.0, result['keyword_score'] * 100)  # Scale up small ranks
                else:
                    keyword_score = min(1.0, result['keyword_score'])  # Use ranks as-is for larger values
            else:
                # FIXED: Handle zero-rank results from PostgreSQL full-text search
                # If we have a keyword result with rank 0, it means PostgreSQL found a match
                # but couldn't calculate a meaningful rank. Give it a minimal score.
                keyword_score = 0.01 if result['keyword_score'] == 0 and 'keyword_score' in result else 0
            
            # Calculate weighted base score
            vector_weight = self.default_config['vector_weight']
            keyword_weight = self.default_config['keyword_weight']
            
            # IMPROVED: For semantic search mode, if keyword_score is very low (0.01), 
            # treat it as pure semantic search and use vector_score as the primary score
            if keyword_score <= 0.01 and vector_score > 0:
                # Pure semantic search - use vector score as primary with minimal keyword contribution
                base_score = vector_score * 0.9 + keyword_score * 0.1
            else:
                # Hybrid search - use normal weighting
                base_score = (vector_score * vector_weight) + (keyword_score * keyword_weight)
            
            # Apply simple boosting based on query (no database queries)
            total_boost = self._calculate_simple_boost(result, query)
            
            # Calculate final score
            final_score = base_score * (1 + total_boost)
            
            # Only include results with meaningful scores (adjusted for lexical search)
            # FIXED: Be more inclusive for lexical search results with zero ranks
            if (final_score > 0.01 or vector_score > 0.05 or keyword_score > 0.01 or 
                (result['keyword_score'] == 0 and 'keyword_score' in result)):  # Include zero-rank keyword results
                scored_result = {
                    'case_id': case_id,
                    'vector_score': vector_score,
                    'keyword_score': keyword_score,
                    'base_score': base_score,
                    'total_boost': total_boost,
                    'final_score': final_score,
                    'result_data': result['result_data']
                }
                
                scored_results.append(scored_result)
        
        return scored_results
    
    def _calculate_simple_boost(self, result: Dict, query: str) -> float:
        """Calculate boost without database queries - IMPROVED for partial matches"""
        total_boost = 0
        
        # Check if case number contains query terms (fast string operation)
        case_number = result['result_data'].get('case_number', '').upper()
        query_upper = query.upper()
        
        if query_upper in case_number:
            total_boost += self.default_config['exact_match_boost']
        
        # IMPROVED: Check if case title contains query terms with better scoring
        case_title = result['result_data'].get('case_title', '').upper()
        if case_title and query_upper:
            # Split query into individual terms for partial matching
            query_terms = [term.strip() for term in query_upper.split() if len(term.strip()) > 2]
            
            # Count how many query terms appear in the title
            matching_terms = 0
            for term in query_terms:
                if term in case_title:
                    matching_terms += 1
            
            # Calculate boost based on term matches
            if matching_terms > 0:
                # Base boost for any title match
                title_boost = 1.0
                
                # Additional boost for multiple term matches
                if matching_terms > 1:
                    title_boost += (matching_terms - 1) * 0.5
                
                # Extra boost for exact phrase match
                if query_upper in case_title:
                    title_boost += 1.5
                
                # Boost for query terms at the beginning of title (more important)
                if case_title.startswith(query_upper):
                    title_boost += 1.0
                
                total_boost += title_boost
        
        # Cap total boost
        total_boost = min(total_boost, self.default_config['max_boost'])
        
        return total_boost
    
    def _fallback_ranking(self, vector_results: List[Dict], keyword_results: List[Dict], top_k: int) -> List[Dict]:
        """Simple fallback ranking"""
        try:
            # Just combine and sort by existing scores
            all_results = []
            
            for result in vector_results:
                case_id = result.get('case_id')
                if case_id is not None:  # Only add if case_id exists
                    all_results.append({
                        'case_id': int(case_id) if isinstance(case_id, float) else case_id,
                        'final_score': result.get('similarity', 0),
                        'vector_score': result.get('similarity', 0),
                        'keyword_score': 0,
                        'result_data': result,
                        'rank': len(all_results) + 1,
                        'ranking_method': 'fallback'
                    })
            
            for result in keyword_results:
                case_id = result.get('case_id')
                if case_id is not None:  # Only add if case_id exists
                    all_results.append({
                        'case_id': int(case_id) if isinstance(case_id, float) else case_id,
                        'final_score': result.get('rank', 0),
                        'vector_score': 0,
                        'keyword_score': result.get('rank', 0),
                        'result_data': result,
                        'rank': len(all_results) + 1,
                        'ranking_method': 'fallback'
                    })
            
            # Sort by final score and return top_k
            ranked_results = sorted(all_results, key=lambda x: x['final_score'], reverse=True)
            return ranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in fallback ranking: {str(e)}")
            return []
