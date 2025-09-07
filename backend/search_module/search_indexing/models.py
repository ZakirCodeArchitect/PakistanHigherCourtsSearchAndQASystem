from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import hashlib
import json
from datetime import datetime


class IndexingConfig(models.Model):
    """Configuration for indexing parameters"""
    
    # Indexing configuration
    chunk_size = models.IntegerField(default=500, help_text="Number of tokens per chunk")
    chunk_overlap = models.IntegerField(default=50, help_text="Overlap between chunks")
    embedding_model = models.CharField(max_length=100, default="all-MiniLM-L6-v2")
    embedding_dimension = models.IntegerField(default=384)
    
    # Processing configuration
    batch_size = models.IntegerField(default=32)
    max_text_length = models.IntegerField(default=8192)
    
    # Versioning
    version = models.CharField(max_length=20, default="1.0")
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Indexing Config v{self.version} ({self.embedding_model})"
    
    class Meta:
        db_table = "indexing_configs"


class DocumentChunk(models.Model):
    """Text chunks for vector indexing"""
    
    # Source information
    case_id = models.IntegerField()  # Store case ID as integer instead of foreign key
    document_id = models.IntegerField(null=True, blank=True)  # Store document ID as integer
    
    # Chunk information
    chunk_id = models.CharField(max_length=64, unique=True, db_index=True)  # Hash of content
    chunk_index = models.IntegerField()  # Position in document
    chunk_text = models.TextField()  # Actual text content
    
    # Location information
    start_char = models.IntegerField()  # Start character position
    end_char = models.IntegerField()    # End character position
    page_number = models.IntegerField(null=True, blank=True)  # Page number if available
    
    # Metadata
    chunk_hash = models.CharField(max_length=64, db_index=True)  # Content hash for deduplication
    token_count = models.IntegerField()  # Number of tokens in chunk
    
    # Processing status
    is_embedded = models.BooleanField(default=False)
    embedding_hash = models.CharField(max_length=64, blank=True)  # Hash of embedding model + text
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chunk {self.chunk_index} of case {self.case_id} ({self.token_count} tokens)"
    
    def save(self, *args, **kwargs):
        if not self.chunk_hash:
            self.chunk_hash = hashlib.sha256(self.chunk_text.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "document_chunks"
        unique_together = ["case_id", "chunk_index"]
        indexes = [
            models.Index(fields=["chunk_hash"]),
            models.Index(fields=["is_embedded"]),
            models.Index(fields=["page_number"]),
        ]


class VectorIndex(models.Model):
    """FAISS vector index for semantic search"""
    
    # Index information
    index_name = models.CharField(max_length=100, unique=True)
    index_type = models.CharField(max_length=50, default="faiss")  # faiss, pgvector, etc.
    
    # Configuration
    embedding_model = models.CharField(max_length=100)
    embedding_dimension = models.IntegerField()
    index_config = models.JSONField(default=dict)  # FAISS parameters
    
    # File storage
    index_file_path = models.CharField(max_length=500)  # Path to FAISS index file
    index_file_size = models.BigIntegerField(default=0)  # Size in bytes
    
    # Statistics
    total_vectors = models.IntegerField(default=0)
    total_chunks = models.IntegerField(default=0)
    
    # Status
    is_built = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Versioning
    version = models.CharField(max_length=20, default="1.0")
    model_version = models.CharField(max_length=20, default="1.0")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Vector Index: {self.index_name} ({self.total_vectors} vectors)"
    
    class Meta:
        db_table = "vector_indexes"


class KeywordIndex(models.Model):
    """Keyword/token index for lexical search"""
    
    # Index information
    index_name = models.CharField(max_length=100, unique=True)
    index_type = models.CharField(max_length=50, default="postgresql")  # postgresql, elasticsearch, etc.
    
    # Configuration
    analyzer_config = models.JSONField(default=dict)  # Text analysis configuration
    weight_config = models.JSONField(default=dict)  # Field weighting configuration
    
    # Statistics
    total_documents = models.IntegerField(default=0)
    total_terms = models.IntegerField(default=0)
    
    # Status
    is_built = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Versioning
    version = models.CharField(max_length=20, default="1.0")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Keyword Index: {self.index_name} ({self.total_documents} documents)"
    
    class Meta:
        db_table = "keyword_indexes"


class FacetIndex(models.Model):
    """Facet index for vocabulary-driven search"""
    
    # Index information
    index_name = models.CharField(max_length=100, unique=True)
    facet_type = models.CharField(max_length=50)  # section, judge, court, etc.
    
    # Configuration
    term_mappings = models.JSONField(default=dict)  # canonical_term -> case_ids
    boost_config = models.JSONField(default=dict)  # Boost configuration for ranking
    
    # Statistics
    total_terms = models.IntegerField(default=0)
    total_mappings = models.IntegerField(default=0)
    
    # Status
    is_built = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Versioning
    version = models.CharField(max_length=20, default="1.0")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Facet Index: {self.index_name} ({self.facet_type})"
    
    class Meta:
        db_table = "facet_indexes"


class FacetTerm(models.Model):
    """Normalized facet terms for optimized storage and querying"""
    
    # Facet information
    facet_type = models.CharField(max_length=50, db_index=True)
    canonical_term = models.CharField(max_length=500, db_index=True)
    
    # Statistics
    occurrence_count = models.IntegerField(default=0)
    case_count = models.IntegerField(default=0)
    
    # Boost configuration
    boost_factor = models.FloatField(default=1.0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.facet_type}: {self.canonical_term} ({self.case_count} cases)"
    
    class Meta:
        db_table = "facet_terms"
        unique_together = ['facet_type', 'canonical_term']
        indexes = [
            models.Index(fields=['facet_type', 'occurrence_count']),
            models.Index(fields=['facet_type', 'case_count']),
            models.Index(fields=['canonical_term']),
        ]


class FacetMapping(models.Model):
    """Mapping between facet terms and cases for fast lookups"""
    
    # Relationships
    facet_term = models.ForeignKey(FacetTerm, on_delete=models.CASCADE, related_name='mappings')
    
    # Case reference
    case_id = models.IntegerField(db_index=True)
    
    # Additional metadata
    occurrence_count = models.IntegerField(default=1)  # How many times this term appears in this case
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.facet_term.canonical_term} -> Case {self.case_id}"
    
    class Meta:
        db_table = "facet_mappings"
        unique_together = ['facet_term', 'case_id']
        indexes = [
            models.Index(fields=['case_id']),
            models.Index(fields=['facet_term', 'case_id']),
        ]


class IndexingLog(models.Model):
    """Log of indexing operations for observability"""
    
    # Operation information
    operation_type = models.CharField(max_length=50)  # build, update, refresh
    index_type = models.CharField(max_length=50)  # vector, keyword, facet
    
    # Processing statistics
    documents_processed = models.IntegerField(default=0)
    chunks_processed = models.IntegerField(default=0)
    vectors_created = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0.0)  # Time in seconds
    
    # Status
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Configuration
    config_version = models.CharField(max_length=20)
    model_version = models.CharField(max_length=20, blank=True)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.operation_type} {self.index_type} index ({self.documents_processed} docs)"
    
    class Meta:
        db_table = "indexing_logs"
        indexes = [
            models.Index(fields=["operation_type"]),
            models.Index(fields=["index_type"]),
            models.Index(fields=["is_successful"]),
            models.Index(fields=["started_at"]),
        ]


class SearchMetadata(models.Model):
    """Enhanced metadata for search optimization and ranking"""
    
    # Document information
    case_id = models.IntegerField()  # Store case ID as integer instead of foreign key
    
    # Search surface (denormalized for fast access)
    case_number_normalized = models.CharField(max_length=300, db_index=True)
    case_title_normalized = models.CharField(max_length=800, db_index=True)
    parties_normalized = models.TextField(blank=True)
    court_normalized = models.CharField(max_length=100, db_index=True)
    status_normalized = models.CharField(max_length=50, db_index=True)
    
    # Dates for recency ranking
    institution_date = models.DateField(null=True, blank=True, db_index=True)
    hearing_date = models.DateField(null=True, blank=True, db_index=True)
    disposal_date = models.DateField(null=True, blank=True, db_index=True)
    
    # TIER 1 ENHANCEMENT: Rich metadata fields
    legal_entities = models.JSONField(default=list, blank=True)  # Extracted legal entities
    legal_concepts = models.JSONField(default=list, blank=True)  # Legal concepts
    case_classification = models.JSONField(default=dict, blank=True)  # Case type classification
    subject_matter = models.JSONField(default=list, blank=True)  # Subject matter tags
    parties_intelligence = models.JSONField(default=dict, blank=True)  # Party analysis
    procedural_stage = models.CharField(max_length=50, blank=True, db_index=True)
    case_timeline = models.JSONField(default=list, blank=True)  # Case timeline
    
    # TIER 1 ENHANCEMENT: Quality and relevance scores
    content_richness_score = models.FloatField(default=0.0, db_index=True)
    data_completeness_score = models.FloatField(default=0.0, db_index=True)
    authority_score = models.FloatField(default=0.0, db_index=True)  # Court hierarchy score
    precedential_value = models.FloatField(default=0.0, db_index=True)
    
    # TIER 1 ENHANCEMENT: Search optimization
    searchable_keywords = models.JSONField(default=list, blank=True)  # Optimized keywords
    semantic_tags = models.JSONField(default=list, blank=True)  # Semantic tags
    relevance_boosters = models.JSONField(default=list, blank=True)  # Boost factors
    
    # Content hashes for idempotency
    content_hash = models.CharField(max_length=64, db_index=True)  # Hash of all content
    text_hash = models.CharField(max_length=64, db_index=True)     # Hash of text content
    metadata_hash = models.CharField(max_length=64, db_index=True) # Hash of metadata
    enhanced_metadata_hash = models.CharField(max_length=64, db_index=True, default='')  # Enhanced metadata hash
    
    # Search statistics
    total_chunks = models.IntegerField(default=0)
    total_terms = models.IntegerField(default=0)
    avg_chunk_length = models.FloatField(default=0.0)
    
    # Processing status
    is_indexed = models.BooleanField(default=False)
    enhanced_metadata_extracted = models.BooleanField(default=False, db_index=True)
    last_indexed = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Search metadata for case {self.case_id}"
    
    class Meta:
        db_table = "search_metadata"
        unique_together = ["case_id"]
        indexes = [
            models.Index(fields=["case_number_normalized"]),
            models.Index(fields=["court_normalized"]),
            models.Index(fields=["status_normalized"]),
            models.Index(fields=["institution_date"]),
            models.Index(fields=["disposal_date"]),
            models.Index(fields=["is_indexed"]),
        ]
