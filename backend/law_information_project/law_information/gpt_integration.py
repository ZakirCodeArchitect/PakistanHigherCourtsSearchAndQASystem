"""
GPT-4o-mini Integration for Law Information Resource
Enhances search with natural language processing while keeping answers database-only
"""

import openai
import json
import re
from django.conf import settings
from django.core.cache import cache
from .models import Law
from .search_enhancements import LegalSearchEnhancer

# Configure OpenAI
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

class GPTLawAssistant:
    """GPT-4o-mini powered legal search assistant"""
    
    @staticmethod
    def process_natural_language_query(user_query):
        """Convert natural language questions to database search terms"""
        
        # Check cache first
        cache_key = f"gpt_query_{hash(user_query)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            prompt = f"""
            Convert this legal question to relevant search terms for a Pakistani legal database.
            
            User Question: "{user_query}"
            
            Available legal categories in the database:
            - Criminal Law: theft, murder, fraud, assault, robbery, burglary
            - Family Law: marriage, divorce, custody, family
            - Property Law: property, land, ownership, possession
            - Court/Jurisdiction: court, tribunal, judge, magistrate, sessions
            - Legal Procedures: punishment, rights, jurisdiction, sections
            - Legal Acts: PPC (Penal Code), Family Laws, Motor Vehicles Act, etc.
            
            Instructions:
            1. Extract 2-5 relevant search terms that exist in Pakistani legal system
            2. Focus on specific legal terms, not general concepts
            3. Include related legal sections if applicable (e.g., PPC 379 for theft)
            4. Return only terms that would likely exist in a Pakistani legal database
            5. If the query is about a non-existent legal concept, suggest the closest Pakistani legal equivalent
            
            Return the search terms as a JSON array.
            Example: ["theft", "PPC 379", "punishment", "jurisdiction"]
            """
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a legal search assistant for Pakistani laws. Always return valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            # Extract search terms from response
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            try:
                search_terms = json.loads(content)
                if isinstance(search_terms, list):
                    # Cache the result for 1 hour
                    cache.set(cache_key, search_terms, 3600)
                    return search_terms
            except json.JSONDecodeError:
                # Fallback: extract terms from text
                search_terms = re.findall(r'"([^"]+)"', content)
                if search_terms:
                    cache.set(cache_key, search_terms, 3600)
                    return search_terms
            
            # Final fallback: return original query words
            fallback_terms = [word for word in user_query.split() if len(word) > 2]
            cache.set(cache_key, fallback_terms, 3600)
            return fallback_terms
            
        except Exception as e:
            print(f"GPT API Error: {e}")
            # Fallback to simple word extraction
            return [word for word in user_query.split() if len(word) > 2]
    
    @staticmethod
    def expand_legal_query(query):
        """Expand legal queries with related Pakistani legal terms"""
        
        cache_key = f"gpt_expand_{hash(query)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            prompt = f"""
            Expand this legal query with related Pakistani legal terms that would exist in a legal database:
            
            Query: "{query}"
            
            If this exact term doesn't exist in Pakistani law, suggest related terms that do exist.
            Focus on:
            - Penal Code (PPC) sections
            - Family Laws
            - Property Laws
            - Court procedures
            - Legal acts and ordinances
            
            Return 3-5 related terms as a JSON array.
            Example: ["motor vehicle", "traffic", "rash driving", "negligence", "accident"]
            """
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a Pakistani legal expert. Return valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                expanded_terms = json.loads(content)
                if isinstance(expanded_terms, list):
                    cache.set(cache_key, expanded_terms, 3600)
                    return expanded_terms
            except json.JSONDecodeError:
                expanded_terms = re.findall(r'"([^"]+)"', content)
                if expanded_terms:
                    cache.set(cache_key, expanded_terms, 3600)
                    return expanded_terms
            
            return [query]
            
        except Exception as e:
            print(f"GPT API Error: {e}")
            return [query]
    
    @staticmethod
    def generate_user_friendly_answer(law_data, user_query):
        """Generate user-friendly explanations of legal information"""
        
        cache_key = f"gpt_answer_{law_data.id}_{hash(user_query)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            prompt = f"""
            Explain this Pakistani law in simple, clear terms for a common person:
            
            Law Title: {law_data.title}
            Sections: {', '.join(law_data.sections) if law_data.sections else 'N/A'}
            Punishment: {law_data.punishment_summary}
            Jurisdiction: {law_data.jurisdiction}
            Rights: {law_data.rights_summary}
            What to Do: {law_data.what_to_do}
            
            User Question: "{user_query}"
            
            Instructions:
            1. Explain in simple, everyday language
            2. Use ONLY the information provided above
            3. Do not add external legal advice
            4. Keep it concise (2-3 sentences)
            5. If the law is NOT directly related to the user's question, say so honestly
            6. Do NOT force connections that don't exist
            7. Use Pakistani legal context
            
            IMPORTANT: If this law is not about the user's specific question, be honest about it.
            Example: "This law is about [actual topic], not [user's question]. However, if you need help with [user's question], you should..."
            
            Provide a clear, honest explanation.
            """
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful legal assistant. Explain laws simply and clearly using only provided information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.4
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Cache the result for 24 hours
            cache.set(cache_key, answer, 86400)
            return answer
            
        except Exception as e:
            print(f"GPT API Error: {e}")
            # Fallback to simple explanation
            return f"This law ({law_data.title}) deals with {user_query}. The punishment is: {law_data.punishment_summary}"
    
    @staticmethod
    def get_smart_suggestions(partial_query):
        """Get intelligent search suggestions"""
        
        cache_key = f"gpt_suggestions_{hash(partial_query)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            prompt = f"""
            Suggest 5 relevant Pakistani legal search terms for: "{partial_query}"
            
            Focus on terms that would exist in a Pakistani legal database:
            - Criminal law terms (theft, murder, fraud, etc.)
            - Family law terms (marriage, divorce, custody, etc.)
            - Property law terms (property, land, ownership, etc.)
            - Court terms (court, tribunal, judge, etc.)
            - Legal sections (PPC 379, PPC 302, etc.)
            
            Return as a JSON array.
            Example: ["theft", "PPC 379", "theft punishment", "theft procedure", "theft control"]
            """
            
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a legal search assistant. Return valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                suggestions = json.loads(content)
                if isinstance(suggestions, list):
                    cache.set(cache_key, suggestions, 3600)
                    return suggestions
            except json.JSONDecodeError:
                suggestions = re.findall(r'"([^"]+)"', content)
                if suggestions:
                    cache.set(cache_key, suggestions, 3600)
                    return suggestions
            
            return []
            
        except Exception as e:
            print(f"GPT API Error: {e}")
            return []
    
    @staticmethod
    def enhanced_search_with_gpt(user_query):
        """Complete enhanced search with GPT-4o-mini integration"""
        
        # Step 1: Use the improved search algorithm directly
        # This ensures we get only relevant results from the start
        results = LegalSearchEnhancer.enhanced_search(
            Law.objects.filter(is_active=True), 
            user_query, 
            'all'
        )
        
        # Step 2: Generate user-friendly answers for relevant results only
        enhanced_results = []
        for law in results[:10]:  # Limit to top 10 results
            try:
                explanation = GPTLawAssistant.generate_user_friendly_answer(law, user_query)
                # Ensure we have a valid explanation
                if not explanation or explanation.strip() == '':
                    explanation = f"This law ({law.title}) is relevant to your query about '{user_query}'. The punishment is: {law.punishment_summary or 'Not specified'}."
            except Exception as e:
                print(f"Error generating explanation for {law.title}: {e}")
                explanation = f"This law ({law.title}) is relevant to your query about '{user_query}'. The punishment is: {law.punishment_summary or 'Not specified'}."
            
            # Get the actual search terms used by the improved algorithm
            expanded_words = LegalSearchEnhancer.expand_synonyms(user_query)
            relevant_terms = LegalSearchEnhancer._filter_relevant_terms(user_query, expanded_words)
            
            enhanced_results.append({
                'law': law,
                'explanation': explanation,
                'source': 'database',
                'search_terms_used': relevant_terms
            })
        
        return enhanced_results[:10]  # Return top 10 relevant results
