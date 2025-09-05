"""
Configuration for AI-powered snippet generation
"""

# AI Snippet Service Configuration
AI_SNIPPET_CONFIG = {
    # Model Configuration
    'model_type': 'api',  # 'api' or 'local'
    'api_provider': 'openai',  # 'openai', 'anthropic', 'google'
    
    # Local Model Configuration (if using local models)
    'local_model_name': 'microsoft/DialoGPT-medium',
    
    # API Configuration
    'openai_model': 'gpt-3.5-turbo',
    'anthropic_model': 'claude-3-haiku-20240307',
    'google_model': 'gemini-1.5-flash',
    
    # Generation Parameters
    'max_snippet_length': 200,
    'temperature': 0.3,
    'max_tokens': 150,
    'timeout': 10,
    
    # Snippet Quality Settings
    'max_snippets_per_case': 3,
    'min_snippet_length': 50,
    'prefer_ai_snippets': True,
    'fallback_to_traditional': True,
    
    # Content Selection
    'max_document_chunks': 5,
    'min_chunk_length': 50,
    'prioritize_relevant_chunks': True,
}

# OpenAI API Configuration
OPENAI_CONFIG = {
    'api_key': None,  # Set in environment variables
    'model': 'gpt-3.5-turbo',
    'max_tokens': 150,
    'temperature': 0.3,
    'timeout': 10,
}

# Anthropic API Configuration
ANTHROPIC_CONFIG = {
    'api_key': None,  # Set in environment variables
    'model': 'claude-3-haiku-20240307',
    'max_tokens': 150,
    'temperature': 0.3,
    'timeout': 10,
}

# Google API Configuration
GOOGLE_CONFIG = {
    'api_key': None,  # Set in environment variables
    'model': 'gemini-1.5-flash',
    'max_tokens': 150,
    'temperature': 0.3,
    'timeout': 10,
}

# Local Model Configuration
LOCAL_MODEL_CONFIG = {
    'model_name': 'microsoft/DialoGPT-medium',
    'device': 'cpu',  # 'cpu' or 'cuda'
    'max_length': 200,
    'temperature': 0.3,
    'do_sample': True,
}

# Prompt Templates
PROMPT_TEMPLATES = {
    'openai': """
You are a legal research assistant. Given the following case information and document content, generate {max_snippets} concise, informative snippets that would help a user understand why this case is relevant to their search query.

Focus on:
1. Key legal issues and facts
2. Important court decisions or orders
3. Relevant legal principles
4. Case outcomes or status

Keep each snippet under 150 words and make them informative and readable.

{context}

Generate {max_snippets} snippets that explain why this case is relevant to the query "{query}":
""",
    
    'anthropic': """
Given this legal case information, generate {max_snippets} concise snippets explaining why this case is relevant to the search query "{query}".

Focus on key legal issues, court decisions, and relevant facts. Keep snippets under 150 words each.

{context}

Generate {max_snippets} informative snippets:
""",
    
    'google': """
Generate {max_snippets} legal case snippets for the query "{query}".

{context}

Snippets:
"""
}

# Legal Term Expansions
LEGAL_TERM_EXPANSIONS = {
    'murder': 'murder killing homicide death sentence killed slain assassination manslaughter',
    'case': 'case matter proceeding suit litigation action',
    'bail': 'bail bond surety release custody',
    'appeal': 'appeal revision petition review',
    'conviction': 'conviction sentence judgment verdict finding',
    'criminal': 'criminal offence crime violation',
    'civil': 'civil dispute matter controversy',
    'constitutional': 'constitutional fundamental rights charter',
    'habeas': 'habeas corpus detention custody imprisonment',
    'contract': 'contract agreement obligation promise',
    'property': 'property ownership possession title',
    'family': 'family marriage divorce custody',
    'employment': 'employment labor work job',
    'tax': 'tax taxation revenue assessment',
    'immigration': 'immigration visa citizenship deportation',
}

# Quality Thresholds
QUALITY_THRESHOLDS = {
    'min_relevance_score': 0.5,
    'max_metadata_ratio': 0.3,  # Max 30% metadata in snippet
    'min_legal_terms': 1,  # At least 1 legal term
    'max_snippet_length': 200,
    'min_snippet_length': 50,
}
