from django.urls import path
from frontend.views import law_info_views

urlpatterns = [
    # Law Information pages
    path('law-info/', law_info_views.LawHomeView.as_view(), name='law_home'),
    path('law-info/search/', law_info_views.LawSearchView.as_view(), name='law_search'),
    path('law-info/<slug:slug>/', law_info_views.LawDetailView.as_view(), name='law_detail'),
    
    # API endpoints
    path('api/law-info/suggestions/', law_info_views.law_suggestions_api, name='law_suggestions_api'),
    path('api/law-info/gpt-search/', law_info_views.gpt_enhanced_search_api, name='law_gpt_search_api'),
    path('api/law-info/track-click/', law_info_views.law_click_tracking_api, name='law_click_tracking_api'),
]
