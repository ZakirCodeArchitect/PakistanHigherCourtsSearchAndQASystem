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
from services.conversation_manager import ConversationManager

class SimpleQAView(View):
    """Simple QA interface view"""
    
    def get(self, request):
        """Render the QA interface"""
        return render(request, 'qa/simple_qa_interface.html', {
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
        """Handle QA requests with AI integration and conversation management"""
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            use_ai = data.get('use_ai', True)  # Default to using AI
            use_advanced_rag = data.get('use_advanced_rag', True)  # Default to using Advanced RAG
            session_id = data.get('session_id')
            user_id = data.get('user_id', 'anonymous')
            
            print(f"Processing question: '{question}' (AI: {use_ai}, Session: {session_id})")
            
            # Use the enhanced QA engine with conversation management
            result = self.qa_engine.ask_question(
                question=question,
                conversation_history=None,
                use_ai=use_ai,
                use_advanced_rag=use_advanced_rag,
                session_id=session_id,
                user_id=user_id
            )
            
            # Add response ID
            result['response_id'] = f"resp_{int(time.time())}"
            
            print(f"Generated answer type: {result.get('answer_type', 'unknown')}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")
            print(f"Documents found: {result.get('documents_found', 0)}")
            print(f"Session ID: {result.get('session_id', 'None')}")
            print(f"Is follow-up: {result.get('is_follow_up', False)}")
            
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

@method_decorator(csrf_exempt, name='dispatch')
class ConversationSessionView(View):
    """View to manage conversation sessions"""
    
    def __init__(self):
        super().__init__()
        self.conversation_manager = ConversationManager()
    
    def post(self, request):
        """Create a new conversation session"""
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id', 'anonymous')
            title = data.get('title')
            description = data.get('description')
            # Default to creating a fresh session unless the client explicitly opts into reuse
            force_new = bool(data.get('force_new', True))
            
            # Reuse the most recent active session for this user only if explicitly requested
            if not force_new:
                try:
                    existing = self.conversation_manager.get_or_create_active_session_for_user(user_id)
                    if existing:
                        return JsonResponse({
                            'session_id': existing.session_id,
                            'user_id': existing.user_id,
                            'title': existing.title,
                            'description': existing.description,
                            'created_at': existing.created_at.isoformat(),
                            'status': 'success',
                            'reused': True
                        })
                except Exception:
                    # Fall back to creating a new session
                    pass
            
            session = self.conversation_manager.create_session(user_id, title, description)
            
            return JsonResponse({
                'session_id': session.session_id,
                'user_id': session.user_id,
                'title': session.title,
                'description': session.description,
                'created_at': session.created_at.isoformat(),
                'status': 'success',
                'reused': False
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error creating session: {str(e)}',
                'status': 'error'
            }, status=500)
    
    def get(self, request):
        """Get session information"""
        try:
            session_id = request.GET.get('session_id')
            user_id = request.GET.get('user_id', 'anonymous')
            
            if session_id:
                session = self.conversation_manager.get_or_create_session(user_id, session_id)
                stats = self.conversation_manager.get_session_statistics(session)
                
                return JsonResponse({
                    'session': {
                        'session_id': session.session_id,
                        'user_id': session.user_id,
                        'title': session.title,
                        'description': session.description,
                        'total_queries': session.total_queries,
                        'success_rate': session.success_rate,
                        'duration': str(session.duration),
                        'created_at': session.created_at.isoformat(),
                        'last_activity': session.last_activity.isoformat() if session.last_activity else None
                    },
                    'statistics': stats,
                    'status': 'success'
                })
            else:
                # Get all sessions for user
                sessions = self.conversation_manager.get_user_sessions(user_id)
                session_list = []
                
                for session in sessions:
                    session_list.append({
                        'session_id': session.session_id,
                        'title': session.title,
                        'total_queries': session.total_queries,
                        'success_rate': session.success_rate,
                        'last_activity': session.last_activity.isoformat() if session.last_activity else None
                    })
                
                return JsonResponse({
                    'sessions': session_list,
                    'status': 'success'
                })
                
        except Exception as e:
            return JsonResponse({
                'error': f'Error getting session: {str(e)}',
                'status': 'error'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ConversationHistoryView(View):
    """View to get conversation history"""
    
    def __init__(self):
        super().__init__()
        self.conversation_manager = ConversationManager()
    
    def get(self, request):
        """Get conversation history for a session"""
        try:
            session_id = request.GET.get('session_id')
            user_id = request.GET.get('user_id', 'anonymous')
            
            if not session_id:
                return JsonResponse({
                    'error': 'Session ID is required',
                    'status': 'error'
                }, status=400)
            
            session = self.conversation_manager.get_or_create_session(user_id, session_id)
            history = self.conversation_manager.get_session_history(session)
            
            return JsonResponse({
                'session_id': session_id,
                'history': history,
                'total_turns': len(history),
                'status': 'success'
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error getting history: {str(e)}',
                'status': 'error'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class RAGTestView(View):
    """RAG System Testing View - Test the Advanced RAG Engine directly"""
    
    def __init__(self):
        super().__init__()
        self.qa_engine = EnhancedQAEngine()
    
    def post(self, request):
        """Test the RAG system with specific queries"""
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            test_type = data.get('test_type', 'full')  # 'full', 'retrieval_only', 'generation_only'
            
            print(f"RAG Test - Question: '{question}', Type: {test_type}")
            
            # Test the RAG system
            if test_type == 'full':
                # Full RAG pipeline test
                result = self.qa_engine.ask_question(
                    question=question,
                    use_ai=True,
                    use_advanced_rag=True,
                    user_id='rag_test_user'
                )
            elif test_type == 'retrieval_only':
                # Test only retrieval
                search_results = self.qa_engine.search_only(question, top_k=5)
                result = {
                    'question': question,
                    'answer': f'Retrieval test completed. Found {len(search_results)} documents.',
                    'answer_type': 'retrieval_test',
                    'sources': search_results,
                    'test_type': 'retrieval_only'
                }
            else:
                # Generation only test (would need to be implemented)
                result = {
                    'question': question,
                    'answer': 'Generation-only test not yet implemented.',
                    'answer_type': 'generation_test',
                    'test_type': 'generation_only'
                }
            
            # Add test metadata
            result['test_timestamp'] = int(time.time())
            result['test_type'] = test_type
            result['rag_enabled'] = True
            
            print(f"RAG Test Result - Type: {result.get('answer_type')}, Sources: {len(result.get('sources', []))}")
            
            return JsonResponse(result)
            
        except Exception as e:
            print(f"Error in RAG Test: {str(e)}")
            return JsonResponse({
                'question': data.get('question', ''),
                'answer': f'RAG Test Error: {str(e)}',
                'answer_type': 'error',
                'test_type': data.get('test_type', 'full'),
                'error': str(e),
                'status': 'error'
            }, status=400)
    
    def get(self, request):
        """Get RAG system status and test information"""
        try:
            # Get system status
            status = self.qa_engine.get_system_status()
            
            # Add RAG-specific test information
            rag_test_info = {
                'rag_system_status': 'operational',
                'available_test_types': ['full', 'retrieval_only', 'generation_only'],
                'sample_queries': [
                    'What is a writ petition under Article 199?',
                    'What are the grounds for divorce in Pakistan?',
                    'How to file an FIR in Pakistan?',
                    'What are tenant rights under Rent Restriction Act?',
                    'How to register a company in Pakistan?'
                ],
                'api_usage': {
                    'endpoint': '/qa/rag-test/',
                    'method': 'POST',
                    'parameters': {
                        'question': 'string (required)',
                        'test_type': 'string (optional: full, retrieval_only, generation_only)'
                    }
                }
            }
            
            return JsonResponse({
                'status': 'success',
                'system_status': status,
                'rag_test_info': rag_test_info
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error getting RAG test info: {str(e)}',
                'status': 'error'
            }, status=500)
