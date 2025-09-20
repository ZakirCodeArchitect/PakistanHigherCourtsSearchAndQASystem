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
        return redirect('dashboard')
    return render(request, 'search/landing_page.html')


def login_view(request):
    """Handle user login with role-based authentication"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        identifier = request.POST.get('identifier')
        
        # Basic validation
        if not all([username, password, user_role, identifier]):
            return render(request, 'search/login.html', {
                'error': 'All fields are required'
            })
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Check if user has a profile
            try:
                from apps.accounts.models import UserProfile
                profile = user.profile
                
                # Verify role matches
                if profile.role != user_role:
                    return render(request, 'search/login.html', {
                        'error': f'Invalid role. Your account is registered as {profile.get_role_display()}'
                    })
                
                # Verify identifier
                if user_role == 'lawyer':
                    if profile.advocate_license_number != identifier:
                        return render(request, 'search/login.html', {
                            'error': 'Invalid advocate license number'
                        })
                elif user_role == 'general_public':
                    if profile.cnic != identifier:
                        return render(request, 'search/login.html', {
                            'error': 'Invalid CNIC'
                        })
                
                # Login successful
                login(request, user)
                
                # Store user role in session for access control
                request.session['user_role'] = user_role
                
                # Redirect based on role
                if user_role == 'lawyer':
                    return redirect('dashboard')  # Lawyers can access all modules
                else:
                    return redirect('law_info_module')  # General public only gets law info
                    
            except Exception as e:
                return render(request, 'search/login.html', {
                    'error': 'User profile not found. Please contact administrator.'
                })
        else:
            return render(request, 'search/login.html', {
                'error': 'Invalid username or password'
            })
    
    return render(request, 'search/login.html')


@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('landing_page')


@login_required
def dashboard(request):
    """Main dashboard after login"""
    return render(request, 'search/dashboard.html')


@login_required
def search_module(request):
    """Search module interface - Lawyers only"""
    # Check if user is a lawyer
    if request.session.get('user_role') != 'lawyer':
        return render(request, 'search/access_denied.html', {
            'message': 'Access denied. This module is only available for lawyers.',
            'user_role': request.session.get('user_role', 'unknown')
        })
    return render(request, 'search/search_module.html')


@login_required
def qa_module(request):
    """QA module interface - Lawyers only"""
    # Check if user is a lawyer
    if request.session.get('user_role') != 'lawyer':
        return render(request, 'search/access_denied.html', {
            'message': 'Access denied. This module is only available for lawyers.',
            'user_role': request.session.get('user_role', 'unknown')
        })
    # Redirect to the question answering module (separate Django project)
    # The QA module runs on a different port/project
    return redirect('/qa/')


def law_info_module(request):
    """Law Info module interface - Available to all users"""
    # This module is accessible to both lawyers and general public
    return redirect('http://localhost:8001/')


def benchmarking_module(request):
    """Benchmarking module interface"""
    # Redirect to the benchmarking dashboard
    return redirect('/search/benchmarking/')


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


@login_required
def case_details(request, case_id):
    """Display detailed information about a specific case"""
    try:
        # Get case details from backend API
        api_url = f"http://localhost:8000/api/search/case/{case_id}/"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            case_data = response.json()
            return render(request, 'search/case_details.html', {
                'case': case_data,
                'case_id': case_id
            })
        else:
            # Fallback: try to get basic case info from database directly
            try:
                from apps.cases.models import Case
                case = Case.objects.get(id=case_id)
                case_data = {
                    'case_id': case.id,
                    'case_number': case.case_number,
                    'case_title': case.case_title,
                    'status': case.status,
                    'court': case.court.name if case.court else None,
                    'institution_date': case.institution_date,
                    'hearing_date': case.hearing_date,
                    'bench': case.bench,
                    'sr_number': case.sr_number
                }
                return render(request, 'search/case_details.html', {
                    'case': case_data,
                    'case_id': case_id
                })
            except Case.DoesNotExist:
                return render(request, 'search/case_details.html', {
                    'case': {'case_id': case_id, 'error': 'Case not found'},
                    'case_id': case_id
                })
            
    except Exception as e:
        return render(request, 'search/case_details.html', {
            'case': {'case_id': case_id, 'error': str(e)},
            'case_id': case_id
        })
