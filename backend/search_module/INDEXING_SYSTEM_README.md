# Hybrid Indexing System Documentation

## Overview

The Hybrid Indexing System is a comprehensive search solution that combines vector (semantic) indexing and keyword (lexical) indexing to provide advanced search capabilities for legal case data. This system enables both semantic similarity search and exact keyword matching with facet-based filtering.

## Architecture

### Components

1. **Vector Indexing Service** (`search_indexing/services/vector_indexing.py`)
   - Uses FAISS for efficient vector similarity search
   - Employs Sentence Transformers for text embeddings
   - Handles document chunking and embedding generation

2. **Keyword Indexing Service** (`search_indexing/services/keyword_indexing.py`)
   - Uses PostgreSQL full-text search capabilities
   - Implements facet indexing for categorical search
   - Handles metadata normalization and indexing

3. **Hybrid Indexing Service** (`search_indexing/services/hybrid_indexing.py`)
   - Orchestrates both vector and keyword indexing
   - Combines and reranks search results
   - Provides unified search interface

4. **Management Commands** (`search_indexing/management/commands/build_indexes.py`)
   - Django management command for building indexes
   - Supports incremental and force rebuilds
   - Provides status monitoring

## Database Models

### Core Models

- **IndexingConfig**: Configuration parameters for indexing
- **DocumentChunk**: Text chunks for vector indexing
- **VectorIndex**: FAISS index metadata and storage
- **KeywordIndex**: PostgreSQL full-text search configuration
- **FacetIndex**: Vocabulary-driven search indexes
- **SearchMetadata**: Normalized search metadata
- **IndexingLog**: Audit trail for indexing operations

### Key Features

- **Integer-based relationships**: Uses `case_id` and `document_id` as integers to avoid migration dependencies
- **Content hashing**: Implements deduplication using SHA-256 hashes
- **Processing status tracking**: Tracks embedding and indexing status
- **Version control**: Supports multiple index versions

## Installation and Setup

### Prerequisites

```bash
pip install faiss-cpu sentence-transformers
```

### Django Configuration

Add to `INSTALLED_APPS` in `settings.py`:
```python
INSTALLED_APPS = [
    # ... other apps
    "search_indexing",
]
```

### Database Migration

```bash
python manage.py makemigrations search_indexing
python manage.py migrate search_indexing
```

## Usage

### Building Indexes

#### Full Hybrid Index
```bash
python manage.py build_indexes
```

#### Force Rebuild
```bash
python manage.py build_indexes --force
```

#### Vector-Only Index
```bash
python manage.py build_indexes --vector-only
```

#### Keyword-Only Index
```bash
python manage.py build_indexes --keyword-only
```

#### Check Status
```bash
python manage.py build_indexes --status
```

#### Incremental Refresh
```bash
python manage.py build_indexes --refresh
```

### Programmatic Usage

#### Basic Search
```python
from search_indexing.services.hybrid_indexing import HybridIndexingService

service = HybridIndexingService()

# Hybrid search
results = service.hybrid_search("legal text", top_k=10)

# Facet search
results = service.search_by_facet("section", "302", top_k=5)
```

#### Advanced Search with Filters
```python
# Search with filters
filters = {
    'court': 'Supreme Court',
    'status': 'Pending',
    'date_from': '2024-01-01',
    'date_to': '2024-12-31'
}

results = service.hybrid_search("murder case", filters=filters, top_k=20)
```

## Configuration

### Default Configuration

```python
DEFAULT_CONFIG = {
    'chunk_size': 512,           # Tokens per chunk
    'chunk_overlap': 50,         # Overlap between chunks
    'embedding_model': 'all-MiniLM-L6-v2',  # Sentence transformer model
    'vector_weight': 0.6,        # Weight for vector search in hybrid
    'keyword_weight': 0.4,       # Weight for keyword search in hybrid
    'facet_boost': 1.5,          # Boost factor for facet matches
    'max_results': 100,          # Maximum results per search
    'min_similarity': 0.3        # Minimum similarity threshold
}
```

### Custom Configuration

```python
from search_indexing.models import IndexingConfig

config = IndexingConfig.objects.create(
    chunk_size=1024,
    chunk_overlap=100,
    embedding_model='all-mpnet-base-v2',
    is_active=True
)
```

## Search Capabilities

### 1. Semantic Search (Vector)
- **Purpose**: Find semantically similar content
- **Use Cases**: Finding cases with similar legal reasoning, concepts, or outcomes
- **Technology**: FAISS + Sentence Transformers
- **Example**: "murder case" finds cases about homicide, killing, manslaughter

### 2. Keyword Search (Lexical)
- **Purpose**: Exact term matching and phrase search
- **Use Cases**: Finding specific case numbers, names, or exact phrases
- **Technology**: PostgreSQL full-text search
- **Example**: "Case No. 123/2024" finds exact case number

### 3. Facet Search (Categorical)
- **Purpose**: Filter by specific categories or terms
- **Use Cases**: Finding cases by judge, court, section, or party type
- **Technology**: Custom facet indexes
- **Example**: "section:302" finds all cases under Section 302

### 4. Hybrid Search (Combined)
- **Purpose**: Combine semantic and keyword search for optimal results
- **Use Cases**: General search queries that benefit from both approaches
- **Technology**: Weighted combination of vector and keyword scores
- **Example**: "murder case in Supreme Court" combines semantic and categorical search

## Performance Optimization

### Chunking Strategy
- **Size**: 512 tokens per chunk (configurable)
- **Overlap**: 50 tokens between chunks (configurable)
- **Limits**: Maximum 50 chunks per case to prevent memory issues

### Batch Processing
- **Embedding Generation**: 32 chunks per batch
- **Index Building**: Processes all chunks in memory-efficient batches
- **Database Operations**: Uses bulk operations where possible

### Caching
- **Model Loading**: Sentence transformer models are cached after first load
- **Index Loading**: FAISS indexes are loaded once and reused
- **Metadata**: Search metadata is cached for quick access

## Monitoring and Logging

### Indexing Logs
All indexing operations are logged with:
- Operation type (build, refresh, update)
- Processing statistics (cases, chunks, vectors)
- Performance metrics (processing time)
- Error tracking and resolution

### Status Monitoring
```python
status = service.get_index_status()
print(f"Vector Index: {status['vector_index']['is_built']}")
print(f"Keyword Index: {status['keyword_index']['is_built']}")
print(f"Total Records: {status['search_metadata']['total_records']}")
```

## Integration with Existing Pipeline

### Data Flow
1. **PDF Processing Pipeline** → Extracts and cleans text
2. **Vocabulary Extraction** → Identifies legal terms
3. **Hybrid Indexing** → Creates search indexes
4. **Search API** → Provides search functionality

### Integration Points
- Uses `UnifiedCaseView` for case data
- Integrates with `Term` and `TermOccurrence` models
- Compatible with existing `DataCleaner` service
- Extends current pipeline architecture

## Future Enhancements

### Planned Features
1. **Real-time Indexing**: Automatic index updates on new data
2. **Advanced Chunking**: Semantic-aware text chunking
3. **Multi-language Support**: Support for Urdu and other languages
4. **Query Expansion**: Automatic query enhancement
5. **Result Clustering**: Group similar results together

### Performance Improvements
1. **GPU Acceleration**: FAISS GPU support for faster indexing
2. **Distributed Indexing**: Multi-node index building
3. **Incremental Updates**: Delta indexing for efficiency
4. **Query Optimization**: Advanced query planning

## Troubleshooting

### Common Issues

#### NumPy Version Conflicts
```bash
# Fix NumPy compatibility
pip install "numpy<2"
```

#### FAISS Installation Issues
```bash
# Install CPU version
pip install faiss-cpu

# Or GPU version (if available)
pip install faiss-gpu
```

#### Memory Issues
- Reduce `chunk_size` in configuration
- Limit `max_chunks_per_case`
- Use smaller embedding models

#### Duplicate Key Errors
- Clear existing chunks: `DocumentChunk.objects.all().delete()`
- Use `--force` flag for complete rebuild
- Check for data consistency issues

### Debug Mode
```python
import logging
logging.getLogger('search_indexing').setLevel(logging.DEBUG)
```

## API Reference

### HybridIndexingService

#### Methods
- `build_hybrid_index(force=False, vector_only=False, keyword_only=False)`
- `hybrid_search(query, filters=None, top_k=10)`
- `search_by_facet(facet_type, term, top_k=10)`
- `get_index_status()`
- `refresh_indexes(incremental=True)`

#### Parameters
- `query`: Search query string
- `filters`: Dictionary of filter criteria
- `top_k`: Maximum number of results
- `force`: Force rebuild all indexes
- `incremental`: Only process new/changed data

## Conclusion

The Hybrid Indexing System provides a robust, scalable solution for legal case search. It combines the best of semantic and keyword search approaches while maintaining high performance and extensibility. The system is designed to integrate seamlessly with the existing data processing pipeline and can be easily extended for future requirements.
