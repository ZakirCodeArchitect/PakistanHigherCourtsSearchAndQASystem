# 🤖 Legal Chatbot Technical Architecture

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Database Architecture](#database-architecture)
3. [RAG Pipeline](#rag-pipeline)
4. [Query Processing Flow](#query-processing-flow)
5. [Response Generation](#response-generation)
6. [Component Details](#component-details)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Technical Specifications](#technical-specifications)

---

## 🏗️ System Overview

Our legal chatbot is a **Retrieval-Augmented Generation (RAG)** system that combines:
- **Vector Search** (Pinecone) for semantic document retrieval
- **AI Generation** (GPT-3.5-turbo) for intelligent answer synthesis
- **PostgreSQL Database** for structured legal data
- **Django Backend** for API management
- **Real-time Web Interface** for user interaction

### Core Components
```
User Query → Query Processing → Vector Search → Document Retrieval → AI Generation → Response
     ↓              ↓              ↓              ↓              ↓           ↓
  Frontend    Query Analysis   Pinecone DB   PostgreSQL DB   OpenAI API   Frontend
```

---

## 🗄️ Database Architecture

### 1. PostgreSQL Database (`ihc_cases_db`)

#### **Primary Tables:**
```sql
-- Core legal cases
cases (355 records)
├── id, case_number, case_title, status, bench, hearing_date
├── court_id (FK → courts)
└── created_at, updated_at

-- Case details
case_details (108 records)
├── case_id (FK → cases)
├── case_description, case_stage, short_order
├── advocates_petitioner, advocates_respondent
└── fir_number, incident, under_section

-- Documents
documents (156 records)
├── id, file_name, file_path, file_size
└── created_at, updated_at

-- Document text extraction
document_texts
├── document_id (FK → documents)
├── page_number, clean_text
└── created_at

-- Court information
courts
├── id, name, jurisdiction
└── created_at
```

#### **QA-Specific Tables:**
```sql
-- Knowledge base for RAG
qa_knowledge_base (183 records)
├── source_type, source_id, source_case_id, source_document_id
├── title, content_text, content_summary
├── court, case_number, case_title, judge_name
├── legal_domain, legal_concepts, legal_entities, citations
├── vector_id, embedding_model, embedding_dimension
├── content_quality_score, legal_relevance_score, completeness_score
└── is_indexed, is_processed, created_at

-- QA sessions
qa_sessions
├── session_id, user_id, title, description
├── context_data, conversation_history
├── total_queries, successful_queries, user_satisfaction_score
└── is_active, created_at, updated_at

-- Individual queries
qa_queries
├── session_id (FK → qa_sessions)
├── query_text, query_type, query_intent
├── processing_time, tokens_used
└── created_at

-- AI responses
qa_responses
├── query_id (FK → qa_queries)
├── answer_text, answer_type, confidence_score
├── model_used, tokens_used, processing_time
├── sources, metadata
└── created_at

-- System configuration
qa_configurations
├── config_name, config_type, description
├── embedding_model, generation_model
├── max_tokens, temperature, top_k_documents
└── is_active, created_at
```

### 2. Pinecone Vector Database

#### **Index: `legal-cases-index`**
```json
{
  "name": "legal-cases-index",
  "dimension": 384,
  "metric": "cosine",
  "vector_count": 545,
  "spec": {
    "cloud": "aws",
    "region": "us-east-1"
  }
}
```

#### **Vector Structure:**
```json
{
  "id": "case_123_case_metadata_4567",
  "values": [0.1234, -0.5678, 0.9012, ...], // 384 dimensions
  "metadata": {
    "case_id": 123,
    "content_type": "case_metadata",
    "content": "Case Title: Writ Petition...",
    "court": "Islamabad High Court",
    "case_number": "WP-123/2025",
    "legal_domain": "Constitutional Law",
    "created_at": "2025-01-10T10:30:00Z"
  }
}
```

---

## 🔄 RAG Pipeline

### 1. **Document Indexing Process**
```
Raw Legal Data → Text Extraction → Chunking → Embedding Generation → Vector Storage
     ↓                ↓              ↓            ↓                    ↓
PostgreSQL DB    PDF Processing   Text Chunks   Sentence Transformer   Pinecone
```

### 2. **Query Processing Pipeline**
```
User Query → Query Analysis → Embedding Generation → Vector Search → Document Retrieval
     ↓            ↓                ↓                    ↓              ↓
Frontend    Query Processor    Sentence Transformer   Pinecone      PostgreSQL
```

### 3. **Response Generation Pipeline**
```
Retrieved Documents → Context Preparation → AI Prompt → GPT-3.5-turbo → Response
        ↓                    ↓              ↓            ↓              ↓
   PostgreSQL DB        Context Builder   Prompt       OpenAI API    Frontend
```

---

## 🔍 Query Processing Flow

### **Step 1: User Input**
```javascript
// Frontend (simple_qa_interface.html)
const query = "What is a writ petition?";
const useAI = true;

fetch('/api/qa/ask/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: query, use_ai: useAI})
})
```

### **Step 2: Django API Processing**
```python
# simple_views.py - SimpleQAAPIView
def post(self, request):
    data = json.loads(request.body)
    question = data.get('question', '')
    use_ai = data.get('use_ai', True)
    
    # Initialize Enhanced QA Engine
    qa_engine = EnhancedQAEngine()
    
    # Process query
    result = qa_engine.ask_question(
        question=question,
        conversation_history=None,
        use_ai=use_ai
    )
    
    return JsonResponse(result)
```

### **Step 3: Enhanced QA Engine Processing**
```python
# enhanced_qa_engine.py
def ask_question(self, question, conversation_history=None, use_ai=True):
    # Step 1: Knowledge Retrieval
    search_results = self.knowledge_retriever.search_legal_cases(question, top_k=5)
    
    # Step 2: Context Preparation
    relevant_documents = self._prepare_case_context(search_results)
    
    # Step 3: AI Generation or Simple Retrieval
    if use_ai and self.ai_generator.enabled:
        answer_data = self.ai_generator.generate_answer(
            question=question,
            context_documents=relevant_documents,
            conversation_history=conversation_history
        )
    else:
        answer_data = self._generate_simple_answer(question, relevant_documents)
    
    return answer_data
```

### **Step 4: Knowledge Retrieval (RAG)**
```python
# knowledge_retriever.py
def search_legal_cases(self, query, top_k=5):
    # Try RAG search first
    if self.rag_service and self.rag_service.pinecone_index:
        rag_results = self.rag_service.search_similar_documents(query, top_k)
        
        if rag_results:
            enhanced_results = self._enhance_rag_results(rag_results)
            return enhanced_results
    
    # Fallback to database search
    return self._database_search(query, top_k)
```

### **Step 5: Vector Search (Pinecone)**
```python
# rag_service.py
def search_similar_documents(self, query, top_k=5):
    # Generate query embedding
    query_embedding = self.create_query_embedding(query)
    
    # Search Pinecone
    search_results = self.pinecone_index.query(
        vector=query_embedding.tolist(),
        top_k=top_k,
        include_metadata=True
    )
    
    # Process results
    results = []
    for match in search_results['matches']:
        result = {
            'id': match['id'],
            'score': match['score'],
            'metadata': match.get('metadata', {}),
            'content': match.get('metadata', {}).get('content', ''),
            'case_id': match.get('metadata', {}).get('case_id'),
            'document_id': match.get('metadata', {}).get('document_id'),
            'content_type': match.get('metadata', {}).get('content_type', 'unknown')
        }
        results.append(result)
    
    return results
```

### **Step 6: AI Answer Generation**
```python
# ai_answer_generator.py
def generate_answer(self, question, context_documents, conversation_history=None):
    # Prepare context
    context_text = self._prepare_context(context_documents)
    
    # Create prompt
    prompt = f"""
    Question: {question}
    
    Context from legal documents:
    {context_text}
    
    Please provide a comprehensive answer based on the legal context provided.
    """
    
    # Call OpenAI API
    response = self.client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    
    return {
        'answer': response.choices[0].message.content,
        'answer_type': 'ai_generated',
        'confidence': 0.9,
        'model_used': 'gpt-3.5-turbo',
        'tokens_used': response.usage.total_tokens,
        'sources': self._extract_sources(context_documents)
    }
```

---

## 🧠 Component Details

### 1. **Sentence Transformer Model**
```python
# Model: all-MiniLM-L6-v2
# Dimensions: 384
# Purpose: Convert text to vector embeddings
# Performance: Fast CPU inference, high quality embeddings

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = embedding_model.encode("What is a writ petition?")
# Result: [0.1234, -0.5678, 0.9012, ...] (384 dimensions)
```

### 2. **Pinecone Vector Database**
```python
# Index: legal-cases-index
# Vector Count: 545
# Dimension: 384
# Metric: Cosine similarity
# Cloud: AWS us-east-1

pc = Pinecone(api_key=api_key)
index = pc.Index("legal-cases-index")
```

### 3. **OpenAI GPT-3.5-turbo**
```python
# Model: gpt-3.5-turbo
# Max Tokens: 1000
# Temperature: 0.7
# Purpose: Generate intelligent legal answers

client = OpenAI(api_key=api_key)
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[...],
    max_tokens=1000,
    temperature=0.7
)
```

### 4. **Django Models**
```python
# QA-specific models for tracking conversations
class QASession(models.Model):
    session_id = models.CharField(max_length=64, unique=True)
    user_id = models.CharField(max_length=100)
    conversation_history = models.JSONField(default=list)
    total_queries = models.IntegerField(default=0)

class QAQuery(models.Model):
    session = models.ForeignKey(QASession, on_delete=models.CASCADE)
    query_text = models.TextField()
    query_type = models.CharField(max_length=50)
    processing_time = models.FloatField()

class QAResponse(models.Model):
    query = models.ForeignKey(QAQuery, on_delete=models.CASCADE)
    answer_text = models.TextField()
    confidence_score = models.FloatField()
    model_used = models.CharField(max_length=100)
    sources = models.JSONField(default=list)
```

---

## 📊 Data Flow Diagrams

### **Complete Query Flow:**
```
1. User Input
   ↓
2. Frontend Validation
   ↓
3. Django API Endpoint
   ↓
4. Enhanced QA Engine
   ↓
5. Knowledge Retriever
   ↓
6. RAG Service (Vector Search)
   ↓
7. Pinecone Database
   ↓
8. Document Enhancement
   ↓
9. AI Answer Generator
   ↓
10. OpenAI API
    ↓
11. Response Processing
    ↓
12. Frontend Display
```

### **RAG Pipeline:**
```
Query → Embedding → Vector Search → Document Retrieval → Context Building → AI Generation → Response
  ↓         ↓            ↓              ↓                ↓              ↓           ↓
Text    Vector      Pinecone       PostgreSQL        Prompt        GPT-3.5    JSON
Input   (384D)      Database       Enhancement       Building      Turbo      Response
```

---

## 🔧 Technical Specifications

### **Performance Metrics:**
- **Query Processing Time**: ~2-5 seconds
- **Vector Search Time**: ~200-500ms
- **AI Generation Time**: ~1-3 seconds
- **Database Query Time**: ~50-200ms
- **Total Response Time**: ~3-8 seconds

### **Scalability:**
- **Vector Database**: Can handle millions of vectors
- **PostgreSQL**: Optimized for legal document queries
- **AI Generation**: Rate-limited by OpenAI API
- **Concurrent Users**: Limited by server resources

### **Error Handling:**
- **Pinecone Unavailable**: Falls back to database search
- **OpenAI API Error**: Returns simple retrieval response
- **Database Error**: Returns error message with fallback
- **Network Issues**: Graceful degradation

### **Security:**
- **API Keys**: Stored in environment variables
- **CSRF Protection**: Disabled for API endpoints
- **Input Validation**: Sanitized user queries
- **Rate Limiting**: Implemented for API calls

---

## 🎯 Current Capabilities

### ✅ **Working Features:**
1. **Semantic Search**: Find relevant legal documents
2. **AI Generation**: Intelligent legal answers
3. **Document Retrieval**: Access to 355 cases, 156 documents
4. **Vector Search**: 545 pre-indexed legal vectors
5. **Session Management**: Track user conversations
6. **Real-time Status**: Monitor system components

### 🚀 **Enhanced Features Needed:**
1. **Document Download**: PDF access for retrieved cases
2. **Metadata Display**: Detailed case information
3. **Citation Tracking**: Source references in answers
4. **Conversation History**: Multi-turn dialogues
5. **User Authentication**: Personalized sessions
6. **Advanced Filtering**: Court, date, case type filters

---

## 🔮 Future Enhancements

### **Phase 1: Enhanced UI**
- Document download links
- Metadata display panels
- Citation formatting
- Conversation history sidebar

### **Phase 2: Advanced Features**
- Multi-turn conversations
- User authentication
- Advanced search filters
- Performance analytics

### **Phase 3: AI Improvements**
- Fine-tuned legal models
- Custom embeddings
- Advanced RAG techniques
- Multi-modal support

---

This technical architecture provides a solid foundation for a production-ready legal chatbot that can understand queries, retrieve relevant documents, and generate intelligent responses while maintaining proper data flow and error handling.
