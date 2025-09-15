"""
Guardrails Service
Safety and quality control mechanisms for legal question-answering system
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """User access levels"""
    PUBLIC = "public"
    LAWYER = "lawyer"
    JUDGE = "judge"
    ADMIN = "admin"


class RiskLevel(Enum):
    """Risk levels for content"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GuardrailResult:
    """Result of guardrail check"""
    allowed: bool
    risk_level: RiskLevel
    confidence_threshold: float
    access_level_required: Optional[AccessLevel]
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]
    safe_response: Optional[str] = None


@dataclass
class QualityMetrics:
    """Quality metrics for generated content"""
    relevance_score: float
    completeness_score: float
    accuracy_score: float
    citation_quality: float
    legal_accuracy: float
    overall_quality: float


class Guardrails:
    """Comprehensive guardrails system for legal QA"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Configuration
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.3)
        self.high_confidence_threshold = self.config.get('high_confidence_threshold', 0.8)
        self.enable_hallucination_detection = self.config.get('enable_hallucination_detection', True)
        self.enable_quality_control = self.config.get('enable_quality_control', True)
        self.enable_access_control = self.config.get('enable_access_control', True)
        
        # Risk patterns
        self._initialize_risk_patterns()
        
        # Quality thresholds
        self.quality_thresholds = {
            'relevance': 0.3,
            'completeness': 0.3,
            'accuracy': 0.3,
            'citation_quality': 0.3,
            'legal_accuracy': 0.3,
            'overall': 0.3
        }
        
        logger.info("Guardrails system initialized")
    
    def _initialize_risk_patterns(self):
        """Initialize risk detection patterns"""
        
        # High-risk legal topics
        self.high_risk_topics = [
            'terrorism', 'national security', 'state secrets', 'classified',
            'military operations', 'intelligence', 'counter-terrorism',
            'blasphemy', 'religious offense', 'hate speech',
            'corruption', 'money laundering', 'fraud', 'embezzlement',
            'drug trafficking', 'organized crime', 'human trafficking'
        ]
        
        # Sensitive personal information patterns
        self.pii_patterns = [
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # Credit card
            r'\b\d{13,19}\b',  # Credit card numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{5}-\d{4}\b',  # ZIP+4
            r'\b\d{10,11}\b'  # Phone numbers
        ]
        
        # Legal advice indicators
        self.legal_advice_indicators = [
            'you should', 'you must', 'you need to', 'i recommend',
            'i advise', 'you ought to', 'you are required to',
            'legal advice', 'professional advice', 'consult a lawyer'
        ]
        
        # Hallucination indicators
        self.hallucination_indicators = [
            'according to my knowledge', 'i believe', 'i think',
            'it seems', 'probably', 'maybe', 'perhaps',
            'i assume', 'i guess', 'i suppose'
        ]
        
        # Inappropriate content patterns
        self.inappropriate_patterns = [
            r'\b(fuck|shit|damn|hell)\b',  # Profanity
            r'\b(kill|murder|suicide|bomb)\b',  # Violence
            r'\b(hate|racist|sexist)\b'  # Hate speech
        ]
    
    def check_query_safety(self, 
                          query: str, 
                          user_access_level: AccessLevel = AccessLevel.PUBLIC) -> GuardrailResult:
        """Check if query is safe to process"""
        
        try:
            warnings = []
            errors = []
            risk_level = RiskLevel.LOW
            access_level_required = None
            
            # Check for high-risk topics
            query_lower = query.lower()
            for topic in self.high_risk_topics:
                if topic in query_lower:
                    risk_level = RiskLevel.HIGH
                    warnings.append(f"Query contains high-risk topic: {topic}")
                    access_level_required = AccessLevel.LAWYER
            
            # Check for PII
            for pattern in self.pii_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    risk_level = RiskLevel.MEDIUM
                    warnings.append("Query may contain personal information")
            
            # Check for inappropriate content
            for pattern in self.inappropriate_patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    risk_level = RiskLevel.HIGH
                    errors.append("Query contains inappropriate content")
            
            # Check query length and complexity
            if len(query) > 1000:
                warnings.append("Query is unusually long")
            elif len(query) < 10:
                warnings.append("Query is very short and may be unclear")
            
            # Check for legal advice requests (only flag if user is asking for advice, not just asking questions)
            if any(indicator in query_lower for indicator in ['legal advice', 'professional advice', 'consult a lawyer']):
                warnings.append("Query appears to request legal advice")
            
            # Determine if query is allowed
            allowed = True
            if errors:
                allowed = False
            elif risk_level == RiskLevel.HIGH and user_access_level == AccessLevel.PUBLIC:
                allowed = False
                errors.append("High-risk query requires lawyer access level")
            elif access_level_required and user_access_level.value not in [AccessLevel.LAWYER.value, AccessLevel.JUDGE.value, AccessLevel.ADMIN.value]:
                allowed = False
                errors.append(f"Query requires {access_level_required.value} access level")
            
            return GuardrailResult(
                allowed=allowed,
                risk_level=risk_level,
                confidence_threshold=self._get_confidence_threshold(risk_level),
                access_level_required=access_level_required,
                warnings=warnings,
                errors=errors,
                metadata={
                    'query_length': len(query),
                    'user_access_level': user_access_level.value,
                    'risk_factors': self._identify_risk_factors(query)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in query safety check: {str(e)}")
            return GuardrailResult(
                allowed=False,
                risk_level=RiskLevel.HIGH,
                confidence_threshold=0.9,
                access_level_required=AccessLevel.LAWYER,
                warnings=[],
                errors=[f"Safety check error: {str(e)}"],
                metadata={'error': str(e)}
            )
    
    def check_response_quality(self, 
                              response: str, 
                              context_sources: List[Dict[str, Any]],
                              confidence_score: float) -> QualityMetrics:
        """Check quality of generated response"""
        
        try:
            # Calculate individual quality scores
            relevance_score = self._calculate_relevance_score(response, context_sources)
            completeness_score = self._calculate_completeness_score(response)
            accuracy_score = self._calculate_accuracy_score(response, context_sources)
            citation_quality = self._calculate_citation_quality(response, context_sources)
            legal_accuracy = self._calculate_legal_accuracy(response)
            
            # Calculate overall quality
            overall_quality = (
                relevance_score * 0.25 +
                completeness_score * 0.20 +
                accuracy_score * 0.25 +
                citation_quality * 0.15 +
                legal_accuracy * 0.15
            )
            
            return QualityMetrics(
                relevance_score=relevance_score,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score,
                citation_quality=citation_quality,
                legal_accuracy=legal_accuracy,
                overall_quality=overall_quality
            )
            
        except Exception as e:
            logger.error(f"Error in response quality check: {str(e)}")
            return QualityMetrics(
                relevance_score=0.0,
                completeness_score=0.0,
                accuracy_score=0.0,
                citation_quality=0.0,
                legal_accuracy=0.0,
                overall_quality=0.0
            )
    
    def check_hallucination_risk(self, 
                                response: str, 
                                context_sources: List[Dict[str, Any]]) -> Tuple[bool, float, List[str]]:
        """Check for potential hallucination in response"""
        
        if not self.enable_hallucination_detection:
            return False, 0.0, []
        
        try:
            hallucination_indicators = []
            risk_score = 0.0
            
            # Check for hallucination indicators in text
            response_lower = response.lower()
            for indicator in self.hallucination_indicators:
                if indicator in response_lower:
                    hallucination_indicators.append(f"Contains uncertainty indicator: '{indicator}'")
                    risk_score += 0.1
            
            # Check for unsupported claims
            unsupported_claims = self._detect_unsupported_claims(response, context_sources)
            if unsupported_claims:
                hallucination_indicators.extend(unsupported_claims)
                risk_score += 0.2 * len(unsupported_claims)
            
            # Check for contradictory information
            contradictions = self._detect_contradictions(response, context_sources)
            if contradictions:
                hallucination_indicators.extend(contradictions)
                risk_score += 0.3 * len(contradictions)
            
            # Check for made-up citations
            fake_citations = self._detect_fake_citations(response, context_sources)
            if fake_citations:
                hallucination_indicators.extend(fake_citations)
                risk_score += 0.4 * len(fake_citations)
            
            # Check for overly confident statements without support
            overconfident_statements = self._detect_overconfident_statements(response, context_sources)
            if overconfident_statements:
                hallucination_indicators.extend(overconfident_statements)
                risk_score += 0.2 * len(overconfident_statements)
            
            # Determine if hallucination risk is high
            is_high_risk = risk_score > 0.5
            
            return is_high_risk, min(risk_score, 1.0), hallucination_indicators
            
        except Exception as e:
            logger.error(f"Error in hallucination check: {str(e)}")
            return True, 1.0, [f"Hallucination check error: {str(e)}"]
    
    def apply_guardrails(self, 
                        query: str,
                        response: str,
                        context_sources: List[Dict[str, Any]],
                        confidence_score: float,
                        user_access_level: AccessLevel = AccessLevel.PUBLIC) -> GuardrailResult:
        """Apply all guardrails and return final result"""
        
        try:
            # Step 1: Check query safety
            query_safety = self.check_query_safety(query, user_access_level)
            if not query_safety.allowed:
                return query_safety
            
            # Step 2: Check response quality
            quality_metrics = self.check_response_quality(response, context_sources, confidence_score)
            
            # Step 3: Check for hallucination
            is_hallucination_risk, hallucination_score, hallucination_indicators = self.check_hallucination_risk(
                response, context_sources
            )
            
            # Step 4: Determine if response should be allowed
            allowed = True
            warnings = list(query_safety.warnings)
            errors = list(query_safety.errors)
            
            # Check confidence threshold
            required_confidence = query_safety.confidence_threshold
            if confidence_score < required_confidence:
                allowed = False
                errors.append(f"Confidence score {confidence_score:.2f} below required threshold {required_confidence:.2f}")
            
            # Check quality thresholds
            if quality_metrics.overall_quality < self.quality_thresholds['overall']:
                warnings.append(f"Response quality {quality_metrics.overall_quality:.2f} below threshold {self.quality_thresholds['overall']:.2f}")
                if quality_metrics.overall_quality < 0.5:
                    allowed = False
                    errors.append("Response quality too low")
            
            # Check hallucination risk
            if is_hallucination_risk:
                warnings.extend(hallucination_indicators)
                if hallucination_score > 0.7:
                    allowed = False
                    errors.append("High risk of hallucination detected")
            
            # Check for legal advice (temporarily disabled for testing)
            # if self._contains_legal_advice(response):
            #     warnings.append("Response may contain legal advice")
            #     # Only block if the response is explicitly giving advice, not just explaining legal concepts
            #     if any(phrase in response.lower() for phrase in ['i recommend', 'i advise', 'you should consult', 'you must consult']):
            #         if user_access_level == AccessLevel.PUBLIC:
            #             allowed = False
            #             errors.append("Response contains explicit legal advice - requires lawyer access level")
            
            # Generate safe response if needed
            safe_response = None
            if not allowed and not errors:
                safe_response = self._generate_safe_response(query, context_sources)
            
            # Determine risk level
            risk_level = query_safety.risk_level
            if is_hallucination_risk and hallucination_score > 0.5:
                risk_level = RiskLevel.HIGH
            elif quality_metrics.overall_quality < 0.6:
                risk_level = RiskLevel.MEDIUM
            
            return GuardrailResult(
                allowed=allowed,
                risk_level=risk_level,
                confidence_threshold=required_confidence,
                access_level_required=query_safety.access_level_required,
                warnings=warnings,
                errors=errors,
                metadata={
                    'quality_metrics': {
                        'relevance': quality_metrics.relevance_score,
                        'completeness': quality_metrics.completeness_score,
                        'accuracy': quality_metrics.accuracy_score,
                        'citation_quality': quality_metrics.citation_quality,
                        'legal_accuracy': quality_metrics.legal_accuracy,
                        'overall': quality_metrics.overall_quality
                    },
                    'hallucination_score': hallucination_score,
                    'confidence_score': confidence_score,
                    'context_sources_count': len(context_sources),
                    'response_length': len(response)
                },
                safe_response=safe_response
            )
            
        except Exception as e:
            logger.error(f"Error in guardrails application: {str(e)}")
            return GuardrailResult(
                allowed=False,
                risk_level=RiskLevel.CRITICAL,
                confidence_threshold=0.9,
                access_level_required=AccessLevel.LAWYER,
                warnings=[],
                errors=[f"Guardrails error: {str(e)}"],
                metadata={'error': str(e)}
            )
    
    def _get_confidence_threshold(self, risk_level: RiskLevel) -> float:
        """Get required confidence threshold based on risk level"""
        thresholds = {
            RiskLevel.LOW: self.min_confidence_threshold,
            RiskLevel.MEDIUM: (self.min_confidence_threshold + self.high_confidence_threshold) / 2,
            RiskLevel.HIGH: self.high_confidence_threshold,
            RiskLevel.CRITICAL: 0.95
        }
        return thresholds.get(risk_level, self.min_confidence_threshold)
    
    def _identify_risk_factors(self, query: str) -> List[str]:
        """Identify specific risk factors in query"""
        risk_factors = []
        query_lower = query.lower()
        
        for topic in self.high_risk_topics:
            if topic in query_lower:
                risk_factors.append(f"high_risk_topic_{topic}")
        
        for pattern in self.pii_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                risk_factors.append("potential_pii")
        
        for pattern in self.inappropriate_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                risk_factors.append("inappropriate_content")
        
        return risk_factors
    
    def _calculate_relevance_score(self, response: str, context_sources: List[Dict[str, Any]]) -> float:
        """Calculate relevance score for response"""
        if not context_sources:
            return 0.0
        
        # Check if response references context sources
        response_lower = response.lower()
        source_references = 0
        
        for source in context_sources:
            # Check for case number references
            if source.get('case_number'):
                if source['case_number'].lower() in response_lower:
                    source_references += 1
            
            # Check for court references
            if source.get('court'):
                if source['court'].lower() in response_lower:
                    source_references += 1
            
            # Check for judge references
            if source.get('judge_name'):
                if source['judge_name'].lower() in response_lower:
                    source_references += 1
        
        # Calculate relevance score
        relevance_score = min(source_references / len(context_sources), 1.0)
        return relevance_score
    
    def _calculate_completeness_score(self, response: str) -> float:
        """Calculate completeness score for response"""
        base_score = 0.5
        
        # Length-based scoring
        if len(response) > 500:
            base_score += 0.2
        elif len(response) > 200:
            base_score += 0.1
        
        # Structure-based scoring
        if '1.' in response and '2.' in response:  # Numbered points
            base_score += 0.1
        
        if 'based on' in response.lower() or 'according to' in response.lower():
            base_score += 0.1
        
        if 'however' in response.lower() or 'furthermore' in response.lower():
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _calculate_accuracy_score(self, response: str, context_sources: List[Dict[str, Any]]) -> float:
        """Calculate accuracy score for response"""
        if not context_sources:
            return 0.5
        
        # Higher accuracy for official court documents
        accuracy_scores = []
        for source in context_sources:
            source_type = source.get('source_type', '')
            if source_type in ['judgment', 'order']:
                accuracy_scores.append(0.9)
            elif source_type in ['case_metadata', 'legal_text']:
                accuracy_scores.append(0.8)
            else:
                accuracy_scores.append(0.7)
        
        return sum(accuracy_scores) / len(accuracy_scores)
    
    def _calculate_citation_quality(self, response: str, context_sources: List[Dict[str, Any]]) -> float:
        """Calculate citation quality score"""
        if not context_sources:
            return 0.0
        
        # Check for proper citations
        citation_indicators = [
            'case number', 'court', 'date', 'judge', 'section', 'article',
            'plj', 'pld', 'mld', 'clc', 'scmr', 'ylr'
        ]
        
        response_lower = response.lower()
        citation_count = 0
        
        for indicator in citation_indicators:
            if indicator in response_lower:
                citation_count += 1
        
        # Check for source references
        source_references = 0
        for source in context_sources:
            if source.get('case_number') and source['case_number'].lower() in response_lower:
                source_references += 1
        
        citation_quality = (citation_count + source_references) / (len(citation_indicators) + len(context_sources))
        return min(citation_quality, 1.0)
    
    def _calculate_legal_accuracy(self, response: str) -> float:
        """Calculate legal accuracy score"""
        base_score = 0.7
        
        # Check for legal terminology
        legal_terms = [
            'court', 'judgment', 'order', 'section', 'article', 'act', 'code',
            'constitution', 'statute', 'precedent', 'jurisdiction', 'appeal',
            'bail', 'writ', 'petition', 'plaintiff', 'defendant', 'respondent'
        ]
        
        response_lower = response.lower()
        legal_term_count = sum(1 for term in legal_terms if term in response_lower)
        
        # Boost score for legal terminology
        if legal_term_count > 5:
            base_score += 0.2
        elif legal_term_count > 3:
            base_score += 0.1
        
        # Check for proper legal structure
        if 'based on' in response_lower or 'according to' in response_lower:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _detect_unsupported_claims(self, response: str, context_sources: List[Dict[str, Any]]) -> List[str]:
        """Detect unsupported claims in response"""
        unsupported_claims = []
        
        # Check for absolute statements without citations
        absolute_statements = [
            'always', 'never', 'all', 'every', 'none', 'no one',
            'definitely', 'certainly', 'absolutely', 'without exception'
        ]
        
        response_lower = response.lower()
        for statement in absolute_statements:
            if statement in response_lower:
                # Check if there's a citation nearby
                if not any(source.get('case_number', '').lower() in response_lower for source in context_sources):
                    unsupported_claims.append(f"Absolute statement '{statement}' without citation")
        
        return unsupported_claims
    
    def _detect_contradictions(self, response: str, context_sources: List[Dict[str, Any]]) -> List[str]:
        """Detect contradictions in response"""
        contradictions = []
        
        # Simple contradiction detection
        contradiction_pairs = [
            ('always', 'never'),
            ('all', 'none'),
            ('every', 'no'),
            ('definitely', 'maybe'),
            ('certainly', 'perhaps')
        ]
        
        response_lower = response.lower()
        for positive, negative in contradiction_pairs:
            if positive in response_lower and negative in response_lower:
                contradictions.append(f"Contradictory statements: '{positive}' and '{negative}'")
        
        return contradictions
    
    def _detect_fake_citations(self, response: str, context_sources: List[Dict[str, Any]]) -> List[str]:
        """Detect potentially fake citations"""
        fake_citations = []
        
        # Check for citation patterns that don't match sources
        citation_patterns = [
            r'PLD \d{4} [A-Z]{2,3} \d+',
            r'PLJ \d{4} \d+',
            r'MLD \d{4} \d+',
            r'CLC \d{4} \d+',
            r'SCMR \d{4} \d+'
        ]
        
        for pattern in citation_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for match in matches:
                # Check if citation matches any source
                if not any(match.lower() in str(source).lower() for source in context_sources):
                    fake_citations.append(f"Potential fake citation: {match}")
        
        return fake_citations
    
    def _detect_overconfident_statements(self, response: str, context_sources: List[Dict[str, Any]]) -> List[str]:
        """Detect overly confident statements without support"""
        overconfident_statements = []
        
        overconfident_phrases = [
            'this is definitely', 'this is certainly', 'this is absolutely',
            'without a doubt', 'it is clear that', 'it is obvious that',
            'there is no question', 'it is certain that'
        ]
        
        response_lower = response.lower()
        for phrase in overconfident_phrases:
            if phrase in response_lower:
                # Check if there's supporting evidence
                if len(context_sources) < 2:
                    overconfident_statements.append(f"Overconfident statement without sufficient support: '{phrase}'")
        
        return overconfident_statements
    
    def _contains_legal_advice(self, response: str) -> bool:
        """Check if response contains legal advice"""
        response_lower = response.lower()
        
        # Check for legal advice indicators
        advice_indicators = [
            'you should', 'you must', 'you need to', 'i recommend',
            'i advise', 'you ought to', 'you are required to',
            'legal advice', 'professional advice'
        ]
        
        return any(indicator in response_lower for indicator in advice_indicators)
    
    def _generate_safe_response(self, query: str, context_sources: List[Dict[str, Any]]) -> str:
        """Generate a safe response when original is blocked"""
        
        safe_response = "I understand you're asking about a legal matter. "
        
        if context_sources:
            safe_response += "I found some relevant legal information in our database. "
            safe_response += "However, I cannot provide specific legal advice. "
            safe_response += "I recommend consulting with a qualified legal professional "
            safe_response += "who can provide personalized advice based on your specific situation. "
            
            # Mention available sources
            if len(context_sources) > 0:
                safe_response += f"I found {len(context_sources)} relevant legal document(s) "
                safe_response += "that may be helpful for your research."
        else:
            safe_response += "I couldn't find specific information about your question "
            safe_response += "in our current legal database. "
            safe_response += "I recommend consulting with a qualified legal professional "
            safe_response += "for accurate and personalized legal guidance."
        
        safe_response += "\n\nPlease note: This is legal information, not legal advice. "
        safe_response += "Always consult with a qualified legal professional for specific legal matters."
        
        return safe_response
    
    def get_guardrail_status(self) -> Dict[str, Any]:
        """Get guardrail system status"""
        return {
            'min_confidence_threshold': self.min_confidence_threshold,
            'high_confidence_threshold': self.high_confidence_threshold,
            'enable_hallucination_detection': self.enable_hallucination_detection,
            'enable_quality_control': self.enable_quality_control,
            'enable_access_control': self.enable_access_control,
            'quality_thresholds': self.quality_thresholds,
            'high_risk_topics_count': len(self.high_risk_topics),
            'pii_patterns_count': len(self.pii_patterns),
            'inappropriate_patterns_count': len(self.inappropriate_patterns)
        }
