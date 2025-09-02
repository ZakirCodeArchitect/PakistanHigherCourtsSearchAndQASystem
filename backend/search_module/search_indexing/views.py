"""
Search API Views
Implements the main search endpoints with proper request handling and response formatting
"""

import time
import logging
from typing import Dict, Any, List
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle
from django.db.models import Count

from .services.query_normalization import QueryNormalizationService
from .services.hybrid_indexing import HybridIndexingService
from .services.fast_ranking import FastRankingService
from .services.snippet_service import SnippetService
from .services.faceting_service import FacetingService
from apps.cases.models import Case, Court

logger = logging.getLogger(__name__)


class SearchAPIView(APIView):
    """Main search endpoint for hybrid retrieval with facets & snippets"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_normalizer = QueryNormalizationService()
        self.hybrid_service = HybridIndexingService(use_pinecone=True)  # Use Pinecone for better performance
        self.ranking_service = FastRankingService()
        self.snippet_service = SnippetService()
        self.faceting_service = FacetingService()
    
    def get(self, request):
        """Handle GET search requests"""
        try:
            start_time = time.time()
            
            # Parse and validate request parameters
            params = self._parse_search_params(request)
            if not params['is_valid']:
                return Response({
                    'error': 'Invalid search parameters',
                    'details': params['errors']
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Normalize query
            query_info = self.query_normalizer.normalize_query(params['query'])
            
            # Perform search based on mode
            if params['mode'] == 'lexical':
                search_results = self._perform_lexical_search(params, query_info)
            elif params['mode'] == 'semantic':
                search_results = self._perform_semantic_search(params, query_info)
            else:  # hybrid
                search_results = self._perform_hybrid_search(params, query_info)
            
            # Apply advanced ranking
            ranked_results = self.ranking_service.rank_results(
                search_results.get('vector_results', []),
                search_results.get('keyword_results', []),
                params['query'],
                None,  # exact_case_match - will be handled by fast ranking service
                params.get('filters')
            )
            
            # Generate snippets if requested
            if params.get('highlight', False):
                for result in ranked_results:
                    result['snippets'] = self.snippet_service.generate_snippets(
                        result['case_id'],
                        params['query'],
                        query_info
                    )
            
            # Compute facets if requested
            facets = {}
            if params.get('return_facets', False):
                facets = self.faceting_service.compute_facets(
                    result_case_ids=[r['case_id'] for r in ranked_results],
                    filters=params.get('filters')
                )
            
            # Apply pagination
            paginated_results = self._apply_pagination(ranked_results, params)
            
            # Calculate latency
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Build response
            response_data = {
                'results': paginated_results['results'],
                'pagination': {
                    'total': paginated_results['total'],
                    'offset': params['offset'],
                    'limit': params['limit'],
                    'has_next': paginated_results['has_next'],
                    'has_previous': paginated_results['has_previous']
                },
                'facets': facets,
                'query_info': {
                    'original_query': params['query'],
                    'normalized_query': query_info['normalized_query'],
                    'citations_found': len(query_info.get('citations', [])),
                    'exact_matches_found': len(query_info.get('exact_identifiers', []))
                },
                'search_metadata': {
                    'mode': params['mode'],
                    'total_results': len(ranked_results),
                    'latency_ms': round(latency, 2),
                    'search_type': 'hybrid' if params['mode'] == 'hybrid' else params['mode']
                }
            }
            
            # Ensure results have proper score fields for display
            for result in response_data['results']:
                # Extract scores from the fast ranking service results
                if 'vector_score' in result:
                    result['vector_score'] = round(result['vector_score'], 4)
                if 'keyword_score' in result:
                    result['keyword_score'] = round(result['keyword_score'], 4)
                if 'final_score' in result:
                    result['final_score'] = round(result['final_score'], 4)
                if 'base_score' in result:
                    result['base_score'] = round(result['base_score'], 4)
            
            # Add debug information if requested
            if params.get('debug', False):
                response_data['debug_signals'] = {
                    'query_normalization': query_info,
                    'ranking_config': self.ranking_service.default_config,
                    'boost_signals': query_info.get('boost_signals', {}),
                    'search_performance': {
                        'query_time': latency,
                        'ranking_time': 0,  # Would need to measure separately
                        'facet_time': 0,    # Would need to measure separately
                    }
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in search API: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _parse_search_params(self, request) -> Dict[str, Any]:
        """Parse and validate search parameters"""
        try:
            params = {
                'query': request.GET.get('q', '').strip(),
                'mode': request.GET.get('mode', 'hybrid').lower(),
                'filters': self._parse_filters(request),
                'offset': int(request.GET.get('offset', 0)),
                'limit': min(int(request.GET.get('limit', 10)), 100),  # Cap at 100
                'return_facets': request.GET.get('return_facets', 'false').lower() == 'true',
                'highlight': request.GET.get('highlight', 'false').lower() == 'true',
                'debug': request.GET.get('debug', 'false').lower() == 'true',
                'is_valid': True,
                'errors': []
            }
            
            # Validate required parameters
            if not params['query']:
                params['is_valid'] = False
                params['errors'].append('Query parameter "q" is required')
            
            if params['mode'] not in ['lexical', 'semantic', 'hybrid']:
                params['is_valid'] = False
                params['errors'].append('Mode must be one of: lexical, semantic, hybrid')
            
            if params['offset'] < 0:
                params['is_valid'] = False
                params['errors'].append('Offset must be non-negative')
            
            if params['limit'] <= 0:
                params['is_valid'] = False
                params['errors'].append('Limit must be positive')
            
            return params
            
        except (ValueError, TypeError) as e:
            return {
                'is_valid': False,
                'errors': [f'Parameter parsing error: {str(e)}']
            }
    
    def _parse_filters(self, request) -> Dict[str, Any]:
        """Parse filter parameters"""
        filters = {}
        
        # Court filter
        court_filter = request.GET.get('court')
        if court_filter:
            try:
                # Try to parse as court ID first
                court_id = int(court_filter)
                if Court.objects.filter(id=court_id).exists():
                    filters['court'] = court_id
                else:
                    filters['court'] = court_filter  # Use as name
            except ValueError:
                filters['court'] = court_filter  # Use as name
        
        # Year filter
        year_filter = request.GET.get('year')
        if year_filter:
            try:
                filters['year'] = int(year_filter)
            except ValueError:
                pass  # Ignore invalid year
        
        # Status filter
        status_filter = request.GET.get('status')
        if status_filter:
            filters['status'] = status_filter
        
        # Judge filter
        judge_filter = request.GET.get('judge')
        if judge_filter:
            filters['judge'] = judge_filter
        
        # Section filter
        section_filter = request.GET.get('section')
        if section_filter:
            filters['section'] = section_filter
        
        # Citation filter
        citation_filter = request.GET.get('citation')
        if citation_filter:
            filters['citation'] = citation_filter
        
        return filters
    
    def _perform_lexical_search(self, params: Dict[str, Any], query_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform lexical-only search"""
        try:
            # Use keyword service for lexical search
            keyword_results = self.hybrid_service.keyword_service.search(
                params['query'],
                filters=params.get('filters'),
                top_k=params['limit'] * 2  # Get more for ranking
            )
            
            return {
                'vector_results': [],
                'keyword_results': keyword_results
            }
            
        except Exception as e:
            logger.error(f"Error in lexical search: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _perform_semantic_search(self, params: Dict[str, Any], query_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic-only search"""
        try:
            # Use vector service for semantic search
            vector_results = self.hybrid_service.vector_service.search(
                params['query'],
                top_k=params['limit'] * 2  # Get more for ranking
            )
            
            return {
                'vector_results': vector_results,
                'keyword_results': []
            }
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _perform_hybrid_search(self, params: Dict[str, Any], query_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform hybrid search"""
        try:
            # Use hybrid service
            hybrid_results = self.hybrid_service.hybrid_search(
                params['query'],
                filters=params.get('filters'),
                top_k=params['limit'] * 2  # Get more for ranking
            )
            
            # Convert to expected format for fast ranking service
            vector_results = []
            keyword_results = []
            
            for result in hybrid_results:
                # Each hybrid result contains both vector and keyword scores
                # Create separate entries for vector and keyword results
                if result.get('vector_score', 0) > 0:
                    vector_results.append({
                        'case_id': result['case_id'],
                        'similarity': result['vector_score'],  # Use vector_score as similarity
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', '')
                    })
                
                if result.get('keyword_score', 0) > 0:
                    keyword_results.append({
                        'case_id': result['case_id'],
                        'rank': result['keyword_score'],  # Use keyword_score as rank
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', '')
                    })
                
                # If neither score is > 0, still include the result with default scores
                if result.get('vector_score', 0) == 0 and result.get('keyword_score', 0) == 0:
                    # This might be an exact match result
                    vector_results.append({
                        'case_id': result['case_id'],
                        'similarity': 0.1,  # Give a small default score
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', '')
                    })
            
            return {
                'vector_results': vector_results,
                'keyword_results': keyword_results
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _apply_pagination(self, results: List[Dict], params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pagination to results"""
        try:
            total = len(results)
            paginator = Paginator(results, params['limit'])
            
            # Calculate page number
            page_number = (params['offset'] // params['limit']) + 1
            
            try:
                page = paginator.page(page_number)
            except:
                # Handle out of range pages
                page = paginator.page(1)
            
            return {
                'results': page.object_list,
                'total': total,
                'has_next': page.has_next(),
                'has_previous': page.has_previous()
            }
            
        except Exception as e:
            logger.error(f"Error applying pagination: {str(e)}")
            return {
                'results': results,
                'total': len(results),
                'has_next': False,
                'has_previous': False
            }


class SuggestAPIView(APIView):
    """Typeahead suggestions endpoint"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.faceting_service = FacetingService()
    
    def get(self, request):
        """Handle GET suggestion requests"""
        try:
            query = request.GET.get('q', '').strip()
            suggestion_type = request.GET.get('type', 'auto').lower()
            
            if not query or len(query) < 2:
                return Response({
                    'suggestions': []
                }, status=status.HTTP_200_OK)
            
            suggestions = []
            
            if suggestion_type == 'auto':
                # Auto-detect type and provide suggestions
                suggestions = self._get_auto_suggestions(query)
            elif suggestion_type == 'case':
                suggestions = self._get_case_suggestions(query)
            elif suggestion_type == 'citation':
                suggestions = self._get_citation_suggestions(query)
            elif suggestion_type == 'section':
                suggestions = self._get_section_suggestions(query)
            elif suggestion_type == 'judge':
                suggestions = self._get_judge_suggestions(query)
            else:
                return Response({
                    'error': 'Invalid suggestion type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'suggestions': suggestions[:10]  # Limit to 10 suggestions
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in suggest API: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_auto_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get auto-detected suggestions"""
        suggestions = []
        
        # Try case number suggestions first
        case_suggestions = self._get_case_suggestions(query)
        suggestions.extend(case_suggestions)
        
        # Try citation suggestions
        citation_suggestions = self._get_citation_suggestions(query)
        suggestions.extend(citation_suggestions)
        
        # Try section suggestions
        section_suggestions = self._get_section_suggestions(query)
        suggestions.extend(section_suggestions)
        
        return suggestions
    
    def _get_case_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get case number suggestions"""
        try:
            cases = Case.objects.filter(
                case_number__icontains=query
            ).order_by('-created_at')[:5]
            
            suggestions = []
            for case in cases:
                suggestions.append({
                    'value': case.case_number,
                    'type': 'case',
                    'canonical_key': case.case_number,
                    'additional_info': case.case_title[:100] if case.case_title else ''
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting case suggestions: {str(e)}")
            return []
    
    def _get_citation_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get citation suggestions"""
        try:
            from apps.cases.models import Term, Case
            
            suggestions = []
            
            # Try to find citation-like terms in the Term model
            try:
                # Look for terms that might be citations (case numbers, legal references)
                citation_terms = Term.objects.filter(
                    canonical__icontains=query
                ).exclude(
                    type__in=['petitioner', 'party', 'advocate']  # Exclude non-citation types
                ).order_by('-occurrence_count')[:3]
                
                for term in citation_terms:
                    suggestions.append({
                        'value': term.canonical,
                        'type': 'citation',
                        'canonical_key': term.canonical,
                        'additional_info': f"Found in {term.occurrence_count} cases"
                    })
            except Exception as e:
                logger.warning(f"Term model citation search failed: {str(e)}")
            
            # Fallback: try to find citations in case numbers
            try:
                citation_cases = Case.objects.filter(
                    case_number__icontains=query
                ).exclude(
                    case_number__isnull=True
                ).exclude(
                    case_number=''
                )[:3]
                
                for case in citation_cases:
                    suggestions.append({
                        'value': case.case_number,
                        'type': 'citation',
                        'canonical_key': case.case_number,
                        'additional_info': case.case_title[:100] if case.case_title else ''
                    })
            except Exception as e:
                logger.warning(f"Case model citation search failed: {str(e)}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting citation suggestions: {str(e)}")
            return []
    
    def _get_section_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get section suggestions"""
        try:
            from apps.cases.models import Term, Case
            
            suggestions = []
            
            # Try to find section terms in the Term model
            try:
                sections = Term.objects.filter(
                    type='section',
                    canonical__icontains=query
                ).order_by('-occurrence_count')[:3]
                
                for section in sections:
                    suggestions.append({
                        'value': section.canonical,
                        'type': 'section',
                        'canonical_key': section.canonical,
                        'additional_info': f"Found in {section.occurrence_count} cases"
                    })
            except Exception as e:
                logger.warning(f"Term model section search failed: {str(e)}")
            
            # Fallback: try to find sections in case numbers (like PPC, CrPC, CPC)
            try:
                # Look for common legal section patterns
                section_patterns = ['PPC', 'CrPC', 'CPC', 'PLD', 'SCMR']
                matching_cases = []
                
                for pattern in section_patterns:
                    if query.upper() in pattern:
                        cases = Case.objects.filter(
                            case_number__icontains=pattern
                        )[:2]  # Limit to 2 per pattern
                        matching_cases.extend(cases)
                
                for case in matching_cases[:3]:
                    suggestions.append({
                        'value': case.case_number,
                        'type': 'section',
                        'canonical_key': case.case_number,
                        'additional_info': case.case_title[:100] if case.case_title else ''
                    })
            except Exception as e:
                logger.warning(f"Case model section search failed: {str(e)}")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting section suggestions: {str(e)}")
            return []
    
    def _get_judge_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get judge suggestions"""
        try:
            judges = Case.objects.filter(
                bench__icontains=query
            ).values('bench').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            suggestions = []
            for judge in judges:
                suggestions.append({
                    'value': judge['bench'],
                    'type': 'judge',
                    'canonical_key': judge['bench'],
                    'additional_info': f"Presided over {judge['count']} cases"
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting judge suggestions: {str(e)}")
            return []


class CaseContextAPIView(APIView):
    """Case context retrieval endpoint"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snippet_service = SnippetService()
    
    def get(self, request, case_id: int):
        """Handle GET case context requests"""
        try:
            query = request.GET.get('q', '').strip()
            
            # Get case
            try:
                case = Case.objects.get(id=case_id)
            except Case.DoesNotExist:
                return Response({
                    'error': 'Case not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get semantic chunks
            chunks = self._get_semantic_chunks(case_id, query)
            
            # Get legal terms
            terms = self._get_legal_terms(case_id, query)
            
            return Response({
                'case_id': case_id,
                'case_number': case.case_number,
                'case_title': case.case_title,
                'chunks': chunks,
                'terms': terms,
                'query': query if query else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in case context API: {str(e)}")
            return Response({
                'error': 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_semantic_chunks(self, case_id: int, query: str = None) -> List[Dict[str, Any]]:
        """Get semantic chunks for a case"""
        try:
            from ..models import DocumentChunk
            
            chunks = DocumentChunk.objects.filter(
                case_id=case_id,
                is_embedded=True
            ).order_by('chunk_index')
            
            chunk_data = []
            for chunk in chunks:
                chunk_info = {
                    'text': chunk.chunk_text,
                    'page_range': chunk.page_number,
                    'char_spans': {
                        'start_char': chunk.start_char,
                        'end_char': chunk.end_char
                    },
                    'vector_score': 0.0,  # Would need to compute with query
                    'chunk_index': chunk.chunk_index,
                    'token_count': chunk.token_count
                }
                
                # If query provided, compute relevance score
                if query:
                    chunk_info['vector_score'] = self._compute_chunk_relevance(chunk, query)
                
                chunk_data.append(chunk_info)
            
            # Sort by relevance if query provided
            if query:
                chunk_data.sort(key=lambda x: x['vector_score'], reverse=True)
            
            return chunk_data[:10]  # Limit to top 10 chunks
            
        except Exception as e:
            logger.error(f"Error getting semantic chunks: {str(e)}")
            return []
    
    def _get_legal_terms(self, case_id: int, query: str = None) -> List[Dict[str, Any]]:
        """Get legal terms for a case"""
        try:
            from apps.cases.models import TermOccurrence
            
            term_occurrences = TermOccurrence.objects.filter(
                case_id=case_id
            ).select_related('term').order_by('-confidence')
            
            terms = []
            for occurrence in term_occurrences:
                term_info = {
                    'canonical': occurrence.term.canonical,
                    'type': occurrence.term.type,
                    'page': occurrence.page_no,
                    'span': {
                        'start_char': occurrence.start_char,
                        'end_char': occurrence.end_char
                    },
                    'confidence': occurrence.confidence,
                    'surface': occurrence.surface
                }
                
                # If query provided, check if term matches
                if query and query.lower() in occurrence.term.canonical.lower():
                    term_info['query_match'] = True
                
                terms.append(term_info)
            
            # Sort by query match first, then by confidence
            if query:
                terms.sort(key=lambda x: (not x.get('query_match', False), -x['confidence']))
            else:
                terms.sort(key=lambda x: -x['confidence'])
            
            return terms[:20]  # Limit to top 20 terms
            
        except Exception as e:
            logger.error(f"Error getting legal terms: {str(e)}")
            return []
    
    def _compute_chunk_relevance(self, chunk, query: str) -> float:
        """Compute relevance score for a chunk given a query"""
        try:
            # Simple relevance based on term overlap
            query_terms = set(query.lower().split())
            chunk_terms = set(chunk.chunk_text.lower().split())
            
            overlap = len(query_terms.intersection(chunk_terms))
            total_terms = len(query_terms.union(chunk_terms))
            
            if total_terms == 0:
                return 0.0
            
            return overlap / total_terms
            
        except Exception as e:
            logger.error(f"Error computing chunk relevance: {str(e)}")
            return 0.0


class SearchStatusAPIView(APIView):
    """Search system status and health endpoint"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hybrid_service = HybridIndexingService()
    
    def get(self, request):
        """Handle GET status requests"""
        try:
            # Get index status
            index_status = self.hybrid_service.get_index_status()
            
            # Get system health metrics
            health_metrics = self._get_health_metrics()
            
            return Response({
                'status': 'healthy' if health_metrics['is_healthy'] else 'degraded',
                'timestamp': time.time(),
                'indexes': index_status,
                'health': health_metrics,
                'system_info': {
                    'version': '1.0.0',
                    'environment': 'production'  # Would get from settings
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in status API: {str(e)}")
            return Response({
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            from django.db import connection
            
            # Database health
            db_healthy = True
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            except Exception:
                db_healthy = False
            
            # Case count
            total_cases = Case.objects.count()
            
            # Index coverage
            from search_indexing.models import SearchMetadata
            indexed_cases = SearchMetadata.objects.filter(is_indexed=True).count()
            index_coverage = (indexed_cases / total_cases * 100) if total_cases > 0 else 0
            
            return {
                'is_healthy': db_healthy and index_coverage > 80,
                'database': {
                    'healthy': db_healthy,
                    'total_cases': total_cases
                },
                'indexing': {
                    'coverage_percentage': round(index_coverage, 2),
                    'indexed_cases': indexed_cases,
                    'total_cases': total_cases
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting health metrics: {str(e)}")
            return {
                'is_healthy': False,
                'error': str(e)
            }
