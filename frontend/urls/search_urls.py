from django.urls import path
from frontend.views import search_views

urlpatterns = [
    # Landing page
    path('', search_views.landing_page, name='landing_page'),
    
    # Dashboard after login
    path('dashboard/', search_views.dashboard, name='dashboard'),
    
    # Search module
    path('search/', search_views.search_module, name='search_module'),
    
    # QA module (Legal Knowledge Resource)
    path('qa/', search_views.qa_module, name='qa_module'),
    
    # Law Info module
    path('law-info/', search_views.law_info_module, name='law_info_module'),
    
    # Benchmarking module
    path('benchmarking/', search_views.benchmarking_module, name='benchmarking_module'),
    
    # Authentication
    path('login/', search_views.login_view, name='login'),
    path('logout/', search_views.logout_view, name='logout'),
    
    # API endpoints for frontend
    path('api/search/', search_views.search_api, name='search_api'),
    path('api/suggestions/', search_views.suggestions_api, name='suggestions_api'),
    path('api/filters/', search_views.filters_api, name='filters_api'),
    path('case/<int:case_id>/', search_views.case_details, name='case_details'),
]
