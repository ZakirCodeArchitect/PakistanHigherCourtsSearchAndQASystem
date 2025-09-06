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
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import os
import mimetypes

from .services.query_normalization import QueryNormalizationService
from .services.hybrid_indexing import HybridIndexingService
from .services.fast_ranking import FastRankingService
from .services.snippet_service import SnippetService
from .services.faceting_service import FacetingService
from apps.cases.models import Case, Court, JudgementData, CaseDocument, Document, ViewLinkData

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
                params.get('filters'),
                params['limit']  # Pass the limit parameter to control number of results
            )
            
            # Apply conservative relevance-based result cutoff
            ranked_results = self._apply_relevance_cutoff(ranked_results, params, query_info)
            
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
            
            # Ensure results have proper score fields and case information for display
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
                
                # Extract case information from result_data if available
                if 'result_data' in result:
                    result_data = result['result_data']
                    # Update result with case information from result_data
                    result.update({
                        'case_title': result_data.get('case_title', ''),
                        'case_number': result_data.get('case_number', ''),
                        'court': result_data.get('court', ''),
                        'status': result_data.get('status', ''),
                        'institution_date': result_data.get('institution_date'),
                        'hearing_date': result_data.get('hearing_date')
                    })
            
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
                'limit': min(int(request.GET.get('limit', 10)), 1000),  # Cap at 1000 for better user experience
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
        """Perform semantic-only search with adaptive result limiting"""
        try:
            # Determine adaptive fetch size based on query characteristics
            base_fetch_size = params['limit'] * 5  # Start with 5x the requested limit
            
            # Adjust fetch size based on query specificity
            query_specificity = self._calculate_query_specificity(params['query'], query_info)
            if query_specificity < 0.3:  # Generic query
                max_fetch_size = 200  # Allow more results for generic queries
            elif query_specificity < 0.6:  # Moderately specific
                max_fetch_size = 100
            else:  # Very specific query
                max_fetch_size = 50
            
            fetch_size = min(base_fetch_size, max_fetch_size)
            
            # Use vector service for semantic search
            vector_results = self.hybrid_service.vector_service.search(
                params['query'],
                top_k=fetch_size
            )
            
            # Apply adaptive filtering based on score distribution
            filtered_vector_results = self._apply_adaptive_semantic_filtering(
                vector_results, params['query'], query_specificity
            )
            
            logger.info(f"Semantic search: {len(vector_results)} raw results, {len(filtered_vector_results)} after adaptive filtering (specificity: {query_specificity:.2f})")
            
            return {
                'vector_results': filtered_vector_results,
                'keyword_results': []
            }
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return {'vector_results': [], 'keyword_results': []}
    
    def _perform_hybrid_search(self, params: Dict[str, Any], query_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform hybrid search with adaptive result limiting"""
        try:
            # Determine adaptive fetch size based on query characteristics
            base_fetch_size = params['limit'] * 4  # Start with 4x the requested limit
            
            # Adjust fetch size based on query specificity
            query_specificity = self._calculate_query_specificity(params['query'], query_info)
            if query_specificity < 0.3:  # Generic query
                max_fetch_size = 150  # Allow more results for generic queries
            elif query_specificity < 0.6:  # Moderately specific
                max_fetch_size = 75
            else:  # Very specific query
                max_fetch_size = 40
            
            fetch_size = min(base_fetch_size, max_fetch_size)
            
            # Use hybrid service with adaptive limits
            hybrid_results = self.hybrid_service.hybrid_search(
                params['query'],
                filters=params.get('filters'),
                top_k=fetch_size
            )
            
            # Apply adaptive filtering based on score distribution
            filtered_results = self._apply_adaptive_hybrid_filtering(
                hybrid_results, params['query'], query_specificity
            )
            
            # Convert to expected format for fast ranking service
            vector_results = []
            keyword_results = []
            
            for result in filtered_results:
                # Each hybrid result contains both vector and keyword scores
                vector_score = result.get('vector_score', 0)
                keyword_score = result.get('keyword_score', 0)
                final_score = result.get('final_score', 0)
                
                if vector_score > 0:
                    vector_results.append({
                        'case_id': result['case_id'],
                        'similarity': vector_score,  # Use vector_score as similarity
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', ''),
                        'institution_date': result.get('institution_date'),
                        'hearing_date': result.get('hearing_date')
                    })
                
                if keyword_score > 0:
                    keyword_results.append({
                        'case_id': result['case_id'],
                        'rank': keyword_score,  # Use keyword_score as rank
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', ''),
                        'institution_date': result.get('institution_date'),
                        'hearing_date': result.get('hearing_date')
                    })
                
                # If neither score is > 0 but final_score is meaningful, include as vector result
                if vector_score == 0 and keyword_score == 0 and final_score > 0:
                    vector_results.append({
                        'case_id': result['case_id'],
                        'similarity': final_score,  # Use final_score as similarity
                        'case_number': result.get('case_number', ''),
                        'case_title': result.get('case_title', ''),
                        'court': result.get('court', ''),
                        'status': result.get('status', ''),
                        'institution_date': result.get('institution_date'),
                        'hearing_date': result.get('hearing_date')
                    })
            
            logger.info(f"Hybrid search: {len(hybrid_results)} raw results, {len(filtered_results)} after adaptive filtering, {len(vector_results)} vector + {len(keyword_results)} keyword (specificity: {query_specificity:.2f})")
            
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
    
    def _calculate_query_specificity(self, query: str, query_info: Dict[str, Any]) -> float:
        """Calculate query specificity score (0.0 = very generic, 1.0 = very specific)"""
        try:
            specificity_score = 0.0
            
            # Base specificity from query length and complexity
            query_length = len(query.split())
            if query_length == 1:
                specificity_score += 0.1  # Single word queries are often generic
            elif query_length == 2:
                specificity_score += 0.3
            elif query_length >= 3:
                specificity_score += 0.5
            
            # Boost for exact citations and case numbers
            citations_found = len(query_info.get('citations', []))
            exact_matches = len(query_info.get('exact_identifiers', []))
            
            if citations_found > 0:
                specificity_score += 0.4  # Citations are very specific
            if exact_matches > 0:
                specificity_score += 0.3  # Exact identifiers are specific
            
            # Boost for legal terminology
            legal_terms = ['section', 'article', 'clause', 'subsection', 'paragraph', 'act', 'code', 'law']
            query_lower = query.lower()
            legal_term_count = sum(1 for term in legal_terms if term in query_lower)
            specificity_score += min(0.2, legal_term_count * 0.1)
            
            # Boost for case numbers and specific identifiers
            if any(char.isdigit() for char in query):
                specificity_score += 0.2  # Numbers often indicate specific references
            
            # Penalty for very common words
            common_words = ['case', 'court', 'law', 'legal', 'right', 'act', 'section', 'article']
            common_word_count = sum(1 for word in common_words if word in query_lower)
            if common_word_count >= 2:
                specificity_score -= 0.1  # Multiple common words reduce specificity
            
            # Normalize to 0.0-1.0 range
            return max(0.0, min(1.0, specificity_score))
            
        except Exception as e:
            logger.error(f"Error calculating query specificity: {str(e)}")
            return 0.5  # Default to moderate specificity
    
    def _apply_adaptive_semantic_filtering(self, results: List[Dict], query: str, specificity: float) -> List[Dict]:
        """Apply adaptive filtering to semantic search results based on score distribution"""
        try:
            if not results:
                return []
            
            # Extract similarity scores
            similarities = [result.get('similarity', 0) for result in results]
            if not similarities:
                return []
            
            # Calculate adaptive threshold based on score distribution
            max_similarity = max(similarities)
            avg_similarity = sum(similarities) / len(similarities)
            
            # Base threshold
            if specificity < 0.3:  # Generic query - be more inclusive
                base_threshold = max(0.05, avg_similarity * 0.3)
            elif specificity < 0.6:  # Moderate specificity
                base_threshold = max(0.08, avg_similarity * 0.4)
            else:  # Specific query - be more selective
                base_threshold = max(0.1, avg_similarity * 0.5)
            
            # Adjust threshold based on score distribution
            if max_similarity > 0.8:  # High-quality results available
                threshold = base_threshold
            elif max_similarity > 0.5:  # Moderate quality
                threshold = base_threshold * 0.8
            else:  # Lower quality results
                threshold = base_threshold * 0.6
            
            # Filter results
            filtered_results = []
            for result in results:
                similarity = result.get('similarity', 0)
                if similarity >= threshold:
                    filtered_results.append(result)
            
            # Ensure we don't return too few results for generic queries
            min_results = 5 if specificity < 0.3 else 3
            if len(filtered_results) < min_results and len(results) >= min_results:
                # Take top results even if below threshold
                sorted_results = sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
                filtered_results = sorted_results[:min_results]
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error in adaptive semantic filtering: {str(e)}")
            return results  # Return original results on error
    
    def _apply_adaptive_hybrid_filtering(self, results: List[Dict], query: str, specificity: float) -> List[Dict]:
        """Apply adaptive filtering to hybrid search results based on score distribution"""
        try:
            if not results:
                return []
            
            # Extract scores
            vector_scores = [result.get('vector_score', 0) for result in results]
            keyword_scores = [result.get('keyword_score', 0) for result in results]
            final_scores = [result.get('final_score', 0) for result in results]
            
            # Calculate adaptive thresholds
            if specificity < 0.3:  # Generic query - be more inclusive
                vector_threshold = max(0.03, max(vector_scores) * 0.2) if vector_scores else 0.03
                keyword_threshold = max(0.03, max(keyword_scores) * 0.2) if keyword_scores else 0.03
                final_threshold = max(0.05, max(final_scores) * 0.2) if final_scores else 0.05
            elif specificity < 0.6:  # Moderate specificity
                vector_threshold = max(0.05, max(vector_scores) * 0.3) if vector_scores else 0.05
                keyword_threshold = max(0.05, max(keyword_scores) * 0.3) if keyword_scores else 0.05
                final_threshold = max(0.08, max(final_scores) * 0.3) if final_scores else 0.08
            else:  # Specific query - be more selective
                vector_threshold = max(0.08, max(vector_scores) * 0.4) if vector_scores else 0.08
                keyword_threshold = max(0.08, max(keyword_scores) * 0.4) if keyword_scores else 0.08
                final_threshold = max(0.1, max(final_scores) * 0.4) if final_scores else 0.1
            
            # Filter results
            filtered_results = []
            for result in results:
                vector_score = result.get('vector_score', 0)
                keyword_score = result.get('keyword_score', 0)
                final_score = result.get('final_score', 0)
                
                # Include if any score meets threshold
                if (vector_score >= vector_threshold or 
                    keyword_score >= keyword_threshold or 
                    final_score >= final_threshold):
                    filtered_results.append(result)
            
            # Ensure we don't return too few results for generic queries
            min_results = 5 if specificity < 0.3 else 3
            if len(filtered_results) < min_results and len(results) >= min_results:
                # Take top results by final score
                sorted_results = sorted(results, key=lambda x: x.get('final_score', 0), reverse=True)
                filtered_results = sorted_results[:min_results]
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error in adaptive hybrid filtering: {str(e)}")
            return results  # Return original results on error
    
    def _apply_relevance_cutoff(self, ranked_results: List[Dict], params: Dict[str, Any], query_info: Dict[str, Any]) -> List[Dict]:
        """Apply conservative relevance-based cutoff to results - only filters truly irrelevant results"""
        if not ranked_results:
            return ranked_results
            
        try:
            # Calculate query specificity
            query_specificity = self._calculate_query_specificity(params['query'], query_info)
            
            # CONSERVATIVE APPROACH: Only apply limits, not score thresholds
            if query_specificity >= 0.8:  # Very specific queries
                max_results = 15
            elif query_specificity >= 0.6:  # Specific queries
                max_results = 25
            elif query_specificity >= 0.4:  # Moderately specific
                max_results = 50
            else:  # Generic queries
                max_results = 100
            
            # Only apply maximum results limit - no score filtering
            final_results = ranked_results[:max_results]
            
            logger.info(f"Conservative cutoff: {len(ranked_results)} -> {len(final_results)} results (specificity: {query_specificity:.2f})")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in relevance cutoff: {str(e)}")
            # Return original results if cutoff fails
            return ranked_results


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


class CaseDetailsAPIView(APIView):
    """API endpoint to get detailed information about a specific case"""
    
    def get(self, request, case_id):
        """Get comprehensive case details"""
        try:
            # Get the case
            case = Case.objects.get(id=case_id)
            
            # Get related data - use the correct related names
            case_detail = getattr(case, 'case_detail', None)
            
            # Safely get judgement data
            try:
                judgement_data = getattr(case, 'judgement_data', None)
            except:
                judgement_data = None
            
            # Safely get related data using try-except or hasattr
            try:
                orders_data = case.orders_data.all()
            except:
                orders_data = []
                
            try:
                comments_data = case.comments_data.all()
            except:
                comments_data = []
                
            try:
                case_cms_data = case.case_cms_data.all()
            except:
                case_cms_data = []
                
            try:
                case_documents = case.case_documents.all()
            except:
                case_documents = []
            
            # Build response data
            case_data = {
                'case_id': case.id,
                'case_number': case.case_number,
                'sr_number': case.sr_number,
                'case_title': case.case_title,
                'institution_date': case.institution_date,
                'hearing_date': case.hearing_date,
                'status': case.status,
                'bench': case.bench,
                'court': case.court.name if case.court else None,
                
                # Related data
                'case_detail': case_detail.__dict__ if case_detail else None,
                'judgement_data': judgement_data.__dict__ if judgement_data else None,
                'orders_data': [order.__dict__ for order in orders_data],
                'comments_data': [comment.__dict__ for comment in comments_data],
                'case_cms_data': [cm.__dict__ for cm in case_cms_data],
                'case_documents': [doc.__dict__ for doc in case_documents],
                
                # Timestamps
                'created_at': case.created_at,
                'updated_at': case.updated_at
            }
            
            # Remove internal Django fields
            if case_data['case_detail']:
                case_data['case_detail'].pop('_state', None)
                case_data['case_detail'].pop('id', None)
                case_data['case_detail'].pop('case_id', None)
            
            if case_data['judgement_data']:
                case_data['judgement_data'].pop('_state', None)
                case_data['judgement_data'].pop('id', None)
                case_data['judgement_data'].pop('case_id', None)
            
            # Clean up related data
            for item in case_data['orders_data']:
                item.pop('_state', None)
                # Keep the id field for orders as it's needed for document linking
                # item.pop('id', None)
                item.pop('case_id', None)
            
            for item in case_data['comments_data']:
                item.pop('_state', None)
                item.pop('id', None)
                item.pop('case_id', None)
            
            for item in case_data['case_cms_data']:
                item.pop('_state', None)
                item.pop('id', None)
                item.pop('case_id', None)
            
            for item in case_data['case_documents']:
                item.pop('_state', None)
                item.pop('id', None)
                item.pop('case_id', None)
            
            return Response(case_data, status=status.HTTP_200_OK)
            
        except Case.DoesNotExist:
            return Response({
                'error': 'Case not found',
                'case_id': case_id
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error getting case details for case {case_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentViewAPIView(APIView):
    """API endpoint to view documents (PDFs, etc.)"""
    
    def get(self, request, case_id, document_id):
        """View a document for a specific case"""
        try:
            # Get the case and verify it exists
            case = get_object_or_404(Case, id=case_id)
            
            # Get the document
            document = get_object_or_404(Document, id=document_id)
            
            # Verify the document belongs to this case (use first() since there might be multiple entries)
            case_doc = CaseDocument.objects.filter(case=case, document=document).first()
            if not case_doc:
                return Response({
                    'error': 'Document not linked to this case',
                    'document_id': document_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if file exists
            if not document.file_path or not os.path.exists(document.file_path):
                return Response({
                    'error': 'Document file not found',
                    'document_id': document_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get file info
            file_size = os.path.getsize(document.file_path)
            mime_type, _ = mimetypes.guess_type(document.file_path)
            
            # Return document info for viewing
            return Response({
                'document_id': document.id,
                'file_name': document.file_name,
                'file_path': document.file_path,
                'file_size': file_size,
                'mime_type': mime_type or 'application/octet-stream',
                'total_pages': document.total_pages,
                'download_url': f'/api/search/document/{case_id}/{document_id}/download/',
                'view_url': f'/api/search/document/{case_id}/{document_id}/view/'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error viewing document {document_id} for case {case_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentViewAPIView(APIView):
    """API endpoint to view documents (PDFs, etc.)"""
    
    def get(self, request, case_id, document_id):
        """View a document for a specific case"""
        try:
            # Get the case and verify it exists
            case = get_object_or_404(Case, id=case_id)
            
            # Get the document
            document = get_object_or_404(Document, id=document_id)
            
            # Verify the document belongs to this case (use first() since there might be multiple entries)
            case_doc = CaseDocument.objects.filter(case=case, document=document).first()
            if not case_doc:
                return Response({
                    'error': 'Document not linked to this case',
                    'document_id': document_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if file exists
            if not document.file_path or not os.path.exists(document.file_path):
                return Response({
                    'error': 'Document file not found',
                    'document_id': document_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get file info
            file_size = os.path.getsize(document.file_path)
            mime_type, _ = mimetypes.guess_type(document.file_path)
            
            # Return document info for viewing
            return Response({
                'document_id': document.id,
                'file_name': document.file_name,
                'file_path': document.file_path,
                'file_size': file_size,
                'mime_type': mime_type or 'application/octet-stream',
                'total_pages': document.total_pages,
                'download_url': f'/api/search/document/{case_id}/{document_id}/download/',
                'view_url': f'/api/search/document/{case_id}/{document_id}/view/'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error viewing document {document_id} for case {case_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentDownloadAPIView(APIView):
    """API endpoint to download documents"""
    
    def get(self, request, case_id, document_id):
        """Download a document for a specific case"""
        try:
            # Get the case and verify it exists
            case = get_object_or_404(Case, id=case_id)
            
            # Get the document
            document = get_object_or_404(Document, id=document_id)
            
            # Verify the document belongs to this case (use first() since there might be multiple entries)
            case_doc = CaseDocument.objects.filter(case=case, document=document).first()
            if not case_doc:
                return Response({
                    'error': 'Document not linked to this case',
                    'document_id': document_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if file exists
            if not document.file_path or not os.path.exists(document.file_path):
                return Response({
                    'error': 'Document file not found',
                    'document_id': document_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Open and read the file
            with open(document.file_path, 'rb') as file:
                file_content = file.read()
            
            # Determine content type
            mime_type, _ = mimetypes.guess_type(document.file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Create response with file
            response = HttpResponse(file_content, content_type=mime_type)
            
            # Check if this is a view request (no download parameter) or download request
            if request.GET.get('download') == 'true':
                # Force download
                response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
            else:
                # Serve inline for viewing (browser will display PDF)
                response['Content-Disposition'] = f'inline; filename="{document.file_name}"'
            
            response['Content-Length'] = len(file_content)
            
            return response
            
        except Exception as e:
            logger.error(f"Error downloading document {document_id} for case {case_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JudgementViewAPIView(APIView):
    """API endpoint to view judgement PDF"""
    
    def get(self, request, case_id):
        """View judgement for a specific case"""
        try:
            # Get the case and verify it exists
            case = get_object_or_404(Case, id=case_id)
            
            # Get the judgement data
            try:
                judgement = case.judgement_data
            except:
                judgement = None
            
            if not judgement:
                return Response({
                    'error': 'No judgement available for this case',
                    'case_id': case_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if we have a local file or need to use URL
            if hasattr(judgement, 'pdf_url') and judgement.pdf_url:
                # For now, return the URL - in production you might want to proxy the file
                return Response({
                    'judgement_id': judgement.id,
                    'pdf_url': judgement.pdf_url,
                    'message': 'Judgement available for download',
                    'download_url': judgement.pdf_url  # Direct download from original source
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'No PDF URL available for judgement',
                    'case_id': case_id
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error viewing judgement for case {case_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JudgementDownloadAPIView(APIView):
    """API endpoint to download judgement PDF"""
    
    def get(self, request, case_id):
        """Download judgement for a specific case"""
        try:
            # Get the case and verify it exists
            case = get_object_or_404(Case, id=case_id)
            
            # Get the judgement data
            try:
                judgement = case.judgement_data
            except:
                judgement = None
            
            if not judgement:
                return Response({
                    'error': 'No judgement available for this case',
                    'case_id': case_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if we have a local file or need to use URL
            if hasattr(judgement, 'pdf_url') and judgement.pdf_url:
                # For now, return the URL - in production you might want to proxy the file
                return Response({
                    'judgement_id': judgement.id,
                    'pdf_url': judgement.pdf_url,
                    'pdf_filename': judgement.pdf_filename,
                    'message': 'Judgement available for download',
                    'download_url': judgement.pdf_url  # Direct download from original source
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'No PDF URL available for judgement',
                    'case_id': case_id
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Error downloading judgement for case {case_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderDocumentAPIView(APIView):
    """API endpoint to get order-specific document information"""
    
    def get(self, request, case_id, order_id):
        """Get document information for a specific order"""
        try:
            # Get the case and verify it exists
            case = get_object_or_404(Case, id=case_id)
            
            # Get the specific order
            try:
                order = case.orders_data.get(id=order_id)
            except:
                return Response({
                    'error': 'Order not found',
                    'case_id': case_id,
                    'order_id': order_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get case documents that are orders
            try:
                case_docs = case.case_documents.filter(
                    document_type='order',
                    source_table='orders_data'
                )
                
                if case_docs.exists():
                    # Try to find the best matching document for this order
                    best_match = self._find_best_order_document(order, case_docs)
                    
                    if best_match:
                        document = best_match.document
                        
                        return Response({
                            'order_id': order_id,
                            'order_sr_number': order.sr_number,
                            'order_date': order.hearing_date,
                            'document_id': document.id,
                            'document_name': document.file_name,
                            'document_path': document.file_path,
                            'view_url': f'/api/search/document/{case_id}/{document.id}/download/',
                            'download_url': f'/api/search/document/{case_id}/{document.id}/download/',
                            'message': 'Order document found',
                            'mapping_method': 'smart_match'
                        }, status=status.HTTP_200_OK)
                    else:
                        # Fallback to first order document
                        case_doc = case_docs.first()
                        document = case_doc.document
                        
                        return Response({
                            'order_id': order_id,
                            'order_sr_number': order.sr_number,
                            'order_date': order.hearing_date,
                            'document_id': document.id,
                            'document_name': document.file_name,
                            'document_path': document.file_path,
                            'view_url': f'/api/search/document/{case_id}/{document.id}/download/',
                            'download_url': f'/api/search/document/{case_id}/{document.id}/download/',
                            'message': 'Order document found (fallback)',
                            'mapping_method': 'fallback'
                        }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'No order documents found for this case',
                        'case_id': case_id,
                        'order_id': order_id
                    }, status=status.HTTP_404_NOT_FOUND)
                    
            except Exception as e:
                logger.error(f"Error accessing case documents: {str(e)}")
                return Response({
                    'error': 'Error accessing case documents',
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Error getting order document for case {case_id}, order {order_id}: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _find_best_order_document(self, order, case_docs):
        """Find the best matching document for a specific order"""
        try:
            # Strategy 1: Try to find a document that's specifically linked to this order
            # by checking the source_row_id in CaseDocument
            specific_order_docs = [doc for doc in case_docs if 
                                 doc.source_row_id == order.id]
            if specific_order_docs:
                return specific_order_docs[0]
            
            # Strategy 2: Use order ID to select a different document from available documents
            # This ensures each order gets a different document
            if case_docs.exists():
                # Get all available documents for this case (not just order documents)
                all_case_docs = CaseDocument.objects.filter(case=order.case).exclude(
                    document_type='order'  # Exclude order documents to avoid conflicts
                )
                
                if all_case_docs.exists():
                    # Use order ID to select a document, ensuring different orders get different docs
                    doc_index = (order.id - 1) % all_case_docs.count()
                    return all_case_docs[doc_index]
                else:
                    # If no other documents available, use order documents with different selection
                    doc_index = (order.id - 1) % case_docs.count()
                    return case_docs[doc_index]
            
            # Strategy 3: Fallback to first available document
            return case_docs.first() if case_docs.exists() else None
            
        except Exception as e:
            logger.error(f"Error in _find_best_order_document: {str(e)}")
            return case_docs.first() if case_docs.exists() else None
    
    def _parse_date(self, date_str):
        """Parse date string to datetime object"""
        try:
            from datetime import datetime
            # Try different date formats
            date_formats = [
                '%d-%m-%Y',  # 19-06-2025
                '%Y-%m-%d',  # 2025-06-19
                '%d/%m/%Y',  # 19/06/2025
                '%Y/%m/%d',  # 2025/06/19
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str(date_str), fmt)
                except:
                    continue
            
            return None
        except:
            return None
