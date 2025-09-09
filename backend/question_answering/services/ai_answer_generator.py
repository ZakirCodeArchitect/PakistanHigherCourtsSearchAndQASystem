"""
AI Answer Generator Service
Uses OpenAI GPT to generate intelligent answers based on retrieved legal documents
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIAnswerGenerator:
    """Generate intelligent answers using OpenAI GPT"""
    
    def __init__(self):
        """Initialize the AI service"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = getattr(settings, 'QA_SETTINGS', {}).get('GENERATION_MODEL', 'gpt-3.5-turbo')
        self.max_tokens = getattr(settings, 'QA_SETTINGS', {}).get('MAX_TOKENS', 1000)
        self.temperature = getattr(settings, 'QA_SETTINGS', {}).get('TEMPERATURE', 0.7)
        
        if not self.api_key:
            logger.warning("OpenAI API key not found. AI features will be disabled.")
            self.enabled = False
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.enabled = True
                logger.info(f"OpenAI client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.enabled = False
                self.client = None
    
    def generate_answer(
        self, 
        question: str, 
        context_documents: List[Dict[str, Any]], 
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate an intelligent answer based on the question and context documents
        
        Args:
            question: The user's question
            context_documents: List of relevant legal documents
            conversation_history: Previous conversation context
            
        Returns:
            Dictionary containing the generated answer and metadata
        """
        if not self.enabled:
            return self._fallback_answer(question, context_documents)
        
        try:
            # Prepare the context from documents
            context_text = self._prepare_context(context_documents)
            
            # Create the prompt for the AI
            prompt = self._create_prompt(question, context_text, conversation_history)
            
            # Generate response using OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.9,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract the generated answer
            generated_answer = response.choices[0].message.content.strip()
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(response, context_documents)
            
            return {
                'answer': generated_answer,
                'answer_type': 'ai_generated',
                'confidence': confidence,
                'model_used': self.model,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else 0,
                'sources': self._extract_sources(context_documents),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error generating AI answer: {str(e)}")
            return self._fallback_answer(question, context_documents)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI"""
        return """You are a knowledgeable legal research assistant specializing in Pakistani law. Your role is to provide accurate, helpful, and well-structured answers to legal questions based on the provided context documents.

Guidelines:
1. Always base your answers on the provided legal documents and context
2. Be precise and accurate in your legal explanations
3. Cite specific laws, articles, or case references when available
4. Use clear, professional language appropriate for legal research
5. If the context doesn't contain enough information, clearly state the limitations
6. Structure your answers logically with clear explanations
7. Always mention the relevant court or legal authority when citing sources
8. Be helpful but never provide legal advice - only legal information

Format your responses clearly and professionally."""
    
    def _create_prompt(self, question: str, context_text: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Create the prompt for the AI"""
        prompt = f"""Question: {question}

Context Documents:
{context_text}

Please provide a comprehensive answer to the question based on the context documents above. Make sure to:
1. Answer the specific question asked
2. Reference the relevant legal documents and sources
3. Provide clear explanations of legal concepts
4. Include relevant case numbers, court names, and legal provisions when available
5. Structure your answer logically and professionally

Answer:"""
        
        return prompt
    
    def _prepare_context(self, documents: List[Dict[str, Any]]) -> str:
        """Prepare context text from documents"""
        if not documents:
            return "No relevant legal documents found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"""
Document {i}: {doc.get('title', 'Untitled')}
Court: {doc.get('court', 'Unknown')}
Case Number: {doc.get('case_number', 'N/A')}
Category: {doc.get('category', 'General')}

Content:
{doc.get('content', 'No content available')}

Keywords: {', '.join(doc.get('keywords', []))}
""")
        
        return "\n".join(context_parts)
    
    def _calculate_confidence(self, response, context_documents: List[Dict]) -> float:
        """Calculate confidence score based on response quality and context"""
        base_confidence = 0.7  # Base confidence for AI-generated answers
        
        # Adjust based on context quality
        if context_documents:
            # Higher confidence if we have good context
            context_score = min(len(context_documents) / 3, 1.0)  # Max 1.0 for 3+ docs
            base_confidence += context_score * 0.2
        
        # Adjust based on response length (longer responses often more comprehensive)
        answer_length = len(response.choices[0].message.content)
        if answer_length > 200:
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)  # Cap at 95%
    
    def _extract_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract source information from documents"""
        sources = []
        for doc in documents:
            sources.append({
                'title': doc.get('title', 'Legal Document'),
                'court': doc.get('court', 'Unknown Court'),
                'case_number': doc.get('case_number', 'N/A'),
                'category': doc.get('category', 'General')
            })
        return sources
    
    def _fallback_answer(self, question: str, context_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback answer when AI is not available"""
        if context_documents:
            # Use the best document for a simple answer
            best_doc = context_documents[0]
            answer = f"Based on {best_doc.get('title', 'Legal Document')} ({best_doc.get('court', 'Unknown Court')}):\n\n{best_doc.get('content', 'No content available')}"
            confidence = 0.6
        else:
            answer = f"I couldn't find specific information about '{question}' in the current knowledge base. However, I can help you with questions about Pakistani law, including bail procedures, writ petitions, constitutional rights, criminal appeals, property rights, and family law. Please try rephrasing your question or ask about a specific legal topic."
            confidence = 0.1
        
        return {
            'answer': answer,
            'answer_type': 'fallback',
            'confidence': confidence,
            'model_used': 'fallback',
            'tokens_used': 0,
            'sources': self._extract_sources(context_documents),
            'status': 'success'
        }
    
    def generate_streaming_answer(
        self, 
        question: str, 
        context_documents: List[Dict[str, Any]], 
        conversation_history: Optional[List[Dict]] = None
    ):
        """
        Generate a streaming answer (for real-time responses)
        This is a placeholder for future streaming implementation
        """
        # For now, return the regular answer
        # In the future, this could use OpenAI's streaming API
        return self.generate_answer(question, context_documents, conversation_history)
