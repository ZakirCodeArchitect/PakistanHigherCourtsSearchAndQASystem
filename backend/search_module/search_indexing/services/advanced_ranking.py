"""
Advanced Ranking Service
Implements sophisticated ranking logic with boosting, diversity control, and score fusion
"""

import logging
import math
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from django.utils import timezone
from django.db.models import Q, F
from apps.cases.models import Case, Term, TermOccurrence
from ..models import SearchMetadata

logger = logging.getLogger(__name__)


class AdvancedRankingService:
    """Advanced ranking service with sophisticated scoring algorithms"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Default ranking configuration
        self.default_config = {
            'semantic_weight': 0.6,
            'lexical_weight': 0.4,
            'exact_match_boost': 3.0,
            'citation_boost': 2.0,
            'legal_term_boost': 1.5,
            'filter_alignment_boost': 0.3,
            'recency_decay_factor': 0.1,
            'diversity_threshold': 0.7,
            'mmr_lambda': 0.5,
            'max_boost': 5.0,
            'score_normalization': 'z_score',  # 'z_score', 'min_max', 'percentile'
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
    
    def rank_results(self, 
                    vector_results: List[Dict], 
                    keyword_results: List[Dict],
                    query_info: Dict[str, Any],
                    filters: Dict[str, Any] = None,
                    top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Rank search results using advanced algorithms
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            query_info: Query normalization and boost information
            filters: Applied search filters
            top_k: Number of top results to return
        
        Returns:
            Ranked list of results with detailed scoring
        """
        try:
            logger.info(f"Starting advanced ranking for {len(vector_results)} vector + {len(keyword_results)} keyword results")
            
            # Step 1: Combine and deduplicate results
            combined_results = self._combine_results(vector_results, keyword_results)
            
            # Step 2: Calculate base scores
            scored_results = self._calculate_base_scores(combined_results, query_info)
            
            # Step 3: Apply boosting
            boosted_results = self._apply_boosting(scored_results, query_info, filters)
            
            # Step 4: Apply recency scoring
            recency_results = self._apply_recency_scoring(boosted_results)
            
            # Step 5: Apply diversity control
            diverse_results = self._apply_diversity_control(recency_results, top_k)
            
            # Step 6: Final score fusion and normalization
            final_results = self._final_score_fusion(diverse_results, top_k)
            
            # Step 7: Add ranking metadata
            ranked_results = self._add_ranking_metadata(final_results, query_info)
            
            logger.info(f"Advanced ranking completed. Top result score: {ranked_results[0]['final_score']:.4f}")
            return ranked_results
            
        except Exception as e:
            logger.error(f"Error in advanced ranking: {str(e)}")
            # Fallback to simple ranking
            return self._fallback_ranking(vector_results, keyword_results, top_k)
    
    def _combine_results(self, vector_results: List[Dict], keyword_results: List[Dict]) -> Dict[int, Dict]:
        """Combine and deduplicate results by case ID"""
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
        
        return combined
    
    def _calculate_base_scores(self, combined_results: Dict[int, Dict], query_info: Dict) -> List[Dict]:
        """Calculate base scores for each result"""
        scored_results = []
        
        for case_id, result in combined_results.items():
            # Normalize scores to 0-1 range
            vector_score = min(1.0, result['vector_score'])
            
            # Keyword score normalization (assuming max rank is around 10)
            keyword_score = min(1.0, result['keyword_score'] / 10.0) if result['keyword_score'] > 0 else 0
            
            scored_result = {
                'case_id': case_id,
                'vector_score': vector_score,
                'keyword_score': keyword_score,
                'base_score': 0,  # Will be calculated in fusion
                'result_data': result['result_data']
            }
            
            scored_results.append(scored_result)
        
        return scored_results
    
    def _apply_boosting(self, results: List[Dict], query_info: Dict, filters: Dict = None) -> List[Dict]:
        """Apply various boosting factors"""
        boosted_results = []
        
        for result in results:
            case_id = result['case_id']
            boost_factors = []
            total_boost = 0
            
            # 1. Exact match boost
            if query_info.get('exact_identifiers'):
                exact_boost = self._calculate_exact_match_boost(case_id, query_info['exact_identifiers'])
                boost_factors.append(('exact_match', exact_boost))
                total_boost += exact_boost
            
            # 2. Citation boost
            if query_info.get('citations'):
                citation_boost = self._calculate_citation_boost(case_id, query_info['citations'])
                boost_factors.append(('citation', citation_boost))
                total_boost += citation_boost
            
            # 3. Legal term boost
            legal_term_boost = self._calculate_legal_term_boost(case_id, query_info)
            if legal_term_boost > 0:
                boost_factors.append(('legal_term', legal_term_boost))
                total_boost += legal_term_boost
            
            # 4. Filter alignment boost
            if filters:
                filter_boost = self._calculate_filter_alignment_boost(case_id, filters)
                if filter_boost > 0:
                    boost_factors.append(('filter_alignment', filter_boost))
                    total_boost += filter_boost
            
            # Cap total boost
            total_boost = min(total_boost, self.default_config['max_boost'])
            
            boosted_result = result.copy()
            boosted_result['boost_factors'] = boost_factors
            boosted_result['total_boost'] = total_boost
            
            boosted_results.append(boosted_result)
        
        return boosted_results
    
    def _calculate_exact_match_boost(self, case_id: int, exact_identifiers: List[Dict]) -> float:
        """Calculate boost for exact case number/citation matches"""
        try:
            case = Case.objects.filter(id=case_id).first()
            if not case:
                return 0.0
            
            boost = 0.0
            
            for identifier in exact_identifiers:
                if identifier['type'] == 'case_number':
                    # Check for exact case number match
                    if case.case_number and identifier['value'].lower() in case.case_number.lower():
                        boost += self.default_config['exact_match_boost']
                        break
            
            return boost
            
        except Exception as e:
            logger.error(f"Error calculating exact match boost: {str(e)}")
            return 0.0
    
    def _calculate_citation_boost(self, case_id: int, citations: List[Dict]) -> float:
        """Calculate boost for legal citation matches"""
        try:
            boost = 0.0
            
            for citation in citations:
                canonical = citation['canonical']
                
                # Check if this case has the cited legal term
                term_occurrences = TermOccurrence.objects.filter(
                    case_id=case_id,
                    term__canonical=canonical
                )
                
                if term_occurrences.exists():
                    # Boost based on occurrence count
                    occurrence_count = term_occurrences.count()
                    citation_boost = min(
                        self.default_config['citation_boost'],
                        occurrence_count * 0.5
                    )
                    boost += citation_boost
            
            return boost
            
        except Exception as e:
            logger.error(f"Error calculating citation boost: {str(e)}")
            return 0.0
    
    def _calculate_legal_term_boost(self, case_id: int, query_info: Dict) -> float:
        """Calculate boost for general legal term matches"""
        try:
            boost = 0.0
            
            # Get canonical terms from query
            canonical_terms = query_info.get('canonical_terms', [])
            if not canonical_terms:
                return 0.0
            
            # Check for term occurrences
            for term_canonical in canonical_terms:
                term_occurrences = TermOccurrence.objects.filter(
                    case_id=case_id,
                    term__canonical__icontains=term_canonical
                )
                
                if term_occurrences.exists():
                    occurrence_count = term_occurrences.count()
                    term_boost = min(
                        self.default_config['legal_term_boost'],
                        occurrence_count * 0.3
                    )
                    boost += term_boost
            
            return boost
            
        except Exception as e:
            logger.error(f"Error calculating legal term boost: {str(e)}")
            return 0.0
    
    def _calculate_filter_alignment_boost(self, case_id: int, filters: Dict) -> float:
        """Calculate boost for filter alignment"""
        try:
            boost = 0.0
            alignment_count = 0
            
            case = Case.objects.filter(id=case_id).first()
            if not case:
                return 0.0
            
            # Check court filter
            if 'court' in filters and case.court:
                if str(case.court.id) == str(filters['court']) or case.court.name.lower() == filters['court'].lower():
                    alignment_count += 1
            
            # Check status filter
            if 'status' in filters and case.status:
                if case.status.lower() == filters['status'].lower():
                    alignment_count += 1
            
            # Check year filter
            if 'year' in filters and case.institution_date:
                try:
                    case_year = datetime.strptime(case.institution_date, '%d-%m-%Y').year
                    if case_year == int(filters['year']):
                        alignment_count += 1
                except:
                    pass
            
            # Calculate boost based on alignment count
            if alignment_count > 0:
                boost = alignment_count * self.default_config['filter_alignment_boost']
            
            return boost
            
        except Exception as e:
            logger.error(f"Error calculating filter alignment boost: {str(e)}")
            return 0.0
    
    def _apply_recency_scoring(self, results: List[Dict]) -> List[Dict]:
        """Apply recency scoring with exponential decay"""
        try:
            recency_results = []
            
            for result in results:
                case_id = result['case_id']
                recency_score = 0.0
                
                # Get case dates
                case = Case.objects.filter(id=case_id).first()
                if case and case.institution_date:
                    try:
                        case_date = datetime.strptime(case.institution_date, '%d-%m-%Y').date()
                        days_old = (date.today() - case_date).days
                        
                        # Exponential decay: newer cases get higher scores
                        if days_old > 0:
                            decay_factor = self.default_config['recency_decay_factor']
                            recency_score = math.exp(-decay_factor * days_old / 365.0)  # Normalize to years
                        else:
                            recency_score = 1.0  # Future dates get max score
                            
                    except Exception as e:
                        logger.warning(f"Error parsing date for case {case_id}: {str(e)}")
                        recency_score = 0.5  # Default score for parsing errors
                
                recency_result = result.copy()
                recency_result['recency_score'] = recency_score
                recency_results.append(recency_result)
            
            return recency_results
            
        except Exception as e:
            logger.error(f"Error applying recency scoring: {str(e)}")
            return results
    
    def _apply_diversity_control(self, results: List[Dict], top_k: int) -> List[Dict]:
        """Apply diversity control using Maximal Marginal Relevance (MMR)"""
        try:
            if len(results) <= top_k:
                return results
            
            # Sort by base score for initial ranking
            sorted_results = sorted(results, key=lambda x: x['vector_score'] + x['keyword_score'], reverse=True)
            
            # MMR selection
            selected = [sorted_results[0]]  # Start with highest scoring result
            remaining = sorted_results[1:]
            
            lambda_param = self.default_config['mmr_lambda']
            
            while len(selected) < top_k and remaining:
                mmr_scores = []
                
                for candidate in remaining:
                    # Relevance score
                    relevance = candidate['vector_score'] + candidate['keyword_score']
                    
                    # Diversity score (average similarity to already selected)
                    diversity = 0.0
                    if selected:
                        similarities = []
                        for selected_result in selected:
                            similarity = self._calculate_case_similarity(
                                candidate['case_id'], 
                                selected_result['case_id']
                            )
                            similarities.append(similarity)
                        diversity = 1.0 - (sum(similarities) / len(similarities))
                    
                    # MMR score
                    mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                    mmr_scores.append((candidate, mmr_score))
                
                # Select candidate with highest MMR score
                best_candidate, _ = max(mmr_scores, key=lambda x: x[1])
                selected.append(best_candidate)
                remaining.remove(best_candidate)
            
            return selected
            
        except Exception as e:
            logger.error(f"Error applying diversity control: {str(e)}")
            return results[:top_k]
    
    def _calculate_case_similarity(self, case_id_1: int, case_id_2: int) -> float:
        """Calculate similarity between two cases (simplified)"""
        try:
            # Simple similarity based on court and status
            case1 = Case.objects.filter(id=case_id_1).first()
            case2 = Case.objects.filter(id=case_id_2).first()
            
            if not case1 or not case2:
                return 0.0
            
            similarity = 0.0
            
            # Court similarity
            if case1.court and case2.court:
                if case1.court.id == case2.court.id:
                    similarity += 0.5
            
            # Status similarity
            if case1.status and case2.status:
                if case1.status.lower() == case2.status.lower():
                    similarity += 0.3
            
            # Year similarity
            if case1.institution_date and case2.institution_date:
                try:
                    year1 = datetime.strptime(case1.institution_date, '%d-%m-%Y').year
                    year2 = datetime.strptime(case2.institution_date, '%d-%m-%Y').year
                    year_diff = abs(year1 - year2)
                    if year_diff <= 1:
                        similarity += 0.2
                    elif year_diff <= 5:
                        similarity += 0.1
                except:
                    pass
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error calculating case similarity: {str(e)}")
            return 0.0
    
    def _final_score_fusion(self, results: List[Dict], top_k: int) -> List[Dict]:
        """Final score fusion and normalization"""
        try:
            fused_results = []
            
            for result in results:
                # Calculate base hybrid score
                semantic_weight = self.default_config['semantic_weight']
                lexical_weight = self.default_config['lexical_weight']
                
                base_score = (
                    result['vector_score'] * semantic_weight +
                    result['keyword_score'] * lexical_weight
                )
                
                # Add boosts
                boosted_score = base_score + result.get('total_boost', 0)
                
                # Add recency
                final_score = boosted_score + (result.get('recency_score', 0) * 0.1)
                
                fused_result = result.copy()
                fused_result['base_score'] = base_score
                fused_result['boosted_score'] = boosted_score
                fused_result['final_score'] = final_score
                
                fused_results.append(fused_result)
            
            # Sort by final score
            fused_results.sort(key=lambda x: x['final_score'], reverse=True)
            
            return fused_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in final score fusion: {str(e)}")
            return results[:top_k]
    
    def _add_ranking_metadata(self, results: List[Dict], query_info: Dict) -> List[Dict]:
        """Add ranking metadata and explanations"""
        try:
            for i, result in enumerate(results):
                result['rank'] = i + 1
                result['search_type'] = 'hybrid'
                
                # Add explanation vector for debug mode
                result['explanation'] = {
                    'vector_score': result['vector_score'],
                    'keyword_score': result['keyword_score'],
                    'base_score': result['base_score'],
                    'boosts_applied': result.get('boost_factors', []),
                    'total_boost': result.get('total_boost', 0),
                    'recency_score': result.get('recency_score', 0),
                    'final_score': result['final_score']
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error adding ranking metadata: {str(e)}")
            return results
    
    def _fallback_ranking(self, vector_results: List[Dict], keyword_results: List[Dict], top_k: int) -> List[Dict]:
        """Fallback ranking when advanced ranking fails"""
        try:
            # Simple combination and ranking
            combined = {}
            
            # Process vector results
            for result in vector_results:
                case_id = result.get('case_id')
                if case_id:
                    combined[case_id] = {
                        'case_id': case_id,
                        'score': result.get('similarity', 0),
                        'search_type': 'vector',
                        'result_data': result
                    }
            
            # Process keyword results
            for result in keyword_results:
                case_id = result.get('case_id')
                if case_id:
                    if case_id in combined:
                        # Take the better score
                        combined[case_id]['score'] = max(
                            combined[case_id]['score'],
                            result.get('rank', 0) / 10.0
                        )
                        combined[case_id]['search_type'] = 'hybrid'
                    else:
                        combined[case_id] = {
                            'case_id': case_id,
                            'score': result.get('rank', 0) / 10.0,
                            'search_type': 'keyword',
                            'result_data': result
                        }
            
            # Sort and return top results
            sorted_results = sorted(combined.values(), key=lambda x: x['score'], reverse=True)
            
            for i, result in enumerate(sorted_results[:top_k]):
                result['rank'] = i + 1
                result['final_score'] = result['score']
            
            return sorted_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in fallback ranking: {str(e)}")
            return []
