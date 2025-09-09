"""
Simple QA System URLs
"""

from django.urls import path
from simple_views import SimpleQAView, SimpleQAAPIView, SimpleDataView, SystemStatusView

urlpatterns = [
    path('', SimpleQAView.as_view(), name='qa_interface'),
    path('ask/', SimpleQAAPIView.as_view(), name='qa_ask'),
    path('data/', SimpleDataView.as_view(), name='qa_data'),
    path('status/', SystemStatusView.as_view(), name='qa_status'),
]
