"""
Legal Semantic Matcher
Advanced semantic matching specifically tuned for legal domain
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import re

logger = logging.getLogger(__name__)


class LegalSemanticMatcher:
    """Advanced semantic matching for legal documents"""
    
    def __init__(self):
        self.model = None
        self.legal_concept_embeddings = {}
        self.legal_concept_hierarchy = self._build_legal_hierarchy()
        self.legal_stopwords = self._get_legal_stopwords()
        
    def initialize_model(self):
        """Initialize or load the semantic model"""
        try:
            if self.model is None:
                # Use a model that works well with legal text
                try:
                    self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
                    logger.info("Legal semantic matcher initialized with CPU device")
                except Exception as tensor_error:
                    logger.warning(f"Tensor error with device specification: {str(tensor_error)}")
                    # Try without device specification
                    self.model = SentenceTransformer('all-MiniLM-L6-v2')
                    logger.info("Legal semantic matcher initialized without device specification")
                
                # Pre-compute embeddings for common legal concepts
                self._precompute_legal_embeddings()
            return True
        except Exception as e:
            logger.error(f"Error initializing legal semantic matcher: {str(e)}")
            return False
    
    def _build_legal_hierarchy(self) -> Dict[str, List[str]]:
        """Build hierarchical relationships between legal concepts"""
        return {
            'civil_law': [
                'contract', 'tort', 'property', 'family', 'commercial',
                'consumer', 'employment', 'intellectual_property'
            ],
            'criminal_law': [
                'felony', 'misdemeanor', 'prosecution', 'defence',
                'evidence', 'procedure', 'sentencing', 'appeal'
            ],
            'constitutional_law': [
                'fundamental_rights', 'due_process', 'equal_protection',
                'separation_powers', 'federalism', 'judicial_review'
            ],
            'administrative_law': [
                'regulation', 'agency', 'rulemaking', 'enforcement',
                'judicial_review', 'due_process'
            ],
            'procedural_law': [
                'jurisdiction', 'venue', 'pleading', 'discovery',
                'trial', 'appeal', 'enforcement'
            ],
            'evidence_law': [
                'admissibility', 'relevance', 'hearsay', 'privilege',
                'authentication', 'burden_proof'
            ]
        }
    
    def _get_legal_stopwords(self) -> set:
        """Get legal-specific stopwords that should be handled carefully"""
        return {
            'court', 'case', 'law', 'legal', 'matter', 'application',
            'petition', 'order', 'judgment', 'ruling', 'decision',
            'vs', 'versus', 'against', 'through', 'and', 'or', 'the'
        }
    
    def _precompute_legal_embeddings(self):
        """Pre-compute embeddings for common legal concepts"""
        legal_concepts = [
            # Case types
            'civil suit', 'criminal case', 'constitutional petition',
            'writ petition', 'appeal case', 'bail application',
            'family matter', 'property dispute', 'commercial dispute',
            'tax case', 'service matter', 'contempt case',
            
            # Legal procedures
            'trial court', 'appellate court', 'supreme court',
            'high court', 'district court', 'sessions court',
            'magistrate court', 'tribunal',
            
            # Legal concepts
            'due process', 'natural justice', 'fair trial',
            'burden of proof', 'standard of proof', 'evidence',
            'precedent', 'jurisdiction', 'venue', 'standing',
            
            # Legal remedies
            'injunction', 'damages', 'compensation', 'restitution',
            'specific performance', 'declaratory relief',
            'mandamus', 'certiorari', 'prohibition'
        ]
        
        try:
            embeddings = self.model.encode(legal_concepts)
            for concept, embedding in zip(legal_concepts, embeddings):
                self.legal_concept_embeddings[concept] = embedding
            logger.info(f"Pre-computed embeddings for {len(legal_concepts)} legal concepts")
        except Exception as e:
            logger.error(f"Error pre-computing legal embeddings: {str(e)}")
    
    def enhance_semantic_matching(self, query: str, document_chunks: List[str]) -> List[Dict[str, Any]]:
        """Enhanced semantic matching with legal domain knowledge"""
        if not self.initialize_model():
            return []
        
        try:
            # Process query with legal understanding
            enhanced_query = self._enhance_query_semantics(query)
            
            # Process document chunks
            processed_chunks = self._preprocess_legal_chunks(document_chunks)
            
            # Compute semantic similarities
            similarities = self._compute_legal_similarities(enhanced_query, processed_chunks)
            
            # Apply legal domain boosting
            boosted_similarities = self._apply_legal_boosting(
                query, processed_chunks, similarities
            )
            
            # Create result objects
            results = []
            for i, (chunk, similarity) in enumerate(zip(processed_chunks, boosted_similarities)):
                results.append({
                    'chunk_index': i,
                    'chunk_text': chunk,
                    'similarity': float(similarity),
                    'legal_relevance': self._assess_legal_relevance(query, chunk),
                    'concept_matches': self._find_concept_matches(query, chunk)
                })
            
            # Sort by enhanced similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in enhanced semantic matching: {str(e)}")
            return []
    
    def _enhance_query_semantics(self, query: str) -> str:
        """Enhance query with legal semantic understanding"""
        enhanced_query = query
        
        # Expand legal abbreviations
        legal_abbrev_map = {
            'w.p': 'writ petition',
            'c.p': 'civil petition',
            'cr.p': 'criminal petition',
            'f.a.o': 'first appeal',
            'c.r': 'civil revision',
            'crl.rev': 'criminal revision',
            'misc': 'miscellaneous',
            'vs': 'versus',
            'thru': 'through'
        }
        
        for abbrev, full_form in legal_abbrev_map.items():
            enhanced_query = re.sub(
                r'\b' + re.escape(abbrev) + r'\b',
                full_form,
                enhanced_query,
                flags=re.IGNORECASE
            )
        
        # Add semantic context based on legal concepts
        legal_context = self._get_semantic_context(query)
        if legal_context:
            enhanced_query = f"{enhanced_query} {legal_context}"
        
        return enhanced_query
    
    def _get_semantic_context(self, query: str) -> str:
        """Get semantic context for legal queries"""
        context_terms = []
        query_lower = query.lower()
        
        # Context mapping for legal domains
        context_mappings = {
            'bail': 'custody detention arrest police',
            'appeal': 'appellate higher court revision',
            'civil': 'damages injunction contract tort',
            'criminal': 'prosecution defence trial evidence',
            'constitutional': 'fundamental rights article constitution',
            'property': 'title possession ownership land',
            'family': 'marriage divorce custody maintenance',
            'commercial': 'business trade contract agreement',
            'tax': 'revenue assessment tribunal appeal',
            'employment': 'service termination benefits pension'
        }
        
        for key_term, context in context_mappings.items():
            if key_term in query_lower:
                context_terms.append(context)
        
        return ' '.join(context_terms[:2])  # Limit context
    
    def _preprocess_legal_chunks(self, chunks: List[str]) -> List[str]:
        """Preprocess document chunks for legal semantic matching"""
        processed_chunks = []
        
        for chunk in chunks:
            # Clean legal text
            cleaned = self._clean_legal_text(chunk)
            
            # Extract legal concepts
            legal_concepts = self._extract_legal_concepts(cleaned)
            
            # Enhance chunk with extracted concepts
            if legal_concepts:
                enhanced_chunk = f"{cleaned} {' '.join(legal_concepts)}"
            else:
                enhanced_chunk = cleaned
            
            processed_chunks.append(enhanced_chunk)
        
        return processed_chunks
    
    def _clean_legal_text(self, text: str) -> str:
        """Clean legal text while preserving important legal terms"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common document artifacts but preserve legal structure
        text = re.sub(r'=+', '', text)
        text = re.sub(r'-{3,}', '', text)
        
        # Normalize legal citations
        text = re.sub(r'\b(\d{4})\s+([A-Z]+)\s+(\d+)\b', r'\1 \2 \3', text)
        
        return text.strip()
    
    def _extract_legal_concepts(self, text: str) -> List[str]:
        """Extract legal concepts from text"""
        concepts = []
        text_lower = text.lower()
        
        # Legal concept patterns
        concept_patterns = {
            'case_types': [
                'civil suit', 'criminal case', 'writ petition',
                'constitutional petition', 'appeal', 'revision',
                'bail application', 'habeas corpus'
            ],
            'legal_procedures': [
                'trial', 'hearing', 'proceeding', 'judgment',
                'order', 'decree', 'ruling', 'decision'
            ],
            'legal_principles': [
                'due process', 'natural justice', 'fair trial',
                'burden of proof', 'reasonable doubt'
            ],
            'remedies': [
                'injunction', 'damages', 'compensation',
                'specific performance', 'mandamus'
            ]
        }
        
        for category, terms in concept_patterns.items():
            for term in terms:
                if term in text_lower:
                    concepts.append(term)
        
        return list(set(concepts))
    
    def _compute_legal_similarities(self, query: str, chunks: List[str]) -> List[float]:
        """Compute similarities with legal domain considerations"""
        try:
            # Get embeddings
            query_embedding = self.model.encode([query])
            chunk_embeddings = self.model.encode(chunks)
            
            # Compute base similarities
            similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
            
            return similarities.tolist()
            
        except Exception as e:
            logger.error(f"Error computing legal similarities: {str(e)}")
            return [0.0] * len(chunks)
    
    def _apply_legal_boosting(self, query: str, chunks: List[str], similarities: List[float]) -> List[float]:
        """Apply legal domain-specific boosting"""
        boosted_similarities = similarities.copy()
        
        query_lower = query.lower()
        
        for i, chunk in enumerate(chunks):
            chunk_lower = chunk.lower()
            boost_factor = 1.0
            
            # Citation boost
            if self._has_citation_match(query, chunk):
                boost_factor *= 2.0
            
            # Exact legal term match boost
            legal_terms_in_query = self._extract_legal_terms(query_lower)
            legal_terms_in_chunk = self._extract_legal_terms(chunk_lower)
            
            common_terms = set(legal_terms_in_query).intersection(set(legal_terms_in_chunk))
            if common_terms:
                boost_factor *= (1.0 + len(common_terms) * 0.3)
            
            # Case party name boost
            if self._has_party_name_match(query, chunk):
                boost_factor *= 1.5
            
            # Legal concept hierarchy boost
            concept_boost = self._get_concept_hierarchy_boost(query, chunk)
            boost_factor *= concept_boost
            
            # Apply boost
            boosted_similarities[i] *= boost_factor
        
        return boosted_similarities
    
    def _has_citation_match(self, query: str, chunk: str) -> bool:
        """Check for citation matches between query and chunk"""
        citation_patterns = [
            r'\b\d{4}\s*[A-Z]+\s*\d+\b',
            r'\b[A-Z]+\s*\d{4}\s*\d+\b',
            r'\b\d+\s*of\s*\d{4}\b'
        ]
        
        query_citations = []
        chunk_citations = []
        
        for pattern in citation_patterns:
            query_citations.extend(re.findall(pattern, query, re.IGNORECASE))
            chunk_citations.extend(re.findall(pattern, chunk, re.IGNORECASE))
        
        # Check for any citation overlap
        return bool(set(query_citations).intersection(set(chunk_citations)))
    
    def _extract_legal_terms(self, text: str) -> List[str]:
        """Extract legal terms from text"""
        legal_terms = [
            'appeal', 'petition', 'bail', 'writ', 'civil', 'criminal',
            'constitutional', 'contract', 'property', 'family',
            'commercial', 'tax', 'court', 'judge', 'justice',
            'judgment', 'order', 'decree', 'injunction', 'damages'
        ]
        
        found_terms = []
        for term in legal_terms:
            if term in text:
                found_terms.append(term)
        
        return found_terms
    
    def _has_party_name_match(self, query: str, chunk: str) -> bool:
        """Check for party name matches"""
        # Simple party name extraction (can be enhanced)
        query_parties = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        chunk_parties = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', chunk)
        
        return bool(set(query_parties).intersection(set(chunk_parties)))
    
    def _get_concept_hierarchy_boost(self, query: str, chunk: str) -> float:
        """Get boost based on legal concept hierarchy"""
        boost = 1.0
        query_lower = query.lower()
        chunk_lower = chunk.lower()
        
        # Check for hierarchical concept relationships
        for category, concepts in self.legal_concept_hierarchy.items():
            query_concepts = [c for c in concepts if c in query_lower]
            chunk_concepts = [c for c in concepts if c in chunk_lower]
            
            if query_concepts and chunk_concepts:
                # Same category boost
                boost *= 1.2
                
                # Same concept boost
                if set(query_concepts).intersection(set(chunk_concepts)):
                    boost *= 1.3
        
        return boost
    
    def _assess_legal_relevance(self, query: str, chunk: str) -> float:
        """Assess legal relevance score"""
        relevance_score = 0.0
        
        # Citation relevance
        if self._has_citation_match(query, chunk):
            relevance_score += 0.4
        
        # Legal term relevance
        query_terms = self._extract_legal_terms(query.lower())
        chunk_terms = self._extract_legal_terms(chunk.lower())
        term_overlap = len(set(query_terms).intersection(set(chunk_terms)))
        if term_overlap > 0:
            relevance_score += min(0.3, term_overlap * 0.1)
        
        # Party name relevance
        if self._has_party_name_match(query, chunk):
            relevance_score += 0.2
        
        # Concept hierarchy relevance
        hierarchy_boost = self._get_concept_hierarchy_boost(query, chunk)
        if hierarchy_boost > 1.0:
            relevance_score += min(0.1, (hierarchy_boost - 1.0) * 0.5)
        
        return min(1.0, relevance_score)
    
    def _find_concept_matches(self, query: str, chunk: str) -> List[str]:
        """Find matching legal concepts between query and chunk"""
        query_concepts = self._extract_legal_concepts(query)
        chunk_concepts = self._extract_legal_concepts(chunk)
        
        return list(set(query_concepts).intersection(set(chunk_concepts)))
