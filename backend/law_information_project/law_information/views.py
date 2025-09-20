"""
Views for Law Information Resource
Public-friendly legal information search and display
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from .models import Law, LawCategory, LawSearchLog
from .search_enhancements import LegalSearchEnhancer
from .gpt_integration import GPTLawAssistant

logger = logging.getLogger(__name__)


class LawSearchView(View):
    """
    Main search view for laws
    Public access - no authentication required
    """
    
    def get(self, request):
        """Display search interface and results"""
        query = request.GET.get('q', '').strip()
        page = request.GET.get('page', 1)
        search_type = request.GET.get('type', 'all')
        
        laws = Law.objects.filter(is_active=True)
        
        # Apply search filters
        if query:
            laws = self._apply_search_filters(laws, query, search_type)
            
            # Log the search
            self._log_search(query, search_type, laws.count(), request)
        
        # Order results
        laws = laws.order_by('-is_featured', 'title')
        
        # Paginate results
        paginator = Paginator(laws, 10)  # 10 results per page
        try:
            laws_page = paginator.page(page)
        except:
            laws_page = paginator.page(1)
        
        # Get featured laws for sidebar
        featured_laws = Law.objects.filter(
            is_active=True, 
            is_featured=True
        ).order_by('title')[:5]
        
        # Get popular tags
        popular_tags = self._get_popular_tags()
        
        context = {
            'laws': laws_page,
            'query': query,
            'search_type': search_type,
            'featured_laws': featured_laws,
            'popular_tags': popular_tags,
            'total_results': laws.count() if query else 0,
        }
        
        return render(request, 'law_info/search.html', context)

    def _apply_search_filters(self, queryset, query, search_type):
        """Apply enhanced search filters with Full-Text Search, ranking, and synonyms"""

        # Handle GPT search type
        if search_type == 'gpt':
            # For GPT search, we'll let the frontend handle it via API
            # Return empty queryset as GPT results will be shown via JavaScript
            return queryset.none()
        
        # Use the enhanced search functionality for other types
        return LegalSearchEnhancer.enhanced_search(queryset, query, search_type)
    
    
    def _log_search(self, query, search_type, results_count, request):
        """Log search query for analytics"""
        try:
            LawSearchLog.objects.create(
                query=query,
                search_type=search_type,
                results_count=results_count,
                user_ip=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
        except Exception as e:
            logger.error(f"Failed to log search: {e}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_popular_tags(self):
        """Get popular tags for display"""
        # This is a simple implementation
        # In production, you might want to cache this or use more sophisticated logic
        all_laws = Law.objects.filter(is_active=True)
        tag_counts = {}
        
        for law in all_laws:
            for tag in law.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Return top 10 tags
        return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]


class LawDetailView(View):
    """
    Detail view for individual law entries
    Public access - no authentication required
    """
    
    def get(self, request, slug):
        """Display detailed law information"""
        law = get_object_or_404(Law, slug=slug, is_active=True)
        
        # Get related laws (same tags or jurisdiction)
        related_laws = self._get_related_laws(law)
        
        # Get featured laws for sidebar
        featured_laws = Law.objects.filter(
            is_active=True, 
            is_featured=True
        ).exclude(id=law.id).order_by('title')[:5]
        
        context = {
            'law': law,
            'related_laws': related_laws,
            'featured_laws': featured_laws,
        }
        
        return render(request, 'law_info/detail.html', context)
    
    def _get_related_laws(self, law):
        """Get related laws based on tags and jurisdiction"""
        related = Law.objects.filter(
            is_active=True
        ).exclude(id=law.id)
        
        # Find laws with common tags
        if law.tags:
            tag_query = Q()
            for tag in law.tags:
                tag_query |= Q(tags__icontains=tag)
            related = related.filter(tag_query)
        
        # If no tag matches, find by jurisdiction
        if not related.exists():
            related = Law.objects.filter(
                is_active=True,
                jurisdiction=law.jurisdiction
            ).exclude(id=law.id)
        
        return related.order_by('title')[:5]


@csrf_exempt
@require_http_methods(["GET"])
def gpt_enhanced_search_api(request):
    """
    GPT-4o-mini enhanced search API
    Converts natural language to database queries and provides user-friendly answers
    """
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'error': 'Query too short'}, status=400)
        
        # Use GPT to enhance the search
        enhanced_results = GPTLawAssistant.enhanced_search_with_gpt(query)
        
        # Format results for API response
        results = []
        for item in enhanced_results:
            law = item['law']
            results.append({
                'id': str(law.id),
                'slug': law.slug,
                'title': law.title,
                'sections': law.sections,
                'punishment_summary': law.punishment_summary,
                'jurisdiction': law.jurisdiction,
                'tags': law.tags,
                'explanation': item['explanation'],
                'source': item['source'],
                'search_terms_used': item['search_terms_used']
            })
        
        return JsonResponse({
            'query': query,
            'results': results,
            'total_results': len(results),
            'enhanced_by_gpt': True
        })
        
    except Exception as e:
        logger.error(f"Error in GPT enhanced search API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def law_suggestions_api(request):
    """
    Enhanced API endpoint for search suggestions with synonyms
    Public access - no authentication required
    """
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'suggestions': []})
        
        # Get suggestions from titles and tags
        title_suggestions = Law.objects.filter(
            is_active=True,
            title__icontains=query
        ).values_list('title', flat=True)[:5]
        
        # Get GPT-powered suggestions
        gpt_suggestions = GPTLawAssistant.get_smart_suggestions(query)
        
        # Get tag suggestions with synonyms
        tag_suggestions = []
        expanded_words = LegalSearchEnhancer.expand_synonyms(query)
        
        for law in Law.objects.filter(is_active=True):
            for tag in law.tags:
                for word in expanded_words:
                    if word.lower() in tag.lower() and tag not in tag_suggestions:
                        tag_suggestions.append(tag)
                        if len(tag_suggestions) >= 5:
                            break
                if len(tag_suggestions) >= 5:
                    break
            if len(tag_suggestions) >= 5:
                break
        
        # Combine all suggestions
        all_suggestions = list(title_suggestions) + tag_suggestions[:5] + gpt_suggestions
        
        return JsonResponse({
            'suggestions': all_suggestions[:10],  # Limit to 10 total
            'expanded_terms': expanded_words[:5],  # Show expanded terms for debugging
            'gpt_suggestions': gpt_suggestions  # Show GPT suggestions
        })
        
    except Exception as e:
        logger.error(f"Error in suggestions API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def law_click_tracking_api(request):
    """
    API endpoint for tracking which law entries are clicked
    Public access - no authentication required
    """
    try:
        data = json.loads(request.body)
        law_id = data.get('law_id')
        query = data.get('query', '')
        
        if law_id:
            try:
                law = Law.objects.get(id=law_id, is_active=True)
                
                # Update the most recent search log with clicked result
                recent_search = LawSearchLog.objects.filter(
                    query=query
                ).order_by('-created_at').first()
                
                if recent_search:
                    recent_search.clicked_result = law
                    recent_search.save()
                
                return JsonResponse({'status': 'success'})
                
            except Law.DoesNotExist:
                return JsonResponse({'error': 'Law not found'}, status=404)
        
        return JsonResponse({'error': 'Invalid data'}, status=400)
        
    except Exception as e:
        logger.error(f"Error in click tracking API: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def law_home_view(request):
    """
    Home page for Law Information Resource
    Public access - no authentication required
    """
    # Get featured laws
    featured_laws = Law.objects.filter(
        is_active=True, 
        is_featured=True
    ).order_by('title')[:6]
    
    # Get recent laws
    recent_laws = Law.objects.filter(
        is_active=True
    ).order_by('-updated_at')[:6]
    
    # Get total counts
    total_laws_count = Law.objects.filter(is_active=True).count()
    total_categories_count = LawCategory.objects.filter(is_active=True).count()
    
    # Get popular tags
    all_laws = Law.objects.filter(is_active=True)
    tag_counts = {}
    
    for law in all_laws:
        for tag in law.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    context = {
        'featured_laws': featured_laws,
        'recent_laws': recent_laws,
        'popular_tags': popular_tags,
        'total_laws_count': total_laws_count,
        'total_categories_count': total_categories_count,
    }
    
    return render(request, 'law_info/home.html', context)