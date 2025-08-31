"""
Normalized Facet Service
Optimized service for handling normalized facet tables
"""

import logging
from typing import List, Dict, Optional, Set
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from ..models import FacetTerm, FacetMapping
from apps.cases.models import Term, TermOccurrence

logger = logging.getLogger(__name__)


class NormalizedFacetService:
    """Service for optimized facet operations using normalized tables"""
    
    def __init__(self):
        self.facet_types = [
            'section', 'judge', 'court', 'party', 'advocate',
            'case_type', 'year', 'status', 'bench_type', 'appeal', 
            'petitioner', 'legal_issue'
        ]
    
    def build_normalized_facets(self, facet_type: str = None) -> Dict[str, any]:
        """Build normalized facet tables from existing Term data"""
        stats = {
            'facet_type': facet_type or 'all',
            'terms_processed': 0,
            'mappings_created': 0,
            'errors': [],
            'success': False
        }
        
        try:
            with transaction.atomic():
                # Process specific facet type or all
                types_to_process = [facet_type] if facet_type else self.facet_types
                
                for ft in types_to_process:
                    logger.info(f"Building normalized facets for: {ft}")
                    
                    # Get terms for this facet type
                    terms = Term.objects.filter(type=ft)
                    
                    for term in terms:
                        # Get case IDs where this term appears
                        case_ids = TermOccurrence.objects.filter(
                            term=term
                        ).values_list('case_id', flat=True).distinct()
                        
                        if case_ids:
                            # Create or update FacetTerm
                            facet_term, created = FacetTerm.objects.get_or_create(
                                facet_type=ft,
                                canonical_term=term.canonical,
                                defaults={
                                    'occurrence_count': term.occurrence_count,
                                    'case_count': len(case_ids),
                                    'boost_factor': min(2.0, 1.0 + (len(case_ids) / 100.0)),
                                    'is_active': True
                                }
                            )
                            
                            if not created:
                                # Update existing term
                                facet_term.occurrence_count = term.occurrence_count
                                facet_term.case_count = len(case_ids)
                                facet_term.boost_factor = min(2.0, 1.0 + (len(case_ids) / 100.0))
                                facet_term.updated_at = timezone.now()
                                facet_term.save()
                            
                            # Create mappings
                            mappings_created = 0
                            for case_id in case_ids:
                                # Get occurrence count for this case
                                case_occurrence_count = TermOccurrence.objects.filter(
                                    term=term, case_id=case_id
                                ).count()
                                
                                # Create or update mapping
                                mapping, mapping_created = FacetMapping.objects.get_or_create(
                                    facet_term=facet_term,
                                    case_id=case_id,
                                    defaults={'occurrence_count': case_occurrence_count}
                                )
                                
                                if not mapping_created:
                                    # Update existing mapping
                                    mapping.occurrence_count = case_occurrence_count
                                    mapping.save()
                                
                                mappings_created += 1
                            
                            stats['terms_processed'] += 1
                            stats['mappings_created'] += mappings_created
                
                stats['success'] = True
                logger.info(f"Normalized facets built successfully: {stats}")
                
        except Exception as e:
            error_msg = f"Error building normalized facets: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def search_by_facet(self, facet_type: str, term: str, top_k: int = 10) -> List[Dict]:
        """Search cases by facet using normalized tables"""
        try:
            # Find the facet term
            facet_term = FacetTerm.objects.filter(
                facet_type=facet_type,
                canonical_term__icontains=term,
                is_active=True
            ).first()
            
            if not facet_term:
                return []
            
            # Get case mappings with occurrence counts
            mappings = FacetMapping.objects.filter(
                facet_term=facet_term
            ).select_related('facet_term').order_by('-occurrence_count')[:top_k]
            
            results = []
            for mapping in mappings:
                results.append({
                    'case_id': mapping.case_id,
                    'facet_type': facet_type,
                    'term': facet_term.canonical_term,
                    'occurrence_count': mapping.occurrence_count,
                    'boost_factor': facet_term.boost_factor,
                    'score': mapping.occurrence_count * facet_term.boost_factor
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in facet search: {str(e)}")
            return []
    
    def get_facet_stats(self, facet_type: str = None) -> Dict:
        """Get statistics for facet terms"""
        try:
            query = FacetTerm.objects.filter(is_active=True)
            if facet_type:
                query = query.filter(facet_type=facet_type)
            
            stats = {
                'total_terms': query.count(),
                'total_mappings': FacetMapping.objects.filter(
                    facet_term__in=query
                ).count(),
                'facet_types': list(query.values_list('facet_type', flat=True).distinct()),
                'top_terms': []
            }
            
            # Get top terms by case count
            top_terms = query.order_by('-case_count')[:10]
            stats['top_terms'] = [
                {
                    'term': term.canonical_term,
                    'facet_type': term.facet_type,
                    'case_count': term.case_count,
                    'occurrence_count': term.occurrence_count
                }
                for term in top_terms
            ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting facet stats: {str(e)}")
            return {}
    
    def get_case_facets(self, case_id: int) -> Dict[str, List[str]]:
        """Get all facets for a specific case"""
        try:
            mappings = FacetMapping.objects.filter(
                case_id=case_id
            ).select_related('facet_term')
            
            case_facets = {}
            for mapping in mappings:
                facet_type = mapping.facet_term.facet_type
                if facet_type not in case_facets:
                    case_facets[facet_type] = []
                
                case_facets[facet_type].append({
                    'term': mapping.facet_term.canonical_term,
                    'occurrence_count': mapping.occurrence_count,
                    'boost_factor': mapping.facet_term.boost_factor
                })
            
            return case_facets
            
        except Exception as e:
            logger.error(f"Error getting case facets: {str(e)}")
            return {}
    
    def cleanup_old_mappings(self) -> Dict:
        """Clean up orphaned mappings"""
        try:
            # Find mappings where case_id doesn't exist in cases table
            from apps.cases.models import Case
            
            existing_case_ids = set(Case.objects.values_list('id', flat=True))
            orphaned_mappings = FacetMapping.objects.exclude(
                case_id__in=existing_case_ids
            )
            
            orphaned_count = orphaned_mappings.count()
            orphaned_mappings.delete()
            
            # Update case counts for affected terms
            self._update_case_counts()
            
            return {
                'orphaned_mappings_removed': orphaned_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up mappings: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _update_case_counts(self):
        """Update case counts for all facet terms"""
        try:
            for facet_term in FacetTerm.objects.all():
                actual_count = FacetMapping.objects.filter(
                    facet_term=facet_term
                ).count()
                
                if facet_term.case_count != actual_count:
                    facet_term.case_count = actual_count
                    facet_term.save()
                    
        except Exception as e:
            logger.error(f"Error updating case counts: {str(e)}")
    
    def get_facet_suggestions(self, facet_type: str, query: str, limit: int = 10) -> List[str]:
        """Get facet term suggestions for autocomplete"""
        try:
            suggestions = FacetTerm.objects.filter(
                facet_type=facet_type,
                canonical_term__icontains=query,
                is_active=True
            ).order_by('-case_count')[:limit]
            
            return [term.canonical_term for term in suggestions]
            
        except Exception as e:
            logger.error(f"Error getting facet suggestions: {str(e)}")
            return []
