from django.urls import path
from .views import (
    SearchAPIView, SuggestAPIView, CaseContextAPIView, SearchStatusAPIView, 
    CaseDetailsAPIView, DocumentViewAPIView, DocumentDownloadAPIView, 
    JudgementViewAPIView, JudgementDownloadAPIView, OrderDocumentAPIView
)

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
    
    # Case details
    path('case/<int:case_id>/', CaseDetailsAPIView.as_view(), name='case_details'),
    
    # Document viewing and downloading
    path('document/<int:case_id>/<int:document_id>/', DocumentViewAPIView.as_view(), name='document_view'),
    path('document/<int:case_id>/<int:document_id>/download/', DocumentDownloadAPIView.as_view(), name='document_download'),
    
    # Judgement viewing and downloading
    path('judgement/<int:case_id>/', JudgementViewAPIView.as_view(), name='judgement_view'),
    path('judgement/<int:case_id>/download/', JudgementDownloadAPIView.as_view(), name='judgement_download'),
    
    # Order document mapping
    path('order/<int:case_id>/<int:order_id>/document/', OrderDocumentAPIView.as_view(), name='order_document'),
]
