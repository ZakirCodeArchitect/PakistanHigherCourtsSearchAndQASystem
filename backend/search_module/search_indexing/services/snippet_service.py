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
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
    
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
            
            # Strategy 1: Generate snippets from lexical matches
            if self.default_config['prefer_lexical_matches']:
                lexical_snippets = self._generate_lexical_snippets(case_id, query, max_snippets)
                snippets.extend(lexical_snippets)
            
            # Strategy 2: Generate snippets from semantic chunks
            if len(snippets) < max_snippets:
                semantic_snippets = self._generate_semantic_snippets(case_id, query_info, max_snippets - len(snippets))
                snippets.extend(semantic_snippets)
            
            # Strategy 3: Generate snippets from case metadata
            if len(snippets) < max_snippets:
                metadata_snippets = self._generate_metadata_snippets(case_id, query, max_snippets - len(snippets))
                snippets.extend(metadata_snippets)
            
            # Sort snippets by relevance and limit
            sorted_snippets = sorted(snippets, key=lambda x: x['relevance_score'], reverse=True)
            return sorted_snippets[:max_snippets]
            
        except Exception as e:
            logger.error(f"Error generating snippets for case {case_id}: {str(e)}")
            return []
    
    def _generate_lexical_snippets(self, case_id: int, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets from lexical text matches"""
        try:
            snippets = []
            query_terms = self._extract_query_terms(query)
            
            # Get document text for this case
            document_texts = DocumentText.objects.filter(
                document__case_id=case_id,
                has_text=True
            ).order_by('page_number')
            
            for doc_text in document_texts:
                if len(snippets) >= max_snippets:
                    break
                
                text_content = doc_text.extracted_text
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
            
            # If we have citations, prioritize chunks with those terms
            if query_info.get('citations'):
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
                            snippets.append(snippet)
            
            # Add general semantic chunks if we still need more
            if len(snippets) < max_snippets:
                for chunk in chunks:
                    if len(snippets) >= max_snippets:
                        break
                    
                    snippet = self._create_snippet_from_chunk(
                        chunk, None, 'semantic_general'
                    )
                    if snippet:
                        snippets.append(snippet)
            
            return snippets
            
        except Exception as e:
            logger.error(f"Error generating semantic snippets: {str(e)}")
            return []
    
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
            # If the text is all on one line (common in chunks), split by sentences
            if '\n' not in chunk_text or len(chunk_text.split('\n')) == 1:
                # Split by sentences and find the first substantial legal content
                sentences = chunk_text.split('. ')
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # Skip metadata sentences
                    if any(pattern in sentence for pattern in [
                        'Document:', 'Type:', 'ORDER SHEET', 'JUDGMENT SHEET',
                        'DATE OF HEARING:', '====================', '====='
                    ]):
                        continue
                    
                    # Skip incomplete sentences that start with numbers or fragments
                    if sentence.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                        # Extract the content after the number
                        parts = sentence.split('.', 1)
                        if len(parts) > 1:
                            sentence = parts[1].strip()
                    
                    # Skip sentences that start with fragments
                    if sentence.startswith(('of ', 'and ', 'the ', 'in ', 'at ', 'on ', 'for ', 'with ', 'by ')):
                        continue
                    
                    # Look for substantial legal content that makes sense
                    if len(sentence) > 100 and any(word in sentence.lower() for word in [
                        'court', 'judge', 'petitioner', 'respondent', 'order', 'judgment', 
                        'law', 'legal', 'counsel', 'application', 'petition', 'appeal',
                        'proceedings', 'hearing', 'argument', 'submits', 'alleged'
                    ]):
                        # Ensure the sentence starts with a capital letter and makes sense
                        if sentence[0].isupper() and not sentence.startswith(('of ', 'and ', 'the ', 'in ', 'at ', 'on ', 'for ', 'with ', 'by ')):
                            return sentence + '.'
                
                # If no substantial legal content found, return the longest complete sentence
                complete_sentences = [s for s in sentences if len(s) > 50 and s[0].isupper() and not s.startswith(('of ', 'and ', 'the ', 'in ', 'at ', 'on ', 'for ', 'with ', 'by '))]
                if complete_sentences:
                    longest_sentence = max(complete_sentences, key=len)
                    return longest_sentence + '.'
                
                # Fallback: return original text if no good sentences found
                return chunk_text
            
            else:
                # Handle multi-line text
                lines = chunk_text.split('\n')
                meaningful_lines = []
                
                # Skip document metadata lines
                skip_patterns = [
                    'Document:', 'Type:', 'ORDER SHEET', 'JUDGMENT SHEET',
                    'Case Number:', 'Case Title:', 'Status:', 'Bench:',
                    'S. No. of order', 'Date of order', 'Order with signature'
                ]
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Skip lines that are mostly metadata
                    is_metadata = any(pattern in line for pattern in skip_patterns)
                    if is_metadata and len(line) < 100:  # Short metadata lines
                        continue
                    
                    # Keep lines with substantial legal content
                    if len(line) > 50:  # Substantial content
                        meaningful_lines.append(line)
                
                # If we have meaningful content, join it
                if meaningful_lines:
                    return ' '.join(meaningful_lines)
                else:
                    return chunk_text
                
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
