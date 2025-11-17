# BM25 + TF-IDF Implementation Plan
## Industry-Grade Lexical Search Upgrade

### Executive Summary

Based on the evaluation results showing low MRR (0.15), NDCG (0.12), and Precision (0.18) for complex queries, and the analysis showing PostgreSQL FTS limitations, we need to implement industry-standard lexical search algorithms: **BM25** and **TF-IDF** with a hybrid scoring approach.

---

## Current State Analysis

### Current Implementation Issues

1. **Simple Substring Matching (`icontains`)**
   - No term frequency consideration
   - No document frequency weighting
   - No proper ranking algorithm
   - Weak for synonyms and multi-concept queries

2. **PostgreSQL FTS Disabled**
   - Previously marked as "broken"
   - Even if working, lacks BM25 weighting
   - No TF-IDF term importance
   - Limited query saturation/normalization

3. **Evaluation Results Show Poor Performance**
   - MRR: 0.15 (very low - should be >0.5)
   - NDCG: 0.12 (very low - should be >0.4)
   - Precision@10: 0.18 (low - should be >0.3)
   - Particularly weak for:
     - Long natural language queries
     - Synonym-based queries
     - Conceptual queries
     - Multi-issue queries

---

## Recommended Solution: Hybrid BM25 + TF-IDF

### Architecture Decision

**Recommended Approach: Python-Native Implementation**

**Option Selected: `rank-bm25` + `scikit-learn` TF-IDF**

**Rationale:**
- ✅ **No external infrastructure** (no Elasticsearch/Typesense setup needed)
- ✅ **Django-native** (works with existing PostgreSQL database)
- ✅ **Already have dependencies** (scikit-learn is installed)
- ✅ **Easy to integrate** (pure Python libraries)
- ✅ **Industry-standard algorithms** (BM25 is the gold standard for lexical IR)
- ✅ **Flexible** (can tune parameters, add custom features)
- ✅ **Fast enough** for legal document search (thousands to tens of thousands of documents)

**Alternative Options Considered:**
- **Elasticsearch**: Best performance, but requires separate infrastructure
- **Typesense**: Fast, but external service dependency
- **Vespa**: Heavy, overkill for current scale
- **Whoosh**: Good option, but rank-bm25 is simpler and more focused

---

## Implementation Strategy

### Phase 1: Core BM25 Implementation

**Algorithm: BM25 (Best Matching 25)**

BM25 formula:
```
score(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))
```

Where:
- `f(qi, D)`: Term frequency of query term `qi` in document `D`
- `IDF(qi)`: Inverse Document Frequency of term `qi`
- `|D|`: Document length
- `avgdl`: Average document length
- `k1`: Term frequency saturation parameter (default: 1.5)
- `b`: Length normalization parameter (default: 0.75)

**Key Features:**
- Term frequency saturation (prevents over-weighting repeated terms)
- Length normalization (normalizes for document length)
- IDF weighting (rare terms get higher weight)

### Phase 2: TF-IDF Keyword Extraction

**Purpose:** Extract and weight important keywords from queries and documents

**Use Cases:**
- Rare terms (PPC, CrPC, citation numbers, FIRs)
- Legal jargon
- Unusual keywords
- Synonym expansion (via token expansion)

**Implementation:**
- Use `scikit-learn`'s `TfidfVectorizer` for document indexing
- Extract top-K TF-IDF terms from documents
- Use TF-IDF scores for query expansion and boosting

### Phase 3: Hybrid Scoring

**Formula:**
```
Final Lexical Score = 0.7 × BM25_Score + 0.3 × TF-IDF_Score
```

**Benefits:**
- **Stronger recall**: BM25 catches more relevant documents
- **Better ranking**: TF-IDF helps with rare/important terms
- **Robust keyword matching**: Combines best of both algorithms

---

## Technical Implementation Plan

### 1. Dependencies

Add to `requirements.txt`:
```txt
rank-bm25>=0.2.2  # Pure Python BM25 implementation
```

(Note: `scikit-learn` is already installed)

### 2. New Service Architecture

```
backend/search_module/search_indexing/services/
├── bm25_indexing.py          # NEW: BM25 indexing and search
├── tfidf_indexing.py         # NEW: TF-IDF keyword extraction
├── hybrid_lexical_search.py  # NEW: Combines BM25 + TF-IDF
└── keyword_indexing.py       # MODIFY: Integrate new services
```

### 3. Data Structure

**BM25 Index:**
- Store pre-computed document term frequencies
- Store document lengths
- Store average document length
- Store IDF values for all terms

**TF-IDF Index:**
- Store TF-IDF vectors for each document
- Store vocabulary mapping
- Store IDF values

**Storage Options:**
1. **In-Memory** (recommended for start): Fast, but requires rebuilding on restart
2. **Pickle files**: Persistent, fast loading
3. **Database table**: Persistent, queryable, but slower

**Recommendation:** Start with in-memory + pickle persistence for fast startup.

### 4. Integration Points

**Modify `KeywordIndexingService.search()`:**
- Replace `icontains` logic with BM25 + TF-IDF hybrid
- Keep existing filters (court, status, dates)
- Maintain backward compatibility with existing API

**Index Building:**
- Build BM25 index from `SearchMetadata` fields:
  - `case_number_normalized`
  - `case_title_normalized`
  - `parties_normalized`
  - `court_normalized`
  - `status_normalized`
  - `searchable_keywords` (if available)
- Build TF-IDF index from same fields
- Update index when new cases are indexed

---

## Field Weighting Strategy

Different fields should have different importance:

```python
FIELD_WEIGHTS = {
    'case_number_normalized': 3.0,    # Highest: Exact matches are very important
    'case_title_normalized': 2.0,      # High: Title is very descriptive
    'parties_normalized': 1.5,         # Medium-High: Parties are important
    'court_normalized': 1.0,           # Medium: Court is contextual
    'status_normalized': 0.5,          # Low: Status is less searchable
    'searchable_keywords': 1.2,        # Medium-High: Optimized keywords
}
```

**BM25 Multi-Field Scoring:**
```
score(document, query) = Σ (field_weight × BM25_score(field, query))
```

---

## Query Processing Pipeline

### 1. Query Normalization
- Normalize legal abbreviations (CrPC, PPC, etc.)
- Lowercase
- Remove extra whitespace
- **NEW**: Extract legal entities and expand synonyms

### 2. Query Expansion (TF-IDF Based)
- Extract important terms from query using TF-IDF
- Expand with synonyms (legal terminology)
- Boost rare terms (citation numbers, FIRs)

### 3. BM25 Search
- Search across all weighted fields
- Calculate BM25 scores
- Return top-K candidates

### 4. TF-IDF Re-ranking
- Calculate TF-IDF similarity scores
- Combine with BM25 scores (0.7 × BM25 + 0.3 × TF-IDF)

### 5. Final Ranking
- Apply field-specific boosts
- Apply recency boost (if applicable)
- Return ranked results

---

## Performance Considerations

### Index Size
- **Estimated**: ~10-50MB for 10,000 cases (in-memory)
- **Disk**: ~5-20MB (pickle files)

### Query Speed
- **BM25**: ~1-10ms per query (in-memory)
- **TF-IDF**: ~5-20ms per query (in-memory)
- **Total**: ~10-30ms per query (acceptable for web search)

### Index Building
- **Initial build**: ~1-5 minutes for 10,000 cases
- **Incremental updates**: ~10-100ms per case

### Memory Usage
- **In-memory index**: ~50-200MB for 10,000 cases
- **Acceptable** for most servers

---

## Migration Strategy

### Phase 1: Parallel Implementation (Week 1)
1. Implement `BM25IndexingService`
2. Implement `TfidfIndexingService`
3. Implement `HybridLexicalSearchService`
4. Add unit tests

### Phase 2: Integration (Week 2)
1. Integrate into `KeywordIndexingService`
2. Add feature flag: `USE_BM25_TFIDF` (default: False)
3. Build indexes for existing data
4. Test with evaluation queries

### Phase 3: Evaluation (Week 3)
1. Run evaluation with new implementation
2. Compare metrics (MRR, NDCG, Precision, Recall)
3. Tune parameters (k1, b, field weights, hybrid weights)
4. Optimize performance

### Phase 4: Production Rollout (Week 4)
1. Enable feature flag for new searches
2. Monitor performance
3. Gradually migrate all searches
4. Remove old `icontains` implementation

---

## Expected Improvements

### Metrics Targets

**Current (icontains):**
- MRR: 0.15
- NDCG: 0.12
- Precision@10: 0.18
- Recall@10: 0.22

**Target (BM25 + TF-IDF):**
- MRR: **0.45-0.60** (3-4x improvement)
- NDCG: **0.40-0.55** (3-4x improvement)
- Precision@10: **0.35-0.50** (2-3x improvement)
- Recall@10: **0.50-0.70** (2-3x improvement)

### Query Category Improvements

**Long Natural Language Queries:**
- Current: Very poor (MRR ~0.05)
- Target: Good (MRR ~0.40)

**Synonym-Based Queries:**
- Current: Poor (MRR ~0.10)
- Target: Good (MRR ~0.45) with query expansion

**Conceptual Queries:**
- Current: Poor (MRR ~0.12)
- Target: Moderate (MRR ~0.35)

**Multi-Issue Queries:**
- Current: Poor (MRR ~0.15)
- Target: Good (MRR ~0.40)

---

## Configuration Parameters

### BM25 Parameters
```python
BM25_CONFIG = {
    'k1': 1.5,        # Term frequency saturation (1.2-2.0)
    'b': 0.75,        # Length normalization (0.0-1.0)
    'epsilon': 0.25,  # IDF smoothing
}
```

### TF-IDF Parameters
```python
TFIDF_CONFIG = {
    'max_features': 10000,      # Maximum vocabulary size
    'min_df': 1,                # Minimum document frequency
    'max_df': 0.95,             # Maximum document frequency (remove common words)
    'ngram_range': (1, 2),      # Unigrams and bigrams
    'stop_words': 'english',    # Remove common words
}
```

### Hybrid Weights
```python
HYBRID_WEIGHTS = {
    'bm25_weight': 0.7,    # BM25 contribution
    'tfidf_weight': 0.3,   # TF-IDF contribution
}
```

### Field Weights
```python
FIELD_WEIGHTS = {
    'case_number_normalized': 3.0,
    'case_title_normalized': 2.0,
    'parties_normalized': 1.5,
    'court_normalized': 1.0,
    'status_normalized': 0.5,
    'searchable_keywords': 1.2,
}
```

---

## Testing Strategy

### Unit Tests
- BM25 scoring correctness
- TF-IDF vectorization
- Hybrid score combination
- Field weighting

### Integration Tests
- End-to-end search queries
- Index building and updating
- Performance benchmarks

### Evaluation Tests
- Run evaluation command with new implementation
- Compare metrics with baseline
- Category-based analysis

---

## Future Enhancements

### Short Term (3-6 months)
1. **Query Expansion**: Legal synonym dictionary
2. **Spell Correction**: Handle misspellings in queries
3. **Phrase Matching**: Boost exact phrase matches
4. **Learning to Rank**: ML-based reranking

### Long Term (6-12 months)
1. **Elasticsearch Migration**: If scale requires it
2. **Distributed Indexing**: For very large datasets
3. **Real-time Updates**: Stream indexing
4. **A/B Testing Framework**: Compare algorithms

---

## Risk Mitigation

### Risks
1. **Performance degradation**: BM25 + TF-IDF might be slower than `icontains`
2. **Index size**: Large indexes might cause memory issues
3. **Index staleness**: Need to keep index updated with new cases

### Mitigation
1. **Benchmarking**: Measure performance before/after
2. **Caching**: Cache frequent queries
3. **Incremental updates**: Update index incrementally
4. **Feature flag**: Easy rollback if issues occur

---

## Conclusion

Implementing BM25 + TF-IDF hybrid lexical search will significantly improve search quality, especially for complex queries involving synonyms, natural language, and multi-concept searches. The Python-native approach using `rank-bm25` and `scikit-learn` provides industry-grade algorithms without requiring external infrastructure.

**Next Steps:**
1. Review and approve this plan
2. Implement Phase 1 (Core BM25)
3. Test and evaluate
4. Iterate and improve

