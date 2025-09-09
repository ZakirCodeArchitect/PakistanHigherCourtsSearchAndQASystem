"""
Query Processor Service
Processes and normalizes user queries for better understanding and retrieval
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Service for processing and normalizing user queries"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Legal terminology patterns
        self._setup_legal_patterns()
        
        # Query classification rules
        self._setup_classification_rules()
        
        logger.info("Query Processor initialized successfully")
    
    def _setup_legal_patterns(self):
        """Setup legal terminology patterns for query processing"""
        self.legal_patterns = {
            # Legal citations
            'citations': [
                r'PLD\s+\d{4}\s+[A-Z]+\s+\d+',
                r'MLD\s+\d{4}\s+[A-Z]+\s+\d+',
                r'CLC\s+\d{4}\s+[A-Z]+\s+\d+',
                r'SCMR\s+\d{4}\s+[A-Z]+\s+\d+',
                r'YLR\s+\d{4}\s+[A-Z]+\s+\d+',
                r'\d{4}\s+[A-Z]+\s+\d+',
            ],
            
            # Legal sections
            'sections': [
                r'section\s+\d+[a-z]?',
                r's\.\s*\d+[a-z]?',
                r'PPC\s+\d+[a-z]?',
                r'CrPC\s+\d+[a-z]?',
                r'CPC\s+\d+[a-z]?',
                r'QSO\s+\d+[a-z]?',
            ],
            
            # Case numbers
            'case_numbers': [
                r'[A-Z]+\.?\s*No\.?\s*\d+/\d{4}',
                r'[A-Z]+\.?\s*\d+/\d{4}',
                r'Case\s+No\.?\s*\d+',
                r'Petition\s+No\.?\s*\d+',
            ],
            
            # Court names
            'courts': [
                r'Islamabad\s+High\s+Court',
                r'Lahore\s+High\s+Court',
                r'Sindh\s+High\s+Court',
                r'Balochistan\s+High\s+Court',
                r'Peshawar\s+High\s+Court',
                r'Supreme\s+Court',
                r'Federal\s+Shariat\s+Court',
                r'IHC',
                r'LHC',
                r'SHC',
                r'BHC',
                r'PHC',
                r'SC',
                r'FSC',
            ],
            
            # Legal terms
            'legal_terms': [
                r'writ\s+petition',
                r'civil\s+petition',
                r'criminal\s+petition',
                r'constitutional\s+petition',
                r'habeas\s+corpus',
                r'mandamus',
                r'certiorari',
                r'prohibition',
                r'quash',
                r'bail',
                r'anticipatory\s+bail',
                r'post\s+arrest\s+bail',
                r'pre\s+arrest\s+bail',
            ]
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
            'ppc': 'Pakistan Penal Code',
            'crpc': 'Code of Criminal Procedure',
            'cpc': 'Code of Civil Procedure',
            'qso': 'Qanun-e-Shahadat Order',
        }
    
    def _setup_classification_rules(self):
        """Setup query classification rules"""
        self.classification_rules = {
            'case_inquiry': [
                'case', 'judgment', 'order', 'decision', 'ruling', 'verdict',
                'what happened in', 'details of', 'outcome of', 'result of'
            ],
            'law_research': [
                'law', 'statute', 'section', 'act', 'provision', 'legal principle',
                'what is the law', 'legal requirement', 'statutory provision'
            ],
            'judge_inquiry': [
                'judge', 'justice', 'bench', 'who decided', 'which judge',
                'judicial opinion', 'judge\'s view', 'bench composition'
            ],
            'lawyer_inquiry': [
                'lawyer', 'advocate', 'counsel', 'attorney', 'legal representative',
                'who represented', 'counsel for', 'advocate for'
            ],
            'court_procedure': [
                'procedure', 'process', 'how to', 'steps', 'requirements',
                'filing', 'application', 'petition', 'appeal process'
            ],
            'citation_lookup': [
                'cite', 'citation', 'reference', 'PLD', 'MLD', 'CLC', 'SCMR', 'YLR',
                'case law', 'precedent', 'authority'
            ]
        }
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process and normalize a user query
        
        Args:
            query: Raw user query
            context: Additional context information
            
        Returns:
            Dictionary containing processed query and metadata
        """
        try:
            # Clean and normalize query
            cleaned_query = self._clean_query(query)
            
            # Extract legal entities
            entities = self._extract_legal_entities(cleaned_query)
            
            # Classify query intent
            intent = self._classify_query_intent(cleaned_query, entities)
            
            # Expand query with synonyms and related terms
            expanded_query = self._expand_query(cleaned_query, intent)
            
            # Calculate confidence
            confidence = self._calculate_confidence(cleaned_query, entities, intent)
            
            # Generate search terms
            search_terms = self._generate_search_terms(expanded_query, entities)
            
            return {
                'original_query': query,
                'processed_text': expanded_query,
                'cleaned_query': cleaned_query,
                'entities': entities,
                'intent': intent,
                'confidence': confidence,
                'search_terms': search_terms,
                'query_type': intent['type'],
                'legal_domain': intent.get('legal_domain', 'general'),
                'complexity': self._assess_complexity(cleaned_query, entities),
                'context': context or {}
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'original_query': query,
                'processed_text': query,
                'cleaned_query': query,
                'entities': {},
                'intent': {'type': 'general_legal', 'confidence': 0.5},
                'confidence': 0.3,
                'search_terms': query.split(),
                'query_type': 'general_legal',
                'legal_domain': 'general',
                'complexity': 'medium',
                'context': context or {}
            }
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query"""
        try:
            # Convert to lowercase
            cleaned = query.lower().strip()
            
            # Remove extra whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # Remove special characters except legal citations
            cleaned = re.sub(r'[^\w\s\.\-\/]', ' ', cleaned)
            
            # Normalize legal abbreviations
            for abbrev, full_form in self.legal_abbreviations.items():
                pattern = r'\b' + re.escape(abbrev) + r'\b'
                cleaned = re.sub(pattern, full_form, cleaned, flags=re.IGNORECASE)
            
            # Fix common misspellings
            misspellings = {
                'judgement': 'judgment',
                'judgements': 'judgments',
                'defence': 'defense',
                'offence': 'offense',
                'licence': 'license',
                'practice': 'practice',
                'practise': 'practice'
            }
            
            for misspelling, correction in misspellings.items():
                pattern = r'\b' + re.escape(misspelling) + r'\b'
                cleaned = re.sub(pattern, correction, cleaned, flags=re.IGNORECASE)
            
            return cleaned.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning query: {e}")
            return query
    
    def _extract_legal_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract legal entities from the query"""
        try:
            entities = {
                'citations': [],
                'sections': [],
                'case_numbers': [],
                'courts': [],
                'legal_terms': [],
                'dates': [],
                'names': []
            }
            
            # Extract citations
            for pattern in self.legal_patterns['citations']:
                matches = re.findall(pattern, query, re.IGNORECASE)
                entities['citations'].extend(matches)
            
            # Extract sections
            for pattern in self.legal_patterns['sections']:
                matches = re.findall(pattern, query, re.IGNORECASE)
                entities['sections'].extend(matches)
            
            # Extract case numbers
            for pattern in self.legal_patterns['case_numbers']:
                matches = re.findall(pattern, query, re.IGNORECASE)
                entities['case_numbers'].extend(matches)
            
            # Extract court names
            for pattern in self.legal_patterns['courts']:
                matches = re.findall(pattern, query, re.IGNORECASE)
                entities['courts'].extend(matches)
            
            # Extract legal terms
            for pattern in self.legal_patterns['legal_terms']:
                matches = re.findall(pattern, query, re.IGNORECASE)
                entities['legal_terms'].extend(matches)
            
            # Extract dates
            date_patterns = [
                r'\d{4}',
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{1,2}-\d{1,2}-\d{4}',
                r'\d{1,2}\s+\w+\s+\d{4}'
            ]
            for pattern in date_patterns:
                matches = re.findall(pattern, query)
                entities['dates'].extend(matches)
            
            # Extract potential names (simple heuristic)
            name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
            matches = re.findall(name_pattern, query)
            entities['names'].extend(matches)
            
            # Remove duplicates
            for key in entities:
                entities[key] = list(set(entities[key]))
            
            return entities
            
        except Exception as e:
            logger.error(f"Error extracting legal entities: {e}")
            return {}
    
    def _classify_query_intent(self, query: str, entities: Dict[str, List[str]]) -> Dict[str, Any]:
        """Classify the intent of the query"""
        try:
            intent_scores = {}
            
            # Score each intent type
            for intent_type, keywords in self.classification_rules.items():
                score = 0
                for keyword in keywords:
                    if keyword in query:
                        score += 1
                
                # Boost score for relevant entities
                if intent_type == 'case_inquiry' and entities.get('case_numbers'):
                    score += 2
                elif intent_type == 'citation_lookup' and entities.get('citations'):
                    score += 3
                elif intent_type == 'law_research' and entities.get('sections'):
                    score += 2
                elif intent_type == 'judge_inquiry' and entities.get('names'):
                    score += 1
                
                intent_scores[intent_type] = score
            
            # Determine primary intent
            if intent_scores:
                primary_intent = max(intent_scores, key=intent_scores.get)
                confidence = min(intent_scores[primary_intent] / 5.0, 1.0)
            else:
                primary_intent = 'general_legal'
                confidence = 0.5
            
            # Determine legal domain
            legal_domain = self._determine_legal_domain(query, entities)
            
            return {
                'type': primary_intent,
                'confidence': confidence,
                'scores': intent_scores,
                'legal_domain': legal_domain,
                'entities_used': len([e for e in entities.values() if e])
            }
            
        except Exception as e:
            logger.error(f"Error classifying query intent: {e}")
            return {
                'type': 'general_legal',
                'confidence': 0.5,
                'scores': {},
                'legal_domain': 'general',
                'entities_used': 0
            }
    
    def _determine_legal_domain(self, query: str, entities: Dict[str, List[str]]) -> str:
        """Determine the legal domain of the query"""
        try:
            domain_indicators = {
                'criminal': ['criminal', 'crime', 'offence', 'offense', 'bail', 'arrest', 'police', 'fir'],
                'civil': ['civil', 'contract', 'property', 'damages', 'injunction', 'suit'],
                'constitutional': ['constitutional', 'fundamental rights', 'writ', 'mandamus', 'certiorari'],
                'family': ['family', 'marriage', 'divorce', 'custody', 'maintenance'],
                'commercial': ['commercial', 'business', 'company', 'corporate', 'trade'],
                'tax': ['tax', 'revenue', 'customs', 'excise', 'duty']
            }
            
            query_lower = query.lower()
            domain_scores = {}
            
            for domain, indicators in domain_indicators.items():
                score = sum(1 for indicator in indicators if indicator in query_lower)
                domain_scores[domain] = score
            
            if domain_scores and max(domain_scores.values()) > 0:
                return max(domain_scores, key=domain_scores.get)
            else:
                return 'general'
                
        except Exception as e:
            logger.error(f"Error determining legal domain: {e}")
            return 'general'
    
    def _expand_query(self, query: str, intent: Dict[str, Any]) -> str:
        """Expand query with synonyms and related terms"""
        try:
            expanded_terms = []
            query_words = query.split()
            
            # Legal synonyms
            legal_synonyms = {
                'case': ['matter', 'suit', 'proceeding', 'litigation'],
                'judgment': ['decision', 'ruling', 'order', 'verdict'],
                'law': ['statute', 'act', 'provision', 'regulation'],
                'court': ['tribunal', 'bench', 'forum'],
                'judge': ['justice', 'magistrate', 'adjudicator'],
                'lawyer': ['advocate', 'counsel', 'attorney'],
                'petition': ['application', 'plea', 'request'],
                'appeal': ['revision', 'review', 'challenge']
            }
            
            for word in query_words:
                expanded_terms.append(word)
                
                # Add synonyms
                if word in legal_synonyms:
                    expanded_terms.extend(legal_synonyms[word][:2])  # Limit to 2 synonyms
            
            # Add intent-specific terms
            intent_type = intent.get('type', 'general_legal')
            if intent_type == 'case_inquiry':
                expanded_terms.extend(['case details', 'judgment', 'outcome'])
            elif intent_type == 'law_research':
                expanded_terms.extend(['legal principle', 'statutory provision'])
            elif intent_type == 'citation_lookup':
                expanded_terms.extend(['case law', 'precedent', 'authority'])
            
            # Remove duplicates while preserving order
            seen = set()
            unique_terms = []
            for term in expanded_terms:
                if term not in seen:
                    seen.add(term)
                    unique_terms.append(term)
            
            return ' '.join(unique_terms)
            
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return query
    
    def _calculate_confidence(self, query: str, entities: Dict[str, List[str]], intent: Dict[str, Any]) -> float:
        """Calculate confidence in query understanding"""
        try:
            base_confidence = 0.5
            
            # Boost for legal entities
            entity_count = sum(len(entity_list) for entity_list in entities.values())
            if entity_count > 0:
                base_confidence += min(entity_count * 0.1, 0.3)
            
            # Boost for clear intent
            intent_confidence = intent.get('confidence', 0.5)
            base_confidence += intent_confidence * 0.2
            
            # Boost for specific legal terms
            legal_terms = entities.get('legal_terms', [])
            if legal_terms:
                base_confidence += 0.1
            
            # Boost for citations or case numbers
            if entities.get('citations') or entities.get('case_numbers'):
                base_confidence += 0.2
            
            return min(base_confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _generate_search_terms(self, query: str, entities: Dict[str, List[str]]) -> List[str]:
        """Generate search terms for retrieval"""
        try:
            search_terms = []
            
            # Add query words
            search_terms.extend(query.split())
            
            # Add extracted entities
            for entity_list in entities.values():
                search_terms.extend(entity_list)
            
            # Add legal domain terms
            legal_domain = self._determine_legal_domain(query, entities)
            if legal_domain != 'general':
                search_terms.append(legal_domain)
            
            # Remove duplicates and empty strings
            search_terms = list(set([term for term in search_terms if term.strip()]))
            
            return search_terms
            
        except Exception as e:
            logger.error(f"Error generating search terms: {e}")
            return query.split()
    
    def _assess_complexity(self, query: str, entities: Dict[str, List[str]]) -> str:
        """Assess query complexity"""
        try:
            complexity_score = 0
            
            # Length-based complexity
            word_count = len(query.split())
            if word_count > 20:
                complexity_score += 2
            elif word_count > 10:
                complexity_score += 1
            
            # Entity-based complexity
            entity_count = sum(len(entity_list) for entity_list in entities.values())
            if entity_count > 5:
                complexity_score += 2
            elif entity_count > 2:
                complexity_score += 1
            
            # Legal term complexity
            legal_terms = entities.get('legal_terms', [])
            if len(legal_terms) > 3:
                complexity_score += 1
            
            # Multiple question indicators
            question_indicators = ['what', 'how', 'why', 'when', 'where', 'who']
            question_count = sum(1 for indicator in question_indicators if indicator in query.lower())
            if question_count > 2:
                complexity_score += 1
            
            # Determine complexity level
            if complexity_score >= 4:
                return 'high'
            elif complexity_score >= 2:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Error assessing complexity: {e}")
            return 'medium'
    
    def is_healthy(self) -> bool:
        """Check if query processor is healthy"""
        try:
            # Simple health check
            test_query = "What is the law regarding bail?"
            result = self.process_query(test_query)
            return 'processed_text' in result
        except Exception as e:
            logger.error(f"Query processor health check failed: {e}")
            return False
