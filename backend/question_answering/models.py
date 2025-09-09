"""
QA System Models - Connected to existing Case models
"""

from django.db import models
from django.contrib.postgres.fields import JSONField
import hashlib
from datetime import datetime


class QASession(models.Model):
    """QA conversation sessions"""
    
    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    user_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Session metadata
    total_queries = models.IntegerField(default=0)
    total_responses = models.IntegerField(default=0)
    
    def __str__(self):
        return f"QA Session {self.session_id}"
    
    class Meta:
        db_table = "qa_sessions"


class QAQuery(models.Model):
    """Individual questions in QA sessions"""
    
    session = models.ForeignKey(QASession, on_delete=models.CASCADE, related_name="queries")
    query_text = models.TextField()
    query_type = models.CharField(max_length=50, default="general")  # general, citation, legal_term
    
    # Query processing metadata
    processed_query = models.TextField(blank=True, null=True)
    query_embedding = models.JSONField(blank=True, null=True)  # Store embedding vector
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Query: {self.query_text[:50]}..."
    
    class Meta:
        db_table = "qa_queries"


class QAResponse(models.Model):
    """AI-generated responses to queries"""
    
    query = models.OneToOneField(QAQuery, on_delete=models.CASCADE, related_name="response")
    
    # Response content
    answer_text = models.TextField()
    answer_type = models.CharField(max_length=50, default="ai_generated")  # ai_generated, document_summary, fallback
    confidence_score = models.FloatField(default=0.0)
    
    # AI metadata
    model_used = models.CharField(max_length=100, default="gpt-3.5-turbo")
    tokens_used = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0.0)  # seconds
    
    # Source information
    source_documents = models.JSONField(default=list)  # List of document IDs used
    source_cases = models.JSONField(default=list)  # List of case IDs used
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Response for: {self.query.query_text[:30]}..."
    
    class Meta:
        db_table = "qa_responses"


class QAKnowledgeBase(models.Model):
    """Indexed legal content for retrieval"""
    
    # Source information
    source_type = models.CharField(max_length=50)  # case_metadata, document_text, order_text
    source_id = models.CharField(max_length=100)  # Unique identifier for the source
    source_case_id = models.IntegerField(null=True, blank=True, db_index=True)  # Reference to Case model
    source_document_id = models.IntegerField(null=True, blank=True, db_index=True)  # Reference to Document model
    
    # Content information
    title = models.CharField(max_length=500)
    content_text = models.TextField()
    content_summary = models.TextField()
    
    # Legal metadata
    court = models.CharField(max_length=200)
    case_number = models.CharField(max_length=300)
    case_title = models.CharField(max_length=800)
    judge_name = models.CharField(max_length=200)
    date_decided = models.DateField(null=True, blank=True)
    
    # Legal classification
    legal_domain = models.CharField(max_length=100)
    legal_concepts = models.JSONField(default=list)
    legal_entities = models.JSONField(default=list)
    citations = models.JSONField(default=list)
    
    # Vector information
    vector_id = models.CharField(max_length=100, unique=True)
    embedding_model = models.CharField(max_length=100)
    embedding_dimension = models.IntegerField()
    
    # Quality metrics
    content_quality_score = models.FloatField()
    legal_relevance_score = models.FloatField()
    completeness_score = models.FloatField()
    
    # Processing status
    is_indexed = models.BooleanField()
    is_processed = models.BooleanField()
    processing_error = models.TextField()
    content_hash = models.CharField(max_length=64)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    indexed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Knowledge Base Entry: {self.title[:50]}..."
    
    class Meta:
        db_table = "qa_knowledge_base"
        indexes = [
            models.Index(fields=["source_case_id"]),
            models.Index(fields=["source_document_id"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["is_indexed"]),
            models.Index(fields=["legal_domain"]),
        ]


class QAFeedback(models.Model):
    """User feedback on responses"""
    
    response = models.ForeignKey(QAResponse, on_delete=models.CASCADE, related_name="feedback")
    
    # Feedback content
    rating = models.IntegerField(choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')])
    feedback_text = models.TextField(blank=True, null=True)
    
    # Feedback metadata
    user_id = models.CharField(max_length=100, blank=True, null=True)
    feedback_type = models.CharField(max_length=50, default="general")  # general, accuracy, helpfulness, clarity
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback {self.rating}/5 for Response {self.response.id}"
    
    class Meta:
        db_table = "qa_feedback"


class QAConfiguration(models.Model):
    """System configuration settings"""
    
    # Configuration identification
    config_name = models.CharField(max_length=100)
    config_type = models.CharField(max_length=50, default="default")
    description = models.TextField()
    config_data = models.JSONField(default=dict)
    
    # Model Configuration
    embedding_model = models.CharField(max_length=100, default="all-MiniLM-L6-v2")
    generation_model = models.CharField(max_length=100, default="gpt-3.5-turbo")
    max_tokens = models.IntegerField(default=1000)
    temperature = models.FloatField(default=0.7)
    
    # Search Configuration
    top_k_documents = models.IntegerField(default=5)
    similarity_threshold = models.FloatField(default=0.7)
    max_context_length = models.IntegerField(default=4000)
    
    # System Configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"QA Config: {self.config_name} ({self.generation_model})"
    
    class Meta:
        db_table = "qa_configurations"


class QAMetrics(models.Model):
    """Performance and usage metrics"""
    
    # Metric identification
    metric_type = models.CharField(max_length=50, db_index=True)  # daily_queries, response_time, accuracy, etc.
    metric_date = models.DateField(db_index=True)
    
    # Metric values
    metric_value = models.FloatField()
    metric_count = models.IntegerField(default=1)
    
    # Additional metadata
    metadata = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.metric_type} on {self.metric_date}: {self.metric_value}"
    
    class Meta:
        db_table = "qa_metrics"
        unique_together = ["metric_type", "metric_date"]
        indexes = [
            models.Index(fields=["metric_type"]),
            models.Index(fields=["metric_date"]),
        ]


class VectorIndex(models.Model):
    """Vector index for semantic search"""
    
    # Index information
    index_name = models.CharField(max_length=100, unique=True)
    index_type = models.CharField(max_length=50, default="pinecone")  # pinecone, faiss, local
    
    # Configuration
    embedding_model = models.CharField(max_length=100, default="all-MiniLM-L6-v2")
    embedding_dimension = models.IntegerField(default=384)
    index_config = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    total_vectors = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Vector Index: {self.index_name} ({self.total_vectors} vectors)"
    
    class Meta:
        db_table = "qa_vector_indexes"


class DocumentEmbedding(models.Model):
    """Document embeddings for vector search"""
    
    # Source information
    knowledge_base_entry = models.ForeignKey(QAKnowledgeBase, on_delete=models.CASCADE, related_name="embeddings")
    vector_index = models.ForeignKey(VectorIndex, on_delete=models.CASCADE, related_name="embeddings")
    
    # Embedding information
    embedding_vector = models.JSONField()  # Store the actual embedding vector
    embedding_id = models.CharField(max_length=100, unique=True, db_index=True)  # External ID (e.g., Pinecone ID)
    
    # Metadata
    embedding_model = models.CharField(max_length=100)
    embedding_dimension = models.IntegerField()
    
    # Status
    is_indexed = models.BooleanField(default=False)
    indexing_error = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Embedding for KB Entry {self.knowledge_base_entry.id}"
    
    class Meta:
        db_table = "qa_document_embeddings"
        unique_together = ["knowledge_base_entry", "vector_index"]
        indexes = [
            models.Index(fields=["embedding_id"]),
            models.Index(fields=["is_indexed"]),
        ]