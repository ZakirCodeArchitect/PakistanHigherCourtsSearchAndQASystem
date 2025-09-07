"""
Result Quality Engine
Advanced result quality assessment and optimization for perfect search results
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    RELEVANCE = "relevance"
    AUTHORITY = "authority"
    RECENCY = "recency"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    PRECEDENTIAL_VALUE = "precedential_value"


@dataclass
class QualityScore:
    """Comprehensive quality score for a search result"""
    overall_score: float
    dimension_scores: Dict[QualityDimension, float]
    quality_indicators: List[str]
    confidence: float
    explanation: str


class ResultQualityEngine:
    """Advanced engine for assessing and optimizing search result quality"""
    
    def __init__(self):
        self.quality_weights = self._load_quality_weights()
        self.authority_hierarchy = self._load_authority_hierarchy()
        self.quality_indicators = self._load_quality_indicators()
    
    def assess_result_quality(self, result: Dict[str, Any], query_analysis: Dict = None) -> QualityScore:
        """Assess comprehensive quality of a search result"""
        try:
            # Calculate individual dimension scores
            dimension_scores = {}
            
            # 1. Relevance Assessment
            dimension_scores[QualityDimension.RELEVANCE] = self._assess_relevance(result, query_analysis)
            
            # 2. Authority Assessment
            dimension_scores[QualityDimension.AUTHORITY] = self._assess_authority(result)
            
            # 3. Recency Assessment
            dimension_scores[QualityDimension.RECENCY] = self._assess_recency(result)
            
            # 4. Completeness Assessment
            dimension_scores[QualityDimension.COMPLETENESS] = self._assess_completeness(result)
            
            # 5. Clarity Assessment
            dimension_scores[QualityDimension.CLARITY] = self._assess_clarity(result)
            
            # 6. Precedential Value Assessment
            dimension_scores[QualityDimension.PRECEDENTIAL_VALUE] = self._assess_precedential_value(result)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(dimension_scores)
            
            # Generate quality indicators
            quality_indicators = self._generate_quality_indicators(result, dimension_scores)
            
            # Calculate confidence
            confidence = self._calculate_confidence(dimension_scores, result)
            
            # Generate explanation
            explanation = self._generate_explanation(dimension_scores, quality_indicators)
            
            return QualityScore(
                overall_score=overall_score,
                dimension_scores=dimension_scores,
                quality_indicators=quality_indicators,
                confidence=confidence,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error assessing result quality: {str(e)}")
            return self._fallback_quality_score()
    
    def optimize_results_by_quality(self, results: List[Dict], query_analysis: Dict = None, max_results: int = 50) -> List[Dict]:
        """Optimize results based on comprehensive quality assessment"""
        try:
            # Assess quality for all results
            quality_assessed_results = []
            
            for result in results:
                quality_score = self.assess_result_quality(result, query_analysis)
                result['quality_score'] = quality_score.overall_score
                result['quality_dimensions'] = {dim.value: score for dim, score in quality_score.dimension_scores.items()}
                result['quality_indicators'] = quality_score.quality_indicators
                result['quality_confidence'] = quality_score.confidence
                result['quality_explanation'] = quality_score.explanation
                
                quality_assessed_results.append(result)
            
            # Apply quality-based filtering
            filtered_results = self._apply_quality_filters(quality_assessed_results, query_analysis)
            
            # Sort by quality-adjusted score
            sorted_results = self._sort_by_quality(filtered_results)
            
            # Apply diversity to prevent over-clustering
            diverse_results = self._apply_quality_diversity(sorted_results, max_results)
            
            logger.info(f"Quality optimization: {len(results)} -> {len(diverse_results)} results")
            return diverse_results
            
        except Exception as e:
            logger.error(f"Error in quality optimization: {str(e)}")
            return results[:max_results]  # Fallback
    
    def _assess_relevance(self, result: Dict, query_analysis: Dict = None) -> float:
        """Assess relevance quality dimension"""
        score = 0.0
        
        # Base relevance from search scores
        if 'final_score' in result:
            score += min(result['final_score'] * 2, 0.4)  # Max 0.4 from search score
        
        # Title relevance
        case_title = result.get('case_title', '').lower()
        if query_analysis and 'query' in query_analysis:
            query_terms = query_analysis['query'].lower().split()
            title_matches = sum(1 for term in query_terms if term in case_title)
            if query_terms:
                score += (title_matches / len(query_terms)) * 0.3
        
        # Legal entity matching
        if query_analysis and 'legal_entities' in query_analysis:
            entities = query_analysis['legal_entities']
            case_content = f"{case_title} {result.get('case_number', '')}".lower()
            
            entity_matches = 0
            for entity in entities:
                if entity.get('normalized', '').lower() in case_content:
                    entity_matches += 1
            
            if entities:
                score += (entity_matches / len(entities)) * 0.2
        
        # Status relevance (decided cases often more relevant)
        status = result.get('status', '').lower()
        if 'decided' in status:
            score += 0.1
        elif 'pending' in status:
            score += 0.05
        
        return min(score, 1.0)
    
    def _assess_authority(self, result: Dict) -> float:
        """Assess authority quality dimension"""
        score = 0.0
        
        # Court hierarchy scoring
        court = result.get('court', '').lower()
        
        if 'supreme court' in court:
            score += 0.5
        elif 'high court' in court:
            score += 0.4
        elif 'district court' in court or 'sessions court' in court:
            score += 0.3
        else:
            score += 0.2
        
        # Case type authority
        case_number = result.get('case_number', '').lower()
        if any(term in case_number for term in ['appeal', 'revision']):
            score += 0.2  # Appellate decisions have higher authority
        elif 'writ' in case_number:
            score += 0.15  # Constitutional cases have good authority
        
        # Bench composition (if available)
        bench = result.get('bench', '').lower()
        if bench:
            # Multiple judges indicate higher authority
            judge_indicators = ['cj', 'chief justice', 'j.', 'justice']
            judge_count = sum(1 for indicator in judge_indicators if indicator in bench)
            score += min(judge_count * 0.05, 0.15)
        
        # Status authority
        status = result.get('status', '').lower()
        if 'decided' in status:
            score += 0.15  # Decided cases have precedential authority
        
        return min(score, 1.0)
    
    def _assess_recency(self, result: Dict) -> float:
        """Assess recency quality dimension"""
        score = 0.5  # Default score
        
        # Institution date recency
        institution_date = result.get('institution_date', '')
        if institution_date:
            try:
                # Extract year from various date formats
                import re
                year_match = re.search(r'\b(20\d{2})\b', institution_date)
                if year_match:
                    year = int(year_match.group())
                    current_year = datetime.now().year
                    
                    # Calculate recency score
                    age = current_year - year
                    if age <= 1:
                        score = 1.0
                    elif age <= 3:
                        score = 0.8
                    elif age <= 5:
                        score = 0.6
                    elif age <= 10:
                        score = 0.4
                    else:
                        score = 0.2
            except:
                pass
        
        # Hearing date recency
        hearing_date = result.get('hearing_date', '')
        if hearing_date and 'recent' in hearing_date.lower():
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_completeness(self, result: Dict) -> float:
        """Assess completeness quality dimension"""
        score = 0.0
        completeness_factors = 0
        
        # Essential fields
        essential_fields = ['case_title', 'case_number', 'court', 'status']
        for field in essential_fields:
            if result.get(field):
                score += 0.15
                completeness_factors += 1
        
        # Additional useful fields
        useful_fields = ['bench', 'institution_date', 'hearing_date']
        for field in useful_fields:
            if result.get(field):
                score += 0.1
        
        # Rich content indicators
        if result.get('snippets'):
            score += 0.15  # Has content snippets
        
        # Metadata richness
        if result.get('result_data'):
            score += 0.1
        
        # Quality indicators from content
        case_title = result.get('case_title', '')
        if len(case_title) > 20:  # Meaningful title length
            score += 0.05
        
        return min(score, 1.0)
    
    def _assess_clarity(self, result: Dict) -> float:
        """Assess clarity quality dimension"""
        score = 0.5  # Default score
        
        # Case title clarity
        case_title = result.get('case_title', '')
        if case_title:
            # Check for clear party names (VS pattern)
            if ' vs ' in case_title.lower() or ' v. ' in case_title.lower():
                score += 0.2
            
            # Check for reasonable length
            if 10 <= len(case_title) <= 200:
                score += 0.1
            
            # Check for non-garbled text
            if not any(char in case_title for char in ['�', '???', '***']):
                score += 0.1
        
        # Case number clarity
        case_number = result.get('case_number', '')
        if case_number:
            # Standard case number patterns
            import re
            if re.search(r'\b\w+\s*\d+/\d{4}\b', case_number):
                score += 0.15
        
        # Court name clarity
        court = result.get('court', '')
        if court and len(court) > 5:
            score += 0.05
        
        return min(score, 1.0)
    
    def _assess_precedential_value(self, result: Dict) -> float:
        """Assess precedential value quality dimension"""
        score = 0.0
        
        # Court level precedential value
        court = result.get('court', '').lower()
        if 'supreme court' in court:
            score += 0.4  # Highest precedential value
        elif 'high court' in court:
            score += 0.3
        elif 'district court' in court:
            score += 0.2
        
        # Case type precedential value
        case_number = result.get('case_number', '').lower()
        if 'appeal' in case_number:
            score += 0.2  # Appeals create precedents
        elif 'revision' in case_number:
            score += 0.15
        elif 'writ' in case_number:
            score += 0.25  # Constitutional precedents
        
        # Status precedential value
        status = result.get('status', '').lower()
        if 'decided' in status:
            score += 0.15  # Only decided cases create precedents
        
        # Bench strength
        bench = result.get('bench', '')
        if bench:
            # Larger benches create stronger precedents
            if 'full bench' in bench.lower() or 'larger bench' in bench.lower():
                score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_overall_score(self, dimension_scores: Dict[QualityDimension, float]) -> float:
        """Calculate weighted overall quality score"""
        total_score = 0.0
        total_weight = 0.0
        
        for dimension, score in dimension_scores.items():
            weight = self.quality_weights.get(dimension, 1.0)
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_quality_indicators(self, result: Dict, dimension_scores: Dict) -> List[str]:
        """Generate quality indicators for the result"""
        indicators = []
        
        # High quality indicators
        if dimension_scores.get(QualityDimension.AUTHORITY, 0) > 0.7:
            court = result.get('court', '')
            if 'supreme court' in court.lower():
                indicators.append("Supreme Court Authority")
            elif 'high court' in court.lower():
                indicators.append("High Court Authority")
        
        if dimension_scores.get(QualityDimension.RECENCY, 0) > 0.8:
            indicators.append("Recent Case")
        
        if dimension_scores.get(QualityDimension.COMPLETENESS, 0) > 0.8:
            indicators.append("Complete Information")
        
        if dimension_scores.get(QualityDimension.PRECEDENTIAL_VALUE, 0) > 0.7:
            indicators.append("High Precedential Value")
        
        # Content quality indicators
        if result.get('snippets'):
            indicators.append("Rich Content")
        
        if result.get('status', '').lower() == 'decided':
            indicators.append("Final Decision")
        
        # Special case types
        case_number = result.get('case_number', '').lower()
        if 'writ' in case_number:
            indicators.append("Constitutional Case")
        elif 'appeal' in case_number:
            indicators.append("Appellate Decision")
        
        return indicators
    
    def _calculate_confidence(self, dimension_scores: Dict, result: Dict) -> float:
        """Calculate confidence in quality assessment"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for complete results
        if result.get('case_title') and result.get('case_number') and result.get('court'):
            confidence += 0.2
        
        # Higher confidence for decided cases
        if result.get('status', '').lower() == 'decided':
            confidence += 0.1
        
        # Higher confidence for higher authority courts
        court = result.get('court', '').lower()
        if 'supreme court' in court:
            confidence += 0.15
        elif 'high court' in court:
            confidence += 0.1
        
        # Lower confidence for very low scores
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        if overall_score < 0.3:
            confidence -= 0.2
        
        return min(max(confidence, 0.0), 1.0)
    
    def _generate_explanation(self, dimension_scores: Dict, quality_indicators: List[str]) -> str:
        """Generate human-readable quality explanation"""
        overall_score = sum(dimension_scores.values()) / len(dimension_scores)
        
        if overall_score > 0.8:
            quality_level = "Excellent"
        elif overall_score > 0.6:
            quality_level = "Good"
        elif overall_score > 0.4:
            quality_level = "Fair"
        else:
            quality_level = "Limited"
        
        explanation = f"{quality_level} quality result"
        
        if quality_indicators:
            explanation += f" with {', '.join(quality_indicators[:3])}"
        
        # Add top dimension
        top_dimension = max(dimension_scores, key=dimension_scores.get)
        top_score = dimension_scores[top_dimension]
        
        if top_score > 0.7:
            explanation += f". Strong {top_dimension.value.replace('_', ' ')}"
        
        return explanation
    
    def _apply_quality_filters(self, results: List[Dict], query_analysis: Dict = None) -> List[Dict]:
        """Apply quality-based filtering"""
        filtered_results = []
        
        for result in results:
            quality_score = result.get('quality_score', 0)
            
            # Minimum quality threshold (lowered for better compatibility)
            if quality_score >= 0.1:
                filtered_results.append(result)
        
        return filtered_results
    
    def _sort_by_quality(self, results: List[Dict]) -> List[Dict]:
        """Sort results by quality-adjusted score"""
        def quality_sort_key(result):
            # Combine original relevance with quality assessment
            original_score = result.get('final_score', 0)
            quality_score = result.get('quality_score', 0)
            
            # Weighted combination
            combined_score = (original_score * 0.6) + (quality_score * 0.4)
            return combined_score
        
        return sorted(results, key=quality_sort_key, reverse=True)
    
    def _apply_quality_diversity(self, results: List[Dict], max_results: int) -> List[Dict]:
        """Apply diversity while maintaining quality"""
        if len(results) <= max_results:
            return results
        
        diverse_results = []
        court_counts = {}
        case_type_counts = {}
        
        for result in results:
            if len(diverse_results) >= max_results:
                break
            
            # Diversity factors
            court = result.get('court', 'unknown')
            case_number = result.get('case_number', '')
            case_type = 'appeal' if 'appeal' in case_number.lower() else 'other'
            
            # Check diversity constraints
            court_count = court_counts.get(court, 0)
            case_type_count = case_type_counts.get(case_type, 0)
            
            # Allow if diversity is maintained or quality is very high
            quality_score = result.get('quality_score', 0)
            
            if (court_count < max_results // 3 and case_type_count < max_results // 2) or quality_score > 0.8:
                diverse_results.append(result)
                court_counts[court] = court_count + 1
                case_type_counts[case_type] = case_type_count + 1
        
        return diverse_results
    
    def _load_quality_weights(self) -> Dict[QualityDimension, float]:
        """Load quality dimension weights"""
        return {
            QualityDimension.RELEVANCE: 2.5,
            QualityDimension.AUTHORITY: 2.0,
            QualityDimension.RECENCY: 1.0,
            QualityDimension.COMPLETENESS: 1.5,
            QualityDimension.CLARITY: 1.2,
            QualityDimension.PRECEDENTIAL_VALUE: 1.8
        }
    
    def _load_authority_hierarchy(self) -> Dict:
        """Load court authority hierarchy"""
        return {
            'supreme_court': 1.0,
            'high_court': 0.8,
            'district_court': 0.6,
            'sessions_court': 0.4,
            'magistrate_court': 0.2
        }
    
    def _load_quality_indicators(self) -> Dict:
        """Load quality indicator definitions"""
        return {
            'excellent': 0.8,
            'good': 0.6,
            'fair': 0.4,
            'poor': 0.2
        }
    
    def _fallback_quality_score(self) -> QualityScore:
        """Provide fallback quality score"""
        return QualityScore(
            overall_score=0.5,
            dimension_scores={dim: 0.5 for dim in QualityDimension},
            quality_indicators=[],
            confidence=0.3,
            explanation="Quality assessment unavailable"
        )
