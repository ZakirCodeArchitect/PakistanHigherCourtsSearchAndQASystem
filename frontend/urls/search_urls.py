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
    
    # Admin functionality
    path('system-admin/login/', search_views.admin_login, name='admin_login'),
    path('system-admin/dashboard/', search_views.admin_dashboard, name='admin_dashboard'),
    path('system-admin/benchmark/', search_views.admin_benchmark, name='admin_benchmark'),
    path('system-admin/users/', search_views.admin_users, name='admin_users'),
    path('system-admin/users/add/', search_views.admin_add_user, name='admin_add_user'),
    path('system-admin/users/edit/<int:user_id>/', search_views.admin_edit_user, name='admin_edit_user'),
    path('system-admin/users/delete/<int:user_id>/', search_views.admin_delete_user, name='admin_delete_user'),
    
    # Law Information Management
    path('system-admin/law-info/', search_views.admin_law_info, name='admin_law_info'),
    path('system-admin/law-info/add/', search_views.admin_add_law, name='admin_add_law'),
    path('system-admin/law-info/edit/<uuid:law_id>/', search_views.admin_edit_law, name='admin_edit_law'),
    path('system-admin/law-info/delete/<uuid:law_id>/', search_views.admin_delete_law, name='admin_delete_law'),
    
    # API endpoints for frontend
    path('api/search/', search_views.search_api, name='search_api'),
    path('api/suggestions/', search_views.suggestions_api, name='suggestions_api'),
    path('api/filters/', search_views.filters_api, name='filters_api'),
    path('case/<int:case_id>/', search_views.case_details, name='case_details'),
]
