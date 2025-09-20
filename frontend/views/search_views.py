from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction
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


# ===== ADMIN FUNCTIONALITY =====

def admin_login(request):
    """Admin login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username == 'admin' and password == 'admin123':  # Simple admin credentials
            # Create or get admin user
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={
                    'is_staff': True,
                    'is_superuser': True,
                    'email': 'admin@phc-system.com'
                }
            )
            admin_user.set_password('admin123')
            admin_user.save()
            
            # Log in the admin user
            login(request, admin_user)
            messages.success(request, 'Welcome to Admin Dashboard!')
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid admin credentials!')
    
    return render(request, 'admin/admin_login.html')


@login_required
def admin_dashboard(request):
    """Admin dashboard with overview and quick access"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    # Get basic statistics
    total_users = User.objects.filter(is_superuser=False).count()
    admin_users = User.objects.filter(is_superuser=True).count()
    
    context = {
        'total_users': total_users,
        'admin_users': admin_users,
        'recent_users': User.objects.filter(is_superuser=False).order_by('-date_joined')[:5]
    }
    
    return render(request, 'admin/admin_dashboard.html', context)


@login_required
def admin_benchmark(request):
    """Query benchmark collection management"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    # For now, redirect to the existing benchmarking module
    return redirect('benchmarking_module')


@login_required
def admin_users(request):
    """User management - list all users"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    users = User.objects.filter(is_superuser=False).select_related('profile').order_by('-date_joined')
    
    context = {
        'users': users
    }
    
    return render(request, 'admin/admin_users.html', context)


@login_required
def admin_add_user(request):
    """Add new user"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        user_role = request.POST.get('user_role')
        identifier = request.POST.get('identifier')
        
        # Debug: Print received data
        print(f"Received data: username={username}, email={email}, user_role={user_role}, identifier={identifier}")
        
        # Validate required fields
        if not username or not email or not password or not user_role:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'admin/admin_add_user.html')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists. Please choose a different username.')
            return render(request, 'admin/admin_add_user.html')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists. Please use a different email address.')
            return render(request, 'admin/admin_add_user.html')
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Create user profile if apps.accounts exists
                try:
                    from apps.accounts.models import UserProfile
                    
                    # Map user_role to the correct UserProfile role
                    profile_role = 'general_public'
                    if user_role == 'lawyer':
                        profile_role = 'lawyer'
                    
                    profile = UserProfile.objects.create(
                        user=user,
                        role=profile_role,
                        advocate_license_number=identifier if user_role == 'lawyer' else None,
                        cnic=identifier if user_role == 'judge' or user_role == 'public' else None,
                        full_name=f"{first_name} {last_name}".strip()
                    )
                except ImportError:
                    # If UserProfile doesn't exist, just create the user
                    pass
                
                messages.success(request, f'User {username} created successfully!')
                return redirect('admin_users')
                
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            print(f"Error creating user: {str(e)}")  # Debug output
    
    return render(request, 'admin/admin_add_user.html')


@login_required
def admin_edit_user(request, user_id):
    """Edit existing user"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        
        # Update password if provided
        new_password = request.POST.get('password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        
        # Update profile if exists
        try:
            from apps.accounts.models import UserProfile
            profile = user.profile
            user_role = request.POST.get('user_role')
            identifier = request.POST.get('identifier')
            
            # Map user_role to the correct UserProfile role
            profile_role = 'general_public'
            if user_role == 'lawyer':
                profile_role = 'lawyer'
            
            profile.role = profile_role
            profile.full_name = f"{user.first_name} {user.last_name}".strip()
            
            if user_role == 'lawyer':
                profile.advocate_license_number = identifier
                profile.cnic = None
            elif user_role == 'judge' or user_role == 'public':
                profile.cnic = identifier
                profile.advocate_license_number = None
            else:
                profile.cnic = identifier
                profile.advocate_license_number = None
                
            profile.save()
        except (ImportError, AttributeError):
            pass
        
        messages.success(request, f'User {user.username} updated successfully!')
        return redirect('admin_users')
    
    context = {
        'user': user
    }
    
    return render(request, 'admin/admin_edit_user.html', context)


@login_required
def admin_delete_user(request, user_id):
    """Delete user"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully!')
        return redirect('admin_users')
    
    context = {
        'user': user
    }
    
    return render(request, 'admin/admin_delete_user.html', context)


# Law Information Management Views

@login_required
def admin_law_info(request):
    """Law information management - list all laws"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    try:
        from law_information.models import Law
        laws = Law.objects.all().order_by('-updated_at')
    except ImportError:
        laws = []
        messages.error(request, 'Law information models not found.')
    
    context = {
        'laws': laws
    }
    
    return render(request, 'admin/admin_law_info.html', context)


@login_required
def admin_add_law(request):
    """Add new law information"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    if request.method == 'POST':
        try:
            from law_information.models import Law, LawCategory
            
            slug = request.POST.get('slug')
            title = request.POST.get('title')
            punishment_summary = request.POST.get('punishment_summary')
            jurisdiction = request.POST.get('jurisdiction')
            rights_summary = request.POST.get('rights_summary')
            what_to_do = request.POST.get('what_to_do')
            
            # Handle sections (comma-separated)
            sections_text = request.POST.get('sections', '')
            sections = [s.strip() for s in sections_text.split(',') if s.strip()]
            
            # Handle tags (comma-separated)
            tags_text = request.POST.get('tags', '')
            tags = [t.strip() for t in tags_text.split(',') if t.strip()]
            
            # Handle category
            category_id = request.POST.get('category')
            category = None
            if category_id:
                category = LawCategory.objects.get(id=category_id)
            
            with transaction.atomic():
                law = Law.objects.create(
                    slug=slug,
                    title=title,
                    sections=sections,
                    punishment_summary=punishment_summary,
                    jurisdiction=jurisdiction,
                    rights_summary=rights_summary,
                    what_to_do=what_to_do,
                    tags=tags,
                    category=category
                )
                
                messages.success(request, f'Law "{title}" created successfully!')
                return redirect('admin_law_info')
                
        except Exception as e:
            messages.error(request, f'Error creating law: {str(e)}')
    
    try:
        from law_information.models import LawCategory
        categories = LawCategory.objects.filter(is_active=True).order_by('name')
    except ImportError:
        categories = []
    
    context = {
        'categories': categories
    }
    
    return render(request, 'admin/admin_add_law.html', context)


@login_required
def admin_edit_law(request, law_id):
    """Edit existing law information"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    try:
        from law_information.models import Law, LawCategory
        law = get_object_or_404(Law, id=law_id)
    except ImportError:
        messages.error(request, 'Law information models not found.')
        return redirect('admin_law_info')
    
    if request.method == 'POST':
        law.slug = request.POST.get('slug')
        law.title = request.POST.get('title')
        law.punishment_summary = request.POST.get('punishment_summary')
        law.jurisdiction = request.POST.get('jurisdiction')
        law.rights_summary = request.POST.get('rights_summary')
        law.what_to_do = request.POST.get('what_to_do')
        
        # Handle sections (comma-separated)
        sections_text = request.POST.get('sections', '')
        law.sections = [s.strip() for s in sections_text.split(',') if s.strip()]
        
        # Handle tags (comma-separated)
        tags_text = request.POST.get('tags', '')
        law.tags = [t.strip() for t in tags_text.split(',') if t.strip()]
        
        # Handle category
        category_id = request.POST.get('category')
        if category_id:
            try:
                law.category = LawCategory.objects.get(id=category_id)
            except LawCategory.DoesNotExist:
                law.category = None
        else:
            law.category = None
        
        law.save()
        
        messages.success(request, f'Law "{law.title}" updated successfully!')
        return redirect('admin_law_info')
    
    categories = LawCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'law': law,
        'categories': categories,
        'sections_display': ', '.join(law.sections) if law.sections else '',
        'tags_display': ', '.join(law.tags) if law.tags else ''
    }
    
    return render(request, 'admin/admin_edit_law.html', context)


@login_required
def admin_delete_law(request, law_id):
    """Delete law information"""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('landing_page')
    
    try:
        from law_information.models import Law
        law = get_object_or_404(Law, id=law_id)
    except ImportError:
        messages.error(request, 'Law information models not found.')
        return redirect('admin_law_info')
    
    if request.method == 'POST':
        title = law.title
        law.delete()
        messages.success(request, f'Law "{title}" deleted successfully!')
        return redirect('admin_law_info')
    
    context = {
        'law': law
    }
    
    return render(request, 'admin/admin_delete_law.html', context)
