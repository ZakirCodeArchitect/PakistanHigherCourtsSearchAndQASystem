"""
Hybrid Indexing Service
Combines vector and keyword indexing for comprehensive search
    """

import logging
import time
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from django.utils import timezone
from django.db import transaction
from apps.cases.models import CaseSearchProfile
from django.conf import settings

from ..models import IndexingConfig, IndexingLog, SearchMetadata
from .vector_indexing import VectorIndexingService
try:
    from .pinecone_indexing import PineconeIndexingService
    PINECONE_AVAILABLE = True
except ImportError:
    PineconeIndexingService = None
    PINECONE_AVAILABLE = False
from .keyword_indexing import KeywordIndexingService
from .precision_optimizer import PrecisionOptimizerService
from .query_expansion import QueryExpansionService
from .legal_semantic_matcher import LegalSemanticMatcher
from .advanced_reranker import AdvancedReranker
try:
    from .learned_reranker import LearnedReranker
except Exception:  # pragma: no cover - safe guard if optional deps missing
    LearnedReranker = None  # type: ignore

logger = logging.getLogger(__name__)


class HybridIndexingService:
    """Hybrid indexing service combining vector and keyword search"""
    
    def __init__(self, use_pinecone: bool = False, config: Dict[str, Any] = None):
        self.config = config or {}
        self.use_pinecone = use_pinecone
        
        # Initialize vector service
        if use_pinecone and PINECONE_AVAILABLE and PineconeIndexingService:
            try:
                self.vector_service = PineconeIndexingService()
                logger.info("Initialized Pinecone vector service")
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone, falling back to FAISS: {str(e)}")
                self.vector_service = VectorIndexingService()
        else:
            if use_pinecone and not PINECONE_AVAILABLE:
                logger.info("Pinecone not available, using FAISS vector service")
            self.vector_service = VectorIndexingService()
        
        # Initialize keyword service
        self.keyword_service = KeywordIndexingService()
        
        # Initialize precision optimizer
        self.precision_optimizer = PrecisionOptimizerService(config)
        
        # Initialize advanced components
        self.query_expander = QueryExpansionService()
        self.semantic_matcher = LegalSemanticMatcher()
        self.advanced_reranker = AdvancedReranker(config)
        self.learned_reranker = None

        model_path = getattr(settings, "LEARNED_RERANKER_MODEL_PATH", None)
        if LearnedReranker and model_path:
            try:
                self.learned_reranker = LearnedReranker(model_path, config)
                logger.info("Learned reranker initialized from %s", model_path)
            except Exception as exc:
                logger.warning("Failed to initialize learned reranker: %s", exc)
                self.learned_reranker = None
        elif model_path:
            logger.warning("Learned reranker model configured but sentence-transformers is unavailable.")
        else:
            logger.info("No learned reranker model configured; skipping learned reranking stage.")
        
        logger.info("Hybrid indexing service initialized")
    
    def _load_config(self) -> Dict:
        """Load indexing configuration"""
        try:
            config = IndexingConfig.objects.filter(is_active=True).first()
            if config:
                return config.config
        except Exception as e:
            logger.warning(f"Could not load indexing config: {str(e)}")
        
        # Default configuration
        return {
            'chunk_size': 512,
            'chunk_overlap': 50,
            'embedding_model': 'all-mpnet-base-v2',
            'vector_weight': 0.6,
            'keyword_weight': 0.4,
            'facet_boost': 1.5,
            'max_results': 100,
            'min_similarity': 0.3
        }
    
    def build_hybrid_index(self, force: bool = False, vector_only: bool = False, keyword_only: bool = False) -> Dict[str, any]:
        """Build hybrid index combining vector and keyword indexing"""
        start_time = time.time()
        stats = {
            'vector_indexed': False,
            'keyword_indexed': False,
            'hybrid_indexed': False,
            'total_cases': 0,
            'total_chunks': 0,
            'total_vectors': 0,
            'total_metadata': 0,
            'processing_time': 0,
            'errors': []
        }
        
        try:
            logger.info("Starting hybrid index building...")
            
            # Build vector index (unless keyword_only is specified)
            if not keyword_only:
                try:
                    if self.use_pinecone and PINECONE_AVAILABLE and PineconeIndexingService:
                        logger.info("Building Pinecone vector index...")
                        vector_stats = self.vector_service.build_pinecone_index(force=force)
                    else:
                        logger.info("Building FAISS vector index...")
                        vector_stats = self.vector_service.build_vector_index(force=force)
                    
                    if vector_stats['index_built']:
                        stats['vector_indexed'] = True
                        stats['total_cases'] = vector_stats.get('cases_processed', 0)
                        stats['total_chunks'] = vector_stats.get('chunks_created', 0)
                        stats['total_vectors'] = vector_stats.get('vectors_created', 0)
                        logger.info(f"Vector indexing completed: {stats['total_chunks']} chunks, {stats['total_vectors']} vectors")
                    else:
                        stats['errors'].extend(vector_stats.get('errors', []))
                        
                except Exception as e:
                    error_msg = f"Error in vector indexing: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Build keyword index (unless vector_only is specified)
            if not vector_only:
                try:
                    logger.info("Building keyword index...")
                    keyword_stats = self.keyword_service.build_keyword_index(force=force)
                    
                    if keyword_stats['index_built']:
                        stats['keyword_indexed'] = True
                        stats['total_metadata'] = keyword_stats.get('metadata_created', 0)
                        logger.info(f"Keyword indexing completed: {stats['total_metadata']} metadata records")
                    else:
                        stats['errors'].extend(keyword_stats.get('errors', []))
                        
                except Exception as e:
                    error_msg = f"Error in keyword indexing: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Mark as hybrid indexed if both components succeeded
            if stats['vector_indexed'] and stats['keyword_indexed']:
                stats['hybrid_indexed'] = True
            elif (vector_only and stats['vector_indexed']) or (keyword_only and stats['keyword_indexed']):
                stats['hybrid_indexed'] = True
            
            # Calculate processing time
            stats['processing_time'] = time.time() - start_time
            
            # Create indexing log
            IndexingLog.objects.create(
                operation_type='build',
                index_type='hybrid',
                documents_processed=stats['total_cases'],
                chunks_processed=stats['total_chunks'],
                vectors_created=stats['total_vectors'],
                processing_time=stats['processing_time'],
                is_successful=stats['hybrid_indexed'],
                error_message='; '.join(stats['errors']) if stats['errors'] else '',
                config_version=self.config.get('version', '1.0'),
                model_version=self.config.get('embedding_model', ''),
                completed_at=timezone.now()
            )
            
            if stats['hybrid_indexed']:
                logger.info(f"Hybrid indexing completed successfully in {stats['processing_time']:.2f} seconds")
            else:
                logger.error(f"Hybrid indexing failed: {'; '.join(stats['errors'])}")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error in hybrid indexing: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
    
    def hybrid_search(self, query: str, filters: Dict[str, any] = None, top_k: int = 10, enable_advanced_features: bool = True) -> List[Dict[str, any]]:
        """Perform hybrid search combining vector and keyword results with exact matching boost - OPTIMIZED VERSION"""
        try:
            logger.info(f"Performing hybrid search for: {query} (advanced: {enable_advanced_features})")
            
            # Step 1: Query expansion and analysis (if advanced features enabled)
            query_analysis = None
            expanded_query_info = None
            if enable_advanced_features:
                expanded_query_info = self.query_expander.enhance_query_with_legal_knowledge(query)
                query_analysis = expanded_query_info['query_analysis']
                logger.info(f"Query type detected: {query_analysis.get('type', 'general')}")
            
            # OPTIMIZATION: Adaptive fetch size based on query complexity
            if query_analysis and query_analysis.get('query_complexity') == 'high':
                fetch_multiplier = 3  # More results for complex queries
            else:
                fetch_multiplier = min(2, max(1, 20 // top_k))  # Standard multiplier
            fetch_size = top_k * fetch_multiplier
            
            # Check for exact case number match first (highest priority)
            exact_case_match = self._find_exact_case_match(query)
            
            # OPTIMIZATION: Fetch results in parallel or with reduced size
            # Get vector search results
            vector_results = self.vector_service.search(query, top_k=fetch_size)
            
            # Get keyword search results
            keyword_results = self.keyword_service.search(query, filters=filters, top_k=fetch_size)
            
            # OPTIMIZATION: Early return if we have enough exact matches
            if exact_case_match and len(vector_results) == 0 and len(keyword_results) == 0:
                # If we have an exact match but no other results, return just the exact match
                return [{
                    'case_id': exact_case_match['case_id'],
                    'case_number': exact_case_match['case_number'],
                    'case_title': exact_case_match['case_title'],
                    'court': exact_case_match['court'],
                    'status': exact_case_match['status'],
                    'institution_date': exact_case_match.get('institution_date', ''),
                    'hearing_date': exact_case_match.get('hearing_date', ''),
                    'vector_score': 0,
                    'keyword_score': 0,
                    'final_score': exact_case_match['exact_score'],
                    'exact_match': True
                }]
            
            # Combine and rerank results
            combined_results = self._combine_and_rerank(
                vector_results, 
                keyword_results, 
                query, 
                top_k,
                exact_case_match
            )
            
            # Apply precision optimization for better relevance
            optimized_results = self.precision_optimizer.optimize_search_results(
                combined_results, 
                query, 
                search_mode='hybrid', 
                filters=filters
            )
            
            # Apply advanced re-ranking (if enabled)
            if enable_advanced_features and len(optimized_results) > 1:
                final_results = self.advanced_reranker.rerank_results(
                    optimized_results,
                    query,
                    query_analysis=query_analysis
                )
                logger.info(f"Advanced re-ranking applied: {len(optimized_results)} -> {len(final_results)} results")
            else:
                final_results = optimized_results

            if (
                enable_advanced_features
                and self.learned_reranker
                and final_results
                and len(final_results) > 1
            ):
                final_results = self.learned_reranker.rerank_results(
                    query,
                    final_results,
                    query_analysis=query_analysis,
                    top_k=top_k
                )
                logger.info("Learned reranker applied to %d results", len(final_results))
            
            # Limit to requested top_k
            final_results = final_results[:top_k]
            
            logger.info(f"Hybrid search completed: {len(combined_results)} -> {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return []
    
    def _find_exact_case_match(self, query: str) -> Optional[Dict]:
        """Find exact case number match for highest priority ranking - OPTIMIZED VERSION"""
        try:
            from apps.cases.models import Case
            
            # Clean the query for exact matching
            clean_query = query.strip().upper()
            
            # OPTIMIZATION: Use a single optimized query instead of multiple queries
            # This reduces database round trips significantly
            
            # Build a more efficient query using Q objects for OR conditions
            from django.db.models import Q
            
            # Create a single query that handles both exact and partial matches
            query_conditions = Q(case_number__iexact=clean_query)
            
            # Add partial match conditions only if query has spaces
            if ' ' in clean_query:
                query_parts = clean_query.split()
                if len(query_parts) >= 2:
                    # Use a more efficient approach: check if case number contains the first part
                    # and then filter in Python for exact matches (faster than complex DB queries)
                    query_conditions |= Q(case_number__icontains=query_parts[0])
            
            # Execute single optimized query with select_related to avoid N+1 queries
            potential_matches = Case.objects.filter(query_conditions).select_related('court')[:5]
            
            if not potential_matches:
                return None
            
            # Find the best match in Python (faster than complex DB queries)
            best_match = None
            best_score = 0
            
            for case in potential_matches:
                case_number_upper = case.case_number.upper()
                score = 0
                
                # Exact match gets highest score
                if case_number_upper == clean_query:
                    score = 1.0
                # Partial match with all parts gets high score
                elif ' ' in clean_query:
                    query_parts = clean_query.split()
                    case_parts = case_number_upper.split()
                    if all(part in case_parts for part in query_parts):
                        score = 0.9
                    # Partial match with first part gets medium score
                    elif query_parts[0] in case_parts:
                        score = 0.7
                
                if score > best_score:
                    best_score = score
                    best_match = case
            
            if best_match and best_score > 0:
                return {
                    'case_id': best_match.id,
                    'case_number': best_match.case_number,
                    'case_title': best_match.case_title,
                    'court': best_match.court.name if best_match.court else '',
                    'status': getattr(best_match, 'status', ''),
                    'institution_date': getattr(best_match, 'institution_date', ''),
                    'hearing_date': getattr(best_match, 'hearing_date', ''),
                    'exact_match': True,
                    'exact_score': best_score
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding exact case match: {str(e)}")
            return None
    
    def _combine_and_rerank(self, vector_results: List[Dict], keyword_results: List[Dict], 
                           query: str, top_k: int, exact_case_match: Optional[Dict] = None) -> List[Dict]:
        """Combine and rerank vector and keyword search results"""
        try:
            # Create case ID to result mapping
            case_results = {}
            
            # Process vector results
            for result in vector_results:
                case_id = result['case_id']
                if case_id not in case_results:
                    case_results[case_id] = {
                        'case_id': case_id,
                        'vector_score': result.get('similarity', 0),
                        'keyword_score': 0,
                        'combined_score': 0,
                        'result_data': result
                    }
                else:
                    case_results[case_id]['vector_score'] = max(
                        case_results[case_id]['vector_score'], 
                        result.get('similarity', 0)
                    )
                    # Merge date fields from vector results
                    if result.get('institution_date'):
                        case_results[case_id]['result_data']['institution_date'] = result['institution_date']
                    if result.get('hearing_date'):
                        case_results[case_id]['result_data']['hearing_date'] = result['hearing_date']
            
            # Process keyword results
            for result in keyword_results:
                case_id = result['case_id']
                if case_id not in case_results:
                    case_results[case_id] = {
                        'case_id': case_id,
                        'vector_score': 0,
                        'keyword_score': result.get('rank', 0),
                        'combined_score': 0,
                        'result_data': result
                    }
                else:
                    case_results[case_id]['keyword_score'] = max(
                        case_results[case_id]['keyword_score'], 
                        result.get('rank', 0)
                    )
                    # Merge date fields from keyword results
                    if result.get('institution_date'):
                        case_results[case_id]['result_data']['institution_date'] = result['institution_date']
                    if result.get('hearing_date'):
                        case_results[case_id]['result_data']['hearing_date'] = result['hearing_date']
            
            # Calculate combined scores
            vector_weight = self.config.get('vector_weight', 0.6)
            keyword_weight = self.config.get('keyword_weight', 0.4)
            
            for case_id, result in case_results.items():
                # Normalize scores to 0-1 range
                normalized_vector = min(1.0, result['vector_score'])
                
                # IMPROVED: Better keyword score normalization
                # Handle very small PostgreSQL ranks and convert to meaningful scores
                keyword_score = result['keyword_score']
                if keyword_score > 0:
                    # For PostgreSQL ranks, use logarithmic scaling to make small ranks meaningful
                    if keyword_score < 0.001:
                        # Very small ranks get a base score
                        normalized_keyword = 0.3 + (keyword_score * 100)  # Scale up small ranks
                    else:
                        # Normal ranks get standard normalization
                        normalized_keyword = min(1.0, keyword_score)
                else:
                    # If keyword score is 0 but case was found, give it a small boost
                    normalized_keyword = 0.1 if case_id in [r['case_id'] for r in keyword_results] else 0.0
                
                # Calculate weighted combined score
                result['combined_score'] = (
                    normalized_vector * vector_weight + 
                    normalized_keyword * keyword_weight
                )
            
            # Add exact match boost if found
            if exact_case_match:
                case_id = exact_case_match['case_id']
                if case_id in case_results:
                    case_results[case_id]['exact_match'] = True
                    case_results[case_id]['exact_score'] = exact_case_match['exact_score']
                    case_results[case_id]['combined_score'] = (
                        case_results[case_id]['combined_score'] * 1.5 + # Apply a boost factor
                        case_results[case_id]['exact_score'] * 2.0 # Add a higher boost for exact matches
                    )
            
            # Sort by combined score and return top results
            sorted_results = sorted(
                case_results.values(), 
                key=lambda x: x['combined_score'], 
                reverse=True
            )[:top_k]
            
            # Format final results
            final_results = []
            for i, result in enumerate(sorted_results):
                final_result = {
                    'rank': i + 1,
                    'case_id': result['case_id'],
                    'combined_score': result['combined_score'],
                    'vector_score': result['vector_score'],
                    'keyword_score': result['keyword_score'],
                    'search_type': 'hybrid',
                    'exact_match': result.get('exact_match', False),
                    'result_data': result['result_data'],
                }
                
                # Merge result data
                result_data = result['result_data']
                final_result.update({
                    'case_number': result_data.get('case_number', ''),
                    'case_title': result_data.get('case_title', ''),
                    'court': result_data.get('court', ''),
                    'status': result_data.get('status', ''),
                    'parties': result_data.get('parties', ''),
                    'institution_date': result_data.get('institution_date'),
                    'hearing_date': result_data.get('hearing_date') or result_data.get('disposal_date')
                })
                
                final_results.append(final_result)
            
            # Attach search profile metadata for downstream ranking
            case_ids = [res['case_id'] for res in final_results]
            if case_ids:
                profiles = CaseSearchProfile.objects.filter(case_id__in=case_ids).values(
                    'case_id',
                    'clean_case_title',
                    'party_tokens',
                    'subject_tags',
                    'keyword_highlights',
                    'case_number_tokens',
                    'section_tags'
                )
                profile_map = {p['case_id']: p for p in profiles}
                for res in final_results:
                    profile = profile_map.get(res['case_id'])
                    if not profile:
                        continue
                    case_profile = {
                        'clean_case_title': profile.get('clean_case_title') or '',
                        'party_tokens': profile.get('party_tokens') or [],
                        'subject_tags': profile.get('subject_tags') or [],
                        'keyword_highlights': profile.get('keyword_highlights') or [],
                        'case_number_tokens': profile.get('case_number_tokens') or [],
                        'section_tags': profile.get('section_tags') or [],
                    }
                    res['case_profile'] = case_profile
                    # Ensure result_data reflects the profile as well
                    res['result_data']['case_profile'] = case_profile
                    if not res.get('case_title') and case_profile['clean_case_title']:
                        res['case_title'] = case_profile['clean_case_title']
                    if case_profile['case_number_tokens']:
                        res['case_number_tokens'] = case_profile['case_number_tokens']
                    if case_profile['section_tags']:
                        res['section_tags'] = case_profile['section_tags']
                    if case_profile['party_tokens']:
                        res['party_tokens'] = case_profile['party_tokens']
                    if case_profile['subject_tags']:
                        res['subject_tags'] = case_profile['subject_tags']
            
            # Force exact matches to the very top
            final_results.sort(key=lambda r: (1 if r.get('exact_match') else 0, r.get('combined_score', 0)), reverse=True)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error combining and reranking results: {str(e)}")
            return []
    
    def search_by_facet(self, facet_type: str, term: str, top_k: int = 10) -> List[Dict[str, any]]:
        """Search using facet index"""
        try:
            logger.info(f"Performing facet search: {facet_type} = {term}")
            
            # Get facet search results
            facet_results = self.keyword_service.search_by_facet(facet_type, term)
            
            # Apply boost factor
            facet_boost = self.config.get('facet_boost', 1.5)
            
            for result in facet_results:
                result['facet_boost'] = facet_boost
                result['search_type'] = 'facet'
            
            # Return top results
            return facet_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in facet search: {str(e)}")
            return []
    
    def get_index_status(self) -> Dict[str, any]:
        """Get status of all indexes"""
        try:
            from ..models import VectorIndex, KeywordIndex, FacetIndex
            
            status = {
                'vector_index': {
                    'exists': False,
                    'is_built': False,
                    'total_vectors': 0,
                    'last_updated': None
                },
                'keyword_index': {
                    'exists': False,
                    'is_built': False,
                    'total_documents': 0,
                    'last_updated': None
                },
                'facet_indexes': {
                    'total': 0,
                    'types': []
                },
                'search_metadata': {
                    'total_records': 0,
                    'indexed_records': 0
                }
            }
            
            # Check vector index
            vector_index = VectorIndex.objects.filter(is_active=True).first()
            if vector_index:
                status['vector_index']['exists'] = True
                status['vector_index']['is_built'] = vector_index.is_built
                status['vector_index']['total_vectors'] = vector_index.total_vectors
                status['vector_index']['last_updated'] = vector_index.updated_at
            
            # Check keyword index
            keyword_index = KeywordIndex.objects.filter(is_active=True).first()
            if keyword_index:
                status['keyword_index']['exists'] = True
                status['keyword_index']['is_built'] = keyword_index.is_built
                status['keyword_index']['total_documents'] = keyword_index.total_documents
                status['keyword_index']['last_updated'] = keyword_index.updated_at
            
            # Check facet indexes
            facet_indexes = FacetIndex.objects.filter(is_active=True)
            built_facet_indexes = facet_indexes.filter(is_built=True)
            status['facet_indexes']['total'] = facet_indexes.count()
            status['facet_indexes']['built'] = built_facet_indexes.count()
            status['facet_indexes']['types'] = list(facet_indexes.values_list('facet_type', flat=True))
            
            # Check search metadata
            total_metadata = SearchMetadata.objects.count()
            indexed_metadata = SearchMetadata.objects.filter(is_indexed=True).count()
            status['search_metadata']['total_records'] = total_metadata
            status['search_metadata']['indexed_records'] = indexed_metadata
            status['search_metadata']['is_built'] = indexed_metadata > 0
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting index status: {str(e)}")
            return {}
    
    def refresh_indexes(self, incremental: bool = True) -> Dict[str, any]:
        """Refresh indexes with new data"""
        try:
            logger.info(f"Refreshing indexes (incremental: {incremental})")
            
            # For incremental refresh, only process new cases
            force = not incremental
            
            # Build hybrid index
            stats = self.build_hybrid_index(force=force)
            
            if stats['hybrid_indexed']:
                logger.info("Index refresh completed successfully")
            else:
                logger.error(f"Index refresh failed: {'; '.join(stats['errors'])}")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error refreshing indexes: {str(e)}"
            logger.error(error_msg)
            return {'errors': [error_msg]}
