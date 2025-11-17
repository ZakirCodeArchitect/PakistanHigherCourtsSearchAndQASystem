"""
BM25 Indexing Service
Industry-standard BM25 algorithm for lexical search
"""

import os
import pickle
import logging
import re
import time
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25Okapi = None

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from ..models import SearchMetadata, IndexingLog

logger = logging.getLogger(__name__)


class BM25IndexingService:
    """
    BM25 indexing service for lexical search
    
    BM25 (Best Matching 25) is an industry-standard ranking function
    used by search engines to rank documents based on query terms.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize BM25 indexing service
        
        Args:
            config: Configuration dictionary with:
                - k1: Term frequency saturation parameter (default: 1.5)
                - b: Length normalization parameter (default: 0.75)
                - index_cache_dir: Directory for index persistence (default: 'bm25_indexes')
                - field_weights: Dictionary of field weights
        """
        self.config = config or {}
        
        # BM25 parameters
        self.k1 = self.config.get('k1', 1.5)  # Term frequency saturation
        self.b = self.config.get('b', 0.75)   # Length normalization
        
        # Field weights for multi-field search
        self.field_weights = self.config.get('field_weights', {
            'case_number_normalized': 3.0,    # Highest: Exact matches are very important
            'case_title_normalized': 2.0,      # High: Title is very descriptive
            'parties_normalized': 1.5,         # Medium-High: Parties are important
            'court_normalized': 1.0,           # Medium: Court is contextual
            'status_normalized': 0.5,          # Low: Status is less searchable
            'searchable_keywords': 1.2,        # Medium-High: Optimized keywords
        })
        
        # Index cache directory
        base_dir = Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else Path(__file__).parent.parent.parent.parent
        self.index_cache_dir = Path(self.config.get('index_cache_dir', base_dir / 'bm25_indexes'))
        self.index_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory indexes
        self.bm25_indexes = {}  # field_name -> BM25Okapi instance
        self.document_texts = {}  # field_name -> List[str] (tokenized documents)
        self.case_id_mapping = []  # index -> case_id
        self.index_built = False
        self.last_index_update = None
        
        # Legal abbreviations for normalization
        self.legal_abbreviations = {
            'Cr.P.C.': 'CrPC',
            'CrPC': 'CrPC',
            'P.P.C.': 'PPC',
            'PPC': 'PPC',
            'C.P.C.': 'CPC',
            'CPC': 'CPC',
            'vs': 'VS',
            'VS': 'VS',
            'pet': 'Petition',
            'app': 'Appeal',
            'rev': 'Revision',
            'misc': 'Miscellaneous',
        }
        
        # Case number abbreviations that should be kept as single tokens
        self.case_abbreviations = {
            'T.A.': 'TA',
            'C.O.': 'CO',
            'C.O.S.': 'COS',
            'F.A.O.': 'FAO',
            'R.S.A.': 'RSA',
            'R.F.A.': 'RFA',
            'I.T.R.': 'ITR',
            'P.S.L.A.': 'PSLA',
            'J.S.A': 'JSA',
            'C.S.R.': 'CSR',
            'W.P.': 'WP',
            'M.R.': 'MR',
            'C.M.': 'CM',
            'P.L.A.': 'PLA',
            'L.A.': 'LA',
            'T.R.': 'TR',
            'E.F.A.': 'EFA',
            'Cr.Obj.': 'CrObj',
            'Crl.': 'Crl',
            'Crl. Misc.': 'CrlMisc',
            'Crl. Appeal': 'CrlAppeal',
            'Crl. Rev.': 'CrlRev',
            'Crl. Org.': 'CrlOrg',
            'Misc. Pet.': 'MiscPet',
            'Misc.': 'Misc',
            'Pet.': 'Pet',
            'Appeal': 'Appeal',
            'Ref.': 'Ref',
            'Cust. Ref.': 'CustRef',
            'Cust.': 'Cust',
            'Inst No.': 'InstNo',
            'Inst': 'Inst',
            'Enfrc.': 'Enfrc',
            'Enfrc. Pet.': 'EnfrcPet',
            'Ex. Pet.': 'ExPet',
            'Ex.': 'Ex',
            'FERA': 'FERA',
            'OGRA Application': 'OGRAApp',
            'SECP Appeal': 'SECPAppeal',
            'Objection Case': 'ObjectionCase',
            'Office Objection': 'OfficeObjection',
        }
        
        # Case number patterns for normalization
        self.case_number_patterns = {
            r'\bMisc\.?\s*Pet\.?': 'MiscPet',
            r'\bMiscellaneous\.?\s*Petition\.?': 'MiscPet',
            r'\bCrl\.?\s*Appeal': 'CrlAppeal',
            r'\bCriminal\.?\s*Appeal': 'CrlAppeal',
            r'\bT\.?\s*A\.?': 'TA',
            r'\bTransfer\.?\s*Application': 'TA',
            r'\bC\.?\s*O\.?': 'CO',
            r'\bCivil\.?\s*Original': 'CO',
            r'\bF\.?\s*A\.?\s*O\.?': 'FAO',
            r'\bFirst\.?\s*Appeal\.?\s*Order': 'FAO',
        }
        
        if not BM25_AVAILABLE:
            logger.warning("rank-bm25 not available. Install with: pip install rank-bm25")
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for indexing with case number normalization"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # First, normalize case number patterns (before other normalization)
        for pattern, replacement in self.case_number_patterns.items():
            text = re.sub(pattern, replacement.lower(), text, flags=re.IGNORECASE)
        
        # Normalize case abbreviations (keep as single tokens)
        for abbrev, normalized in self.case_abbreviations.items():
            # Match with optional periods and spaces
            pattern = r'\b' + re.escape(abbrev.replace('.', r'\.?')) + r'\b'
            text = re.sub(pattern, normalized.lower(), text, flags=re.IGNORECASE)
        
        # Normalize legal abbreviations
        for abbrev, full in self.legal_abbreviations.items():
            text = re.sub(r'\b' + re.escape(abbrev.lower()) + r'\b', full.lower(), text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms with improved abbreviation handling
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Normalize first (this handles abbreviations)
        normalized = self.normalize_text(text)
        
        # Extract case numbers (patterns like "1/2024", "3/2025")
        case_numbers = re.findall(r'\b\d{1,4}/\d{4}\b', normalized)
        
        # Extract abbreviations that were normalized (like "ta", "co", "fao")
        # These are now single tokens after normalization
        
        # Split on whitespace and punctuation, keep alphanumeric tokens
        tokens = re.findall(r'\b\w+\b', normalized)
        
        # Add case numbers as separate tokens
        for case_num in case_numbers:
            # Add full case number
            tokens.append(case_num)
            # Also add parts separately for partial matching
            parts = case_num.split('/')
            if len(parts) == 2:
                tokens.append(parts[0])  # Number part
                tokens.append(parts[1])  # Year part
        
        # Filter out very short tokens (less than 2 characters) except for numbers and abbreviations
        # Keep single-letter abbreviations that are common (like "a", "b" in case numbers)
        filtered_tokens = []
        for t in tokens:
            if len(t) >= 2 or t.isdigit() or t in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']:
                filtered_tokens.append(t)
        
        return filtered_tokens
    
    def build_index(self, force: bool = False) -> Dict[str, Any]:
        """
        Build BM25 index from SearchMetadata
        
        Args:
            force: Force rebuild even if index exists
            
        Returns:
            Dictionary with build statistics
        """
        if not BM25_AVAILABLE:
            return {
                'index_built': False,
                'error': 'rank-bm25 not available. Install with: pip install rank-bm25'
            }
        
        start_time = time.time()
        stats = {
            'index_built': False,
            'total_documents': 0,
            'total_fields': 0,
            'processing_time': 0,
            'errors': []
        }
        
        try:
            logger.info("Building BM25 index...")
            
            # Check if index already exists and is recent
            if not force and self._load_cached_index():
                logger.info("Loaded existing BM25 index from cache")
                stats['index_built'] = True
                stats['total_documents'] = len(self.case_id_mapping)
                stats['total_fields'] = len(self.bm25_indexes)
                return stats
            
            # Get all indexed metadata
            metadata_list = list(SearchMetadata.objects.filter(is_indexed=True).select_related())
            
            if not metadata_list:
                logger.warning("No indexed metadata found. Run keyword indexing first.")
                stats['errors'].append("No indexed metadata found")
                return stats
            
            stats['total_documents'] = len(metadata_list)
            
            # Prepare documents for each field
            field_documents = defaultdict(list)
            self.case_id_mapping = []
            
            for metadata in metadata_list:
                case_id = metadata.case_id
                self.case_id_mapping.append(case_id)
                
                # Process each searchable field
                for field_name, weight in self.field_weights.items():
                    field_value = getattr(metadata, field_name, None)
                    
                    if field_value:
                        # Handle different field types
                        if isinstance(field_value, list):
                            # JSONField (e.g., searchable_keywords)
                            text = ' '.join(str(v) for v in field_value)
                        else:
                            text = str(field_value)
                        
                        # Tokenize the text
                        tokens = self.tokenize(text)
                        
                        # Store tokens for this field
                        field_documents[field_name].append(tokens)
                    else:
                        # Empty field - add empty list
                        field_documents[field_name].append([])
            
            # Build BM25 index for each field
            self.bm25_indexes = {}
            self.document_texts = {}
            
            for field_name, documents in field_documents.items():
                if documents:
                    try:
                        # Create BM25 index for this field
                        bm25 = BM25Okapi(documents, k1=self.k1, b=self.b)
                        self.bm25_indexes[field_name] = bm25
                        self.document_texts[field_name] = documents
                        stats['total_fields'] += 1
                        logger.info(f"Built BM25 index for field '{field_name}': {len(documents)} documents")
                    except Exception as e:
                        error_msg = f"Error building BM25 index for field '{field_name}': {str(e)}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
            
            # Mark as built
            self.index_built = True
            self.last_index_update = timezone.now()
            
            # Save to cache
            self._save_cached_index()
            
            stats['processing_time'] = time.time() - start_time
            stats['index_built'] = True
            
            logger.info(f"BM25 index built successfully: {stats['total_documents']} documents, "
                       f"{stats['total_fields']} fields in {stats['processing_time']:.2f}s")
            
            # Create indexing log
            try:
                IndexingLog.objects.create(
                    operation_type='build',
                    index_type='bm25',
                    documents_processed=stats['total_documents'],
                    processing_time=stats['processing_time'],
                    is_successful=stats['index_built'],
                    error_message='; '.join(stats['errors']) if stats['errors'] else '',
                    completed_at=timezone.now()
                )
            except Exception as e:
                logger.warning(f"Could not create indexing log: {str(e)}")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error building BM25 index: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            stats['processing_time'] = time.time() - start_time
            return stats
    
    def search(self, query: str, filters: Dict[str, Any] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search using BM25 with exact match boosting
        
        Args:
            query: Search query string
            filters: Optional filters (court, status, dates)
            top_k: Number of results to return
            
        Returns:
            List of search results with BM25 scores
        """
        if not BM25_AVAILABLE:
            logger.error("BM25 not available")
            return []
        
        if not self.index_built:
            logger.warning("BM25 index not built. Building now...")
            build_stats = self.build_index()
            if not build_stats['index_built']:
                logger.error("Failed to build BM25 index")
                return []
        
        try:
            # First, check for exact case number matches (highest priority)
            exact_case_matches = self._find_exact_case_number_matches(query, filters)
            
            # Tokenize query
            query_tokens = self.tokenize(query)
            
            if not query_tokens:
                logger.warning(f"Query '{query}' produced no tokens after tokenization")
                # Still return exact matches if found
                if exact_case_matches:
                    return exact_case_matches
                return []
            
            # Get candidate case IDs based on filters
            candidate_indices = None
            if filters:
                candidate_indices = self._get_filtered_indices(filters)
                if not candidate_indices:
                    # Still return exact matches if found
                    if exact_case_matches:
                        return exact_case_matches
                    return []
            
            # Search across all fields with weighted scores
            field_scores = defaultdict(lambda: defaultdict(float))
            
            for field_name, bm25_index in self.bm25_indexes.items():
                try:
                    # Get BM25 scores for this field
                    scores = bm25_index.get_scores(query_tokens)
                    
                    # Apply field weight
                    weight = self.field_weights.get(field_name, 1.0)
                    
                    # Store weighted scores
                    for idx, score in enumerate(scores):
                        if candidate_indices is None or idx in candidate_indices:
                            field_scores[idx][field_name] = score * weight
                            
                except Exception as e:
                    logger.warning(f"Error searching field '{field_name}': {str(e)}")
                    continue
            
            # Combine scores from all fields with exact match boosting
            combined_scores = []
            normalized_query = self.normalize_text(query)
            
            # Combine scores from all fields first
            combined_scores = []
            for idx in range(len(self.case_id_mapping)):
                if candidate_indices is not None and idx not in candidate_indices:
                    continue
                
                # Sum scores from all fields
                total_score = sum(field_scores[idx].values())
                
                if total_score > 0:
                    combined_scores.append({
                        'index': idx,
                        'case_id': self.case_id_mapping[idx],
                        'score': total_score,
                        'field_scores': dict(field_scores[idx])
                    })
            
            # Sort by score to get top candidates for exact match checking
            combined_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Only check exact matches for top candidates (to avoid performance issues)
            top_candidates = combined_scores[:top_k * 3]  # Check top 3x results for exact matches
            candidate_case_ids = [r['case_id'] for r in top_candidates]
            
            # Pre-fetch metadata only for top candidates
            metadata_dict = {}
            if candidate_case_ids:
                metadata_objects = SearchMetadata.objects.filter(
                    case_id__in=candidate_case_ids,
                    is_indexed=True
                ).only('case_id', 'case_number_normalized', 'case_title_normalized')
                metadata_dict = {m.case_id: m for m in metadata_objects}
            
            # Apply exact match boosting
            normalized_query = self.normalize_text(query)
            query_lower = query.lower().strip()
            
            for result in combined_scores:
                case_id = result['case_id']
                metadata = metadata_dict.get(case_id)
                
                if metadata:
                    # Boost for exact case number match (highest priority)
                    if metadata.case_number_normalized:
                        case_num_normalized = self.normalize_text(metadata.case_number_normalized)
                        case_num_lower = metadata.case_number_normalized.lower().strip()
                        
                        # Exact match (case-insensitive)
                        if query_lower == case_num_lower:
                            result['score'] *= 10.0  # Very strong boost for exact match
                        # Partial match (query is substring of case number or vice versa)
                        elif query_lower in case_num_lower or case_num_lower in query_lower:
                            result['score'] *= 5.0  # Strong boost for partial match
                        # Normalized match
                        elif normalized_query in case_num_normalized or case_num_normalized in normalized_query:
                            result['score'] *= 4.0  # Strong boost for normalized match
                        # Token-based match
                        elif any(token in case_num_normalized for token in query_tokens if len(token) > 2):
                            result['score'] *= 2.0  # Medium boost for token match
                    
                    # Boost for exact case title match
                    if metadata.case_title_normalized:
                        title_normalized = self.normalize_text(metadata.case_title_normalized)
                        title_lower = metadata.case_title_normalized.lower().strip()
                        
                        # Exact match
                        if query_lower == title_lower:
                            result['score'] *= 8.0
                        # Partial match
                        elif query_lower in title_lower or title_lower in query_lower:
                            result['score'] *= 3.0
                        # Normalized match
                        elif normalized_query in title_normalized or title_normalized in normalized_query:
                            result['score'] *= 2.5
                
            # Re-sort after boosting
            combined_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Get top-k results
            top_results = combined_scores[:top_k * 2]  # Get more for metadata retrieval
            
            # Fetch full metadata for results (if not already fetched)
            case_ids = [r['case_id'] for r in top_results]
            if not metadata_dict or set(case_ids) - set(metadata_dict.keys()):
                # Fetch missing metadata
                missing_ids = set(case_ids) - set(metadata_dict.keys()) if metadata_dict else set(case_ids)
                if missing_ids:
                    missing_metadata = SearchMetadata.objects.filter(
                        case_id__in=missing_ids,
                        is_indexed=True
                    )
                    for m in missing_metadata:
                        metadata_dict[m.case_id] = m
            
            # Format results
            results = []
            exact_match_case_ids = {r['case_id'] for r in exact_case_matches} if exact_case_matches else set()
            
            # Add exact matches first (highest priority)
            if exact_case_matches:
                results.extend(exact_case_matches)
            
            # Add BM25 results (excluding exact matches to avoid duplicates)
            for result in top_results[:top_k]:
                case_id = result['case_id']
                if case_id in exact_match_case_ids:
                    continue  # Skip if already in exact matches
                
                metadata = metadata_dict.get(case_id)
                
                if metadata:
                    results.append({
                        'case_id': case_id,
                        'case_number': metadata.case_number_normalized,
                        'case_title': metadata.case_title_normalized,
                        'parties': metadata.parties_normalized,
                        'court': metadata.court_normalized,
                        'status': metadata.status_normalized,
                        'institution_date': metadata.institution_date,
                        'hearing_date': metadata.hearing_date,
                        'disposal_date': metadata.disposal_date,
                        'rank': result['score'],
                        'bm25_score': result['score'],
                        'field_scores': result['field_scores']
                    })
            
            # Limit to top_k
            results = results[:top_k]
            
            logger.info(f"BM25 search completed: {len(results)} results for query '{query}' ({len(exact_case_matches)} exact matches)")
            return results
            
        except Exception as e:
            logger.error(f"Error in BM25 search: {str(e)}")
            return []
    
    def _find_exact_case_number_matches(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Find exact case number matches before BM25 search
        
        Args:
            query: Search query
            filters: Optional filters
            
        Returns:
            List of exact match results with high scores
        """
        try:
            # Normalize query for matching
            normalized_query = self.normalize_text(query)
            query_lower = query.lower().strip()
            
            # Build queryset
            queryset = SearchMetadata.objects.filter(is_indexed=True)
            
            # Apply filters
            if filters:
                if 'court' in filters:
                    queryset = queryset.filter(court_normalized__icontains=filters['court'])
                if 'status' in filters:
                    queryset = queryset.filter(status_normalized__icontains=filters['status'])
                if 'date_from' in filters:
                    queryset = queryset.filter(institution_date__gte=filters['date_from'])
                if 'date_to' in filters:
                    queryset = queryset.filter(institution_date__lte=filters['date_to'])
            
            # Check for exact matches in case_number_normalized
            exact_matches = []
            
            # Exact match (case-insensitive)
            exact_cases = queryset.filter(
                case_number_normalized__iexact=query
            )[:5]
            
            for metadata in exact_cases:
                exact_matches.append({
                    'case_id': metadata.case_id,
                    'case_number': metadata.case_number_normalized,
                    'case_title': metadata.case_title_normalized,
                    'parties': metadata.parties_normalized,
                    'court': metadata.court_normalized,
                    'status': metadata.status_normalized,
                    'institution_date': metadata.institution_date,
                    'hearing_date': metadata.hearing_date,
                    'disposal_date': metadata.disposal_date,
                    'rank': 1000.0,  # Very high score for exact match
                    'bm25_score': 1000.0,
                    'field_scores': {'exact_match': 1000.0}
                })
            
            # If no exact match, check normalized match
            if not exact_matches:
                normalized_cases = queryset.filter(
                    case_number_normalized__icontains=normalized_query
                )[:3]
                
                for metadata in normalized_cases:
                    case_num_normalized = self.normalize_text(metadata.case_number_normalized)
                    # Check if normalized query matches normalized case number
                    if normalized_query == case_num_normalized or normalized_query in case_num_normalized:
                        exact_matches.append({
                            'case_id': metadata.case_id,
                            'case_number': metadata.case_number_normalized,
                            'case_title': metadata.case_title_normalized,
                            'parties': metadata.parties_normalized,
                            'court': metadata.court_normalized,
                            'status': metadata.status_normalized,
                            'institution_date': metadata.institution_date,
                            'hearing_date': metadata.hearing_date,
                            'disposal_date': metadata.disposal_date,
                            'rank': 800.0,  # High score for normalized match
                            'bm25_score': 800.0,
                            'field_scores': {'normalized_match': 800.0}
                        })
            
            return exact_matches
            
        except Exception as e:
            logger.warning(f"Error finding exact case number matches: {str(e)}")
            return []
    
    def _get_filtered_indices(self, filters: Dict[str, Any]) -> Optional[set]:
        """
        Get document indices that match filters
        
        Args:
            filters: Filter dictionary
            
        Returns:
            Set of document indices, or None if no filtering needed
        """
        try:
            # Get all metadata that matches filters
            queryset = SearchMetadata.objects.filter(is_indexed=True)
            
            if 'court' in filters:
                queryset = queryset.filter(court_normalized__icontains=filters['court'])
            if 'status' in filters:
                queryset = queryset.filter(status_normalized__icontains=filters['status'])
            if 'date_from' in filters:
                queryset = queryset.filter(institution_date__gte=filters['date_from'])
            if 'date_to' in filters:
                queryset = queryset.filter(institution_date__lte=filters['date_to'])
            
            # Get case IDs
            filtered_case_ids = set(queryset.values_list('case_id', flat=True))
            
            # Map to indices
            filtered_indices = {
                idx for idx, case_id in enumerate(self.case_id_mapping)
                if case_id in filtered_case_ids
            }
            
            return filtered_indices if filtered_indices else None
            
        except Exception as e:
            logger.error(f"Error getting filtered indices: {str(e)}")
            return None
    
    def _save_cached_index(self):
        """Save BM25 index to disk for persistence"""
        try:
            cache_file = self.index_cache_dir / 'bm25_index.pkl'
            
            # Note: BM25Okapi objects are not directly pickleable
            # We need to save the document texts and rebuild on load
            cache_data = {
                'document_texts': self.document_texts,
                'case_id_mapping': self.case_id_mapping,
                'field_weights': self.field_weights,
                'k1': self.k1,
                'b': self.b,
                'last_update': self.last_index_update.isoformat() if self.last_index_update else None
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.info(f"Saved BM25 index cache to {cache_file}")
            
        except Exception as e:
            logger.warning(f"Could not save BM25 index cache: {str(e)}")
    
    def _load_cached_index(self) -> bool:
        """Load BM25 index from disk cache"""
        try:
            cache_file = self.index_cache_dir / 'bm25_index.pkl'
            
            if not cache_file.exists():
                return False
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Rebuild BM25 indexes from cached document texts
            self.document_texts = cache_data.get('document_texts', {})
            self.case_id_mapping = cache_data.get('case_id_mapping', [])
            self.field_weights = cache_data.get('field_weights', self.field_weights)
            self.k1 = cache_data.get('k1', self.k1)
            self.b = cache_data.get('b', self.b)
            
            # Rebuild BM25 indexes
            self.bm25_indexes = {}
            for field_name, documents in self.document_texts.items():
                if documents:
                    bm25 = BM25Okapi(documents, k1=self.k1, b=self.b)
                    self.bm25_indexes[field_name] = bm25
            
            # Restore last update time
            last_update_str = cache_data.get('last_update')
            if last_update_str:
                try:
                    from dateutil.parser import parse
                    self.last_index_update = parse(last_update_str)
                except ImportError:
                    # Fallback to datetime.fromisoformat if dateutil not available
                    from datetime import datetime
                    try:
                        self.last_index_update = datetime.fromisoformat(last_update_str)
                    except:
                        self.last_index_update = None
            
            self.index_built = True
            
            logger.info(f"Loaded BM25 index cache: {len(self.case_id_mapping)} documents, "
                       f"{len(self.bm25_indexes)} fields")
            return True
            
        except Exception as e:
            logger.warning(f"Could not load BM25 index cache: {str(e)}")
            return False
    
    def update_index(self, case_ids: List[int]) -> Dict[str, Any]:
        """
        Incrementally update index with new cases
        
        Args:
            case_ids: List of case IDs to add/update
            
        Returns:
            Update statistics
        """
        # For now, rebuild the entire index
        # TODO: Implement true incremental updates
        logger.info(f"Incremental update requested for {len(case_ids)} cases. Rebuilding index...")
        return self.build_index(force=True)
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index"""
        return {
            'index_built': self.index_built,
            'total_documents': len(self.case_id_mapping),
            'total_fields': len(self.bm25_indexes),
            'field_names': list(self.bm25_indexes.keys()),
            'last_update': self.last_index_update.isoformat() if self.last_index_update else None,
            'k1': self.k1,
            'b': self.b,
            'field_weights': self.field_weights
        }

