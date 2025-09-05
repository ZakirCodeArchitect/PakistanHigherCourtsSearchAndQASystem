"""
Snippet Generation Service
Creates relevant snippets with span information for search results
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from django.db.models import Q
from apps.cases.models import Case, TermOccurrence, DocumentText
from ..models import DocumentChunk
from .simple_ai_snippet_service import SimpleAISnippetService

logger = logging.getLogger(__name__)


class SnippetService:
    """Service for generating search result snippets"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Default configuration
        self.default_config = {
            'max_snippet_length': 300,
            'min_snippet_length': 100,
            'context_words': 20,  # Words around match
            'max_snippets_per_result': 3,
            'prefer_lexical_matches': True,
            'include_page_numbers': True,
            'highlight_terms': True,
            'use_ai_snippets': True,  # Enable AI-powered snippets
            'ai_snippet_priority': True  # Prioritize AI snippets over traditional ones
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
        
        # Initialize AI snippet service
        self.ai_snippet_service = None
        if self.default_config.get('use_ai_snippets', False):
            try:
                self.ai_snippet_service = SimpleAISnippetService()
            except Exception as e:
                logger.warning(f"Failed to initialize AI snippet service: {e}")
                self.ai_snippet_service = None
    
    def generate_snippets(self, 
                          case_id: int, 
                          query: str, 
                          query_info: Dict[str, Any],
                          max_snippets: int = None) -> List[Dict[str, Any]]:
        """
        Generate snippets for a search result
        
        Args:
            case_id: Case ID to generate snippets for
            query: Original search query
            query_info: Query normalization information
            max_snippets: Maximum number of snippets to generate
        
        Returns:
            List of snippet objects with text and span information
        """
        try:
            max_snippets = max_snippets or self.default_config['max_snippets_per_result']
            
            snippets = []
            
            # Strategy 1: Try AI-powered snippet generation first (if enabled)
            if (self.ai_snippet_service and 
                self.default_config.get('ai_snippet_priority', False)):
                
                ai_snippets = self._generate_ai_snippets(case_id, query, query_info, max_snippets)
                if ai_snippets:
                    snippets.extend(ai_snippets)
                    logger.info(f"Generated {len(ai_snippets)} AI snippets for case {case_id}")
            
            # Strategy 2: Fallback to traditional methods if AI snippets insufficient
            if len(snippets) < max_snippets:
                # Generate snippets from semantic chunks (prioritize actual content)
                semantic_snippets = self._generate_semantic_snippets(case_id, query_info, max_snippets - len(snippets))
                snippets.extend(semantic_snippets)
                
                # Generate snippets from lexical matches with expanded terms
                if len(snippets) < max_snippets:
                    expanded_query = self._expand_query_terms(query)
                    lexical_snippets = self._generate_lexical_snippets(case_id, expanded_query, max_snippets - len(snippets))
                    snippets.extend(lexical_snippets)
                
                # Generate snippets from case metadata (fallback only)
                if len(snippets) < max_snippets:
                    metadata_snippets = self._generate_metadata_snippets(case_id, query, max_snippets - len(snippets))
                    snippets.extend(metadata_snippets)
            
            # Sort snippets by relevance and limit
            sorted_snippets = sorted(snippets, key=lambda x: x['relevance_score'], reverse=True)
            return sorted_snippets[:max_snippets]
            
        except Exception as e:
            logger.error(f"Error generating snippets for case {case_id}: {str(e)}")
            return []
    
    def _generate_ai_snippets(self, case_id: int, query: str, query_info: Dict[str, Any], max_snippets: int) -> List[Dict[str, Any]]:
        """Generate AI-powered snippets for a case"""
        try:
            # Get case data
            case = Case.objects.filter(id=case_id).first()
            if not case:
                return []
            
            # Prepare case data
            case_data = {
                'case_title': case.case_title or 'Unknown Case',
                'court': case.court.name if case.court else 'Unknown Court',
                'status': case.status or 'Unknown Status',
                'case_number': case.case_number or 'N/A',
                'institution_date': case.institution_date,
                'hearing_date': case.hearing_date
            }
            
            # Get document chunks for context
            document_chunks = []
            chunks = DocumentChunk.objects.filter(
                case_id=case_id,
                is_embedded=True
            ).order_by('chunk_index')[:5]  # Limit to first 5 chunks
            
            for chunk in chunks:
                if chunk.chunk_text and len(chunk.chunk_text.strip()) > 50:
                    document_chunks.append(chunk.chunk_text)
            
            # Generate AI snippets
            ai_snippets = self.ai_snippet_service.generate_ai_snippet(
                case_data=case_data,
                query=query,
                document_chunks=document_chunks,
                max_snippets=max_snippets
            )
            
            return ai_snippets
            
        except Exception as e:
            logger.error(f"Error generating AI snippets for case {case_id}: {str(e)}")
            return []
    
    def _expand_query_terms(self, query: str) -> str:
        """Expand query terms to include related legal terms"""
        # Legal term expansions
        expansions = {
            'murder': 'murder killing homicide death sentence killed slain assassination',
            'case': 'case matter proceeding suit litigation',
            'bail': 'bail bond surety release',
            'appeal': 'appeal revision petition',
            'conviction': 'conviction sentence judgment verdict',
            'criminal': 'criminal offence crime',
            'civil': 'civil dispute matter',
            'constitutional': 'constitutional fundamental rights',
            'habeas': 'habeas corpus detention custody'
        }
        
        expanded_terms = []
        query_lower = query.lower()
        
        for term, expansion in expansions.items():
            if term in query_lower:
                expanded_terms.extend(expansion.split())
        
        # Add original terms
        expanded_terms.extend(query.split())
        
        # Remove duplicates and return
        return ' '.join(list(set(expanded_terms)))
    
    def _generate_lexical_snippets(self, case_id: int, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets from lexical text matches"""
        try:
            snippets = []
            query_terms = self._extract_query_terms(query)
            
            # Get document text for this case through CaseDocument relationship
            from apps.cases.models import CaseDocument
            case_documents = CaseDocument.objects.filter(case_id=case_id).values_list('document_id', flat=True)
            document_texts = DocumentText.objects.filter(
                document_id__in=case_documents,
                has_text=True
            ).order_by('page_number')
            
            for doc_text in document_texts:
                if len(snippets) >= max_snippets:
                    break
                
                text_content = doc_text.clean_text or doc_text.raw_text
                if not text_content:
                    continue
                
                # Find matches for each query term
                for term in query_terms:
                    if len(snippets) >= max_snippets:
                        break
                    
                    # Case-insensitive search
                    term_pattern = re.compile(re.escape(term), re.IGNORECASE)
                    matches = list(term_pattern.finditer(text_content))
                    
                    for match in matches:
                        if len(snippets) >= max_snippets:
                            break
                        
                        snippet = self._create_snippet_from_match(
                            text_content, match, doc_text.page_number, term, 'lexical'
                        )
                        
                        if snippet:
                            snippets.append(snippet)
            
            return snippets
            
        except Exception as e:
            logger.error(f"Error generating lexical snippets: {str(e)}")
            return []
    
    def _generate_semantic_snippets(self, case_id: int, query_info: Dict[str, Any], max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets from semantic chunks"""
        try:
            snippets = []
            
            # Get document chunks for this case
            chunks = DocumentChunk.objects.filter(
                case_id=case_id,
                is_embedded=True
            ).order_by('chunk_index')
            
            # Extract query terms for matching
            original_query = query_info.get('original_query', '')
            expanded_query = self._expand_query_terms(original_query)
            query_terms = self._extract_query_terms(expanded_query)
            
            # Strategy 1: Find chunks with exact query term matches
            for chunk in chunks:
                if len(snippets) >= max_snippets:
                    break
                
                chunk_text = chunk.chunk_text.lower()
                matched_terms = [term for term in query_terms if term.lower() in chunk_text]
                
                if matched_terms:
                    snippet = self._create_snippet_from_chunk(
                        chunk, matched_terms[0], 'semantic_exact_match'
                    )
                    if snippet:
                        snippet['relevance_score'] = 0.8  # High relevance for exact matches
                        snippets.append(snippet)
            
            # Strategy 2: If we have citations, prioritize chunks with those terms
            if len(snippets) < max_snippets and query_info.get('citations'):
                citation_terms = [citation['canonical'] for citation in query_info['citations']]
                
                for chunk in chunks:
                    if len(snippets) >= max_snippets:
                        break
                    
                    # Check if chunk contains citation terms
                    chunk_text = chunk.chunk_text.lower()
                    citation_matches = [term for term in citation_terms if term.lower() in chunk_text]
                    
                    if citation_matches:
                        snippet = self._create_snippet_from_chunk(
                            chunk, citation_matches[0], 'semantic_citation'
                        )
                        if snippet:
                            snippet['relevance_score'] = 0.7  # High relevance for citations
                            snippets.append(snippet)
            
            # Strategy 3: Add general semantic chunks if we still need more
            if len(snippets) < max_snippets:
                for chunk in chunks:
                    if len(snippets) >= max_snippets:
                        break
                    
                    # Skip chunks that are just metadata
                    if self._is_metadata_chunk(chunk.chunk_text):
                        continue
                    
                    snippet = self._create_snippet_from_chunk(
                        chunk, None, 'semantic_general'
                    )
                    if snippet:
                        snippet['relevance_score'] = 0.5  # Medium relevance for general content
                        snippets.append(snippet)
            
            return snippets
            
        except Exception as e:
            logger.error(f"Error generating semantic snippets: {str(e)}")
            return []
    
    def _is_metadata_chunk(self, chunk_text: str) -> bool:
        """Check if a chunk contains only metadata"""
        metadata_indicators = [
            'case metadata:', 'basic_info:', 'bench:', 'status:', 'sr_number:',
            'justice', 'court:', 'pending', 'decided', 'case number:', 'case title:'
        ]
        
        # If chunk is mostly metadata indicators, consider it metadata
        text_lower = chunk_text.lower()
        metadata_count = sum(1 for indicator in metadata_indicators if indicator in text_lower)
        
        # If more than 3 metadata indicators, likely metadata
        return metadata_count > 3
    
    def _generate_metadata_snippets(self, case_id: int, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets from case metadata"""
        try:
            snippets = []
            
            case = Case.objects.filter(id=case_id).first()
            if not case:
                return snippets
            
            query_terms = self._extract_query_terms(query)
            
            # Check case title
            if case.case_title:
                title_snippet = self._create_metadata_snippet(
                    case.case_title, 'case_title', query_terms, 'metadata_title'
                )
                if title_snippet:
                    snippets.append(title_snippet)
            
            # Check case number
            if case.case_number:
                number_snippet = self._create_metadata_snippet(
                    case.case_number, 'case_number', query_terms, 'metadata_number'
                )
                if number_snippet:
                    snippets.append(number_snippet)
            
            # Check bench information
            if case.bench:
                bench_snippet = self._create_metadata_snippet(
                    case.bench, 'bench', query_terms, 'metadata_bench'
                )
                if bench_snippet:
                    snippets.append(bench_snippet)
            
            return snippets[:max_snippets]
            
        except Exception as e:
            logger.error(f"Error generating metadata snippets: {str(e)}")
            return []
    
    def _create_snippet_from_match(self, 
                                  text: str, 
                                  match: re.Match, 
                                  page_number: int, 
                                  matched_term: str, 
                                  snippet_type: str) -> Optional[Dict[str, Any]]:
        """Create a snippet from a text match"""
        try:
            start_pos = match.start()
            end_pos = match.end()
            
            # Calculate context boundaries
            context_start = max(0, start_pos - (self.default_config['context_words'] * 5))  # Approximate word length
            context_end = min(len(text), end_pos + (self.default_config['context_words'] * 5))
            
            # Extract snippet text
            snippet_text = text[context_start:context_end]
            
            # Clean up snippet boundaries (try to start/end at word boundaries)
            snippet_text = self._clean_snippet_boundaries(snippet_text)
            
            # Skip if snippet is too short
            if len(snippet_text) < self.default_config['min_snippet_length']:
                return None
            
            # Truncate if too long
            if len(snippet_text) > self.default_config['max_snippet_length']:
                snippet_text = snippet_text[:self.default_config['max_snippet_length']] + "..."
            
            # Calculate relative positions within snippet
            relative_start = start_pos - context_start
            relative_end = end_pos - context_start
            
            # Highlight matched term if enabled
            if self.default_config['highlight_terms']:
                highlighted_text = self._highlight_term(snippet_text, matched_term, relative_start, relative_end)
            else:
                highlighted_text = snippet_text
            
            snippet = {
                'text': highlighted_text,
                'original_text': snippet_text,
                'snippet_type': snippet_type,
                'matched_term': matched_term,
                'page_number': page_number if self.default_config['include_page_numbers'] else None,
                'char_spans': {
                    'start_char': relative_start,
                    'end_char': relative_end,
                    'absolute_start': start_pos,
                    'absolute_end': end_pos
                },
                'relevance_score': self._calculate_snippet_relevance(snippet_type, matched_term, len(snippet_text)),
                'length': len(snippet_text)
            }
            
            return snippet
            
        except Exception as e:
            logger.error(f"Error creating snippet from match: {str(e)}")
            return None
    
    def _create_snippet_from_chunk(self, 
                                  chunk: DocumentChunk, 
                                  matched_term: str, 
                                  snippet_type: str) -> Optional[Dict[str, Any]]:
        """Create a snippet from a document chunk"""
        try:
            chunk_text = chunk.chunk_text
            
            # Skip if chunk is too short
            if len(chunk_text) < self.default_config['min_snippet_length']:
                return None
            
            # Extract meaningful content from chunk
            meaningful_text = self._extract_meaningful_content(chunk_text)
            
            # Truncate if too long
            if len(meaningful_text) > self.default_config['max_snippet_length']:
                # Try to find a good break point
                truncated_text = self._truncate_at_sentence_boundary(meaningful_text)
            else:
                truncated_text = meaningful_text
            
            snippet = {
                'text': truncated_text,
                'original_text': chunk_text,
                'snippet_type': snippet_type,
                'matched_term': matched_term or 'semantic_chunk',
                'page_number': chunk.page_number if self.default_config['include_page_numbers'] else None,
                'char_spans': {
                    'start_char': chunk.start_char,
                    'end_char': chunk.end_char,
                    'absolute_start': chunk.start_char,
                    'absolute_end': chunk.end_char
                },
                'relevance_score': self._calculate_snippet_relevance(snippet_type, matched_term, len(truncated_text)),
                'length': len(truncated_text)
            }
            
            return snippet
            
        except Exception as e:
            logger.error(f"Error creating snippet from chunk: {str(e)}")
            return None
    
    def _extract_meaningful_content(self, chunk_text: str) -> str:
        """Extract meaningful legal content from chunk text, removing document metadata"""
        try:
            # Remove common metadata patterns
            text = chunk_text
            
            # Remove document metadata
            metadata_patterns = [
                r'Document: [^.]*\.',
                r'Type: [^.]*\.',
                r'ORDER SHEET[^.]*\.',
                r'JUDGMENT SHEET[^.]*\.',
                r'DATE OF HEARING:[^.]*\.',
                r'====================[^.]*\.',
                r'=====[^.]*\.',
                r'Case Number: [^.]*\.',
                r'Case Title: [^.]*\.',
                r'Status: [^.]*\.',
                r'Bench: [^.]*\.',
                r'Case Metadata: [^.]*\.',
                r'basic_info: [^.]*\.',
                r'Justice [^.]*\.',
                r'Court: [^.]*\.',
            ]
            
            import re
            for pattern in metadata_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
            # Clean up extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # If we have substantial content left, return it
            if len(text) > 50:
                return text
            
            # Fallback: try to extract sentences
            sentences = chunk_text.split('. ')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 20:
                    continue
                
                # Skip metadata sentences
                if any(pattern in sentence for pattern in [
                    'Document:', 'Type:', 'ORDER SHEET', 'JUDGMENT SHEET',
                    'DATE OF HEARING:', '====================', '=====',
                    'Case Number:', 'Case Title:', 'Status:', 'Bench:',
                    'Case Metadata:', 'basic_info:', 'Justice', 'Court:'
                ]):
                    continue
                
                # Return the first meaningful sentence
                if len(sentence) > 30:
                    return sentence
            
            # If all else fails, return the original text truncated
            return chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
                
        except Exception as e:
            logger.error(f"Error extracting meaningful content: {str(e)}")
            return chunk_text
    
    def _create_metadata_snippet(self, 
                                text: str, 
                                field_name: str, 
                                query_terms: List[str], 
                                snippet_type: str) -> Optional[Dict[str, Any]]:
        """Create a snippet from metadata fields"""
        try:
            if not text:
                return None
            
            # Check if any query terms match this metadata
            matched_terms = []
            for term in query_terms:
                if term.lower() in text.lower():
                    matched_terms.append(term)
            
            if not matched_terms:
                return None
            
            # Use the best matching term
            best_term = max(matched_terms, key=lambda x: len(x))
            
            snippet = {
                'text': text,
                'original_text': text,
                'snippet_type': snippet_type,
                'matched_term': best_term,
                'page_number': None,
                'char_spans': {
                    'start_char': 0,
                    'end_char': len(text),
                    'absolute_start': 0,
                    'absolute_end': len(text)
                },
                'relevance_score': self._calculate_snippet_relevance(snippet_type, best_term, len(text)),
                'length': len(text),
                'metadata_field': field_name
            }
            
            return snippet
            
        except Exception as e:
            logger.error(f"Error creating metadata snippet: {str(e)}")
            return None
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from query"""
        try:
            # Remove common words and punctuation
            common_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were'}
            
            # Split and clean
            terms = re.findall(r'\b\w+\b', query.lower())
            
            # Filter out common words and short terms
            meaningful_terms = [term for term in terms if term not in common_words and len(term) > 2]
            
            return meaningful_terms
            
        except Exception as e:
            logger.error(f"Error extracting query terms: {str(e)}")
            return []
    
    def _clean_snippet_boundaries(self, text: str) -> str:
        """Clean snippet boundaries to start/end at word boundaries"""
        try:
            # Find first word boundary
            first_word_match = re.search(r'\b\w', text)
            if first_word_match:
                start_pos = first_word_match.start()
                text = text[start_pos:]
            
            # Find last word boundary
            last_word_match = re.search(r'\w\b', text)
            if last_word_match:
                end_pos = last_word_match.end()
                text = text[:end_pos]
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning snippet boundaries: {str(e)}")
            return text
    
    def _truncate_at_sentence_boundary(self, text: str) -> str:
        """Truncate text at sentence boundary"""
        try:
            if len(text) <= self.default_config['max_snippet_length']:
                return text
            
            # Find the last sentence boundary within max length
            truncated = text[:self.default_config['max_snippet_length']]
            
            # Look for sentence endings
            sentence_endings = ['.', '!', '?', '\n']
            last_sentence_end = -1
            
            for ending in sentence_endings:
                pos = truncated.rfind(ending)
                if pos > last_sentence_end:
                    last_sentence_end = pos
            
            if last_sentence_end > self.default_config['min_snippet_length']:
                # Found a good sentence boundary
                return truncated[:last_sentence_end + 1]
            else:
                # No good sentence boundary, try word boundary
                last_space = truncated.rfind(' ')
                if last_space > self.default_config['min_snippet_length']:
                    return truncated[:last_space] + "..."
                else:
                    return truncated + "..."
            
        except Exception as e:
            logger.error(f"Error truncating at sentence boundary: {str(e)}")
            return text[:self.default_config['max_snippet_length']] + "..."
    
    def _highlight_term(self, text: str, term: str, start_pos: int, end_pos: str) -> str:
        """Highlight the matched term in the snippet"""
        try:
            if not self.default_config['highlight_terms']:
                return text
            
            # Simple highlighting with ** markers
            highlighted = text[:start_pos] + f"**{text[start_pos:end_pos]}**" + text[end_pos:]
            
            return highlighted
            
        except Exception as e:
            logger.error(f"Error highlighting term: {str(e)}")
            return text
    
    def _calculate_snippet_relevance(self, snippet_type: str, matched_term: str, snippet_length: int) -> float:
        """Calculate relevance score for a snippet"""
        try:
            base_score = 0.0
            
            # Type-based scoring
            if snippet_type == 'lexical':
                base_score = 1.0  # Highest priority
            elif snippet_type == 'semantic_citation':
                base_score = 0.9
            elif snippet_type == 'semantic_general':
                base_score = 0.7
            elif snippet_type == 'metadata_title':
                base_score = 0.8
            elif snippet_type == 'metadata_number':
                base_score = 0.6
            elif snippet_type == 'metadata_bench':
                base_score = 0.5
            else:
                base_score = 0.5
            
            # Length-based adjustment
            if snippet_length < 150:
                length_factor = 0.8  # Prefer medium-length snippets
            elif snippet_length < 300:
                length_factor = 1.0
            else:
                length_factor = 0.9
            
            # Term specificity adjustment
            if matched_term and len(matched_term) > 5:
                term_factor = 1.0
            elif matched_term and len(matched_term) > 3:
                term_factor = 0.9
            else:
                term_factor = 0.7
            
            final_score = base_score * length_factor * term_factor
            
            return min(1.0, final_score)
            
        except Exception as e:
            logger.error(f"Error calculating snippet relevance: {str(e)}")
            return 0.5
