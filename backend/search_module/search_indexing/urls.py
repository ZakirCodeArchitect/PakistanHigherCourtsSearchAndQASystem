from django.urls import path
from .views import SearchAPIView, SuggestAPIView, CaseContextAPIView, SearchStatusAPIView

app_name = 'search_indexing'

urlpatterns = [
    # Main search endpoint
    path('search/', SearchAPIView.as_view(), name='search'),
    
    # Typeahead suggestions
    path('suggest/', SuggestAPIView.as_view(), name='suggest'),
    
    # Case context retrieval
    path('case/<int:case_id>/contexts/', CaseContextAPIView.as_view(), name='case_contexts'),
    
    # System status and health
    path('status/', SearchStatusAPIView.as_view(), name='status'),
]
