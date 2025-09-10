"""
Question-Answering System Models
Database models for storing QA sessions, queries, responses, and knowledge base
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class QASession(models.Model):
    """Represents a conversation session between user and QA system"""
    
    # Session identification
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    user_id = models.CharField(max_length=100, db_index=True, default='anonymous')
    
    # Session metadata
    title = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')
    
    # Session context
    context_data = models.JSONField(default=dict, blank=True)  # Legal domain, court focus, etc.
    conversation_history = models.JSONField(default=list, blank=True)  # Full conversation
    
    # Session status
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    
    # Performance metrics
    total_queries = models.IntegerField(default=0)
    successful_queries = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    user_satisfaction_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"QA Session {self.session_id[:8]} - {self.user_id}"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_queries > 0:
            return (self.successful_queries / self.total_queries) * 100
        return 0.0
    
    @property
    def duration(self):
        """Calculate session duration"""
        if self.last_activity and self.created_at:
            return self.last_activity - self.created_at
        return timedelta(0)
    
    def add_conversation_turn(self, query, response, context_documents=None, query_id=None, response_id=None):
        """Add a conversation turn to the session history"""
        turn = {
            'timestamp': timezone.now().isoformat(),
            'query': query,
            'response': response,
            'context_documents': context_documents or [],
            'query_id': query_id,
            'response_id': response_id
        }
        
        if not self.conversation_history:
            self.conversation_history = []
        
        self.conversation_history.append(turn)
        self.total_queries += 1
        self.last_activity = timezone.now()
        self.save()
    
    def get_recent_context(self, max_turns=5):
        """Get recent conversation context for follow-up queries"""
        if not self.conversation_history:
            return []
        
        recent_turns = self.conversation_history[-max_turns:]
        context = []
        
        for turn in recent_turns:
            context.append({
                'query': turn.get('query', ''),
                'response': turn.get('response', ''),
                'timestamp': turn.get('timestamp', '')
            })
        
        return context
    
    def get_context_summary(self, max_turns=3):
        """Get a summary of the conversation context for AI prompts"""
        if not self.conversation_history:
            return ""
        
        recent_turns = self.conversation_history[-max_turns:]
        summary = "Previous conversation context:\n"
        
        for i, turn in enumerate(recent_turns, 1):
            summary += f"{i}. Q: {turn.get('query', '')}\n"
            response_preview = turn.get('response', '')
            if len(response_preview) > 200:
                response_preview = response_preview[:200] + "..."
            summary += f"   A: {response_preview}\n\n"
        
        return summary
    
    def get_conversation_topics(self):
        """Extract main topics from conversation history"""
        topics = set()
        for turn in self.conversation_history:
            query = turn.get('query', '').lower()
            # Simple topic extraction based on keywords
            if 'writ' in query:
                topics.add('writ petitions')
            if 'constitutional' in query:
                topics.add('constitutional law')
            if 'criminal' in query:
                topics.add('criminal law')
            if 'civil' in query:
                topics.add('civil law')
            if 'judge' in query:
                topics.add('judges')
            if 'lawyer' in query:
                topics.add('lawyers')
        return list(topics)
    
    class Meta:
        db_table = "qa_sessions"
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user_id', 'is_active']),
            models.Index(fields=['created_at']),
        ]


class QAQuery(models.Model):
    """Individual questions asked in a QA session"""
    
    # Relationships
    session = models.ForeignKey(QASession, on_delete=models.CASCADE, related_name='queries')
    
    # Query information
    query_text = models.TextField()
    query_type = models.CharField(max_length=50, choices=[
        ('legal_question', 'Legal Question'),
        ('case_inquiry', 'Case Inquiry'),
        ('law_research', 'Law Research'),
        ('judge_inquiry', 'Judge Inquiry'),
        ('lawyer_inquiry', 'Lawyer Inquiry'),
        ('court_procedure', 'Court Procedure'),
        ('citation_lookup', 'Citation Lookup'),
        ('general_legal', 'General Legal'),
    ])
    
    # Query processing
    processed_query = models.TextField(blank=True, default='')  # Normalized/expanded query
    query_intent = models.JSONField(default=dict, blank=True)  # Extracted intent and entities
    query_confidence = models.FloatField(default=0.0)  # Confidence in query understanding
    
    # Context information
    context_window = models.JSONField(default=list, blank=True)  # Previous queries for context
    user_context = models.JSONField(default=dict, blank=True)  # User-specific context
    
    # Processing metadata
    processing_time = models.FloatField(default=0.0)  # Time to process query
    retrieval_time = models.FloatField(default=0.0)  # Time to retrieve knowledge
    generation_time = models.FloatField(default=0.0)  # Time to generate answer
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ], default='pending')
    
    error_message = models.TextField(blank=True, default='')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Query: {self.query_text[:50]}... ({self.query_type})"
    
    class Meta:
        db_table = "qa_queries"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['query_type']),
            models.Index(fields=['status']),
        ]


class QAResponse(models.Model):
    """AI-generated responses to user queries"""
    
    # Relationships
    query = models.OneToOneField(QAQuery, on_delete=models.CASCADE, related_name='response')
    
    # Response content
    answer_text = models.TextField()
    answer_type = models.CharField(max_length=50, choices=[
        ('direct_answer', 'Direct Answer'),
        ('explanation', 'Explanation'),
        ('case_summary', 'Case Summary'),
        ('legal_analysis', 'Legal Analysis'),
        ('procedural_guidance', 'Procedural Guidance'),
        ('citation_reference', 'Citation Reference'),
        ('clarification_request', 'Clarification Request'),
    ])
    
    # Source information
    source_documents = models.JSONField(default=list, blank=True)  # List of source document IDs
    source_cases = models.JSONField(default=list, blank=True)  # List of source case IDs
    source_citations = models.JSONField(default=list, blank=True)  # Legal citations used
    confidence_score = models.FloatField(default=0.0)  # Confidence in answer accuracy
    
    # Answer metadata
    answer_metadata = models.JSONField(default=dict, blank=True)  # Additional metadata
    reasoning_chain = models.JSONField(default=list, blank=True)  # Step-by-step reasoning
    limitations = models.TextField(blank=True, default='')  # Known limitations of answer
    
    # Quality metrics
    relevance_score = models.FloatField(default=0.0)
    completeness_score = models.FloatField(default=0.0)
    accuracy_score = models.FloatField(default=0.0)
    
    # User feedback
    user_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    user_feedback = models.TextField(blank=True, default='')
    feedback_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Response to: {self.query.query_text[:30]}..."
    
    class Meta:
        db_table = "qa_responses"
        ordering = ['-created_at']


class QAKnowledgeBase(models.Model):
    """Indexed legal content for QA system knowledge retrieval"""
    
    # Source information
    source_type = models.CharField(max_length=50, choices=[
        ('case_document', 'Case Document'),
        ('case_metadata', 'Case Metadata'),
        ('legal_text', 'Legal Text'),
        ('judgment', 'Judgment'),
        ('order', 'Order'),
        ('comment', 'Comment'),
        ('statute', 'Statute'),
        ('regulation', 'Regulation'),
    ])
    
    # Content identification
    source_id = models.CharField(max_length=100, db_index=True)  # ID from original system
    source_case_id = models.IntegerField(null=True, blank=True, db_index=True)
    source_document_id = models.IntegerField(null=True, blank=True, db_index=True)
    
    # Content information
    title = models.CharField(max_length=500)
    content_text = models.TextField()
    content_summary = models.TextField(blank=True, default='')
    
    # Legal metadata
    court = models.CharField(max_length=100, blank=True, default='')
    case_number = models.CharField(max_length=200, blank=True, default='')
    case_title = models.CharField(max_length=500, blank=True, default='')
    judge_name = models.CharField(max_length=200, blank=True, default='')
    date_decided = models.DateField(null=True, blank=True)
    
    # Legal classification
    legal_domain = models.CharField(max_length=100, blank=True, default='')  # criminal, civil, constitutional
    legal_concepts = models.JSONField(default=list, blank=True)  # List of legal concepts
    legal_entities = models.JSONField(default=list, blank=True)  # Extracted legal entities
    citations = models.JSONField(default=list, blank=True)  # Legal citations found
    
    # Vector information
    vector_id = models.CharField(max_length=100, blank=True, default='')  # Pinecone vector ID
    embedding_model = models.CharField(max_length=100, default='all-MiniLM-L6-v2')
    embedding_dimension = models.IntegerField(default=384)
    
    # Quality metrics
    content_quality_score = models.FloatField(default=0.0)
    legal_relevance_score = models.FloatField(default=0.0)
    completeness_score = models.FloatField(default=0.0)
    
    # Processing status
    is_indexed = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, default='')
    
    # Content hash for deduplication
    content_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    indexed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Knowledge: {self.title[:50]}... ({self.source_type})"
    
    def save(self, *args, **kwargs):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                f"{self.source_type}:{self.source_id}:{self.content_text}".encode()
            ).hexdigest()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "qa_knowledge_base"
        unique_together = ['source_type', 'source_id']
        indexes = [
            models.Index(fields=['source_type']),
            models.Index(fields=['source_case_id']),
            models.Index(fields=['source_document_id']),
            models.Index(fields=['court']),
            models.Index(fields=['legal_domain']),
            models.Index(fields=['is_indexed']),
            models.Index(fields=['content_hash']),
        ]


class QAFeedback(models.Model):
    """User feedback on QA responses"""
    
    # Relationships
    response = models.ForeignKey(QAResponse, on_delete=models.CASCADE, related_name='feedback')
    user_id = models.CharField(max_length=100, db_index=True, default='anonymous')
    
    # Feedback content
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 (poor) to 5 (excellent)"
    )
    feedback_text = models.TextField(blank=True, default='')
    
    # Feedback categories
    accuracy_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    relevance_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    completeness_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    clarity_rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Feedback metadata
    feedback_type = models.CharField(max_length=50, choices=[
        ('user_rating', 'User Rating'),
        ('expert_review', 'Expert Review'),
        ('system_evaluation', 'System Evaluation'),
    ], default='user_rating')
    
    is_helpful = models.BooleanField(null=True, blank=True)
    would_recommend = models.BooleanField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Feedback: {self.rating}/5 for response {self.response.id}"
    
    class Meta:
        db_table = "qa_feedback"
        unique_together = ['response', 'user_id']
        ordering = ['-created_at']


class QAConfiguration(models.Model):
    """Configuration settings for QA system"""
    
    # Configuration identification
    config_name = models.CharField(max_length=100, unique=True)
    config_type = models.CharField(max_length=50, choices=[
        ('system', 'System Configuration'),
        ('model', 'Model Configuration'),
        ('retrieval', 'Retrieval Configuration'),
        ('generation', 'Generation Configuration'),
    ])
    
    # Configuration data
    config_data = models.JSONField(default=dict)
    description = models.TextField(blank=True, default='')
    
    # Model settings
    embedding_model = models.CharField(max_length=100, default='all-MiniLM-L6-v2')
    generation_model = models.CharField(max_length=100, default='gpt-3.5-turbo')
    max_tokens = models.IntegerField(default=1000)
    temperature = models.FloatField(default=0.7)
    
    # Retrieval settings
    top_k_documents = models.IntegerField(default=5)
    similarity_threshold = models.FloatField(default=0.7)
    max_context_length = models.IntegerField(default=4000)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"QA Config: {self.config_name} ({self.config_type})"
    
    class Meta:
        db_table = "qa_configurations"
        ordering = ['-is_default', 'config_name']


class QAMetrics(models.Model):
    """System performance and usage metrics"""
    
    # Metric identification
    metric_name = models.CharField(max_length=100, db_index=True)
    metric_type = models.CharField(max_length=50, choices=[
        ('performance', 'Performance Metric'),
        ('usage', 'Usage Metric'),
        ('quality', 'Quality Metric'),
        ('system', 'System Metric'),
    ])
    
    # Metric data
    metric_value = models.FloatField()
    metric_unit = models.CharField(max_length=20, default='')
    metric_data = models.JSONField(default=dict, blank=True)
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Context
    context_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Metric: {self.metric_name} = {self.metric_value} {self.metric_unit}"
    
    class Meta:
        db_table = "qa_metrics"
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_name', 'recorded_at']),
            models.Index(fields=['metric_type']),
            models.Index(fields=['period_start', 'period_end']),
        ]
