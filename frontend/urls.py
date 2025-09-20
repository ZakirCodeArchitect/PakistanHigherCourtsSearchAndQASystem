# Frontend URLs Aggregator
from django.urls import path, include

app_name = 'frontend'

urlpatterns = [
    # Search module URLs
    path('', include('frontend.urls.search_urls')),
    
    # Other module URLs will be added as they are created
    # path('qa/', include('frontend.urls.qa_urls')),
    # path('law-info/', include('frontend.urls.law_info_urls')),
    # path('benchmarking/', include('frontend.urls.benchmarking_urls')),
]
