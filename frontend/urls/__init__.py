# Frontend URLs
from django.urls import path, include

urlpatterns = [
    # Search module URLs
    path('', include('frontend.urls.search_urls')),
    
    # QA module URLs
    path('', include('frontend.urls.qa_urls')),
    
    # Law Info module URLs
    path('', include('frontend.urls.law_info_urls')),
    
    # Benchmarking module URLs
    path('', include('frontend.urls.benchmarking_urls')),
]