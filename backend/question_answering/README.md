# Question Answering System

AI-powered legal question answering system for Pakistan Higher Courts Search & QA System.

## Features

- **Natural Language Processing**: Advanced query understanding and processing
- **Legal Knowledge Base**: Comprehensive database of Pakistani legal cases and documents
- **AI-Powered Answers**: Intelligent answer generation using OpenAI GPT models
- **Vector Search**: Pinecone-based semantic search for relevant legal content
- **Chat Interface**: Interactive chatbot for legal research
- **Session Management**: Track and manage conversation sessions
- **Analytics Dashboard**: Performance metrics and usage analytics
- **Feedback System**: User rating and feedback collection

## Architecture

### Core Components

1. **QA Engine**: Main orchestrator for question-answering process
2. **Knowledge Retriever**: Retrieves relevant legal knowledge using Pinecone
3. **Answer Generator**: Generates intelligent answers using AI models
4. **Context Manager**: Manages conversation context and session state
5. **Query Processor**: Processes and normalizes user queries

### Database Models

- **QASession**: Conversation sessions between users and the system
- **QAQuery**: Individual questions asked in sessions
- **QAResponse**: AI-generated responses to queries
- **QAKnowledgeBase**: Indexed legal content for retrieval
- **QAFeedback**: User feedback on responses
- **QAConfiguration**: System configuration settings
- **QAMetrics**: Performance and usage metrics

## Installation

1. **Clone the repository**:
   ```bash
   cd backend/question_answering
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export PINECONE_API_KEY="your-pinecone-api-key"
   export PINECONE_ENVIRONMENT="us-west1-gcp"
   ```

4. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Populate knowledge base**:
   ```bash
   python manage.py populate_knowledge_base
   ```

7. **Index knowledge base**:
   ```bash
   python manage.py index_knowledge_base
   ```

8. **Run the server**:
   ```bash
   python manage.py runserver
   ```

## Usage

### API Endpoints

#### Session Management
- `GET /api/qa/sessions/` - List user sessions
- `POST /api/qa/sessions/` - Create new session
- `GET /api/qa/sessions/{session_id}/` - Get session details
- `PUT /api/qa/sessions/{session_id}/` - Update session
- `DELETE /api/qa/sessions/{session_id}/` - Delete session

#### Question Answering
- `POST /api/qa/ask/` - Ask a question
- `POST /api/qa/ask/stream/` - Ask question with streaming response

#### Feedback
- `POST /api/qa/responses/{response_id}/feedback/` - Submit feedback

#### Analytics
- `GET /api/qa/analytics/` - Get analytics data
- `GET /api/qa/metrics/` - Get system metrics

### Frontend Interface

- `/qa/` - Main QA interface
- `/qa/chat/` - Chat interface
- `/qa/sessions/` - Session management
- `/qa/analytics/` - Analytics dashboard

## Configuration

### QA Settings

```python
QA_SETTINGS = {
    'EMBEDDING_MODEL': 'all-MiniLM-L6-v2',
    'GENERATION_MODEL': 'gpt-3.5-turbo',
    'MAX_TOKENS': 1000,
    'TEMPERATURE': 0.7,
    'TOP_K_DOCUMENTS': 5,
    'SIMILARITY_THRESHOLD': 0.7,
    'MAX_CONTEXT_LENGTH': 4000,
    'ENABLE_STREAMING': True,
    'ENABLE_FEEDBACK': True,
}
```

### Pinecone Configuration

```python
PINECONE_API_KEY = "your-api-key"
PINECONE_ENVIRONMENT = "us-west1-gcp"
PINECONE_INDEX_NAME = "legal-knowledge-base"
```

## Management Commands

### Populate Knowledge Base
```bash
python manage.py populate_knowledge_base [options]
```

Options:
- `--force`: Force repopulation of all items
- `--limit N`: Limit number of cases to process
- `--case-id ID`: Process specific case ID
- `--source-types TYPE1 TYPE2`: Types of knowledge to populate
- `--dry-run`: Show what would be populated

### Index Knowledge Base
```bash
python manage.py index_knowledge_base [options]
```

Options:
- `--force`: Force reindexing of all items
- `--limit N`: Limit number of items to process
- `--source-type TYPE`: Index only specific source type
- `--dry-run`: Show what would be indexed

## Development

### Project Structure

```
question_answering/
├── apps.py
├── models.py
├── views.py
├── urls.py
├── admin.py
├── services/
│   ├── qa_engine.py
│   ├── knowledge_retriever.py
│   ├── answer_generator.py
│   ├── context_manager.py
│   └── query_processor.py
├── management/
│   └── commands/
│       ├── populate_knowledge_base.py
│       └── index_knowledge_base.py
├── templates/
│   └── question_answering/
│       ├── qa_interface.html
│       ├── qa_chat.html
│       ├── qa_sessions.html
│       └── qa_analytics.html
└── core/
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── asgi.py
```

### Adding New Features

1. **New Service**: Add to `services/` directory
2. **New Model**: Add to `models.py`
3. **New API Endpoint**: Add to `views.py` and `urls.py`
4. **New Management Command**: Add to `management/commands/`

## Testing

```bash
python manage.py test
```

## Deployment

### Production Settings

1. Set `DEBUG = False`
2. Configure proper database
3. Set up static file serving
4. Configure logging
5. Set up monitoring

### Environment Variables

```bash
export DJANGO_SETTINGS_MODULE=question_answering.core.settings
export SECRET_KEY="your-secret-key"
export DEBUG=False
export ALLOWED_HOSTS="your-domain.com"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is part of the Pakistan Higher Courts Search & QA System.
