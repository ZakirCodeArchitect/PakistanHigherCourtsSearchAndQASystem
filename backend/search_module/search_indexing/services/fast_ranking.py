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
            
            logger.info(f"Fast ranking completed. Top result score: {final_results[0]['final_score']:.4f}")
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
            
            # Keyword score normalization (assuming max rank is around 10)
            keyword_score = min(1.0, result['keyword_score'] / 10.0) if result['keyword_score'] > 0 else 0
            
            # Calculate weighted base score
            vector_weight = self.default_config['vector_weight']
            keyword_weight = self.default_config['keyword_weight']
            base_score = (vector_score * vector_weight) + (keyword_score * keyword_weight)
            
            # Apply simple boosting based on query (no database queries)
            total_boost = self._calculate_simple_boost(result, query)
            
            # Calculate final score
            final_score = base_score * (1 + total_boost)
            
            # Only include results with meaningful scores
            if final_score > 0.05 or vector_score > 0.1 or keyword_score > 0.1:
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
        """Calculate boost without database queries"""
        total_boost = 0
        
        # Check if case number contains query terms (fast string operation)
        case_number = result['result_data'].get('case_number', '').upper()
        query_upper = query.upper()
        
        if query_upper in case_number:
            total_boost += self.default_config['exact_match_boost']
        
        # Check if case title contains query terms (fast string operation)
        case_title = result['result_data'].get('case_title', '').upper()
        if query_upper in case_title:
            total_boost += 0.5  # Smaller boost for title match
        
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
