"""
Faceting Service
Provides faceted search capabilities and suggestions
"""

import logging
from typing import Dict, List, Optional, Any
from django.db.models import Q, Count
from apps.cases.models import Case, Court

logger = logging.getLogger(__name__)


class FacetingService:
    """Service for computing facets and providing suggestions"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Default configuration
        self.default_config = {
            'max_facet_values': 50,
            'min_facet_count': 1,
            'cache_ttl': 300,  # 5 minutes
        }
        
        # Update with custom config
        if config:
            self.default_config.update(config)
    
    def compute_facets(self, 
                       result_case_ids: List[int] = None,
                       filters: Dict[str, Any] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Compute facets for search results
        
        Args:
            result_case_ids: List of case IDs from search results
            filters: Currently applied filters
            
        Returns:
            Dictionary of facet types with their values and counts
        """
        try:
            facets = {}
            
            # Court facets - show all available courts
            facets['court'] = self._get_court_facets(None, filters)
            
            # Status facets - show all available statuses
            facets['status'] = self._get_status_facets(None, filters)
            
            # Year facets - show all available years
            facets['year'] = self._get_year_facets(None, filters)
            
            # Case type facets - show all available case types
            facets['case_type'] = self._get_case_type_facets(None, filters)
            
            return facets
            
        except Exception as e:
            logger.error(f"Error computing facets: {str(e)}")
            return {}
    
    def _get_court_facets(self, case_ids: List[int] = None, filters: Dict = None) -> List[Dict]:
        """Get court facets"""
        try:
            queryset = Court.objects.all()
            
            if case_ids:
                queryset = queryset.filter(cases__id__in=case_ids)
            
            if filters and 'court' in filters:
                # Exclude currently selected court
                queryset = queryset.exclude(id=filters['court'])
            
            court_facets = queryset.annotate(
                count=Count('cases')
            ).filter(
                count__gte=self.default_config['min_facet_count']
            ).order_by('-count')[:self.default_config['max_facet_values']]
            
            return [
                {
                    'value': court.name,
                    'count': court.count,
                    'selected': False
                }
                for court in court_facets
            ]
            
        except Exception as e:
            logger.error(f"Error getting court facets: {str(e)}")
            return []
    
    def _get_status_facets(self, case_ids: List[int] = None, filters: Dict = None) -> List[Dict]:
        """Get status facets"""
        try:
            queryset = Case.objects.values('status').annotate(
                count=Count('id')
            ).filter(
                count__gte=self.default_config['min_facet_count']
            )
            
            if case_ids:
                queryset = queryset.filter(id__in=case_ids)
            
            if filters and 'status' in filters:
                # Exclude currently selected status
                queryset = queryset.exclude(status=filters['status'])
            
            status_facets = queryset.order_by('-count')[:self.default_config['max_facet_values']]
            
            return [
                {
                    'value': status['status'],
                    'count': status['count'],
                    'selected': False
                }
                for status in status_facets if status['status']
            ]
            
        except Exception as e:
            logger.error(f"Error getting status facets: {str(e)}")
            return []
    
    def _get_year_facets(self, case_ids: List[int] = None, filters: Dict = None) -> List[Dict]:
        """Get year facets"""
        try:
            queryset = Case.objects.values('institution_date').annotate(
                count=Count('id')
            ).filter(
                count__gte=self.default_config['min_facet_count']
            )
            
            if case_ids:
                queryset = queryset.filter(id__in=case_ids)
            
            if filters and 'year' in filters:
                # Exclude currently selected year
                queryset = queryset.exclude(institution_date__year=filters['year'])
            
            year_facets = queryset.order_by('-institution_date')[:self.default_config['max_facet_values']]
            
            return [
                {
                    'value': str(year['institution_date'].year) if year['institution_date'] else 'Unknown',
                    'count': year['count'],
                    'selected': False
                }
                for year in year_facets
            ]
            
        except Exception as e:
            logger.error(f"Error getting year facets: {str(e)}")
            return []
    
    def _get_case_type_facets(self, case_ids: List[int] = None, filters: Dict = None) -> List[Dict]:
        """Get case type facets"""
        try:
            queryset = Case.objects.values('case_type').annotate(
                count=Count('id')
            ).filter(
                count__gte=self.default_config['min_facet_count']
            )
            
            if case_ids:
                queryset = queryset.filter(id__in=case_ids)
            
            if filters and 'case_type' in filters:
                # Exclude currently selected case type
                queryset = queryset.exclude(case_type=filters['case_type'])
            
            type_facets = queryset.order_by('-count')[:self.default_config['max_facet_values']]
            
            return [
                {
                    'value': case_type['case_type'] or 'Unknown',
                    'count': case_type['count'],
                    'selected': False
                }
                for case_type in type_facets
            ]
            
        except Exception as e:
            logger.error(f"Error getting case type facets: {str(e)}")
            return []
    
    def get_suggestions(self, query: str, suggestion_type: str = 'auto') -> List[Dict[str, Any]]:
        """
        Get typeahead suggestions
        
        Args:
            query: Query string (minimum 2 characters)
            suggestion_type: Type of suggestions ('auto', 'case', 'citation', 'section', 'judge')
            
        Returns:
            List of suggestion objects
        """
        try:
            if not query or len(query.strip()) < 2:
                return []
            
            query = query.strip()
            
            if suggestion_type == 'auto':
                return self._get_auto_suggestions(query)
            elif suggestion_type == 'case':
                return self._get_case_suggestions(query)
            elif suggestion_type == 'citation':
                return self._get_citation_suggestions(query)
            elif suggestion_type == 'section':
                return self._get_section_suggestions(query)
            elif suggestion_type == 'judge':
                return self._get_judge_suggestions(query)
            else:
                return self._get_auto_suggestions(query)
                
        except Exception as e:
            logger.error(f"Error getting suggestions: {str(e)}")
            return []
    
    def _get_auto_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get automatic suggestions based on query"""
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
        
        # Try judge suggestions
        judge_suggestions = self._get_judge_suggestions(query)
        suggestions.extend(judge_suggestions)
        
        # Sort by relevance and limit
        suggestions.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return suggestions[:10]
    
    def _get_case_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get case number suggestions"""
        try:
            cases = Case.objects.filter(
                case_number__icontains=query
            ).values('case_number')[:5]
            
            return [
                {
                    'value': case['case_number'],
                    'type': 'case_number',
                    'canonical_key': case['case_number'],
                    'additional_info': f"Case number"
                }
                for case in cases if case['case_number']
            ]
            
        except Exception as e:
            logger.error(f"Error getting case suggestions: {str(e)}")
            return []
    
    def _get_citation_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get citation suggestions"""
        try:
            # Simple citation pattern matching
            if 'ppc' in query.lower() or 'cpc' in query.lower() or 'crpc' in query.lower():
                return [
                    {
                        'value': f"{query.upper()} 302",
                        'type': 'citation',
                        'canonical_key': f"{query.lower()}:302",
                        'additional_info': "Common legal citation"
                    }
                ]
            return []
            
        except Exception as e:
            logger.error(f"Error getting citation suggestions: {str(e)}")
            return []
    
    def _get_section_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get section suggestions"""
        try:
            # For now, return empty list - can be enhanced with actual section data
            return []
            
        except Exception as e:
            logger.error(f"Error getting section suggestions: {str(e)}")
            return []
    
    def _get_judge_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Get judge suggestions"""
        try:
            # For now, return empty list - can be enhanced with actual judge data
            return []
            
        except Exception as e:
            logger.error(f"Error getting judge suggestions: {str(e)}")
            return []
    
    def get_facet_statistics(self) -> Dict[str, Any]:
        """Get overall facet statistics"""
        try:
            stats = {
                'total_cases': Case.objects.count(),
                'total_courts': Court.objects.count(),
                'status_distribution': {},
                'year_distribution': {}
            }
            
            # Get status distribution
            status_counts = Case.objects.values('status').annotate(
                count=Count('id')
            )
            for status in status_counts:
                if status['status']:
                    stats['status_distribution'][status['status']] = status['count']
            
            # Get year distribution (last 10 years)
            from datetime import datetime, timedelta
            current_year = datetime.now().year
            
            for year in range(current_year - 9, current_year + 1):
                year_count = Case.objects.filter(
                    institution_date__year=year
                ).count()
                if year_count > 0:
                    stats['year_distribution'][str(year)] = year_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting facet statistics: {str(e)}")
            return {}
