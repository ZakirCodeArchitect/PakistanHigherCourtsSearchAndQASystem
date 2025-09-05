import json
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
import requests
import openai
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

logger = logging.getLogger(__name__)

class AISnippetService:
    """
    AI-powered snippet generation service that uses language models
    to create high-quality, contextual snippets from case data
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = {
            'model_type': 'api',  # 'api' or 'local'
            'api_provider': 'openai',  # 'openai', 'anthropic', 'google'
            'local_model_name': 'microsoft/DialoGPT-medium',
            'max_snippet_length': 200,
            'temperature': 0.3,
            'max_tokens': 150,
            'timeout': 10,
        }
        
        # Update with custom config
        if config:
            self.config.update(config)
        
        # Initialize API clients
        self._init_api_clients()
        
        # Initialize local model (if needed)
        self.local_model = None
        self.local_tokenizer = None
        
    def _init_api_clients(self):
        """Initialize API clients for different providers"""
        try:
            if self.config['api_provider'] == 'openai':
                openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)
            elif self.config['api_provider'] == 'anthropic':
                self.anthropic_client = None  # Will be initialized when needed
        except Exception as e:
            logger.warning(f"API client initialization failed: {e}")
    
    def generate_ai_snippet(self, 
                           case_data: Dict[str, Any], 
                           query: str,
                           document_chunks: List[str] = None,
                           max_snippets: int = 3) -> List[Dict[str, Any]]:
        """
        Generate AI-powered snippets from case data
        
        Args:
            case_data: Case information (title, court, status, etc.)
            query: Original search query
            document_chunks: List of document chunk texts
            max_snippets: Maximum number of snippets to generate
            
        Returns:
            List of AI-generated snippet objects
        """
        try:
            # Prepare context for AI model
            context = self._prepare_context(case_data, query, document_chunks)
            
            # Generate snippets using AI
            if self.config['model_type'] == 'api':
                snippets = self._generate_api_snippets(context, query, max_snippets)
            else:
                snippets = self._generate_local_snippets(context, query, max_snippets)
            
            return snippets
            
        except Exception as e:
            logger.error(f"Error generating AI snippets: {str(e)}")
            # Fallback to simple extraction
            return self._fallback_snippet_generation(case_data, document_chunks)
    
    def _prepare_context(self, 
                        case_data: Dict[str, Any], 
                        query: str, 
                        document_chunks: List[str]) -> str:
        """Prepare context for AI model"""
        
        # Extract key information
        case_title = case_data.get('case_title', 'Unknown Case')
        court = case_data.get('court', 'Unknown Court')
        status = case_data.get('status', 'Unknown Status')
        case_number = case_data.get('case_number', 'N/A')
        
        # Prepare document content
        document_content = ""
        if document_chunks:
            # Take first few chunks with most relevant content
            relevant_chunks = self._select_relevant_chunks(document_chunks, query)
            document_content = "\n\n".join(relevant_chunks[:3])  # Max 3 chunks
        
        context = f"""
CASE INFORMATION:
Title: {case_title}
Court: {court}
Status: {status}
Case Number: {case_number}

DOCUMENT CONTENT:
{document_content}

SEARCH QUERY: {query}
"""
        return context.strip()
    
    def _select_relevant_chunks(self, chunks: List[str], query: str) -> List[str]:
        """Select most relevant chunks based on query terms"""
        query_terms = query.lower().split()
        scored_chunks = []
        
        for chunk in chunks:
            if not chunk or len(chunk.strip()) < 50:
                continue
                
            # Simple relevance scoring
            chunk_lower = chunk.lower()
            score = sum(1 for term in query_terms if term in chunk_lower)
            
            # Boost score for legal terms
            legal_terms = ['court', 'judge', 'order', 'judgment', 'law', 'legal', 'case', 'petition', 'appeal']
            score += sum(0.5 for term in legal_terms if term in chunk_lower)
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by relevance and return top chunks
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_chunks]
    
    def _generate_api_snippets(self, context: str, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets using API-based models"""
        
        if self.config['api_provider'] == 'openai':
            return self._generate_openai_snippets(context, query, max_snippets)
        elif self.config['api_provider'] == 'anthropic':
            return self._generate_anthropic_snippets(context, query, max_snippets)
        elif self.config['api_provider'] == 'google':
            return self._generate_google_snippets(context, query, max_snippets)
        else:
            raise ValueError(f"Unsupported API provider: {self.config['api_provider']}")
    
    def _generate_openai_snippets(self, context: str, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets using OpenAI API"""
        try:
            prompt = f"""
You are a legal research assistant. Given the following case information and document content, generate {max_snippets} concise, informative snippets that would help a user understand why this case is relevant to their search query.

Focus on:
1. Key legal issues and facts
2. Important court decisions or orders
3. Relevant legal principles
4. Case outcomes or status

Keep each snippet under 150 words and make them informative and readable.

{context}

Generate {max_snippets} snippets that explain why this case is relevant to the query "{query}":
"""
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a legal research assistant specializing in case law analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature'],
                timeout=self.config['timeout']
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_ai_response(content, query)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return []
    
    def _generate_anthropic_snippets(self, context: str, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets using Anthropic Claude API"""
        try:
            prompt = f"""
Given this legal case information, generate {max_snippets} concise snippets explaining why this case is relevant to the search query "{query}".

Focus on key legal issues, court decisions, and relevant facts. Keep snippets under 150 words each.

{context}

Generate {max_snippets} informative snippets:
"""
            
            # This would use Anthropic's API when available
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            return []
    
    def _generate_google_snippets(self, context: str, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets using Google Gemini API"""
        try:
            # This would use Google's Gemini API when available
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Google API error: {str(e)}")
            return []
    
    def _generate_local_snippets(self, context: str, query: str, max_snippets: int) -> List[Dict[str, Any]]:
        """Generate snippets using local language model"""
        try:
            if not self.local_model:
                self._load_local_model()
            
            # Prepare prompt for local model
            prompt = f"Generate {max_snippets} legal case snippets for query '{query}':\n{context}\n\nSnippets:"
            
            # Generate using local model
            inputs = self.local_tokenizer.encode(prompt, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.local_model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.config['max_tokens'],
                    temperature=self.config['temperature'],
                    do_sample=True,
                    pad_token_id=self.local_tokenizer.eos_token_id
                )
            
            generated_text = self.local_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return self._parse_ai_response(generated_text, query)
            
        except Exception as e:
            logger.error(f"Local model error: {str(e)}")
            return []
    
    def _load_local_model(self):
        """Load local language model"""
        try:
            model_name = self.config['local_model_name']
            self.local_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.local_model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Set pad token
            if self.local_tokenizer.pad_token is None:
                self.local_tokenizer.pad_token = self.local_tokenizer.eos_token
                
        except Exception as e:
            logger.error(f"Failed to load local model: {str(e)}")
            raise
    
    def _parse_ai_response(self, response: str, query: str) -> List[Dict[str, Any]]:
        """Parse AI response into snippet objects"""
        try:
            snippets = []
            
            # Try to extract numbered snippets
            lines = response.split('\n')
            current_snippet = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a new snippet (starts with number or bullet)
                if (line.startswith(('1.', '2.', '3.', '4.', '5.')) or 
                    line.startswith(('•', '-', '*')) or
                    len(current_snippet) > 100):
                    
                    if current_snippet:
                        snippets.append(self._create_snippet_object(current_snippet, query))
                        current_snippet = ""
                
                # Add line to current snippet
                if line.startswith(('1.', '2.', '3.', '4.', '5.')):
                    current_snippet = line[2:].strip()
                elif line.startswith(('•', '-', '*')):
                    current_snippet = line[1:].strip()
                else:
                    current_snippet += " " + line
            
            # Add final snippet
            if current_snippet:
                snippets.append(self._create_snippet_object(current_snippet, query))
            
            # If no structured snippets found, treat entire response as one snippet
            if not snippets and response:
                snippets.append(self._create_snippet_object(response, query))
            
            return snippets[:3]  # Max 3 snippets
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return []
    
    def _create_snippet_object(self, text: str, query: str) -> Dict[str, Any]:
        """Create a snippet object from text"""
        # Clean up the text
        text = text.strip()
        if text.endswith('.'):
            text = text[:-1]
        
        return {
            'text': text,
            'type': 'ai_generated',
            'relevance_score': 0.9,  # High relevance for AI-generated content
            'matched_term': query,
            'length': len(text),
            'source': 'ai_model'
        }
    
    def _fallback_snippet_generation(self, case_data: Dict[str, Any], document_chunks: List[str]) -> List[Dict[str, Any]]:
        """Fallback snippet generation when AI fails"""
        snippets = []
        
        # Create simple snippets from case data
        case_title = case_data.get('case_title', 'Unknown Case')
        court = case_data.get('court', 'Unknown Court')
        status = case_data.get('status', 'Unknown Status')
        
        snippet_text = f"This case involves {case_title} in {court}. Status: {status}."
        snippets.append({
            'text': snippet_text,
            'type': 'fallback',
            'relevance_score': 0.5,
            'matched_term': 'case_info',
            'length': len(snippet_text),
            'source': 'fallback'
        })
        
        return snippets
