"""
URL configuration for Law Information Resource
"""

from django.urls import path
from . import views

app_name = 'law_information'

urlpatterns = [
    # Home page
    path('', views.law_home_view, name='home'),
    
    # Law search interface (renamed to avoid conflict)
    path('law-search/', views.LawSearchView.as_view(), name='search'),
    
    # Law detail pages
    path('<slug:slug>/', views.LawDetailView.as_view(), name='law_detail'),
    
    # API endpoints (renamed to avoid conflicts)
    path('api/law-suggestions/', views.law_suggestions_api, name='suggestions_api'),
    path('api/law-gpt-search/', views.gpt_enhanced_search_api, name='gpt_search_api'),
    path('api/law-track-click/', views.law_click_tracking_api, name='click_tracking_api'),
]
