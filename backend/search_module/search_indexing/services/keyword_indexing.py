"""
Keyword Indexing Service
Handles lexical indexing using PostgreSQL full-text search and vocabulary
"""

import re
import hashlib
import logging
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
import time

from django.db import connection
from django.utils import timezone
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, F

from ..models import KeywordIndex, FacetIndex, SearchMetadata, IndexingLog
from .enhanced_metadata_service import EnhancedMetadataService

logger = logging.getLogger(__name__)


class KeywordIndexingService:
    """Service for creating and managing keyword indexes"""
    
    def __init__(self):
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
        
        # TIER 1 INTEGRATION: Initialize enhanced metadata service
        self.enhanced_metadata_service = EnhancedMetadataService()
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for indexing"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Normalize legal abbreviations
        for abbrev, full in self.legal_abbreviations.items():
            text = re.sub(r'\b' + re.escape(abbrev.lower()) + r'\b', full.lower(), text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def create_search_metadata(self, case_id_or_case, case_data: Dict = None) -> Optional[SearchMetadata]:
        """Create search metadata for a case"""
        try:
            # Handle both Case object and case_id + case_data
            if case_data is None:
                # Assume case_id_or_case is a Case object
                from apps.cases.models import Case
                if isinstance(case_id_or_case, Case):
                    case_obj = case_id_or_case
                    case_id = case_obj.id
                    # Convert Case object to case_data dict
                    case_data = {
                        'case_number': case_obj.case_number or '',
                        'case_title': case_obj.case_title or '',
                        'court': getattr(case_obj.court, 'name', '') if case_obj.court else '',
                        'status': case_obj.status or '',
                        'institution_date': case_obj.institution_date,
                        'hearing_date': getattr(case_obj, 'hearing_date', None),
                    }
                else:
                    raise ValueError("Invalid arguments: expected Case object or case_id + case_data")
            else:
                # Traditional case_id + case_data approach
                case_id = case_id_or_case
                case_obj = None
                try:
                    from apps.cases.models import Case
                    case_obj = Case.objects.get(id=case_id)
                except Case.DoesNotExist:
                    logger.warning(f"Case {case_id} not found for metadata extraction")
            
            # Normalize case data
            case_number_normalized = self.normalize_text(case_data.get('case_number', ''))
            case_title_normalized = self.normalize_text(case_data.get('case_title', ''))
            # Fix: Use court name instead of bench
            court_name = case_data.get('court_name', '') or case_data.get('court', '') or case_data.get('bench', '')
            court_normalized = self.normalize_text(court_name)
            status_normalized = self.normalize_text(case_data.get('status', ''))
            
            # Get parties information
            parties = case_data.get('parties', [])
            parties_normalized = " | ".join(parties) if parties else ""
            
            # Parse dates
            institution_date = None
            hearing_date = None
            disposal_date = None
            
            try:
                if case_data.get('institution_date'):
                    institution_date = datetime.strptime(case_data['institution_date'], '%d-%m-%Y').date()
            except:
                pass
            
            try:
                if case_data.get('hearing_date'):
                    hearing_date = datetime.strptime(case_data['hearing_date'], '%d-%m-%Y').date()
            except:
                pass
            
            try:
                if case_data.get('disposal_date'):
                    disposal_date = datetime.strptime(case_data['disposal_date'], '%d-%m-%Y').date()
            except:
                pass
            
            # TIER 1 INTEGRATION: Extract enhanced metadata from case
            from apps.cases.models import Case
            try:
                case_obj = Case.objects.get(id=case_id)
                enhanced_metadata = self.enhanced_metadata_service.extract_enhanced_metadata(case_obj)
            except Case.DoesNotExist:
                logger.warning(f"Case {case_id} not found for enhanced metadata extraction")
                enhanced_metadata = {}
            except Exception as e:
                logger.error(f"Error extracting enhanced metadata for case {case_id}: {str(e)}")
                enhanced_metadata = {}
            
            # Calculate content hashes
            content_text = f"{case_number_normalized} {case_title_normalized} {parties_normalized} {court_normalized} {status_normalized}"
            content_hash = hashlib.sha256(content_text.encode()).hexdigest()
            
            # Get text content for text hash
            text_content = case_data.get('pdf_content', '')
            text_hash = hashlib.sha256(text_content.encode()).hexdigest()
            
            # Metadata hash
            metadata_text = f"{case_number_normalized}|{case_title_normalized}|{parties_normalized}|{court_normalized}|{status_normalized}"
            metadata_hash = hashlib.sha256(metadata_text.encode()).hexdigest()
            
            # Enhanced metadata hash
            enhanced_metadata_text = str(enhanced_metadata)
            enhanced_metadata_hash = hashlib.sha256(enhanced_metadata_text.encode()).hexdigest()
            
            # Count chunks and terms
            from ..models import DocumentChunk
            total_chunks = DocumentChunk.objects.filter(case_id=case_id).count()
            
            # Calculate total terms from basic case information if no documents
            if total_chunks == 0:
                # Use basic case information as searchable content
                basic_content = f"{case_number_normalized} {case_title_normalized} {parties_normalized} {court_normalized}"
                total_terms = len(basic_content.split())
                
                # Create a virtual document chunk for basic case information
                from ..models import DocumentChunk
                virtual_chunk, created = DocumentChunk.objects.get_or_create(
                    case_id=case_id,
                    chunk_index=0,
                    defaults={
                        'content': basic_content,
                        'token_count': total_terms,
                        'chunk_type': 'basic_info',
                        'metadata': {
                            'source': 'case_basic_info',
                            'case_number': case_number_normalized,
                            'case_title': case_title_normalized,
                            'parties': parties_normalized,
                            'court': court_normalized
                        }
                    }
                )
                if created:
                    total_chunks = 1
            else:
                total_terms = 0  # Will be calculated when vocabulary is available
            
            avg_chunk_length = 0
            if total_chunks > 0:
                avg_chunk_length = sum(chunk.token_count for chunk in DocumentChunk.objects.filter(case_id=case_id)) / total_chunks
            
            # Create or update search metadata with enhanced fields
            search_metadata, created = SearchMetadata.objects.get_or_create(
                case_id=case_id,
                defaults={
                    'case_number_normalized': case_number_normalized,
                    'case_title_normalized': case_title_normalized,
                    'parties_normalized': parties_normalized,
                    'court_normalized': court_normalized,
                    'status_normalized': status_normalized,
                    'institution_date': institution_date,
                    'hearing_date': hearing_date,
                    'disposal_date': disposal_date,
                    'content_hash': content_hash,
                    'text_hash': text_hash,
                    'metadata_hash': metadata_hash,
                    'enhanced_metadata_hash': enhanced_metadata_hash,
                    'total_chunks': total_chunks,
                    'total_terms': total_terms,
                    'avg_chunk_length': avg_chunk_length,
                    'is_indexed': False,
                    # TIER 1 ENHANCEMENT: Enhanced metadata fields
                    'legal_entities': enhanced_metadata.get('legal_entities', []),
                    'legal_concepts': enhanced_metadata.get('legal_concepts', []),
                    'case_classification': enhanced_metadata.get('case_type_classification', {}),
                    'subject_matter': enhanced_metadata.get('subject_matter', []),
                    'parties_intelligence': enhanced_metadata.get('parties_intelligence', {}),
                    'procedural_stage': enhanced_metadata.get('procedural_stage', ''),
                    'case_timeline': enhanced_metadata.get('case_timeline', []),
                    'content_richness_score': enhanced_metadata.get('content_richness_score', 0.0),
                    'data_completeness_score': enhanced_metadata.get('data_completeness_score', 0.0),
                    'authority_score': self._calculate_authority_score(court_normalized),
                    'precedential_value': self._calculate_precedential_value(case_data),
                    'searchable_keywords': enhanced_metadata.get('searchable_keywords', []),
                    'semantic_tags': enhanced_metadata.get('semantic_tags', []),
                    'relevance_boosters': enhanced_metadata.get('relevance_boosters', []),
                    'enhanced_metadata_extracted': True
                }
            )
            
            if not created:
                # Update existing metadata
                search_metadata.case_number_normalized = case_number_normalized
                search_metadata.case_title_normalized = case_title_normalized
                search_metadata.parties_normalized = parties_normalized
                search_metadata.court_normalized = court_normalized
                search_metadata.status_normalized = status_normalized
                search_metadata.institution_date = institution_date
                search_metadata.hearing_date = hearing_date
                search_metadata.disposal_date = disposal_date
                search_metadata.content_hash = content_hash
                search_metadata.text_hash = text_hash
                search_metadata.metadata_hash = metadata_hash
                search_metadata.total_chunks = total_chunks
                search_metadata.total_terms = total_terms
                search_metadata.avg_chunk_length = avg_chunk_length
                search_metadata.updated_at = timezone.now()
                search_metadata.save()
            
            return search_metadata
            
        except Exception as e:
            logger.error(f"Error creating search metadata for case {case_id}: {str(e)}")
            return None
    
    def _calculate_authority_score(self, court_normalized: str) -> float:
        """Calculate authority score based on court hierarchy"""
        court_lower = court_normalized.lower()
        
        if 'supreme court' in court_lower:
            return 1.0
        elif 'high court' in court_lower:
            return 0.8
        elif 'district court' in court_lower or 'sessions court' in court_lower:
            return 0.6
        elif 'magistrate' in court_lower:
            return 0.4
        else:
            return 0.5  # Default score
    
    def _calculate_precedential_value(self, case_data: Dict) -> float:
        """Calculate precedential value based on case characteristics"""
        score = 0.0
        
        # Status-based scoring
        status = case_data.get('status', '').lower()
        if 'decided' in status:
            score += 0.4
        elif 'pending' in status:
            score += 0.1
        
        # Case type-based scoring
        case_number = case_data.get('case_number', '').lower()
        if 'appeal' in case_number:
            score += 0.3
        elif 'revision' in case_number:
            score += 0.25
        elif 'writ' in case_number:
            score += 0.35
        else:
            score += 0.1
        
        # Court-based scoring (already handled in authority_score)
        court = case_data.get('court_name', '').lower()
        if 'supreme court' in court:
            score += 0.3
        elif 'high court' in court:
            score += 0.2
        elif 'district court' in court:
            score += 0.1
        
        return min(score, 1.0)
    
    def build_facet_index(self, facet_type: str) -> Dict[str, any]:
        """Build facet index for vocabulary-driven search"""
        stats = {
            'terms_processed': 0,
            'mappings_created': 0,
            'index_built': False,
            'errors': []
        }
        
        try:
            # Get real terms from database
            from apps.cases.models import Term, TermOccurrence
            
            terms = Term.objects.filter(type=facet_type)
            total_terms = terms.count()
            
            if total_terms == 0:
                logger.warning(f"No terms found for facet type: {facet_type}")
                stats['index_built'] = True  # Mark as successful even if no terms
                return stats
            
            # Create term mappings
            term_mappings = {}
            boost_config = {}
            
            for term in terms:
                # Get case IDs where this term appears
                case_ids = TermOccurrence.objects.filter(term=term).values_list('case_id', flat=True).distinct()
                
                if case_ids:
                    term_mappings[term.canonical] = list(case_ids)
                    boost_config[term.canonical] = {
                        'occurrence_count': term.occurrence_count,
                        'case_count': len(case_ids),
                        'boost_factor': min(2.0, 1.0 + (len(case_ids) / 100.0))
                    }
                    
                    stats['terms_processed'] += 1
                    stats['mappings_created'] += len(case_ids)
            
            # Create or update facet index
            facet_index, created = FacetIndex.objects.get_or_create(
                index_name=f"facet_{facet_type}",
                defaults={
                    'facet_type': facet_type,
                    'term_mappings': term_mappings,
                    'boost_config': boost_config,
                    'total_terms': stats['terms_processed'],
                    'total_mappings': stats['mappings_created'],
                    'is_built': True,
                    'version': '1.0'
                }
            )
            
            if not created:
                # Update existing index
                facet_index.term_mappings = term_mappings
                facet_index.boost_config = boost_config
                facet_index.total_terms = stats['terms_processed']
                facet_index.total_mappings = stats['mappings_created']
                facet_index.is_built = True
                facet_index.updated_at = timezone.now()
                facet_index.save()
            
            stats['index_built'] = True
            logger.info(f"Built facet index for {facet_type}: {stats['terms_processed']} terms, {stats['mappings_created']} mappings")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error building facet index for {facet_type}: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
    
    def build_keyword_index(self, force: bool = False) -> Dict[str, any]:
        """Build keyword index using PostgreSQL full-text search"""
        start_time = time.time()
        stats = {
            'cases_processed': 0,
            'metadata_created': 0,
            'facet_indexes_built': 0,
            'index_built': False,
            'errors': []
        }
        
        try:
            # Get real cases from database
            from apps.cases.models import UnifiedCaseView, PartiesDetailData
            
            if force:
                # Process all cases
                cases_to_process = UnifiedCaseView.objects.all()
            else:
                # Only process cases that don't have search metadata
                existing_case_ids = set(SearchMetadata.objects.values_list('case_id', flat=True))
                cases_to_process = UnifiedCaseView.objects.exclude(case_id__in=existing_case_ids)
            
            total_cases = cases_to_process.count()
            logger.info(f"Processing {total_cases} cases for keyword indexing")
            
            if total_cases == 0:
                logger.info("No cases to process for keyword indexing")
                stats['index_built'] = True  # Mark as successful even if no cases
                return stats
            
            # Process each case
            for i, unified_view in enumerate(cases_to_process):
                try:
                    logger.info(f"Processing case {i+1}/{total_cases}: {unified_view.case.case_number}")
                    
                    # Prepare case data
                    case_data = {
                        'id': unified_view.case.id,
                        'case_number': unified_view.case.case_number or '',
                        'case_title': unified_view.case.case_title or '',
                        'status': unified_view.case.status or '',
                        'bench': unified_view.case.bench or '',
                        'institution_date': unified_view.case.institution_date,
                        'hearing_date': unified_view.case.hearing_date,
                        'disposal_date': None,
                        'pdf_content': ''
                    }
                    
                    # Get disposal date from case details
                    try:
                        case_detail = unified_view.case.case_detail.first()
                        if case_detail and hasattr(case_detail, 'case_disposal_date') and case_detail.case_disposal_date:
                            case_data['disposal_date'] = case_detail.case_disposal_date
                    except Exception as e:
                        logger.warning(f"Could not get case detail for case {unified_view.case.case_number}: {str(e)}")
                        case_data['disposal_date'] = None
                    
                    # Get parties information
                    parties = []
                    for party in unified_view.case.parties_detail_data.all():
                        if party.party_name:
                            parties.append(party.party_name)
                    case_data['parties'] = parties
                    
                    # Extract PDF content
                    if unified_view.pdf_content_summary and 'complete_pdf_content' in unified_view.pdf_content_summary:
                        case_data['pdf_content'] = unified_view.pdf_content_summary['complete_pdf_content']
                    elif unified_view.pdf_content_summary and 'cleaned_pdf_content' in unified_view.pdf_content_summary:
                        case_data['pdf_content'] = unified_view.pdf_content_summary['cleaned_pdf_content']
                    
                    # Create search metadata
                    search_metadata = self.create_search_metadata(case_data['id'], case_data)
                    if search_metadata:
                        search_metadata.is_indexed = True
                        search_metadata.last_indexed = timezone.now()
                        search_metadata.save()
                        
                        stats['cases_processed'] += 1
                        stats['metadata_created'] += 1
                    
                except Exception as e:
                    error_msg = f"Error processing case {unified_view.case.case_number}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Build facet indexes for different term types
            facet_types = ['section', 'judge', 'court', 'party', 'advocate']
            
            for facet_type in facet_types:
                try:
                    facet_stats = self.build_facet_index(facet_type)
                    if facet_stats['index_built']:
                        stats['facet_indexes_built'] += 1
                    stats['errors'].extend(facet_stats['errors'])
                except Exception as e:
                    error_msg = f"Error building facet index for {facet_type}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Create keyword index record
            keyword_index, created = KeywordIndex.objects.get_or_create(
                index_name="legal_cases_keyword",
                defaults={
                    'index_type': 'postgresql',
                    'analyzer_config': {
                        'normalize_abbreviations': True,
                        'case_sensitive': False,
                        'multilingual': True
                    },
                    'weight_config': {
                        'title_weight': 3.0,
                        'parties_weight': 2.0,
                        'body_weight': 1.0
                    },
                    'total_documents': stats['cases_processed'],
                    'total_terms': 0,  # Will be updated when vocabulary is available
                    'is_built': True,
                    'version': '1.0'
                }
            )
            
            if not created:
                # Update existing index
                keyword_index.total_documents = stats['cases_processed']
                keyword_index.is_built = True
                keyword_index.updated_at = timezone.now()
                keyword_index.save()
            
            stats['index_built'] = True
            
            # Log processing time
            processing_time = time.time() - start_time
            stats['processing_time'] = processing_time
            
            # Create indexing log
            IndexingLog.objects.create(
                operation_type='build',
                index_type='keyword',
                documents_processed=stats['cases_processed'],
                chunks_processed=0,
                vectors_created=0,
                processing_time=processing_time,
                is_successful=stats['index_built'],
                error_message='; '.join(stats['errors']) if stats['errors'] else '',
                config_version='1.0',
                model_version='',
                completed_at=timezone.now()
            )
            
            logger.info(f"Keyword indexing completed: {stats['cases_processed']} cases, {stats['facet_indexes_built']} facet indexes")
            return stats
            
        except Exception as e:
            error_msg = f"Error in keyword indexing: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
    
    def _build_search_query(self, query: str, filters: Dict[str, Any] = None) -> Q:
        """Build optimized database query"""
        # Base search query
        search_query = Q()
        
        # Add text search conditions
        if query:
            # Use multiple search strategies for better coverage
            search_query |= Q(case_number_normalized__icontains=query)
            search_query |= Q(case_title_normalized__icontains=query)
            search_query |= Q(parties_normalized__icontains=query)
            search_query |= Q(court_normalized__icontains=query)
            search_query |= Q(status_normalized__icontains=query)
        
        # Add filters
        if filters:
            for key, value in filters.items():
                if value:
                    if key == 'court':
                        search_query &= Q(court_normalized__icontains=value)
                    elif key == 'status':
                        search_query &= Q(status_normalized__icontains=value)
                    elif key == 'year':
                        search_query &= Q(institution_date__year=value)
        
        return search_query
    
    def _rank_results(self, results: List[Any], query: str, top_k: int) -> List[Dict[str, Any]]:
        """Rank results based on relevance and boost factors"""
        ranked_results = []
        
        for result in results:
            score = 0.0
            
            # Boost exact matches
            if query.lower() in result.case_number_normalized.lower():
                score += 10.0
            if query.lower() in result.case_title_normalized.lower():
                score += 8.0
            if query.lower() in result.parties_normalized.lower():
                score += 6.0
            if query.lower() in result.court_normalized.lower():
                score += 5.0
            
            # Boost recent cases
            if result.institution_date:
                score += 1.0
            
            # Boost high-priority courts
            if result.court_normalized:
                if 'supreme' in result.court_normalized.lower():
                    score += 2.0
                elif 'high' in result.court_normalized.lower():
                    score += 1.5
            
            ranked_results.append({
                'case_id': result.case_id,
                'case_number': result.case_number_normalized,
                'case_title': result.case_title_normalized,
                'court': result.court_normalized,
                'status': result.status_normalized,
                'parties': result.parties_normalized,
                'institution_date': result.institution_date,
                'hearing_date': result.disposal_date,  # Map disposal_date to hearing_date for consistency
                'rank': score
            })
        
        # Sort by score and return top results
        ranked_results.sort(key=lambda x: x['rank'], reverse=True)
        return ranked_results[:top_k]
    
    def search(self, query: str, filters: Dict[str, any] = None, top_k: int = 10) -> List[Dict[str, any]]:
        """Search using keyword indexing"""
        try:
            # Normalize query
            normalized_query = self.normalize_text(query)
            
            # Build search query
            search_vector = (
                SearchVector('case_number_normalized', weight='A') +
                SearchVector('case_title_normalized', weight='B') +
                SearchVector('parties_normalized', weight='C') +
                SearchVector('court_normalized', weight='D')
            )
            
            search_query = SearchQuery(normalized_query, config='english')
            
            # Apply filters
            queryset = SearchMetadata.objects.filter(is_indexed=True)
            
            if filters:
                if 'court' in filters:
                    queryset = queryset.filter(court_normalized__icontains=filters['court'])
                if 'status' in filters:
                    queryset = queryset.filter(status_normalized__icontains=filters['status'])
                if 'date_from' in filters:
                    queryset = queryset.filter(institution_date__gte=filters['date_from'])
                if 'date_to' in filters:
                    queryset = queryset.filter(institution_date__lte=filters['date_to'])
            
            # FIXED: Disable broken PostgreSQL full-text search and use reliable icontains search
            # PostgreSQL full-text search is returning incorrect results (same results for all queries)
            # Use simple icontains search which works correctly
            results = queryset.filter(
                Q(case_number_normalized__icontains=normalized_query) |
                Q(case_title_normalized__icontains=normalized_query) |
                Q(parties_normalized__icontains=normalized_query) |
                Q(court_normalized__icontains=normalized_query) |
                Q(status_normalized__icontains=normalized_query)  # FIXED: Added status field search
            )[:top_k * 2]  # Get more results for better scoring
            
            # Add a dummy rank field for compatibility
            for result in results:
                result.rank = 1.0  # Give all results a high rank since they actually match
            
            # FIXED: Handle PostgreSQL's very small ranks properly
            # PostgreSQL ranks can be very small (like 1e-20), but they're still meaningful
            # Only try partial matching if we have NO results at all
            if not results:
                # Try partial matching by splitting query into terms
                query_terms = normalized_query.split()
                partial_results = []
                
                for term in query_terms:
                    if len(term) >= 2:  # Only search for terms with 2+ characters
                        # First try metadata matching - this is more reliable
                        term_results = queryset.filter(
                            Q(case_number_normalized__icontains=term) |
                            Q(case_title_normalized__icontains=term) |
                            Q(parties_normalized__icontains=term) |
                            Q(status_normalized__icontains=term)  # FIXED: Added status field to fallback search
                        )[:top_k]
                        
                        for result in term_results:
                            # Calculate a simple relevance score
                            score = 0
                            if term.lower() in result.case_number_normalized.lower():
                                score += 10  # High score for case number match
                            if term.lower() in result.case_title_normalized.lower():
                                score += 5   # Medium score for title match
                            if term.lower() in result.parties_normalized.lower():
                                score += 3   # Lower score for parties match
                            if term.lower() in result.status_normalized.lower():
                                score += 4   # Medium-high score for status match
                            
                            if score > 0:
                                partial_results.append({
                                    'result': result,
                                    'score': score,
                                    'matched_term': term
                                })
                        
                        # FIXED: Disable document chunk search for single-term queries to prevent irrelevant results
                        # Document chunk search should only be used for multi-term queries where we need to find
                        # cases that contain multiple terms in their content
                        if len(query_terms) > 1 and len(partial_results) == 0:  # Only for multi-term queries with no metadata results
                            from ..models import DocumentChunk
                            content_matches = DocumentChunk.objects.filter(
                                chunk_text__icontains=term,
                                is_embedded=True
                            ).values('case_id').distinct()[:top_k]
                            
                            for match in content_matches:
                                case_id = match['case_id']
                                # Get the SearchMetadata for this case
                                try:
                                    case_metadata = queryset.filter(case_id=case_id).first()
                                    if case_metadata:
                                        # FIXED: Only add if the case metadata actually contains the term
                                        # This prevents adding cases that only have the term in document content
                                        case_contains_term = (
                                            term.lower() in case_metadata.case_number_normalized.lower() or
                                            term.lower() in case_metadata.case_title_normalized.lower() or
                                            term.lower() in case_metadata.parties_normalized.lower()
                                        )
                                        
                                        if case_contains_term:
                                            # Calculate content relevance score
                                            content_score = 2  # Base score for content match
                                            
                                            # Check if this case is already in partial_results
                                            existing_result = next((item for item in partial_results if item['result'].case_id == case_id), None)
                                            if existing_result:
                                                # Boost existing score
                                                existing_result['score'] += content_score
                                            else:
                                                # Add new result
                                                partial_results.append({
                                                    'result': case_metadata,
                                                    'score': content_score,
                                                    'matched_term': term
                                                })
                                except:
                                    continue
                
                # Sort by score and take top results
                partial_results.sort(key=lambda x: x['score'], reverse=True)
                
                # Create a mapping of case_id to score for easy lookup
                score_mapping = {item['result'].case_id: item['score'] for item in partial_results}
                
                results = [item['result'] for item in partial_results[:top_k]]
                
                # Add rank field using actual calculated scores
                for result in results:
                    result.rank = score_mapping.get(result.case_id, 0.1) / 10.0  # Normalize scores to reasonable range
            
            # Format results
            search_results = []
            for result in results:
                search_results.append({
                    'rank': result.rank,
                    'case_id': result.case_id,
                    'case_number': result.case_number_normalized,
                    'case_title': result.case_title_normalized,
                    'court': result.court_normalized,
                    'status': result.status_normalized,
                    'parties': result.parties_normalized,
                    'institution_date': result.institution_date,
                    'hearing_date': result.disposal_date  # Map disposal_date to hearing_date for consistency
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            return []
    
    def search_by_facet(self, facet_type: str, term: str, top_k: int = 10) -> List[Dict[str, any]]:
        """Search using facet index"""
        try:
            # Get facet index
            facet_index = FacetIndex.objects.filter(
                index_name=f"facet_{facet_type}",
                is_active=True,
                is_built=True
            ).first()
            
            if not facet_index:
                logger.error(f"No active facet index found for {facet_type}")
                return []
            
            # Get case IDs for the term
            case_ids = facet_index.term_mappings.get(term, [])
            
            if not case_ids:
                return []
            
            # Get search metadata for these cases
            search_metadata = SearchMetadata.objects.filter(case_id__in=case_ids)
            
            # Format results
            results = []
            for metadata in search_metadata:
                results.append({
                    'case_id': metadata.case_id,
                    'case_number': metadata.case_number_normalized,
                    'case_title': metadata.case_title_normalized,
                    'status': metadata.status_normalized,
                    'court': metadata.court_normalized,
                    'facet_type': facet_type,
                    'facet_term': term
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in facet search: {str(e)}")
            return []
