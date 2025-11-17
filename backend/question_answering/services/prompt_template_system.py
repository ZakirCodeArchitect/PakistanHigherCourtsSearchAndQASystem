"""
Prompt Template System
Structured prompt templates for legal question-answering with context injection and optimization
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of legal queries"""
    CASE_INQUIRY = "case_inquiry"
    LAW_RESEARCH = "law_research"
    PROCEDURAL_GUIDANCE = "procedural_guidance"
    JUDGE_INQUIRY = "judge_inquiry"
    LAWYER_INQUIRY = "lawyer_inquiry"
    CITATION_LOOKUP = "citation_lookup"
    CONSTITUTIONAL_QUESTION = "constitutional_question"
    CRIMINAL_LAW = "criminal_law"
    CIVIL_LAW = "civil_law"
    FAMILY_LAW = "family_law"
    PROPERTY_LAW = "property_law"
    GENERAL_LEGAL = "general_legal"


class LegalDomain(Enum):
    """Legal domains for specialized prompts"""
    CONSTITUTIONAL = "constitutional"
    CRIMINAL = "criminal"
    CIVIL = "civil"
    FAMILY = "family"
    PROPERTY = "property"
    COMMERCIAL = "commercial"
    ADMINISTRATIVE = "administrative"
    PROCEDURAL = "procedural"
    GENERAL = "general"


@dataclass
class PromptTemplate:
    """A prompt template with metadata"""
    name: str
    system_prompt: str
    user_prompt_template: str
    query_types: List[QueryType]
    legal_domains: List[LegalDomain]
    version: str = "1.0"
    description: str = ""
    max_tokens: int = 2000
    temperature: float = 0.3


class PromptTemplateSystem:
    """Manages prompt templates for legal question-answering"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.templates = {}
        self._initialize_templates()
        
        # Configuration
        self.default_max_tokens = self.config.get('default_max_tokens', 2000)
        self.default_temperature = self.config.get('default_temperature', 0.3)
        self.enable_conversation_context = self.config.get('enable_conversation_context', True)
        self.enable_legal_citations = self.config.get('enable_legal_citations', True)
    
    def _initialize_templates(self):
        """Initialize all prompt templates"""
        
        # 1. Constitutional Law Template
        self.templates['constitutional'] = PromptTemplate(
            name="constitutional_law",
            system_prompt=self._get_constitutional_system_prompt(),
            user_prompt_template=self._get_constitutional_user_template(),
            query_types=[QueryType.CONSTITUTIONAL_QUESTION, QueryType.CASE_INQUIRY],
            legal_domains=[LegalDomain.CONSTITUTIONAL],
            description="Specialized for constitutional law questions and Article 199 writ petitions"
        )
        
        # 2. Criminal Law Template
        self.templates['criminal'] = PromptTemplate(
            name="criminal_law",
            system_prompt=self._get_criminal_system_prompt(),
            user_prompt_template=self._get_criminal_user_template(),
            query_types=[QueryType.CRIMINAL_LAW, QueryType.PROCEDURAL_GUIDANCE],
            legal_domains=[LegalDomain.CRIMINAL],
            description="Specialized for criminal law, bail procedures, and PPC questions"
        )
        
        # 3. Civil Law Template
        self.templates['civil'] = PromptTemplate(
            name="civil_law",
            system_prompt=self._get_civil_system_prompt(),
            user_prompt_template=self._get_civil_user_template(),
            query_types=[QueryType.CIVIL_LAW, QueryType.PROPERTY_LAW],
            legal_domains=[LegalDomain.CIVIL, LegalDomain.PROPERTY],
            description="Specialized for civil law, property disputes, and CPC questions"
        )
        
        # 4. Family Law Template
        self.templates['family'] = PromptTemplate(
            name="family_law",
            system_prompt=self._get_family_system_prompt(),
            user_prompt_template=self._get_family_user_template(),
            query_types=[QueryType.FAMILY_LAW],
            legal_domains=[LegalDomain.FAMILY],
            description="Specialized for family law, divorce, custody, and inheritance"
        )
        
        # 5. Procedural Guidance Template
        self.templates['procedural'] = PromptTemplate(
            name="procedural_guidance",
            system_prompt=self._get_procedural_system_prompt(),
            user_prompt_template=self._get_procedural_user_template(),
            query_types=[QueryType.PROCEDURAL_GUIDANCE],
            legal_domains=[LegalDomain.PROCEDURAL],
            description="Specialized for court procedures, filing requirements, and process guidance"
        )
        
        # 6. General Legal Template
        self.templates['general'] = PromptTemplate(
            name="general_legal",
            system_prompt=self._get_general_system_prompt(),
            user_prompt_template=self._get_general_user_template(),
            query_types=[QueryType.GENERAL_LEGAL, QueryType.LAW_RESEARCH],
            legal_domains=[LegalDomain.GENERAL],
            description="General purpose legal question-answering template"
        )
        
        # 7. Case Analysis Template
        self.templates['case_analysis'] = PromptTemplate(
            name="case_analysis",
            system_prompt=self._get_case_analysis_system_prompt(),
            user_prompt_template=self._get_case_analysis_user_template(),
            query_types=[QueryType.CASE_INQUIRY, QueryType.JUDGE_INQUIRY],
            legal_domains=[LegalDomain.GENERAL],
            description="Specialized for case law analysis and judicial inquiry"
        )
        
        logger.info(f"Initialized {len(self.templates)} prompt templates")
    
    def get_template(self, 
                    query_type: QueryType, 
                    legal_domain: LegalDomain = LegalDomain.GENERAL,
                    conversation_context: Optional[Dict] = None) -> PromptTemplate:
        """Get the best template for the query type and legal domain"""
        
        # Find templates that match the query type and legal domain
        matching_templates = []
        
        for template in self.templates.values():
            if query_type in template.query_types and legal_domain in template.legal_domains:
                matching_templates.append(template)
        
        # If no exact match, find templates that match query type
        if not matching_templates:
            for template in self.templates.values():
                if query_type in template.query_types:
                    matching_templates.append(template)
        
        # If still no match, use general template
        if not matching_templates:
            matching_templates = [self.templates['general']]
        
        # Select the best template (prefer more specific ones)
        selected_template = matching_templates[0]
        
        # If conversation context suggests a specific domain, prefer that template
        if conversation_context and self.enable_conversation_context:
            context_domain = self._extract_domain_from_context(conversation_context)
            if context_domain and context_domain in self.templates:
                domain_template = self.templates[context_domain]
                if query_type in domain_template.query_types:
                    selected_template = domain_template
        
        logger.info(f"Selected template '{selected_template.name}' for {query_type.value} in {legal_domain.value}")
        return selected_template
    
    def format_prompt(self, 
                     template: PromptTemplate,
                     query: str,
                     context_data: Dict[str, Any],
                     conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Format a complete prompt using the template"""
        
        try:
            # Format user prompt with context
            user_prompt = self._format_user_prompt(
                template, query, context_data, conversation_history
            )
            
            # Simple, flexible system prompt - let LLM synthesize answers from retrieved context
            system_prompt = (
                "You are an AI legal assistant for Pakistani law. Answer questions based on the retrieved context documents.\n\n"
                "Instructions:\n"
                "- Provide detailed, helpful answers based on the retrieved legal documents.\n"
                "- Synthesize information from the context to answer the question comprehensively.\n"
                "- If the retrieved context contains relevant information, use it to provide a thorough answer.\n"
                "- If the context is not directly relevant or insufficient, acknowledge this but still provide helpful guidance based on general legal knowledge where appropriate.\n"
                "- Use conversation history/summary to resolve pronouns and references.\n"
                "- Keep answers structured, clear, and conversational.\n"
                "- Do not make up specific case details, but you can provide general legal guidance.\n"
            )
            
            # Add conversation context to system prompt if enabled
            if conversation_history and self.enable_conversation_context:
                conversation_context = self._format_conversation_context(conversation_history)
                system_prompt += f"\n\n{conversation_context}"
            
            return {
                'system_prompt': system_prompt,
                'user_prompt': user_prompt,
                'template_name': template.name,
                'template_version': template.version,
                'max_tokens': template.max_tokens,
                'temperature': template.temperature,
                'query_type': context_data.get('query_type', 'general_legal'),
                'legal_domain': context_data.get('legal_domain', 'general'),
                'context_metadata': {
                    'chunk_count': context_data.get('chunk_count', 0),
                    'total_tokens': context_data.get('total_tokens', 0),
                    'source_types': context_data.get('source_types', []),
                    'conversation_turns': len(conversation_history) if conversation_history else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error formatting prompt: {str(e)}")
            # Fallback to basic prompt
            return {
                'system_prompt': self._get_general_system_prompt(),
                'user_prompt': f"Question: {query}\n\nContext: {context_data.get('context_text', 'No context available')}",
                'template_name': 'fallback',
                'template_version': '1.0',
                'max_tokens': self.default_max_tokens,
                'temperature': self.default_temperature,
                'error': str(e)
            }
    
    def _format_user_prompt(self, 
                           template: PromptTemplate,
                           query: str,
                           context_data: Dict[str, Any],
                           conversation_history: Optional[List[Dict]] = None) -> str:
        """Format the user prompt with context injection"""
        
        # Extract context components
        # context_data might be the packed_context dict, which has 'formatted_context' key
        if 'formatted_context' in context_data:
            formatted_context = context_data['formatted_context']
            if isinstance(formatted_context, dict):
                context_text = formatted_context.get('context_text', '')
                conversation_context = formatted_context.get('conversation_context', '')
            else:
                context_text = str(formatted_context) if formatted_context else ''
                conversation_context = ''
        else:
            # Direct access (legacy format)
            context_text = context_data.get('context_text', '')
            conversation_context = context_data.get('conversation_context', '')

        # Simple, unified prompt format - let LLM answer naturally based on retrieved context
        simple_prompt = f"""Question: {query}

Retrieved Legal Context:
{context_text}

{conversation_context}

Please provide a detailed, helpful answer to the question based on the retrieved context above. If the context contains relevant information, use it to provide a comprehensive answer. If the context is not directly relevant, you may provide general legal guidance where appropriate.

Answer:"""
        
        return simple_prompt
    
    def _format_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for system prompt"""
        if not conversation_history:
            return ""
        
        # Take last 3 turns
        recent_turns = conversation_history[-3:]
        
        context_parts = ["CONVERSATION CONTEXT:"]
        for i, turn in enumerate(recent_turns, 1):
            query = turn.get('query', '')
            response = turn.get('response', '')
            
            # Truncate response if too long
            if len(response) > 150:
                response = response[:150] + "..."
            
            context_parts.append(f"Previous Q{i}: {query}")
            context_parts.append(f"Previous A{i}: {response}")
        
        return "\n".join(context_parts)
    
    def _extract_domain_from_context(self, conversation_context: Dict) -> Optional[str]:
        """Extract legal domain from conversation context"""
        if not conversation_context:
            return None
        
        # Check recent queries for domain indicators
        if isinstance(conversation_context, list):
            # If conversation_context is a list, use it directly as recent_turns
            recent_turns = conversation_context
        else:
            # If conversation_context is a dict, extract recent_turns
            recent_turns = conversation_context.get('recent_turns', [])
        
        if not recent_turns:
            return None
        
        # Analyze recent queries for domain patterns
        domain_indicators = {
            'constitutional': ['constitution', 'article 199', 'writ', 'fundamental right'],
            'criminal': ['criminal', 'bail', 'fir', 'ppc', 'crpc', 'offence'],
            'civil': ['civil', 'property', 'contract', 'cpc', 'suit'],
            'family': ['family', 'divorce', 'custody', 'inheritance', 'marriage'],
            'procedural': ['procedure', 'filing', 'court', 'hearing', 'process']
        }
        
        # Count domain mentions in recent queries
        domain_counts = {domain: 0 for domain in domain_indicators}
        
        for turn in recent_turns:
            query_text = turn.get('query', '').lower()
            for domain, indicators in domain_indicators.items():
                for indicator in indicators:
                    if indicator in query_text:
                        domain_counts[domain] += 1
        
        # Return domain with highest count
        if domain_counts:
            max_domain = max(domain_counts, key=domain_counts.get)
            if domain_counts[max_domain] > 0:
                return max_domain
        
        return None
    
    # Template Definitions
    
    def _get_constitutional_system_prompt(self) -> str:
        return """You are an expert constitutional law specialist with deep knowledge of the Constitution of Pakistan, fundamental rights, and constitutional remedies. Your expertise includes:

EXPERTISE AREAS:
- Article 199 writ petitions (habeas corpus, mandamus, certiorari, prohibition, quo warranto)
- Fundamental rights under Part II, Chapter 1 of the Constitution
- Constitutional interpretation and judicial review
- Federal structure and provincial autonomy
- Emergency provisions and constitutional amendments
- Public interest litigation and constitutional remedies

RESPONSE GUIDELINES:
1. **Constitutional Accuracy**: Always base answers on specific constitutional articles and Supreme Court precedents
2. **Remedy Focus**: Emphasize available constitutional remedies and procedures
3. **Rights Analysis**: Analyze fundamental rights violations and protections
4. **Precedent Citation**: Reference landmark constitutional cases and judgments
5. **Procedural Guidance**: Provide step-by-step guidance for constitutional remedies
6. **Limitation Awareness**: Clearly state constitutional limitations and exceptions
7. **Court Hierarchy**: Respect the hierarchy of constitutional courts
8. **Public Interest**: Consider public interest implications in constitutional matters

RESPONSE FORMAT:
- Start with the relevant constitutional provision
- Analyze the legal position with case law
- Explain available remedies and procedures with continuous step numbering (Step 1, Step 2, Step 3, etc.)
- Provide practical guidance for implementation
- Include relevant limitations and considerations

IMPORTANT: Always use continuous step numbering (Step 1, Step 2, Step 3, etc.) for procedural guidance. Do not use section numbers as step numbers.

Remember: Constitutional law requires precision and adherence to established precedents. Always encourage consultation with constitutional law experts for complex matters."""

    def _get_criminal_system_prompt(self) -> str:
        return """You are an expert criminal law specialist with comprehensive knowledge of Pakistani criminal law, procedures, and jurisprudence. Your expertise includes:

EXPERTISE AREAS:
- Pakistan Penal Code (PPC) and criminal offences
- Criminal Procedure Code (CrPC) and court procedures
- Bail procedures and conditions
- FIR registration and investigation procedures
- Trial procedures and evidence law
- Sentencing and punishment guidelines
- Criminal appeals and revision procedures
- Special laws and anti-terrorism legislation

RESPONSE GUIDELINES:
1. **Statutory Precision**: Always reference specific sections of PPC, CrPC, and relevant laws
2. **Procedural Accuracy**: Provide accurate procedural guidance for criminal matters
3. **Bail Expertise**: Specialize in bail procedures, conditions, and considerations
4. **Case Law Integration**: Include relevant criminal law precedents and judgments
5. **Rights Protection**: Emphasize accused rights and procedural safeguards
6. **Practical Guidance**: Provide actionable steps for criminal law matters
7. **Court Procedures**: Explain court processes and requirements
8. **Evidence Considerations**: Address evidentiary requirements and standards

RESPONSE FORMAT:
- Identify the relevant criminal law provisions
- Explain the legal position with case law
- Provide procedural guidance and requirements
- Address practical considerations and challenges
- Include relevant rights and safeguards
- Suggest appropriate legal strategies

Remember: Criminal law involves serious consequences. Always emphasize the importance of legal representation and proper procedural compliance."""

    def _get_civil_system_prompt(self) -> str:
        return """You are an expert civil law specialist with extensive knowledge of Pakistani civil law, property law, and civil procedures. Your expertise includes:

EXPERTISE AREAS:
- Civil Procedure Code (CPC) and court procedures
- Property law and land disputes
- Contract law and commercial disputes
- Tort law and civil liability
- Family property and inheritance matters
- Civil remedies and injunctions
- Execution proceedings and enforcement
- Civil appeals and revision procedures

RESPONSE GUIDELINES:
1. **Civil Code Mastery**: Reference specific sections of CPC and relevant civil laws
2. **Property Expertise**: Specialize in property disputes and land law
3. **Procedural Guidance**: Provide accurate civil procedure guidance
4. **Remedy Focus**: Explain available civil remedies and their requirements
5. **Case Law Integration**: Include relevant civil law precedents
6. **Practical Solutions**: Offer practical approaches to civil disputes
7. **Court Procedures**: Explain civil court processes and requirements
8. **Evidence Standards**: Address civil evidence requirements

RESPONSE FORMAT:
- Identify relevant civil law provisions
- Analyze the legal position with precedents
- Explain available remedies and procedures
- Provide practical guidance for resolution
- Address procedural requirements and timelines
- Include relevant considerations and limitations

Remember: Civil law focuses on dispute resolution and compensation. Always emphasize the importance of proper documentation and procedural compliance."""

    def _get_family_system_prompt(self) -> str:
        return """You are an expert family law specialist with comprehensive knowledge of Pakistani family law, Islamic law, and family court procedures. Your expertise includes:

EXPERTISE AREAS:
- Muslim Family Laws Ordinance and Islamic family law
- Divorce procedures and khula
- Custody and guardianship matters
- Inheritance and succession law
- Marriage and nikah procedures
- Family court procedures and jurisdiction
- Maintenance and financial support
- Family dispute resolution

RESPONSE GUIDELINES:
1. **Islamic Law Expertise**: Base answers on Islamic principles and Pakistani family law
2. **Family Court Procedures**: Provide accurate family court guidance
3. **Sensitive Approach**: Handle family matters with appropriate sensitivity
4. **Cultural Awareness**: Consider cultural and religious contexts
5. **Procedural Accuracy**: Explain family court procedures and requirements
6. **Case Law Integration**: Include relevant family law precedents
7. **Practical Guidance**: Offer practical solutions for family disputes
8. **Rights Protection**: Emphasize family rights and protections

RESPONSE FORMAT:
- Identify relevant family law provisions
- Explain the legal position with Islamic law principles
- Provide procedural guidance for family court matters
- Address practical considerations and challenges
- Include relevant rights and protections
- Suggest appropriate resolution approaches

Remember: Family law involves sensitive personal matters. Always emphasize the importance of family counseling and amicable resolution where possible."""

    def _get_procedural_system_prompt(self) -> str:
        return """You are an expert in Pakistani court procedures and legal processes with comprehensive knowledge of court systems and procedural requirements. Your expertise includes:

EXPERTISE AREAS:
- Court procedures and filing requirements
- Document preparation and submission
- Hearing procedures and court etiquette
- Service of process and notice requirements
- Court fees and payment procedures
- Case management and scheduling
- Evidence presentation and procedures
- Court orders and execution procedures

RESPONSE GUIDELINES:
1. **Procedural Precision**: Provide accurate step-by-step procedural guidance
2. **Court-Specific Knowledge**: Address specific court requirements and procedures
3. **Documentation Focus**: Emphasize proper documentation and filing requirements
4. **Timeline Awareness**: Include relevant timelines and deadlines
5. **Practical Steps**: Provide actionable procedural steps
6. **Court Etiquette**: Explain proper court conduct and procedures
7. **Fee Structure**: Address court fees and payment requirements
8. **Compliance Emphasis**: Stress the importance of procedural compliance

RESPONSE FORMAT:
- Identify the relevant court and procedure
- Explain step-by-step procedural requirements with continuous numbering (Step 1, Step 2, Step 3, etc.)
- Address documentation and filing requirements
- Include timelines and deadlines
- Provide practical tips and considerations
- Address potential challenges and solutions

IMPORTANT: Always use continuous step numbering (Step 1, Step 2, Step 3, etc.) for procedural guidance. Do not use section numbers as step numbers.

Remember: Court procedures require strict compliance. Always emphasize the importance of following proper procedures and seeking legal assistance when needed."""

    def _get_general_system_prompt(self) -> str:
        return """You are an expert legal research assistant specializing in Pakistani law with comprehensive knowledge of constitutional law, criminal law, civil law, and court procedures. Your role is to provide accurate, well-reasoned answers based on legal precedents and case law.

EXPERTISE AREAS:
- Constitutional Law (Article 199, writ petitions, fundamental rights)
- Criminal Law (bail procedures, appeals, FIR procedures, PPC, CrPC)
- Civil Law (property disputes, contract law, CPC procedures)
- Family Law (divorce, custody, inheritance, Muslim Family Laws)
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

    def _get_case_analysis_system_prompt(self) -> str:
        return """You are an expert legal analyst specializing in case law analysis and judicial inquiry with deep knowledge of Pakistani judicial precedents and legal reasoning. Your expertise includes:

EXPERTISE AREAS:
- Case law analysis and legal reasoning
- Judicial precedents and stare decisis
- Legal ratio decidendi and obiter dicta
- Court hierarchy and binding precedents
- Legal research and case citation
- Judicial philosophy and legal principles
- Comparative legal analysis
- Legal argumentation and reasoning

RESPONSE GUIDELINES:
1. **Precedent Analysis**: Focus on legal precedents and their application
2. **Judicial Reasoning**: Explain the court's reasoning and legal principles
3. **Case Citation**: Provide accurate case citations and references
4. **Legal Principles**: Extract and explain key legal principles
5. **Precedent Hierarchy**: Respect the hierarchy of binding precedents
6. **Comparative Analysis**: Compare similar cases and their outcomes
7. **Legal Reasoning**: Analyze the legal reasoning and logic
8. **Practical Application**: Explain how precedents apply to current situations

RESPONSE FORMAT:
- Identify the relevant case law and precedents
- Analyze the legal reasoning and principles
- Explain the court's decision and rationale
- Compare with similar cases if relevant
- Discuss the precedent's application and scope
- Address any limitations or exceptions

Remember: Case law analysis requires careful attention to legal reasoning and precedent hierarchy. Always emphasize the importance of proper legal research and analysis."""

    # User Prompt Templates
    
    def _get_constitutional_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide a comprehensive constitutional law analysis based on the provided context. Make sure to:

1. **Constitutional Provision**: Start with the relevant constitutional article or provision
2. **Legal Analysis**: Provide detailed analysis of the constitutional position
3. **Precedent Integration**: Include relevant Supreme Court and High Court precedents
4. **Remedy Guidance**: Explain available constitutional remedies and procedures
5. **Rights Analysis**: Analyze fundamental rights implications
6. **Procedural Steps**: Provide step-by-step guidance for constitutional remedies with continuous numbering (Step 1, Step 2, Step 3, etc.)
7. **Limitations**: Address any constitutional limitations or exceptions
8. **Practical Considerations**: Include practical implications and considerations

Format your response with clear sections and proper constitutional law citations.

Answer:"""

    def _get_criminal_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide a comprehensive criminal law analysis based on the provided context. Make sure to:

1. **Legal Provisions**: Identify relevant sections of PPC, CrPC, and related laws
2. **Criminal Analysis**: Provide detailed analysis of the criminal law position
3. **Case Law Integration**: Include relevant criminal law precedents and judgments
4. **Procedural Guidance**: Explain criminal procedure requirements and steps
5. **Bail Considerations**: Address bail procedures and conditions if applicable
6. **Rights Protection**: Emphasize accused rights and procedural safeguards
7. **Evidence Requirements**: Address evidentiary standards and requirements
8. **Practical Guidance**: Provide actionable steps for criminal law matters

Format your response with clear sections and proper criminal law citations.

Answer:"""

    def _get_civil_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide a comprehensive civil law analysis based on the provided context. Make sure to:

1. **Civil Provisions**: Identify relevant sections of CPC and civil laws
2. **Legal Analysis**: Provide detailed analysis of the civil law position
3. **Precedent Integration**: Include relevant civil law precedents and judgments
4. **Remedy Guidance**: Explain available civil remedies and their requirements
5. **Procedural Steps**: Provide step-by-step civil procedure guidance
6. **Property Considerations**: Address property law aspects if applicable
7. **Evidence Standards**: Address civil evidence requirements
8. **Practical Solutions**: Offer practical approaches to civil disputes

Format your response with clear sections and proper civil law citations.

Answer:"""

    def _get_family_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide a comprehensive family law analysis based on the provided context. Make sure to:

1. **Family Law Provisions**: Identify relevant family law and Islamic law provisions
2. **Legal Analysis**: Provide detailed analysis of the family law position
3. **Islamic Law Integration**: Include relevant Islamic law principles and precedents
4. **Family Court Procedures**: Explain family court procedures and requirements
5. **Sensitive Approach**: Handle family matters with appropriate sensitivity
6. **Cultural Considerations**: Address cultural and religious contexts
7. **Practical Guidance**: Provide practical solutions for family disputes
8. **Rights Protection**: Emphasize family rights and protections

Format your response with clear sections and proper family law citations.

Answer:"""

    def _get_procedural_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide comprehensive procedural guidance based on the provided context. Make sure to:

1. **Court Identification**: Identify the relevant court and jurisdiction
2. **Procedural Requirements**: Explain step-by-step procedural requirements with continuous numbering (Step 1, Step 2, Step 3, etc.)
3. **Documentation**: Address required documents and filing procedures
4. **Timelines**: Include relevant timelines and deadlines
5. **Court Procedures**: Explain court processes and requirements
6. **Fee Structure**: Address court fees and payment requirements
7. **Practical Tips**: Provide practical tips and considerations
8. **Compliance**: Emphasize the importance of procedural compliance

IMPORTANT: When providing step-by-step procedures, use continuous numbering (Step 1, Step 2, Step 3, etc.) regardless of section numbers. Do not use section numbers as step numbers.

Format your response with clear sections and practical procedural guidance.

Answer:"""

    def _get_general_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide a comprehensive legal analysis based on the provided context. Make sure to:

1. **Direct Answer**: Start with a clear, direct answer to the specific question
2. **Legal Analysis**: Provide detailed legal reasoning and analysis
3. **Proper Citations**: Include specific case numbers, court names, dates, and legal provisions
4. **Precedent References**: Cite relevant case law and legal precedents
5. **Procedural Guidance**: Include any relevant procedural steps or requirements with continuous numbering (Step 1, Step 2, Step 3, etc.)
6. **Context Integration**: Reference previous conversation context when relevant
7. **Professional Structure**: Organize your answer with clear headings and logical flow
8. **Practical Implications**: Explain what this means for the user's situation
9. **Limitations**: Clearly state any limitations or uncertainties in the information
10. **Next Steps**: Suggest appropriate next steps or additional resources

Format your response professionally with clear sections and proper legal citations.

Answer:"""

    def _get_case_analysis_user_template(self) -> str:
        return """Question: {question}

Legal Context:
{context}

{conversation_context}

Please provide a comprehensive case law analysis based on the provided context. Make sure to:

1. **Case Identification**: Identify the relevant case law and precedents
2. **Legal Analysis**: Analyze the legal reasoning and principles established
3. **Precedent Hierarchy**: Explain the binding nature and scope of precedents
4. **Comparative Analysis**: Compare with similar cases if relevant
5. **Legal Principles**: Extract and explain key legal principles
6. **Application**: Explain how precedents apply to current situations
7. **Limitations**: Address any limitations or exceptions to the precedents
8. **Practical Implications**: Discuss the practical implications of the case law

Format your response with clear sections and proper case law citations.

Answer:"""
