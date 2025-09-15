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
from .local_ai_generator import LocalAIGenerator

logger = logging.getLogger(__name__)

class AIAnswerGenerator:
    """Generate intelligent answers using OpenAI GPT"""
    
    def __init__(self):
        """Initialize the AI service"""
        # Load .env file
        try:
            from dotenv import load_dotenv
            load_dotenv('.env')
        except Exception:
            pass
            
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = getattr(settings, 'QA_SETTINGS', {}).get('GENERATION_MODEL', 'gpt-4')
        self.max_tokens = getattr(settings, 'QA_SETTINGS', {}).get('MAX_TOKENS', 1500)
        self.temperature = getattr(settings, 'QA_SETTINGS', {}).get('TEMPERATURE', 0.3)
        
        logger.info(f"AI Answer Generator initialized with model: {self.model}")
        logger.info(f"API Key present: {bool(self.api_key)}")
        
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
        
        # Initialize local AI generator as backup
        self.local_ai = LocalAIGenerator()
    
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
        logger.info(f"Generating answer with model: {self.model}, enabled: {self.enabled}, client: {bool(self.client)}")
        
        if not self.enabled:
            logger.warning("AI service not enabled - using fallback")
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
            # Try local AI generator as backup
            try:
                logger.info("Attempting to use local AI generator as backup")
                return self.local_ai.generate_answer(question, context_documents)
            except Exception as local_error:
                logger.error(f"Local AI generator also failed: {str(local_error)}")
                return self._fallback_answer(question, context_documents)
    
    def _get_system_prompt(self) -> str:
        """Get the enhanced system prompt for the AI"""
        return """You are an expert legal research assistant specializing in Pakistani law with deep knowledge of constitutional law, criminal law, civil law, and court procedures. Your role is to provide comprehensive, accurate, and well-structured answers to legal questions based on the provided context documents.

EXPERTISE AREAS:
- Constitutional Law (Article 199, writ petitions, fundamental rights)
- Criminal Law (bail procedures, appeals, FIR procedures)
- Civil Law (property disputes, contract law, family law)
- Court Procedures (filing procedures, hearing processes, documentation)
- Legal Research (case law analysis, statutory interpretation)

RESPONSE GUIDELINES:
1. **Accuracy First**: Always base your answers strictly on the provided legal documents and context
2. **Comprehensive Analysis**: Provide detailed explanations with legal reasoning and precedents
3. **Proper Citations**: Include specific case numbers, court names, dates, and legal provisions
4. **Professional Language**: Use clear, precise legal terminology appropriate for legal professionals
5. **Structured Format**: Organize answers with clear headings, bullet points, and logical flow
6. **Context Awareness**: Reference previous conversation context when relevant
7. **Limitation Disclosure**: Clearly state when information is insufficient or uncertain
8. **Legal Authority**: Always mention the relevant court, judge, or legal authority
9. **Practical Guidance**: Include procedural steps and practical considerations when applicable
10. **Disclaimer**: Always clarify that this is legal information, not legal advice

RESPONSE FORMAT:
- Start with a direct answer to the question
- Provide detailed legal analysis with citations
- Include relevant case law and precedents
- Explain procedural aspects if applicable
- Conclude with practical implications or next steps

Remember: You are providing legal information and research assistance, not legal advice. Always encourage users to consult qualified legal professionals for specific legal matters."""
    
    def _create_prompt(self, question: str, context_text: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """Create the enhanced prompt for the AI with conversation context"""
        
        # Add conversation context if available
        conversation_context = ""
        if conversation_history:
            conversation_context = "\n\nPrevious Conversation Context:\n"
            for i, turn in enumerate(conversation_history[-3:], 1):  # Last 3 turns
                conversation_context += f"{i}. Q: {turn.get('query', '')}\n"
                response_preview = turn.get('response', '')
                if len(response_preview) > 150:
                    response_preview = response_preview[:150] + "..."
                conversation_context += f"   A: {response_preview}\n\n"
        
        prompt = f"""Question: {question}{conversation_context}

Context Documents:
{context_text}

Please provide a comprehensive answer to the question based on the context documents above. Make sure to:
1. **Direct Answer**: Start with a clear, direct answer to the specific question
2. **Legal Analysis**: Provide detailed legal reasoning and analysis
3. **Proper Citations**: Include specific case numbers, court names, dates, and legal provisions
4. **Precedent References**: Cite relevant case law and legal precedents
5. **Procedural Guidance**: Include any relevant procedural steps or requirements
6. **Context Integration**: Reference previous conversation context when relevant
7. **Professional Structure**: Organize your answer with clear headings and logical flow
8. **Practical Implications**: Explain what this means for the user's situation
9. **Limitations**: Clearly state any limitations or uncertainties in the information
10. **Next Steps**: Suggest appropriate next steps or additional resources

Format your response professionally with clear sections and proper legal citations.

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
        """Enhanced fallback answer when AI is not available"""
        if context_documents:
            # Generate intelligent answer from context documents
            answer = self._generate_intelligent_fallback(question, context_documents)
            confidence = 0.75
        else:
            answer = f"I couldn't find specific information about '{question}' in the current knowledge base. However, I can help you with questions about Pakistani law, including bail procedures, writ petitions, constitutional rights, criminal appeals, property rights, and family law. Please try rephrasing your question or ask about a specific legal topic."
            confidence = 0.1
        
        return {
            'answer': answer,
            'answer_type': 'intelligent_fallback',
            'confidence': confidence,
            'model_used': 'intelligent_fallback',
            'tokens_used': 0,
            'sources': self._extract_sources(context_documents),
            'status': 'success'
        }
    
    def _generate_intelligent_fallback(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate intelligent answer from context documents"""
        question_lower = question.lower()
        
        # Analyze question type
        if 'what is' in question_lower:
            return self._generate_definition_answer(question, documents)
        elif 'how to' in question_lower or 'how do' in question_lower:
            return self._generate_procedural_answer(question, documents)
        elif 'requirements' in question_lower:
            return self._generate_requirements_answer(question, documents)
        elif 'when' in question_lower:
            return self._generate_temporal_answer(question, documents)
        elif 'where' in question_lower:
            return self._generate_location_answer(question, documents)
        else:
            return self._generate_general_answer(question, documents)
    
    def _generate_definition_answer(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate definition-style answer"""
        answer_parts = []
        
        # Direct answer
        if 'writ petition' in question.lower():
            answer_parts.append("## What is a Writ Petition?\n")
            answer_parts.append("A **writ petition** is a constitutional remedy available under Article 199 of the Constitution of Pakistan. It is a legal instrument used to challenge the actions or decisions of public authorities, government bodies, or officials when they exceed their jurisdiction or violate fundamental rights.\n")
        
        # Add context from documents
        if documents:
            answer_parts.append("## Relevant Legal Cases:\n")
            for i, doc in enumerate(documents[:3], 1):
                answer_parts.append(f"**{i}. {doc.get('title', 'Legal Case')}**")
                answer_parts.append(f"- **Court**: {doc.get('court', 'Unknown Court')}")
                answer_parts.append(f"- **Case Number**: {doc.get('case_number', 'N/A')}")
                if doc.get('content'):
                    # Extract relevant parts of content
                    content = doc.get('content', '')
                    if len(content) > 200:
                        content = content[:200] + "..."
                    answer_parts.append(f"- **Details**: {content}")
                answer_parts.append("")
        
        # Add legal principles
        answer_parts.append("## Key Legal Principles:")
        answer_parts.append("- Writ petitions are filed under Article 199 of the Constitution")
        answer_parts.append("- They can challenge actions of public authorities")
        answer_parts.append("- They protect fundamental rights")
        answer_parts.append("- They provide speedy remedy against administrative actions")
        
        return "\n".join(answer_parts)
    
    def _generate_procedural_answer(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate procedural guidance answer"""
        answer_parts = []
        
        if 'file' in question.lower() and 'writ' in question.lower():
            answer_parts.append("## How to File a Writ Petition\n")
            answer_parts.append("### Step-by-Step Process:\n")
            answer_parts.append("1. **Identify the Ground**: Determine if the case involves violation of fundamental rights or excess of jurisdiction")
            answer_parts.append("2. **Prepare Petition**: Draft the petition with proper legal grounds")
            answer_parts.append("3. **File in High Court**: Submit to the relevant High Court having jurisdiction")
            answer_parts.append("4. **Pay Court Fees**: Deposit required court fees")
            answer_parts.append("5. **Serve Notice**: Serve notice to concerned authorities")
            answer_parts.append("6. **Hearing**: Attend court hearings as scheduled")
        
        # Add relevant cases
        if documents:
            answer_parts.append("\n## Relevant Cases:\n")
            for doc in documents[:2]:
                answer_parts.append(f"- **{doc.get('title', 'Case')}** ({doc.get('court', 'Court')})")
                if doc.get('case_number'):
                    answer_parts.append(f"  Case No: {doc.get('case_number')}")
        
        return "\n".join(answer_parts)
    
    def _generate_requirements_answer(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate requirements-based answer"""
        answer_parts = []
        
        answer_parts.append("## Requirements for Filing\n")
        answer_parts.append("### Essential Requirements:\n")
        answer_parts.append("1. **Legal Standing**: Petitioner must have locus standi")
        answer_parts.append("2. **Proper Grounds**: Must establish violation of fundamental rights")
        answer_parts.append("3. **Jurisdiction**: File in appropriate High Court")
        answer_parts.append("4. **Documentation**: Required documents and affidavits")
        answer_parts.append("5. **Court Fees**: Payment of prescribed fees")
        
        # Add case examples
        if documents:
            answer_parts.append("\n## Case Examples:\n")
            for doc in documents[:2]:
                answer_parts.append(f"- **{doc.get('title', 'Case')}**")
                answer_parts.append(f"  Court: {doc.get('court', 'Unknown')}")
                if doc.get('status'):
                    answer_parts.append(f"  Status: {doc.get('status')}")
        
        return "\n".join(answer_parts)
    
    def _generate_temporal_answer(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate time-related answer"""
        answer_parts = []
        
        answer_parts.append("## Timeline Information\n")
        answer_parts.append("### Important Timeframes:\n")
        answer_parts.append("- **Filing**: Within reasonable time of cause of action")
        answer_parts.append("- **Limitation**: Generally 3 years for civil matters")
        answer_parts.append("- **Hearing**: As per court schedule")
        answer_parts.append("- **Decision**: Varies by case complexity")
        
        return "\n".join(answer_parts)
    
    def _generate_location_answer(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate location-based answer"""
        answer_parts = []
        
        answer_parts.append("## Jurisdiction and Location\n")
        answer_parts.append("### Where to File:\n")
        answer_parts.append("- **High Courts**: Islamabad, Lahore, Karachi, Peshawar, Quetta")
        answer_parts.append("- **Territorial Jurisdiction**: Based on cause of action")
        answer_parts.append("- **Subject Matter**: Constitutional matters")
        
        return "\n".join(answer_parts)
    
    def _generate_general_answer(self, question: str, documents: List[Dict[str, Any]]) -> str:
        """Generate general answer"""
        answer_parts = []
        
        answer_parts.append("## Legal Information\n")
        answer_parts.append("Based on the available legal documents, here's the relevant information:\n")
        
        if documents:
            for i, doc in enumerate(documents[:3], 1):
                answer_parts.append(f"**{i}. {doc.get('title', 'Legal Case')}**")
                answer_parts.append(f"- **Court**: {doc.get('court', 'Unknown Court')}")
                answer_parts.append(f"- **Case Number**: {doc.get('case_number', 'N/A')}")
                if doc.get('content'):
                    content = doc.get('content', '')
                    if len(content) > 150:
                        content = content[:150] + "..."
                    answer_parts.append(f"- **Details**: {content}")
                answer_parts.append("")
        
        return "\n".join(answer_parts)
    
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
