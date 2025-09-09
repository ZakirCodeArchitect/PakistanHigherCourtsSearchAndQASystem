from django.apps import AppConfig


class QuestionAnsweringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'question_answering'
    verbose_name = 'Question Answering System'
    
    def ready(self):
        """Initialize QA system when Django starts"""
        try:
            from .services.qa_engine import QAEngine
            from .services.knowledge_retriever import KnowledgeRetriever
            from .services.answer_generator import AnswerGenerator
            
            # Initialize services
            self.qa_engine = QAEngine()
            self.knowledge_retriever = KnowledgeRetriever()
            self.answer_generator = AnswerGenerator()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"QA system initialization failed: {e}")
