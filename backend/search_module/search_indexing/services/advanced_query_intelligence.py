"""
Advanced Query Intelligence Service
Provides perfect query understanding and expansion for legal search
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    CASE_LOOKUP = "case_lookup"
    LEGAL_RESEARCH = "legal_research"
    PRECEDENT_SEARCH = "precedent_search"
    PROCEDURAL_INQUIRY = "procedural_inquiry"
    FACTUAL_SEARCH = "factual_search"
    COMPARATIVE_ANALYSIS = "comparative_analysis"


@dataclass
class QueryAnalysis:
    """Comprehensive query analysis result"""
    intent: QueryIntent
    confidence: float
    legal_entities: List[Dict[str, Any]]
    query_type: str
    specificity_score: float
    expansion_terms: List[str]
    semantic_concepts: List[str]
    search_strategy: str
    expected_result_types: List[str]
    boost_factors: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'intent': self.intent.value if self.intent else 'unknown',
            'confidence': self.confidence,
            'legal_entities': self.legal_entities,
            'query_type': self.query_type,
            'specificity_score': self.specificity_score,
            'expansion_terms': self.expansion_terms,
            'semantic_concepts': self.semantic_concepts,
            'search_strategy': self.search_strategy,
            'expected_result_types': self.expected_result_types,
            'boost_factors': self.boost_factors
        }


class AdvancedQueryIntelligence:
    """Advanced query understanding and expansion for perfect search results"""
    
    def __init__(self):
        self.legal_dictionary = self._load_legal_dictionary()
        self.synonym_map = self._load_synonym_map()
        self.abbreviation_map = self._load_abbreviation_map()
        self.concept_hierarchy = self._load_concept_hierarchy()
        self.query_patterns = self._load_query_patterns()
    
    def analyze_query(self, query: str, user_context: Dict = None) -> QueryAnalysis:
        """Perform comprehensive query analysis"""
        try:
            # Step 1: Basic preprocessing
            cleaned_query = self._preprocess_query(query)
            
            # Step 2: Intent detection
            intent, intent_confidence = self._detect_intent(cleaned_query)
            
            # Step 3: Legal entity extraction
            legal_entities = self._extract_legal_entities(cleaned_query)
            
            # Step 4: Query type classification
            query_type = self._classify_query_type(cleaned_query)
            
            # Step 5: Specificity scoring
            specificity_score = self._calculate_specificity(cleaned_query, legal_entities)
            
            # Step 6: Query expansion
            expansion_terms = self._expand_query(cleaned_query, intent, legal_entities)
            
            # Step 7: Semantic concept extraction
            semantic_concepts = self._extract_semantic_concepts(cleaned_query)
            
            # Step 8: Search strategy determination
            search_strategy = self._determine_search_strategy(intent, specificity_score, query_type)
            
            # Step 9: Expected result types
            expected_result_types = self._predict_result_types(intent, legal_entities)
            
            # Step 10: Boost factors
            boost_factors = self._calculate_boost_factors(intent, legal_entities, specificity_score)
            
            return QueryAnalysis(
                intent=intent,
                confidence=intent_confidence,
                legal_entities=legal_entities,
                query_type=query_type,
                specificity_score=specificity_score,
                expansion_terms=expansion_terms,
                semantic_concepts=semantic_concepts,
                search_strategy=search_strategy,
                expected_result_types=expected_result_types,
                boost_factors=boost_factors
            )
            
        except Exception as e:
            logger.error(f"Error in query analysis: {str(e)}")
            # Return fallback analysis
            return self._fallback_analysis(query)
    
    def expand_query_intelligently(self, query: str, analysis: QueryAnalysis) -> Dict[str, Any]:
        """Intelligent query expansion based on analysis"""
        expanded_query = {
            'original_query': query,
            'primary_terms': self._extract_primary_terms(query, analysis),
            'expanded_terms': analysis.expansion_terms,
            'semantic_terms': analysis.semantic_concepts,
            'legal_synonyms': self._get_legal_synonyms(query),
            'contextual_terms': self._get_contextual_terms(query, analysis.intent),
            'must_have_terms': self._identify_must_have_terms(query, analysis.legal_entities),
            'should_have_terms': self._identify_should_have_terms(query, analysis),
            'boost_terms': self._identify_boost_terms(query, analysis),
            'filter_suggestions': self._suggest_filters(analysis)
        }
        
        return expanded_query
    
    def _load_legal_dictionary(self) -> Dict[str, List[str]]:
        """Load legal dictionary with terms and their meanings"""
        return {
            'contract': ['agreement', 'covenant', 'pact', 'deal', 'arrangement'],
            'property': ['real estate', 'land', 'immovable', 'estate', 'premises'],
            'criminal': ['penal', 'offense', 'crime', 'violation', 'felony'],
            'civil': ['private', 'non-criminal', 'tort', 'dispute', 'litigation'],
            'appeal': ['revision', 'review', 'challenge', 'petition'],
            'judgment': ['decision', 'ruling', 'verdict', 'order', 'decree'],
            'court': ['tribunal', 'forum', 'bench', 'judiciary'],
            'petition': ['application', 'plea', 'request', 'motion'],
            'writ': ['mandamus', 'certiorari', 'prohibition', 'habeas corpus'],
            'constitutional': ['fundamental rights', 'basic rights', 'charter']
        }
    
    def _load_synonym_map(self) -> Dict[str, List[str]]:
        """Load synonym mappings for legal terms"""
        return {
            'vs': ['versus', 'v.', 'against'],
            'ltd': ['limited', 'pvt ltd', 'private limited'],
            'govt': ['government', 'state', 'administration'],
            'dept': ['department', 'ministry'],
            'sec': ['section', 'clause'],
            'act': ['statute', 'law', 'legislation'],
            'cpc': ['civil procedure code'],
            'crpc': ['criminal procedure code'],
            'ipc': ['indian penal code', 'pakistan penal code'],
            'constitution': ['basic law', 'fundamental law']
        }
    
    def _load_abbreviation_map(self) -> Dict[str, str]:
        """Load abbreviation expansions"""
        return {
            'LHC': 'Lahore High Court',
            'IHC': 'Islamabad High Court',
            'SHC': 'Sindh High Court',
            'PHC': 'Peshawar High Court',
            'BHC': 'Balochistan High Court',
            'SC': 'Supreme Court',
            'CJ': 'Chief Justice',
            'J': 'Justice',
            'CPC': 'Civil Procedure Code',
            'CrPC': 'Criminal Procedure Code',
            'PPC': 'Pakistan Penal Code',
            'FIR': 'First Information Report',
            'SLP': 'Special Leave Petition',
            'PIL': 'Public Interest Litigation'
        }
    
    def _load_concept_hierarchy(self) -> Dict[str, Dict]:
        """Load legal concept hierarchy"""
        return {
            'civil_law': {
                'contract_law': ['breach of contract', 'specific performance', 'damages'],
                'property_law': ['ownership', 'possession', 'transfer', 'inheritance'],
                'tort_law': ['negligence', 'defamation', 'nuisance'],
                'family_law': ['marriage', 'divorce', 'custody', 'maintenance']
            },
            'criminal_law': {
                'violent_crimes': ['murder', 'assault', 'robbery'],
                'property_crimes': ['theft', 'burglary', 'fraud'],
                'white_collar': ['embezzlement', 'corruption', 'tax evasion']
            },
            'constitutional_law': {
                'fundamental_rights': ['equality', 'liberty', 'privacy'],
                'state_powers': ['executive', 'legislative', 'judicial'],
                'federalism': ['provincial rights', 'federal jurisdiction']
            },
            'administrative_law': {
                'government_actions': ['licensing', 'permits', 'regulations'],
                'public_services': ['employment', 'benefits', 'procurement']
            }
        }
    
    def _load_query_patterns(self) -> Dict[str, List[str]]:
        """Load common query patterns"""
        return {
            'case_search': [
                r'case (number|no\.?)\s*:?\s*([A-Z0-9/\-\s]+)',
                r'([A-Z]{2,}\s*\d+/\d+)',
                r'(civil|criminal|constitutional)\s+(appeal|petition|suit)\s+(no\.?|number)\s*:?\s*(\d+)'
            ],
            'party_search': [
                r'([A-Z][a-zA-Z\s]+)\s+(vs?\.?|versus|against)\s+([A-Z][a-zA-Z\s]+)',
                r'petitioner\s*:?\s*([A-Z][a-zA-Z\s]+)',
                r'respondent\s*:?\s*([A-Z][a-zA-Z\s]+)'
            ],
            'legal_concept': [
                r'(contract|property|criminal|civil|constitutional)\s+(law|rights|dispute)',
                r'(fundamental|basic|constitutional)\s+rights',
                r'(breach|violation)\s+of\s+([a-zA-Z\s]+)'
            ],
            'court_jurisdiction': [
                r'(lahore|islamabad|sindh|peshawar|balochistan|supreme)\s+(high\s+)?court',
                r'(LHC|IHC|SHC|PHC|BHC|SC)'
            ]
        }
    
    def _preprocess_query(self, query: str) -> str:
        """Basic query preprocessing"""
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Expand common abbreviations
        for abbrev, full_form in self.abbreviation_map.items():
            query = query.replace(abbrev, full_form)
        
        return query.strip()
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of legal query"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['case number', 'case no', 'appeal no']):
            return 'case_lookup'
        elif any(term in query_lower for term in ['vs', 'versus', 'against']):
            return 'party_search'
        elif any(term in query_lower for term in ['contract', 'property', 'criminal', 'civil']):
            return 'legal_concept'
        elif any(term in query_lower for term in ['court', 'judge', 'bench']):
            return 'jurisdiction'
        else:
            return 'general_search'
    
    def _extract_primary_terms(self, query: str, analysis: 'QueryAnalysis') -> List[str]:
        """Extract primary search terms from query"""
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
        
        # Split query into terms
        terms = query.lower().split()
        
        # Filter out stop words and short terms
        primary_terms = [term for term in terms if term not in stop_words and len(term) > 2]
        
        return primary_terms[:5]  # Return top 5 primary terms
    
    def _extract_semantic_concepts(self, query: str) -> List[str]:
        """Extract semantic concepts from query"""
        concepts = []
        query_lower = query.lower()
        
        # Map query terms to semantic concepts
        concept_map = {
            'contract': ['agreement', 'covenant', 'deal'],
            'property': ['real estate', 'land', 'ownership'],
            'criminal': ['crime', 'offense', 'violation'],
            'civil': ['dispute', 'litigation', 'damages'],
            'court': ['tribunal', 'judiciary', 'bench'],
            'appeal': ['review', 'revision', 'challenge']
        }
        
        for concept, synonyms in concept_map.items():
            if concept in query_lower or any(syn in query_lower for syn in synonyms):
                concepts.append(concept)
        
        return concepts
    
    def _normalize_entity(self, entity: str, entity_type: str = None) -> str:
        """Normalize legal entity names"""
        entity_lower = entity.lower().strip()
        
        # Common normalizations
        normalizations = {
            'lhc': 'Lahore High Court',
            'ihc': 'Islamabad High Court',
            'shc': 'Sindh High Court',
            'phc': 'Peshawar High Court',
            'sc': 'Supreme Court',
            'vs': 'versus',
            'v.': 'versus'
        }
        
        return normalizations.get(entity_lower, entity)
    
    def _get_legal_synonyms(self, query: str) -> List[str]:
        """Get legal synonyms for query terms"""
        synonyms = []
        query_terms = query.lower().split()
        
        synonym_map = {
            'contract': ['agreement', 'pact', 'deal'],
            'property': ['estate', 'land', 'realty'],
            'court': ['tribunal', 'forum', 'bench'],
            'case': ['matter', 'suit', 'proceeding'],
            'appeal': ['petition', 'application', 'review']
        }
        
        for term in query_terms:
            if term in synonym_map:
                synonyms.extend(synonym_map[term])
        
        return synonyms
    
    def _get_contextual_terms(self, query: str, intent) -> List[str]:
        """Get contextual terms based on query and intent"""
        contextual_terms = []
        
        # Add context based on intent
        if hasattr(intent, 'value'):
            intent_value = intent.value
        else:
            intent_value = str(intent)
        
        context_map = {
            'legal_research': ['law', 'statute', 'precedent'],
            'case_lookup': ['number', 'citation', 'reference'],
            'precedent_search': ['similar', 'precedent', 'authority']
        }
        
        if intent_value in context_map:
            contextual_terms.extend(context_map[intent_value])
        
        return contextual_terms
    
    def _identify_must_have_terms(self, query: str, legal_entities: List) -> List[str]:
        """Identify terms that must appear in results"""
        must_have = []
        
        # Case numbers are always must-have
        import re
        case_number_pattern = r'\b[A-Z]{2,}\s*\d+/\d+\b'
        case_numbers = re.findall(case_number_pattern, query)
        must_have.extend(case_numbers)
        
        # Legal entities are must-have
        for entity in legal_entities:
            if isinstance(entity, dict) and 'text' in entity:
                must_have.append(entity['text'])
            elif isinstance(entity, str):
                must_have.append(entity)
        
        return must_have
    
    def _identify_should_have_terms(self, query: str, analysis) -> List[str]:
        """Identify terms that should appear in results"""
        should_have = []
        
        # Add semantic concepts
        if hasattr(analysis, 'semantic_concepts'):
            should_have.extend(analysis.semantic_concepts)
        
        # Add expanded terms
        if hasattr(analysis, 'expansion_terms'):
            should_have.extend(analysis.expansion_terms)
        
        return should_have
    
    def _identify_boost_terms(self, query: str, analysis) -> List[str]:
        """Identify terms that should boost relevance"""
        boost_terms = []
        
        # Court names boost relevance
        court_terms = ['court', 'tribunal', 'bench', 'judge', 'justice']
        query_lower = query.lower()
        
        for term in court_terms:
            if term in query_lower:
                boost_terms.append(term)
        
        return boost_terms
    
    def _suggest_filters(self, analysis) -> Dict[str, Any]:
        """Suggest filters based on analysis"""
        filters = {}
        
        # Suggest court filter if court mentioned
        if hasattr(analysis, 'legal_entities'):
            for entity in analysis.legal_entities:
                if isinstance(entity, dict) and 'court' in str(entity).lower():
                    filters['court'] = entity
                    break
        
        return filters
    
    def _detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """Detect user intent from query"""
        query_lower = query.lower()
        
        # Intent patterns with confidence scores
        intent_patterns = {
            QueryIntent.CASE_LOOKUP: [
                (r'\b(case\s+number|case\s+no|file\s+no)\b', 0.9),
                (r'\b\d+/\d{4}\b', 0.8),  # Case number pattern
                (r'\bvs?\.\s+\w+', 0.7),  # Party vs Party
                (r'\b(crl|civil|writ)\s+(appeal|petition|misc)\b', 0.8)
            ],
            QueryIntent.LEGAL_RESEARCH: [
                (r'\b(research|analysis|study|examine)\b', 0.8),
                (r'\b(legal\s+principle|doctrine|precedent)\b', 0.9),
                (r'\b(interpretation|meaning|definition)\b', 0.7),
                (r'\b(case\s+law|jurisprudence)\b', 0.8)
            ],
            QueryIntent.PRECEDENT_SEARCH: [
                (r'\b(precedent|similar\s+case|comparable)\b', 0.9),
                (r'\b(earlier\s+decision|previous\s+ruling)\b', 0.8),
                (r'\b(following|relied\s+upon|cited)\b', 0.7),
                (r'\b(binding|persuasive|authority)\b', 0.8)
            ],
            QueryIntent.PROCEDURAL_INQUIRY: [
                (r'\b(procedure|process|steps|how\s+to)\b', 0.8),
                (r'\b(filing|submission|application)\b', 0.7),
                (r'\b(court\s+fee|limitation|time\s+limit)\b', 0.8),
                (r'\b(appeal\s+process|revision\s+procedure)\b', 0.9)
            ],
            QueryIntent.FACTUAL_SEARCH: [
                (r'\b(facts|circumstances|details|incident)\b', 0.7),
                (r'\b(what\s+happened|sequence\s+of\s+events)\b', 0.8),
                (r'\b(background|context|situation)\b', 0.6),
                (r'\b(evidence|witness|testimony)\b', 0.7)
            ]
        }
        
        # Calculate scores for each intent
        intent_scores = {}
        for intent, patterns in intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern, weight in patterns:
                if re.search(pattern, query_lower):
                    score += weight
                    matches += 1
            
            if matches > 0:
                intent_scores[intent] = score / len(patterns)  # Normalize by pattern count
        
        # Default to legal research if no clear intent
        if not intent_scores:
            return QueryIntent.LEGAL_RESEARCH, 0.5
        
        # Return intent with highest score
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        return best_intent, confidence
    
    def _extract_legal_entities(self, query: str) -> List[Dict[str, Any]]:
        """Extract legal entities with enhanced patterns"""
        entities = []
        
        # Enhanced legal entity patterns
        entity_patterns = {
            'statute': [
                r'\b(PPC|Pakistan\s+Penal\s+Code)\s*(\d+[A-Z]?)\b',
                r'\b(CrPC|Criminal\s+Procedure\s+Code)\s*(\d+[A-Z]?)\b',
                r'\b(CPC|Civil\s+Procedure\s+Code)\s*(\d+[A-Z]?)\b',
                r'\b(Constitution|Article)\s+(\d+[A-Z]?)\b',
                r'\b(Qanun-e-Shahadat|Evidence\s+Act)\s+(\d+[A-Z]?)\b'
            ],
            'case_citation': [
                r'\b\d{4}\s+(SCMR|PLD|YLR|CLR|PLJ|CLC)\s+\d+\b',
                r'\b(PLD|SCMR|YLR)\s+\d{4}\s+(SC|FSC|LHC|IHC|PHC|SHC|BHC)\s+\d+\b',
                r'\b\d{4}\s+\w+\s+\d+\s*\([A-Z]+\)\b'
            ],
            'case_number': [
                r'\b(Crl|Civil|Const|Writ)\.\s*(Appeal|Petition|Misc|Application)\s*\d+/\d{4}\b',
                r'\b[A-Z]+\s*\d+/\d{4}\b',
                r'\bW\.P\.?\s*\d+/\d{4}\b',
                r'\bF\.I\.R\.?\s*\d+/\d{4}\b'
            ],
            'court': [
                r'\b(Supreme\s+Court|High\s+Court|District\s+Court|Sessions?\s+Court)\b',
                r'\b(Islamabad|Lahore|Karachi|Peshawar|Quetta)\s+High\s+Court\b',
                r'\b(Federal\s+Shariat\s+Court|Anti-Terrorism\s+Court)\b'
            ],
            'legal_concept': [
                r'\b(Fundamental\s+Rights?|Due\s+Process|Natural\s+Justice)\b',
                r'\b(Burden\s+of\s+Proof|Standard\s+of\s+Proof)\b',
                r'\b(Res\s+Judicata|Limitation|Jurisdiction)\b',
                r'\b(Habeas\s+Corpus|Mandamus|Certiorari|Prohibition)\b'
            ],
            'legal_procedure': [
                r'\b(Appeal|Revision|Review|Rehearing)\b',
                r'\b(Bail|Acquittal|Conviction|Sentence)\b',
                r'\b(Injunction|Stay|Interim\s+Relief)\b',
                r'\b(Cross-examination|Evidence|Witness)\b'
            ]
        }
        
        # Extract entities
        for entity_type, patterns in entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        'type': entity_type,
                        'text': match.group(),
                        'position': match.span(),
                        'confidence': 0.9,
                        'normalized': self._normalize_entity(match.group(), entity_type)
                    })
        
        return entities
    
    def _calculate_specificity(self, query: str, legal_entities: List[Dict]) -> float:
        """Calculate query specificity score (0.0 to 1.0)"""
        score = 0.0
        
        # Base score from query length
        words = query.split()
        if len(words) == 1:
            score += 0.1
        elif len(words) <= 3:
            score += 0.3
        elif len(words) <= 6:
            score += 0.5
        else:
            score += 0.7
        
        # Boost for legal entities
        entity_weights = {
            'case_citation': 0.3,
            'case_number': 0.25,
            'statute': 0.2,
            'court': 0.1,
            'legal_concept': 0.15,
            'legal_procedure': 0.1
        }
        
        for entity in legal_entities:
            entity_type = entity.get('type')
            if entity_type in entity_weights:
                score += entity_weights[entity_type]
        
        # Boost for exact phrases (quoted terms)
        if '"' in query:
            score += 0.1
        
        # Boost for specific patterns
        specific_patterns = [
            r'\bvs?\.\s+\w+',  # Party names
            r'\b\d+/\d{4}\b',  # Year patterns
            r'\b(decided|pending|disposed)\b'  # Status terms
        ]
        
        for pattern in specific_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                score += 0.05
        
        return min(score, 1.0)
    
    def _expand_query(self, query: str, intent: QueryIntent, legal_entities: List[Dict]) -> List[str]:
        """Expand query with relevant terms"""
        expansion_terms = set()
        query_lower = query.lower()
        
        # Intent-based expansion
        intent_expansions = {
            QueryIntent.CASE_LOOKUP: ['case number', 'file number', 'parties', 'court'],
            QueryIntent.LEGAL_RESEARCH: ['legal principle', 'doctrine', 'precedent', 'jurisprudence'],
            QueryIntent.PRECEDENT_SEARCH: ['similar case', 'comparable', 'precedent', 'authority'],
            QueryIntent.PROCEDURAL_INQUIRY: ['procedure', 'process', 'steps', 'requirements'],
            QueryIntent.FACTUAL_SEARCH: ['facts', 'circumstances', 'evidence', 'details']
        }
        
        if intent in intent_expansions:
            expansion_terms.update(intent_expansions[intent])
        
        # Legal entity-based expansion
        for entity in legal_entities:
            entity_type = entity.get('type')
            entity_text = entity.get('text', '').lower()
            
            if entity_type == 'statute':
                if 'ppc' in entity_text:
                    expansion_terms.update(['criminal law', 'penal code', 'offense'])
                elif 'crpc' in entity_text:
                    expansion_terms.update(['criminal procedure', 'investigation', 'trial'])
                elif 'cpc' in entity_text:
                    expansion_terms.update(['civil procedure', 'suit', 'decree'])
            
            elif entity_type == 'legal_concept':
                if 'fundamental rights' in entity_text:
                    expansion_terms.update(['constitutional law', 'basic rights', 'liberty'])
                elif 'due process' in entity_text:
                    expansion_terms.update(['fair trial', 'natural justice', 'procedural fairness'])
        
        # Synonym expansion
        for word in query.split():
            if word.lower() in self.synonym_map:
                expansion_terms.update(self.synonym_map[word.lower()])
        
        # Remove original query terms
        original_terms = set(query.lower().split())
        expansion_terms = expansion_terms - original_terms
        
        return list(expansion_terms)[:20]  # Limit expansion terms
    
    def _determine_search_strategy(self, intent: QueryIntent, specificity: float, query_type: str) -> str:
        """Determine optimal search strategy"""
        
        # High specificity queries
        if specificity > 0.7:
            if intent == QueryIntent.CASE_LOOKUP:
                return "exact_match_priority"
            else:
                return "precision_focused"
        
        # Medium specificity
        elif specificity > 0.4:
            if intent in [QueryIntent.LEGAL_RESEARCH, QueryIntent.PRECEDENT_SEARCH]:
                return "semantic_hybrid"
            else:
                return "balanced_hybrid"
        
        # Low specificity (broad queries)
        else:
            if intent == QueryIntent.FACTUAL_SEARCH:
                return "semantic_expansion"
            else:
                return "comprehensive_coverage"
    
    def _predict_result_types(self, intent: QueryIntent, legal_entities: List[Dict]) -> List[str]:
        """Predict expected result types"""
        result_types = []
        
        # Intent-based predictions
        intent_results = {
            QueryIntent.CASE_LOOKUP: ['specific_case', 'case_details'],
            QueryIntent.LEGAL_RESEARCH: ['legal_principles', 'case_law', 'statutory_provisions'],
            QueryIntent.PRECEDENT_SEARCH: ['similar_cases', 'binding_precedents'],
            QueryIntent.PROCEDURAL_INQUIRY: ['procedural_rules', 'court_procedures'],
            QueryIntent.FACTUAL_SEARCH: ['factual_cases', 'evidence_based']
        }
        
        if intent in intent_results:
            result_types.extend(intent_results[intent])
        
        # Entity-based predictions
        entity_results = {
            'case_citation': ['cited_cases', 'reported_cases'],
            'case_number': ['specific_case', 'case_file'],
            'statute': ['statutory_cases', 'legal_provisions'],
            'court': ['court_specific_cases'],
            'legal_concept': ['conceptual_cases', 'principle_based']
        }
        
        for entity in legal_entities:
            entity_type = entity.get('type')
            if entity_type in entity_results:
                result_types.extend(entity_results[entity_type])
        
        return list(set(result_types))  # Remove duplicates
    
    def _calculate_boost_factors(self, intent: QueryIntent, legal_entities: List[Dict], specificity: float) -> Dict[str, float]:
        """Calculate boost factors for different aspects"""
        boost_factors = {}
        
        # Intent-based boosts
        intent_boosts = {
            QueryIntent.CASE_LOOKUP: {'exact_match': 2.0, 'case_number': 1.8},
            QueryIntent.LEGAL_RESEARCH: {'legal_concepts': 1.5, 'precedents': 1.3},
            QueryIntent.PRECEDENT_SEARCH: {'similar_cases': 1.7, 'citations': 1.4},
            QueryIntent.PROCEDURAL_INQUIRY: {'procedures': 1.6, 'rules': 1.2},
            QueryIntent.FACTUAL_SEARCH: {'facts': 1.3, 'evidence': 1.2}
        }
        
        if intent in intent_boosts:
            boost_factors.update(intent_boosts[intent])
        
        # Specificity-based boosts
        if specificity > 0.7:
            boost_factors['precision'] = 1.4
        elif specificity > 0.4:
            boost_factors['balanced'] = 1.2
        else:
            boost_factors['coverage'] = 1.1
        
        # Entity-based boosts
        for entity in legal_entities:
            entity_type = entity.get('type')
            if entity_type == 'case_citation':
                boost_factors['citations'] = 1.6
            elif entity_type == 'statute':
                boost_factors['statutory'] = 1.4
            elif entity_type == 'court':
                boost_factors['court_specific'] = 1.3
        
        return boost_factors
    
    def _load_legal_dictionary(self) -> Dict:
        """Load comprehensive legal dictionary"""
        return {
            'criminal_law': ['murder', 'theft', 'fraud', 'assault', 'robbery', 'kidnapping'],
            'civil_law': ['contract', 'tort', 'property', 'damages', 'injunction', 'specific performance'],
            'constitutional_law': ['fundamental rights', 'due process', 'equal protection', 'separation of powers'],
            'procedural_law': ['jurisdiction', 'venue', 'pleadings', 'discovery', 'trial', 'appeal'],
            'evidence_law': ['admissibility', 'relevance', 'hearsay', 'burden of proof', 'standard of proof']
        }
    
    def _load_synonym_map(self) -> Dict:
        """Load legal synonym mapping"""
        return {
            'murder': ['homicide', 'killing', 'culpable homicide'],
            'theft': ['stealing', 'larceny', 'misappropriation'],
            'appeal': ['appellate proceedings', 'higher court review'],
            'bail': ['pre-trial release', 'interim liberty'],
            'court': ['tribunal', 'forum', 'judicial forum'],
            'judge': ['judicial officer', 'magistrate', 'justice'],
            'case': ['matter', 'proceeding', 'litigation', 'suit'],
            'law': ['statute', 'act', 'legislation', 'enactment']
        }
    
    def _load_abbreviation_map(self) -> Dict:
        """Load legal abbreviation mapping"""
        return {
            'PPC': 'Pakistan Penal Code',
            'CrPC': 'Criminal Procedure Code',
            'CPC': 'Civil Procedure Code',
            'SCMR': 'Supreme Court Monthly Review',
            'PLD': 'Pakistan Legal Decisions',
            'YLR': 'Yearly Law Reports',
            'W.P': 'Writ Petition',
            'F.I.R': 'First Information Report'
        }
    
    def _fallback_analysis(self, query: str) -> QueryAnalysis:
        """Provide fallback analysis when main analysis fails"""
        return QueryAnalysis(
            intent=QueryIntent.LEGAL_RESEARCH,
            confidence=0.5,
            legal_entities=[],
            query_type="general",
            specificity_score=0.3,
            expansion_terms=[],
            semantic_concepts=[],
            search_strategy="balanced_hybrid",
            expected_result_types=["general_cases"],
            boost_factors={"default": 1.0}
        )
