from django.urls import path
from frontend.views import qa_views

urlpatterns = [
    # QA Interface
    path('qa/', qa_views.qa_interface, name='qa_interface'),
    path('qa/chat/', qa_views.qa_chat, name='qa_chat'),
    path('qa/analytics/', qa_views.qa_analytics, name='qa_analytics'),
    path('qa/sessions/', qa_views.qa_sessions, name='qa_sessions'),
    path('qa/simple/', qa_views.simple_qa_interface, name='simple_qa_interface'),
    
    # API endpoints
    path('api/qa/ask/', qa_views.qa_ask_question, name='qa_ask_question'),
]
