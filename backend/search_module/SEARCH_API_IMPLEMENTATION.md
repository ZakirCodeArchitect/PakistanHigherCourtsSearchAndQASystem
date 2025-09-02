# Search API & Ranking System Implementation

## 🎯 Overview

This document describes the implementation of the Search API & Ranking system for the Pakistan Higher Courts Search and QA System. The system provides sophisticated hybrid search capabilities combining lexical, semantic, and faceted search with advanced ranking algorithms.

## 🏗️ Architecture

### Core Components

1. **Query Normalization Service** (`QueryNormalizationService`)
   - Legal citation canonicalization (PPC:302, CrPC:497)
   - Legal abbreviation normalization
   - Exact identifier detection
   - Boost signal generation

2. **Advanced Ranking Service** (`AdvancedRankingService`)
   - Hybrid score fusion (0.6 semantic + 0.4 lexical)
   - Multi-factor boosting system
   - Recency scoring with exponential decay
   - Diversity control using MMR (Maximal Marginal Relevance)

3. **Snippet Generation Service** (`SnippetService`)
   - Lexical match-based snippets
   - Semantic chunk-based snippets
   - Metadata-based snippets
   - Span information and highlighting

4. **Faceting Service** (`FacetingService`)
   - Normalized facet computation
   - Dynamic facet generation
   - Filter-aware faceting
   - Fast facet suggestions

5. **Hybrid Indexing Service** (`HybridIndexingService`)
   - Vector search (FAISS + Sentence Transformers)
   - Keyword search (PostgreSQL full-text)
   - Result combination and reranking

## 🚀 API Endpoints

### 1. Main Search Endpoint

**`GET /api/search/search/`**

**Purpose**: Hybrid retrieval with facets & snippets

**Parameters**:
- `q` (required): Search query string
- `mode`: Search mode (`lexical`, `semantic`, `hybrid`)
- `filters`: JSON filters for court, year, status, judge, section, citation
- `offset`: Pagination offset (default: 0)
- `limit`: Results per page (default: 10, max: 100)
- `return_facets`: Boolean to return facets (default: false)
- `highlight`: Boolean to generate snippets (default: false)
- `debug`: Boolean for debug information (default: false)

**Response**:
```json
{
  "results": [
    {
      "rank": 1,
      "case_id": 123,
      "case_number": "Application 2/2025",
      "case_title": "Case Title",
      "court": "Islamabad High Court",
      "status": "Pending",
      "final_score": 0.95,
      "explanation": {
        "vector_score": 0.8,
        "keyword_score": 0.7,
        "boosts_applied": [["exact_match", 3.0]],
        "total_boost": 3.0
      },
      "snippets": [...]
    }
  ],
  "pagination": {
    "total": 150,
    "offset": 0,
    "limit": 10,
    "has_next": true,
    "has_previous": false
  },
  "facets": {
    "court": [
      {"value": "Islamabad High Court", "count": 45, "selected": false}
    ]
  },
  "query_info": {
    "original_query": "PPC 302",
    "normalized_query": "ppc 302 ppc:302",
    "citations_found": 1,
    "exact_matches_found": 0
  },
  "search_metadata": {
    "mode": "hybrid",
    "total_results": 150,
    "latency_ms": 45.2,
    "search_type": "hybrid"
  }
}
```

### 2. Suggestions Endpoint

**`GET /api/search/suggest/`**

**Purpose**: Typeahead suggestions for case numbers, citations, sections, judges

**Parameters**:
- `q`: Query string (minimum 2 characters)
- `type`: Suggestion type (`auto`, `case`, `citation`, `section`, `judge`)

**Response**:
```json
{
  "suggestions": [
    {
      "value": "PPC 302",
      "type": "citation",
      "canonical_key": "ppc:302",
      "additional_info": "Found in 25 cases"
    }
  ]
}
```

### 3. Case Context Endpoint

**`GET /api/search/case/{case_id}/contexts/`**

**Purpose**: Retrieve semantic chunks and legal terms for a specific case

**Parameters**:
- `q` (optional): Query for relevance scoring

**Response**:
```json
{
  "case_id": 123,
  "case_number": "Application 2/2025",
  "case_title": "Case Title",
  "chunks": [
    {
      "text": "Chunk text content...",
      "page_range": 5,
      "char_spans": {"start_char": 100, "end_char": 200},
      "vector_score": 0.85,
      "chunk_index": 1,
      "token_count": 150
    }
  ],
  "terms": [
    {
      "canonical": "ppc:302",
      "type": "section",
      "page": 5,
      "span": {"start_char": 150, "end_char": 155},
      "confidence": 0.95,
      "surface": "302 PPC"
    }
  ]
}
```

### 4. Status Endpoint

**`GET /api/search/status/`**

**Purpose**: System health and index status

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1640995200.0,
  "indexes": {
    "vector_index": {
      "exists": true,
      "is_built": true,
      "total_vectors": 15000,
      "last_updated": "2024-01-01T00:00:00Z"
    }
  },
  "health": {
    "is_healthy": true,
    "database": {"healthy": true, "total_cases": 5000},
    "indexing": {"coverage_percentage": 95.5, "indexed_cases": 4775}
  }
}
```

## 🔧 Query Normalization

### Legal Citation Patterns

The system automatically recognizes and normalizes legal citations:

- **PPC**: `"497 CrPC"` → `"crpc:497"`
- **CrPC**: `"s. 497"` → `"crpc:497"`
- **CPC**: `"C.P.C. 151"` → `"cpc:151"`
- **Case Numbers**: `"Application 2/2025"` → Exact match boost

### Boost Signals

- **Citation Boost**: +2.0 for matching legal citations
- **Exact Match Boost**: +3.0 for exact case number matches
- **Legal Term Boost**: +1.5 for matching legal vocabulary
- **Filter Alignment Boost**: +0.3 per matching filter

## 🎯 Ranking Algorithm

### Score Fusion Formula

```
FinalScore = (0.6 × SemanticScore + 0.4 × LexicalScore + Boosts) × RecencyFactor
```

### Ranking Factors

1. **Base Scores**
   - Lexical relevance (PostgreSQL full-text)
   - Semantic similarity (FAISS vector search)

2. **Boosting System**
   - Exact identifier matches
   - Legal citation matches
   - Filter alignment
   - Legal term occurrences

3. **Recency Scoring**
   - Exponential decay based on decision date
   - Newer cases get slight preference

4. **Diversity Control**
   - MMR algorithm prevents similar results
   - Balances relevance and diversity

## 🎨 Snippet Generation

### Snippet Types

1. **Lexical Snippets** (Priority 1)
   - Based on exact text matches
   - Include context around matches
   - Highlight matched terms

2. **Semantic Snippets** (Priority 2)
   - Based on semantic chunks
   - Citation-aware chunk selection
   - Optimal length (100-300 characters)

3. **Metadata Snippets** (Priority 3)
   - Case title, number, bench information
   - Query-relevant metadata fields

### Snippet Features

- **Span Information**: Page numbers and character positions
- **Term Highlighting**: Bold markers around matches
- **Relevance Scoring**: Snippet quality assessment
- **Length Optimization**: Sentence boundary truncation

## 🔍 Faceting System

### Facet Types

- **Court**: High Court, Supreme Court, etc.
- **Status**: Pending, Decided, Dismissed
- **Year**: Institution year
- **Case Type**: Application, Petition, Appeal
- **Section**: Legal sections (PPC, CrPC, CPC)
- **Citation**: Legal citations
- **Judge**: Presiding judges

### Facet Computation

- **Normalized Facets**: Pre-computed using `FacetTerm` tables
- **Dynamic Facets**: Computed on-the-fly from case data
- **Filter-Aware**: Facets respect applied filters
- **Performance Optimized**: Cached and indexed

## ⚡ Performance Features

### Caching Strategy

- **Facet Cache**: 5-minute TTL for computed facets
- **Query Cache**: Short TTL for common queries
- **Result Cache**: Pagination-aware result caching

### Optimization Techniques

- **Normalized Tables**: Fast facet lookups
- **Indexed Fields**: Database optimization
- **Batch Processing**: Efficient bulk operations
- **Lazy Loading**: On-demand snippet generation

## 🧪 Testing

### Test Script

Run the test script to verify API functionality:

```bash
python test_search_api.py
```

### Test Coverage

- ✅ Search endpoint (hybrid, lexical, semantic)
- ✅ Suggestions endpoint (typeahead)
- ✅ Status endpoint (health check)
- ✅ Case context endpoint (chunks and terms)
- ✅ Query normalization
- ✅ Facet computation
- ✅ Snippet generation

## 🚀 Getting Started

### 1. Start the Django Server

```bash
python manage.py runserver
```

### 2. Test Basic Search

```bash
curl "http://localhost:8000/api/search/search/?q=PPC%20302&mode=hybrid&limit=5"
```

### 3. Test Suggestions

```bash
curl "http://localhost:8000/api/search/suggest/?q=PPC&type=auto"
```

### 4. Check System Status

```bash
curl "http://localhost:8000/api/search/status/"
```

## 📊 Performance Metrics

### Target Performance

- **Hybrid Search P95**: <150ms (warm)
- **Facet Response**: <50ms
- **Snippet Generation**: <100ms
- **Suggestions**: <30ms

### Monitoring

- **Latency Tracking**: Per-request timing
- **Error Rates**: Exception monitoring
- **Index Coverage**: Percentage of indexed cases
- **Cache Hit Rates**: Facet and query caching

## 🔮 Future Enhancements

### Phase 2 Features

1. **Advanced Filtering**
   - Date range filters
   - Complex boolean logic
   - Saved search queries

2. **Personalization**
   - User search history
   - Relevance feedback
   - Custom ranking preferences

3. **Analytics Dashboard**
   - Search analytics
   - Popular queries
   - Performance metrics

4. **Export Capabilities**
   - CSV/JSON export
   - Bulk result processing
   - API rate limiting

## 🐛 Troubleshooting

### Common Issues

1. **No Search Results**
   - Check if indexes are built
   - Verify case data exists
   - Check query normalization

2. **Slow Performance**
   - Verify database indexes
   - Check vector index status
   - Monitor cache hit rates

3. **Facet Errors**
   - Check normalized facet tables
   - Verify facet term mappings
   - Check database connections

### Debug Mode

Enable debug mode for detailed information:

```bash
curl "http://localhost:8000/api/search/search/?q=test&debug=true"
```

## 📚 API Documentation

### Swagger/OpenAPI

The API follows RESTful principles and can be documented with Swagger:

- **Base URL**: `/api/search/`
- **Authentication**: None (public API)
- **Rate Limiting**: Configurable per endpoint
- **Error Handling**: Standard HTTP status codes

### Response Formats

- **Success**: 200 OK with JSON payload
- **Validation Error**: 400 Bad Request
- **Not Found**: 404 Not Found
- **Server Error**: 500 Internal Server Error

## 🤝 Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8
2. **Testing**: Add tests for new features
3. **Documentation**: Update this README
4. **Performance**: Monitor latency and throughput

### Adding New Features

1. **Service Layer**: Implement business logic
2. **API Views**: Add endpoint handlers
3. **URL Routing**: Update URL patterns
4. **Testing**: Add comprehensive tests
5. **Documentation**: Update API docs

---

**Last Updated**: January 2025  
**Version**: 1.0.0  
**Maintainer**: Development Team
