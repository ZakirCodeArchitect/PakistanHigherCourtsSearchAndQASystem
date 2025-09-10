"""
Simple QA System URLs
"""

from django.urls import path
from simple_views import SimpleQAView, SimpleQAAPIView, SimpleDataView, SystemStatusView, ConversationSessionView, ConversationHistoryView

urlpatterns = [
    path('', SimpleQAView.as_view(), name='qa_interface'),
    path('ask/', SimpleQAAPIView.as_view(), name='qa_ask'),
    path('data/', SimpleDataView.as_view(), name='qa_data'),
    path('status/', SystemStatusView.as_view(), name='qa_status'),
    
    # Conversation management endpoints
    path('sessions/', ConversationSessionView.as_view(), name='qa_sessions'),
    path('history/', ConversationHistoryView.as_view(), name='qa_history'),
]
