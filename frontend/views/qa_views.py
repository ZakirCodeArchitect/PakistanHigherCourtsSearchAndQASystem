"""
QA Module Views
Views for the Question Answering system frontend
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests


@login_required
def qa_interface(request):
    """Main QA interface"""
    return render(request, 'qa/qa_interface.html')


@login_required
def qa_chat(request):
    """QA Chat interface"""
    return render(request, 'qa/qa_chat.html')


@login_required
def qa_analytics(request):
    """QA Analytics dashboard"""
    return render(request, 'qa/qa_analytics.html')


@login_required
def qa_sessions(request):
    """QA Sessions management"""
    return render(request, 'qa/qa_sessions.html')


@login_required
def simple_qa_interface(request):
    """Simple QA interface"""
    return render(request, 'qa/simple_qa_interface.html')


@login_required
@csrf_exempt
def qa_ask_question(request):
    """API endpoint to ask questions"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            
            # Here you would integrate with the actual QA backend
            # For now, return a mock response
            response = {
                'answer': f"This is a mock response to: {question}",
                'confidence': 0.85,
                'sources': []
            }
            
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
