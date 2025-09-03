from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import requests
from django.conf import settings


def landing_page(request):
    """Landing page with login option"""
    if request.user.is_authenticated:
        return redirect('frontend:dashboard')
    return render(request, 'frontend/landing_page.html')


def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('frontend:dashboard')
        else:
            return render(request, 'frontend/login.html', {
                'error': 'Invalid username or password'
            })
    
    return render(request, 'frontend/login.html')


@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('frontend:landing_page')


@login_required
def dashboard(request):
    """Main dashboard after login"""
    return render(request, 'frontend/dashboard.html')


@login_required
def search_module(request):
    """Search module interface"""
    return render(request, 'frontend/search_module.html')


@csrf_exempt
@require_http_methods(["POST"])
def search_api(request):
    """Frontend API endpoint for search"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        mode = data.get('mode', 'hybrid')
        filters = data.get('filters', {})
        offset = data.get('offset', 0)
        limit = data.get('limit', 10)
        
        # Forward request to backend search API
        backend_url = f"{request.build_absolute_uri('/').rstrip('/')}/api/search/search/"
        
        payload = {
            'q': query,
            'mode': mode,
            'filters': json.dumps(filters),
            'offset': offset,
            'limit': limit,
            'return_facets': 'true',
            'highlight': 'true'
        }
        
        response = requests.get(backend_url, params=payload)
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Search failed'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def suggestions_api(request):
    """Frontend API endpoint for suggestions"""
    try:
        query = request.GET.get('q', '')
        suggestion_type = request.GET.get('type', 'auto')
        
        # Forward request to backend suggestions API
        backend_url = f"{request.build_absolute_uri('/').rstrip('/')}/api/search/suggest/"
        
        payload = {
            'q': query,
            'type': suggestion_type
        }
        
        response = requests.get(backend_url, params=payload)
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Suggestions failed'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def filters_api(request):
    """Frontend API endpoint for filters"""
    try:
        # Forward request to backend status API to get filter information
        backend_url = f"{request.build_absolute_uri('/').rstrip('/')}/api/search/status/"
        
        response = requests.get(backend_url)
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Filters failed'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
