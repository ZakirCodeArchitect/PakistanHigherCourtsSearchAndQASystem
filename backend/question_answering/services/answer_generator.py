"""
Answer Generator Service
Generates intelligent answers using AI models and retrieved legal knowledge
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional, Generator
import openai
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Service for generating intelligent answers using AI models"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_initialized = False
        
        # Configuration
        self.model_name = self.config.get('generation_model', 'gpt-3.5-turbo')
        self.max_tokens = self.config.get('max_tokens', 1000)
        self.temperature = self.config.get('temperature', 0.7)
        self.enable_streaming = self.config.get('enable_streaming', True)
        
        # Initialize OpenAI
        self._initialize_openai()
        
        # Legal domain prompts
        self._setup_legal_prompts()
        
        logger.info("Answer Generator initialized successfully")
    
    def _initialize_openai(self):
        """Initialize OpenAI API client"""
        try:
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in settings")
                self.is_initialized = False
                return
            
            openai.api_key = api_key
            self.is_initialized = True
            logger.info("OpenAI API initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing OpenAI: {e}")
            self.is_initialized = False
    
    def _setup_legal_prompts(self):
        """Setup legal domain-specific prompts"""
        self.legal_prompts = {
            'system_prompt': """You are an expert legal AI assistant specializing in Pakistani law and court procedures. 
            You have access to a comprehensive database of legal cases, judgments, and legal documents from Pakistan's higher courts.
            
            Your role is to:
            1. Provide accurate, well-reasoned answers based on legal precedents and case law
            2. Cite relevant cases, statutes, and legal authorities
            3. Explain complex legal concepts in clear, understandable language
            4. Distinguish between different types of legal questions (criminal, civil, constitutional, etc.)
            5. Provide practical guidance while emphasizing the need for professional legal consultation
            
            Guidelines:
            - Always base your answers on the provided legal context and precedents
            - Use proper legal terminology and citations
            - Be precise and avoid speculation
            - If information is insufficient, clearly state limitations
            - Recommend consulting qualified legal professionals for specific cases
            - Maintain objectivity and neutrality in legal analysis""",
            
            'case_inquiry_prompt': """Based on the provided legal context, answer the following question about the case(s):
            
            Question: {question}
            
            Legal Context:
            {context}
            
            Please provide:
            1. A direct answer to the question
            2. Relevant case details and legal principles
            3. Key citations and precedents
            4. Any important legal implications
            
            Format your response clearly with proper legal citations.""",
            
            'law_research_prompt': """Based on the provided legal context, answer the following legal research question:
            
            Question: {question}
            
            Legal Context:
            {context}
            
            Please provide:
            1. A comprehensive answer covering the legal principles
            2. Relevant statutory provisions and case law
            3. Analysis of legal precedents
            4. Practical implications and applications
            
            Ensure your response is well-structured with proper legal citations.""",
            
            'judge_inquiry_prompt': """Based on the provided legal context, answer the following question about the judge(s):
            
            Question: {question}
            
            Legal Context:
            {context}
            
            Please provide:
            1. Information about the judge(s) mentioned
            2. Relevant cases and decisions
            3. Legal principles established
            4. Judicial philosophy or approach (if evident)
            
            Focus on factual information and avoid personal opinions.""",
            
            'general_legal_prompt': """Based on the provided legal context, answer the following general legal question:
            
            Question: {question}
            
            Legal Context:
            {context}
            
            Please provide:
            1. A clear and comprehensive answer
            2. Relevant legal principles and precedents
            3. Practical guidance and implications
            4. Important considerations and limitations
            
            Ensure your response is accurate and helpful for legal understanding."""
        }
    
    def generate_answer(self, 
                       question: str, 
                       knowledge_context: List[Dict[str, Any]], 
                       session_context: Dict[str, Any] = None,
                       query_intent: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate an answer for a question using retrieved knowledge
        
        Args:
            question: User's question
            knowledge_context: Retrieved legal knowledge
            session_context: Session context and history
            query_intent: Query intent and classification
            
        Returns:
            Dictionary containing answer and metadata
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                return self._generate_fallback_answer(question, knowledge_context)
            
            # Determine answer type and select appropriate prompt
            answer_type = self._determine_answer_type(query_intent)
            prompt_template = self._select_prompt_template(answer_type)
            
            # Prepare context
            formatted_context = self._format_knowledge_context(knowledge_context)
            
            # Build the prompt
            prompt = prompt_template.format(
                question=question,
                context=formatted_context
            )
            
            # Generate answer using OpenAI
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.legal_prompts['system_prompt']},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            )
            
            # Extract answer
            answer_text = response.choices[0].message.content.strip()
            
            # Post-process answer
            processed_answer = self._post_process_answer(
                answer_text, knowledge_context, answer_type
            )
            
            generation_time = time.time() - start_time
            
            return {
                'answer': processed_answer['answer'],
                'answer_type': answer_type,
                'confidence': processed_answer['confidence'],
                'sources': processed_answer['sources'],
                'citations': processed_answer['citations'],
                'reasoning': processed_answer['reasoning'],
                'metadata': {
                    'model_used': self.model_name,
                    'generation_time': generation_time,
                    'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else 0,
                    'knowledge_sources': len(knowledge_context)
                },
                'relevance_score': processed_answer['relevance_score'],
                'completeness_score': processed_answer['completeness_score'],
                'accuracy_score': processed_answer['accuracy_score']
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return self._generate_fallback_answer(question, knowledge_context)
    
    def generate_answer_stream(self, 
                              question: str, 
                              knowledge_context: List[Dict[str, Any]], 
                              session_context: Dict[str, Any] = None,
                              query_intent: Dict[str, Any] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Generate streaming answer for real-time response
        
        Yields:
            Dictionary containing streaming response chunks
        """
        try:
            if not self.is_initialized:
                yield {
                    'type': 'error',
                    'error': 'Answer generator not initialized',
                    'answer': self._generate_fallback_answer(question, knowledge_context)['answer']
                }
                return
            
            # Determine answer type and select appropriate prompt
            answer_type = self._determine_answer_type(query_intent)
            prompt_template = self._select_prompt_template(answer_type)
            
            # Prepare context
            formatted_context = self._format_knowledge_context(knowledge_context)
            
            # Build the prompt
            prompt = prompt_template.format(
                question=question,
                context=formatted_context
            )
            
            # Stream answer using OpenAI
            response_stream = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.legal_prompts['system_prompt']},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            # Stream response chunks
            full_answer = ""
            for chunk in response_stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_answer += content
                    
                    yield {
                        'type': 'content',
                        'content': content,
                        'answer_type': answer_type
                    }
            
            # Post-process final answer
            processed_answer = self._post_process_answer(
                full_answer, knowledge_context, answer_type
            )
            
            # Yield final result
            yield {
                'type': 'complete',
                'answer': processed_answer['answer'],
                'answer_type': answer_type,
                'confidence': processed_answer['confidence'],
                'sources': processed_answer['sources'],
                'citations': processed_answer['citations'],
                'reasoning': processed_answer['reasoning'],
                'metadata': {
                    'model_used': self.model_name,
                    'knowledge_sources': len(knowledge_context)
                },
                'relevance_score': processed_answer['relevance_score'],
                'completeness_score': processed_answer['completeness_score'],
                'accuracy_score': processed_answer['accuracy_score']
            }
            
        except Exception as e:
            logger.error(f"Error in streaming answer generation: {e}")
            yield {
                'type': 'error',
                'error': str(e),
                'answer': self._generate_fallback_answer(question, knowledge_context)['answer']
            }
    
    def _determine_answer_type(self, query_intent: Dict[str, Any] = None) -> str:
        """Determine the type of answer to generate"""
        if not query_intent:
            return 'general_legal'
        
        intent_type = query_intent.get('type', 'general_legal')
        
        type_mapping = {
            'case_inquiry': 'case_summary',
            'law_research': 'legal_analysis',
            'judge_inquiry': 'citation_reference',
            'lawyer_inquiry': 'citation_reference',
            'court_procedure': 'procedural_guidance',
            'citation_lookup': 'citation_reference',
            'general_legal': 'explanation'
        }
        
        return type_mapping.get(intent_type, 'explanation')
    
    def _select_prompt_template(self, answer_type: str) -> str:
        """Select appropriate prompt template based on answer type"""
        template_mapping = {
            'case_summary': self.legal_prompts['case_inquiry_prompt'],
            'legal_analysis': self.legal_prompts['law_research_prompt'],
            'citation_reference': self.legal_prompts['judge_inquiry_prompt'],
            'procedural_guidance': self.legal_prompts['general_legal_prompt'],
            'explanation': self.legal_prompts['general_legal_prompt']
        }
        
        return template_mapping.get(answer_type, self.legal_prompts['general_legal_prompt'])
    
    def _format_knowledge_context(self, knowledge_context: List[Dict[str, Any]]) -> str:
        """Format knowledge context for the prompt"""
        if not knowledge_context:
            return "No relevant legal context found."
        
        formatted_context = []
        
        for i, item in enumerate(knowledge_context[:5], 1):  # Limit to top 5 sources
            context_item = f"Source {i}:\n"
            context_item += f"Title: {item.get('title', 'N/A')}\n"
            context_item += f"Court: {item.get('court', 'N/A')}\n"
            context_item += f"Case Number: {item.get('case_number', 'N/A')}\n"
            context_item += f"Legal Domain: {item.get('legal_domain', 'N/A')}\n"
            context_item += f"Content: {item.get('content_preview', item.get('content', 'N/A'))}\n"
            
            if item.get('citations'):
                context_item += f"Citations: {', '.join(item['citations'])}\n"
            
            context_item += f"Relevance Score: {item.get('relevance_score', 0.0):.2f}\n"
            context_item += "---\n"
            
            formatted_context.append(context_item)
        
        return "\n".join(formatted_context)
    
    def _post_process_answer(self, 
                           answer: str, 
                           knowledge_context: List[Dict[str, Any]], 
                           answer_type: str) -> Dict[str, Any]:
        """Post-process the generated answer"""
        try:
            # Extract sources
            sources = []
            for item in knowledge_context:
                if item.get('case_id'):
                    sources.append({
                        'type': 'case',
                        'id': item['case_id'],
                        'title': item.get('title', ''),
                        'court': item.get('court', ''),
                        'case_number': item.get('case_number', ''),
                        'relevance_score': item.get('relevance_score', 0.0)
                    })
                elif item.get('document_id'):
                    sources.append({
                        'type': 'document',
                        'id': item['document_id'],
                        'title': item.get('title', ''),
                        'relevance_score': item.get('relevance_score', 0.0)
                    })
            
            # Extract citations
            citations = []
            for item in knowledge_context:
                if item.get('citations'):
                    citations.extend(item['citations'])
            
            # Calculate confidence based on source quality
            confidence = self._calculate_confidence(answer, knowledge_context)
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(answer, knowledge_context)
            
            # Calculate completeness score
            completeness_score = self._calculate_completeness_score(answer, answer_type)
            
            # Calculate accuracy score (based on source reliability)
            accuracy_score = self._calculate_accuracy_score(knowledge_context)
            
            # Extract reasoning chain
            reasoning = self._extract_reasoning_chain(answer)
            
            return {
                'answer': answer,
                'confidence': confidence,
                'sources': sources,
                'citations': list(set(citations)),
                'reasoning': reasoning,
                'relevance_score': relevance_score,
                'completeness_score': completeness_score,
                'accuracy_score': accuracy_score
            }
            
        except Exception as e:
            logger.error(f"Error post-processing answer: {e}")
            return {
                'answer': answer,
                'confidence': 0.5,
                'sources': [],
                'citations': [],
                'reasoning': [],
                'relevance_score': 0.5,
                'completeness_score': 0.5,
                'accuracy_score': 0.5
            }
    
    def _calculate_confidence(self, answer: str, knowledge_context: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the answer"""
        try:
            base_confidence = 0.5
            
            # Boost for high-quality sources
            if knowledge_context:
                avg_relevance = sum(item.get('relevance_score', 0.0) for item in knowledge_context) / len(knowledge_context)
                base_confidence += avg_relevance * 0.3
            
            # Boost for comprehensive answer
            if len(answer) > 200:
                base_confidence += 0.1
            
            # Boost for citations
            if any(item.get('citations') for item in knowledge_context):
                base_confidence += 0.1
            
            # Boost for multiple sources
            if len(knowledge_context) > 2:
                base_confidence += 0.1
            
            return min(base_confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _calculate_relevance_score(self, answer: str, knowledge_context: List[Dict[str, Any]]) -> float:
        """Calculate relevance score for the answer"""
        try:
            if not knowledge_context:
                return 0.0
            
            # Average relevance of sources
            avg_relevance = sum(item.get('relevance_score', 0.0) for item in knowledge_context) / len(knowledge_context)
            return min(avg_relevance, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating relevance score: {e}")
            return 0.5
    
    def _calculate_completeness_score(self, answer: str, answer_type: str) -> float:
        """Calculate completeness score for the answer"""
        try:
            base_score = 0.5
            
            # Length-based scoring
            if len(answer) > 500:
                base_score += 0.2
            elif len(answer) > 200:
                base_score += 0.1
            
            # Structure-based scoring
            if '1.' in answer and '2.' in answer:  # Numbered points
                base_score += 0.1
            
            if 'based on' in answer.lower() or 'according to' in answer.lower():
                base_score += 0.1
            
            if 'however' in answer.lower() or 'furthermore' in answer.lower():
                base_score += 0.1
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating completeness score: {e}")
            return 0.5
    
    def _calculate_accuracy_score(self, knowledge_context: List[Dict[str, Any]]) -> float:
        """Calculate accuracy score based on source reliability"""
        try:
            if not knowledge_context:
                return 0.0
            
            # Higher accuracy for official court documents
            accuracy_scores = []
            for item in knowledge_context:
                source_type = item.get('source_type', '')
                if source_type in ['judgment', 'order']:
                    accuracy_scores.append(0.9)
                elif source_type in ['case_metadata', 'legal_text']:
                    accuracy_scores.append(0.8)
                else:
                    accuracy_scores.append(0.7)
            
            return sum(accuracy_scores) / len(accuracy_scores)
            
        except Exception as e:
            logger.error(f"Error calculating accuracy score: {e}")
            return 0.5
    
    def _extract_reasoning_chain(self, answer: str) -> List[str]:
        """Extract reasoning chain from the answer"""
        try:
            reasoning = []
            
            # Look for reasoning indicators
            reasoning_indicators = [
                'based on', 'according to', 'in light of', 'considering',
                'the court held', 'the judgment states', 'it was decided',
                'the principle is', 'the law provides', 'the statute states'
            ]
            
            sentences = answer.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if any(indicator in sentence.lower() for indicator in reasoning_indicators):
                    reasoning.append(sentence)
            
            return reasoning[:5]  # Limit to 5 reasoning points
            
        except Exception as e:
            logger.error(f"Error extracting reasoning chain: {e}")
            return []
    
    def _generate_fallback_answer(self, question: str, knowledge_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a fallback answer when AI generation fails"""
        try:
            if knowledge_context:
                # Use the most relevant source
                best_source = max(knowledge_context, key=lambda x: x.get('relevance_score', 0.0))
                
                answer = f"Based on the available legal information:\n\n"
                answer += f"**{best_source.get('title', 'Legal Document')}**\n\n"
                answer += f"Court: {best_source.get('court', 'N/A')}\n"
                answer += f"Case Number: {best_source.get('case_number', 'N/A')}\n\n"
                answer += f"Relevant Content: {best_source.get('content_preview', 'Content not available')}\n\n"
                answer += "Please note: This is a basic response based on available legal documents. "
                answer += "For comprehensive legal advice, please consult with a qualified legal professional."
                
                sources = [{
                    'type': 'document',
                    'id': best_source.get('document_id', ''),
                    'title': best_source.get('title', ''),
                    'relevance_score': best_source.get('relevance_score', 0.0)
                }]
            else:
                answer = "I apologize, but I couldn't find relevant legal information to answer your question. "
                answer += "Please try rephrasing your question or consult with a qualified legal professional for assistance."
                sources = []
            
            return {
                'answer': answer,
                'answer_type': 'explanation',
                'confidence': 0.3,
                'sources': sources,
                'citations': [],
                'reasoning': [],
                'relevance_score': 0.3,
                'completeness_score': 0.4,
                'accuracy_score': 0.3
            }
            
        except Exception as e:
            logger.error(f"Error generating fallback answer: {e}")
            return {
                'answer': "I apologize, but I'm unable to process your question at the moment. Please try again later or consult with a legal professional.",
                'answer_type': 'explanation',
                'confidence': 0.1,
                'sources': [],
                'citations': [],
                'reasoning': [],
                'relevance_score': 0.1,
                'completeness_score': 0.1,
                'accuracy_score': 0.1
            }
    
    def is_healthy(self) -> bool:
        """Check if the answer generator is healthy"""
        return self.is_initialized
