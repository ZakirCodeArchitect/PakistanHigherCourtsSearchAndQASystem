# QA Knowledge Base & Storage System

## Overview

This enhanced Knowledge Base system is specifically designed for the **Question-Answering module** and implements the complete architecture from the design diagrams. It provides comprehensive document processing, chunking, enrichment, law reference normalization, and full-text indexing optimized for RAG (Retrieval-Augmented Generation) and AI response generation.

## Architecture Components

### 1. QA-Specific Canonical Schema (PostgreSQL)

The QA module uses PostgreSQL with the following **QA-specific tables**:

- **qa_knowledge_base**: Processed chunks optimized for AI context
- **qa_sessions**: Chat session management
- **qa_queries**: Individual questions in sessions
- **qa_responses**: AI-generated responses with citations
- **qa_feedback**: User feedback on responses
- **qa_configurations**: System configuration settings
- **qa_metrics**: Performance and usage metrics

### 2. QA Chat Data Tables

- **conversations**: Chat session management
- **messages**: Individual messages in conversations
- **message_citations**: Citations attached to messages
- **message_feedback**: User feedback on responses

### 3. QA-Specific Chunking & Enrichment

#### Document Splitting for AI Context
- **Chunk Size**: 500-900 tokens (optimized for AI context)
- **Overlap**: 100-token overlap between consecutive chunks
- **Smart Splitting**: Breaks at sentence boundaries for better AI understanding

#### QA Metadata Attachment
Each chunk is enriched with QA-specific metadata:
```python
{
    "case_no": "CASE-123",
    "court": "High Court of Sindh",
    "judges": ["Justice Ali", "Justice Khan"],
    "year": 2023,
    "sections": ["s. 379 PPC", "s. 497 CrPC"],
    "paragraph_no": 1,
    "url": "https://example.com/case/123",
    "page": 1,
    "document_type": "judgment",
    "content_type": "text",
    "legal_domain": "criminal",
    "ai_context_score": 0.85,  # Relevance for AI responses
    "qa_relevance": 0.92       # QA-specific relevance score
}
```

#### Law Reference Normalization for QA
- **Pattern Recognition**: Detects various law reference formats
- **Canonical Format**: Converts to standard format (e.g., "s. 379 PPC")
- **QA Context**: Generates QA-specific context and relevance scores
- **Legal Abbreviations**: Support for PPC, CrPC, CPC, QSO, Constitution

### 4. Vector Store for RAG

- **Embedding Generation**: Uses Sentence Transformers (all-MiniLM-L6-v2)
- **Storage**: FAISS and Pinecone integration
- **QA Metadata**: Full QA-specific metadata attached to each vector
- **AI Context Scoring**: Relevance scores for AI response generation

### 5. Full-Text Index for QA

- **PostgreSQL Trigram Index**: For keyword fallback and highlighting
- **QA-Specific Search**: Optimized for question-answering context
- **Hybrid Search**: Combines vector and keyword search for RAG

## Key Features

### QA-Enhanced Chunking Service

```python
from services.qa_knowledge_base import QAEnhancedChunkingService

chunking_service = QAEnhancedChunkingService()

# Process a document for QA context
chunks = chunking_service.chunk_document_for_qa(
    case_id=123,
    document_id=456,
    text="Legal document text...",
    document_type="judgment"
)
```

### QA Law Reference Normalization

```python
from services.qa_knowledge_base import QALawReferenceNormalizer

normalizer = QALawReferenceNormalizer()
result = normalizer.normalize_reference(
    "The accused was charged under section 379 of PPC for theft."
)

# Result includes QA-specific context:
# {
#     "processed_text": "The accused was charged under s. 379 PPC for theft.",
#     "normalized_references": [...],
#     "qa_context": {
#         "acts_mentioned": ["ppc"],
#         "sections_by_act": {"ppc": [379]},
#         "avg_relevance": 0.9
#     }
# }
```

### QA Knowledge Base Service

```python
from services.qa_knowledge_base import QAKnowledgeBaseService

qa_kb_service = QAKnowledgeBaseService()

# Process a case for QA
result = qa_kb_service.process_case_for_qa(case_id=123, force_reprocess=False)

# Get QA statistics
stats = qa_kb_service.get_qa_processing_stats()
```

## API Endpoints

### QA Knowledge Base Processing

```bash
# Process specific case for QA
POST /api/qa/kb/process/
{
    "case_id": 123,
    "force_reprocess": false
}

# Process case range for QA
POST /api/qa/kb/process/
{
    "case_range": "1-100",
    "force_reprocess": false
}

# Process all cases for QA
POST /api/qa/kb/process/
{
    "process_all": true,
    "force_reprocess": false
}
```

### QA Statistics and Monitoring

```bash
# Get QA processing statistics
GET /api/qa/kb/stats/

# Get QA system health
GET /api/qa/kb/health/

# Search QA Knowledge Base
POST /api/qa/kb/search/
{
    "query": "theft mobile phone",
    "limit": 10,
    "legal_domain": "criminal"
}
```

### QA Law Reference Normalization

```bash
# Test QA normalization
POST /api/qa/kb/normalize/
{
    "text": "The accused was charged under section 379 of PPC for theft."
}
```

### QA Chunking Testing

```bash
# Test QA chunking
POST /api/qa/kb/chunking/test/
{
    "text": "Legal document text...",
    "case_id": 123,
    "document_type": "judgment"
}
```

## Management Commands

### Process QA Knowledge Base

```bash
# Process specific case for QA
python manage.py process_qa_knowledge_base --case-id 123 --verbose

# Process case range for QA
python manage.py process_qa_knowledge_base --case-range "1-100" --verbose

# Process all cases for QA
python manage.py process_qa_knowledge_base --all-cases --verbose

# Force reprocess
python manage.py process_qa_knowledge_base --case-id 123 --force-reprocess

# Show QA statistics only
python manage.py process_qa_knowledge_base --stats-only
```

## Configuration

### QA Chunking Configuration

```python
from services.qa_knowledge_base import QAChunkingConfig

config = QAChunkingConfig(
    chunk_size=700,        # Target 500-900 tokens for AI context
    chunk_overlap=100,     # 100-token overlap
    min_chunk_size=200,    # Minimum chunk size
    max_chunk_size=1000,   # Maximum chunk size
    token_ratio=0.75,      # Characters per token ratio
    legal_context_weight=1.2  # Weight for legal context
)
```

### QA Legal Abbreviations

The system recognizes and normalizes these legal abbreviations for QA context:

- **PPC**: Pakistan Penal Code
- **CrPC**: Code of Criminal Procedure
- **CPC**: Code of Civil Procedure
- **QSO**: Qanun-e-Shahadat Order
- **Constitution**: Constitution of Pakistan
- **Art**: Article
- **S**: Section
- **SS**: Sections

## Database Models

### QA-Specific Models

- **QAKnowledgeBase**: Processed chunks optimized for AI context
- **QASession**: Chat session management with conversation history
- **QAQuery**: Individual questions with processing metadata
- **QAResponse**: AI-generated responses with citations and sources
- **QAFeedback**: User feedback on response quality
- **QAConfiguration**: System configuration for QA operations
- **QAMetrics**: Performance metrics and analytics

## Testing

Run the comprehensive QA test suite:

```bash
cd backend/question_answering
python test_qa_knowledge_base.py
```

The test suite covers:
- QA law reference normalization
- QA enhanced chunking
- QA metadata creation
- Complete QA Knowledge Base processing
- QA statistics and monitoring

## Performance Monitoring

### QA Metrics Collected

- **Processing Time**: Time taken for QA operations
- **AI Context Scores**: Relevance scores for AI responses
- **QA Relevance**: QA-specific relevance metrics
- **Legal Domain Distribution**: Distribution across legal domains
- **Quality Metrics**: Content quality and legal relevance scores

### QA Health Monitoring

The system provides comprehensive QA health monitoring:

- **Database Connectivity**: PostgreSQL connection status
- **QA Knowledge Base Health**: QA entries and processing status
- **Processing Health**: Error rates and active operations
- **Quality Metrics**: Content quality and relevance scores

## Integration with Existing QA System

### Enhanced QA Engine Integration

```python
from services.enhanced_qa_engine import EnhancedQAEngine
from services.qa_knowledge_base import QAKnowledgeBaseService

# Initialize QA engine with enhanced KB
qa_engine = EnhancedQAEngine()
qa_kb_service = QAKnowledgeBaseService()

# Process cases for QA
result = qa_kb_service.process_case_for_qa(case_id=123)

# Use in QA engine
answer = qa_engine.ask_question(
    question="What is a writ petition?",
    session_id="session_123",
    user_id="user_456"
)
```

### RAG Service Integration

```python
from services.rag_service import RAGService
from services.qa_knowledge_base import QAKnowledgeBaseService

# Initialize services
rag_service = RAGService()
qa_kb_service = QAKnowledgeBaseService()

# Process cases for RAG
qa_kb_service.process_case_for_qa(case_id=123)

# Search using RAG
results = rag_service.search_similar_documents("writ petition", top_k=5)
```

## Best Practices

### QA Processing Strategy

1. **Process Cases for QA**: Use QA-specific processing for better AI context
2. **Monitor QA Metrics**: Track AI context scores and QA relevance
3. **Quality Assurance**: Verify law reference normalization and metadata accuracy
4. **Performance Optimization**: Monitor processing times and optimize chunk sizes

### QA Performance Optimization

1. **Chunk Size Tuning**: Adjust chunk size based on AI model requirements
2. **Overlap Optimization**: Balance overlap vs. processing time for QA context
3. **Metadata Quality**: Ensure comprehensive metadata for better AI responses
4. **Legal Domain Classification**: Accurate classification for better retrieval

### QA Quality Assurance

1. **Reference Validation**: Verify law reference normalization accuracy
2. **Metadata Accuracy**: Ensure QA metadata is correctly attached
3. **AI Context Scoring**: Monitor and improve AI context relevance scores
4. **User Feedback**: Collect and analyze user feedback on QA responses

## Troubleshooting

### Common QA Issues

1. **Low AI Context Scores**: Check chunk quality and legal domain classification
2. **Poor QA Relevance**: Verify metadata completeness and legal terminology
3. **Processing Errors**: Check database connectivity and case data availability
4. **Normalization Issues**: Verify law reference patterns and abbreviations

### Debug Commands

```bash
# Check QA system health
python manage.py process_qa_knowledge_base --stats-only

# Test QA normalization
curl -X POST http://localhost:8000/api/qa/kb/normalize/ \
  -H "Content-Type: application/json" \
  -d '{"text": "section 379 PPC"}'

# Check QA processing logs
python manage.py shell
>>> from question_answering.models import QAKnowledgeBase
>>> QAKnowledgeBase.objects.filter(legal_domain='criminal').count()
```

## Future Enhancements

1. **Advanced QA Normalization**: Support for more legal reference formats
2. **QA Quality Scoring**: Enhanced content quality assessment for AI context
3. **Automated QA Indexing**: Scheduled QA index updates
4. **QA Performance Analytics**: Advanced QA performance analytics and reporting
5. **Multi-language QA Support**: Support for Urdu and other languages in QA context

---

This QA Knowledge Base system provides a complete, production-ready foundation for the question-answering module with advanced chunking, enrichment, normalization, and monitoring capabilities specifically optimized for RAG and AI response generation.
