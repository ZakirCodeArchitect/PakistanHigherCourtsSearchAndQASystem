from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Landing page
    path('', views.landing_page, name='landing_page'),
    
    # Dashboard after login
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Search module
    path('search/', views.search_module, name='search_module'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints for frontend
    path('api/search/', views.search_api, name='search_api'),
    path('api/suggestions/', views.suggestions_api, name='suggestions_api'),
    path('api/filters/', views.filters_api, name='filters_api'),
    path('case/<int:case_id>/', views.case_details, name='case_details'),
]
