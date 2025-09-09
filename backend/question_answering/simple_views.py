"""
Simple QA System Views - Basic functionality without complex models
"""

from django.http import JsonResponse, HttpResponse
from django.views import View
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import time
from sample_data import search_sample_data, get_sample_data
from services.enhanced_qa_engine import EnhancedQAEngine

class SimpleQAView(View):
    """Simple QA interface view"""
    
    def get(self, request):
        """Render the QA interface"""
        return render(request, 'question_answering/simple_qa_interface.html', {
            'title': 'Question Answering System',
            'message': 'Welcome to the QA System!'
        })

@method_decorator(csrf_exempt, name='dispatch')
class SimpleQAAPIView(View):
    """Enhanced QA API endpoint with AI integration"""
    
    def __init__(self):
        super().__init__()
        self.qa_engine = EnhancedQAEngine()
    
    def post(self, request):
        """Handle QA requests with AI integration"""
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            use_ai = data.get('use_ai', True)  # Default to using AI
            
            print(f"Processing question: '{question}' (AI: {use_ai})")
            
            # Use the enhanced QA engine
            result = self.qa_engine.ask_question(
                question=question,
                conversation_history=None,  # Could be added later
                use_ai=use_ai
            )
            
            # Add response ID
            result['response_id'] = f"resp_{int(time.time())}"
            
            print(f"Generated answer type: {result.get('answer_type', 'unknown')}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")
            print(f"Documents found: {result.get('documents_found', 0)}")
            
            return JsonResponse(result)
            
        except Exception as e:
            print(f"Error in QA API: {str(e)}")
            return JsonResponse({
                'question': data.get('question', ''),
                'answer': f"I apologize, but I encountered an error while processing your question: {str(e)}. Please try again.",
                'answer_type': 'error',
                'confidence': 0.0,
                'sources': [],
                'response_id': f"resp_{int(time.time())}",
                'status': 'error',
                'error': str(e)
            }, status=400)

class SimpleDataView(View):
    """View to show available sample data"""
    
    def get(self, request):
        """Show available legal documents"""
        data = get_sample_data()
        return JsonResponse({
            'total_documents': len(data),
            'documents': data,
            'status': 'success'
        })

class SystemStatusView(View):
    """View to show system status"""
    
    def __init__(self):
        super().__init__()
        self.qa_engine = EnhancedQAEngine()
    
    def get(self, request):
        """Show system status"""
        status = self.qa_engine.get_system_status()
        return JsonResponse({
            'system_status': status,
            'status': 'success'
        })
