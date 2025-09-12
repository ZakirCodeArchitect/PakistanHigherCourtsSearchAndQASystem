from django.urls import path, include
import views

app_name = 'question_answering'

urlpatterns = [
    # Main QA endpoints
    path('api/qa/', include([
        # Session management
        path('sessions/', views.QASessionListCreateView.as_view(), name='session_list_create'),
        path('sessions/<str:session_id>/', views.QASessionDetailView.as_view(), name='session_detail'),
        path('sessions/<str:session_id>/queries/', views.QAQueryListCreateView.as_view(), name='query_list_create'),
        
        # Question answering
        path('ask/', views.QAAskView.as_view(), name='ask_question'),
        path('ask/stream/', views.QAAskStreamView.as_view(), name='ask_question_stream'),
        
        # Query management
        path('queries/<int:query_id>/', views.QAQueryDetailView.as_view(), name='query_detail'),
        path('queries/<int:query_id>/response/', views.QAResponseDetailView.as_view(), name='response_detail'),
        
        # Feedback
        path('responses/<int:response_id>/feedback/', views.QAFeedbackView.as_view(), name='response_feedback'),
        
        # Knowledge base
        path('knowledge/', views.QAKnowledgeBaseView.as_view(), name='knowledge_base'),
        path('knowledge/search/', views.QAKnowledgeSearchView.as_view(), name='knowledge_search'),
        
        # System status
        path('status/', views.QAStatusView.as_view(), name='qa_status'),
        path('health/', views.QAHealthView.as_view(), name='qa_health'),
        
        # Analytics
        path('analytics/', views.QAAnalyticsView.as_view(), name='qa_analytics'),
        path('metrics/', views.QAMetricsView.as_view(), name='qa_metrics'),
        
        # QA Knowledge Base endpoints
        path('kb/', include('question_answering.urls.qa_knowledge_base_urls')),
    ])),
    
    # Frontend routes
    path('', views.QAInterfaceView.as_view(), name='qa_interface'),
    path('chat/', views.QAChatView.as_view(), name='qa_chat'),
    path('sessions/', views.QASessionsView.as_view(), name='qa_sessions'),
    path('analytics/', views.QAAnalyticsDashboardView.as_view(), name='qa_analytics_dashboard'),
]
