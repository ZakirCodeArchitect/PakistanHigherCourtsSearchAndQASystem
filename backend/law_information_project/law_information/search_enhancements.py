"""
Enhanced search functionality for Law Information Resource
Implements Full-Text Search, Ranking, and Synonym Expansion
"""

from django.db import models
from django.db.models import Q, F, Value
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models.functions import Concat
import re


class LegalSearchEnhancer:
    """Enhanced search functionality with FTS, ranking, and synonyms"""
    
    # Legal synonyms mapping
    LEGAL_SYNONYMS = {
        # Theft related
        'theft': ['stealing', 'robbery', 'burglary', 'larceny', 'thieving', 'pilfering'],
        'stealing': ['theft', 'robbery', 'burglary', 'larceny', 'thieving', 'pilfering'],
        'robbery': ['theft', 'stealing', 'burglary', 'larceny', 'mugging', 'hold-up'],
        'burglary': ['theft', 'stealing', 'robbery', 'larceny', 'breaking', 'entering'],
        
        # Violence related
        'murder': ['homicide', 'killing', 'assassination', 'slaying'],
        'homicide': ['murder', 'killing', 'assassination', 'slaying'],
        'assault': ['attack', 'battery', 'violence', 'beating', 'striking'],
        'attack': ['assault', 'battery', 'violence', 'beating', 'striking'],
        'violence': ['assault', 'attack', 'battery', 'beating', 'striking'],
        
        # Fraud related
        'fraud': ['cheating', 'deception', 'scam', 'swindling', 'embezzlement', 'forgery'],
        'cheating': ['fraud', 'deception', 'scam', 'swindling', 'embezzlement'],
        'scam': ['fraud', 'cheating', 'deception', 'swindling', 'embezzlement'],
        'deception': ['fraud', 'cheating', 'scam', 'swindling', 'embezzlement'],
        
        # Family related
        'family': ['marriage', 'divorce', 'custody', 'domestic', 'spouse', 'children'],
        'marriage': ['family', 'divorce', 'wedding', 'matrimony', 'spouse'],
        'divorce': ['family', 'marriage', 'separation', 'dissolution', 'annulment'],
        'custody': ['family', 'children', 'guardianship', 'parental', 'care'],
        
        # Court related
        'court': ['tribunal', 'judiciary', 'bench', 'judge', 'magistrate', 'sessions'],
        'tribunal': ['court', 'judiciary', 'bench', 'judge', 'magistrate'],
        'judge': ['court', 'tribunal', 'judiciary', 'magistrate', 'justice'],
        'magistrate': ['court', 'tribunal', 'judge', 'justice', 'sessions'],
        
        # Property related
        'property': ['land', 'real estate', 'ownership', 'possession', 'asset', 'belongings'],
        'land': ['property', 'real estate', 'ownership', 'possession', 'territory'],
        'ownership': ['property', 'land', 'possession', 'title', 'deed'],
        'possession': ['property', 'land', 'ownership', 'holding', 'keeping'],
        
        # Employment related
        'employment': ['job', 'work', 'labor', 'worker', 'employee', 'occupation'],
        'job': ['employment', 'work', 'labor', 'worker', 'employee', 'occupation'],
        'work': ['employment', 'job', 'labor', 'worker', 'employee', 'occupation'],
        'labor': ['employment', 'job', 'work', 'worker', 'employee', 'labour'],
        'worker': ['employment', 'job', 'work', 'labor', 'employee', 'staff'],
        
        # Legal terms
        'punishment': ['penalty', 'sentence', 'fine', 'imprisonment', 'jail'],
        'penalty': ['punishment', 'sentence', 'fine', 'imprisonment', 'jail'],
        'sentence': ['punishment', 'penalty', 'fine', 'imprisonment', 'jail'],
        'fine': ['punishment', 'penalty', 'sentence', 'monetary', 'payment'],
        'imprisonment': ['punishment', 'penalty', 'sentence', 'jail', 'prison'],
        
        # Rights related
        'rights': ['privileges', 'entitlements', 'freedoms', 'liberties', 'claims'],
        'privileges': ['rights', 'entitlements', 'freedoms', 'liberties', 'claims'],
        'entitlements': ['rights', 'privileges', 'freedoms', 'liberties', 'claims'],
    }
    
    @classmethod
    def expand_synonyms(cls, query):
        """Expand query with synonyms"""
        words = query.lower().split()
        expanded_words = set()
        
        for word in words:
            expanded_words.add(word)
            if word in cls.LEGAL_SYNONYMS:
                expanded_words.update(cls.LEGAL_SYNONYMS[word])
        
        return list(expanded_words)
    
    @classmethod
    def create_search_vector(cls, law):
        """Create a search vector for a law entry"""
        # Combine all searchable fields
        searchable_text = f"{law.title} {' '.join(law.sections)} {' '.join(law.tags)} {law.jurisdiction} {law.punishment_summary}"
        
        # Create search vector with different weights
        return SearchVector(
            Value(law.title, output_field=models.CharField()),
            Value(' '.join(law.sections), output_field=models.CharField()),
            Value(' '.join(law.tags), output_field=models.CharField()),
            Value(law.jurisdiction, output_field=models.CharField()),
            Value(law.punishment_summary, output_field=models.CharField())
        )
    
    @classmethod
    def enhanced_search(cls, queryset, query, search_type='all'):
        """Enhanced search with Full-Text Search, ranking, and synonyms"""
        
        if not query.strip():
            return queryset.none()
        
        # Handle field-specific searches
        if search_type == 'title':
            return cls._field_specific_search(queryset, query, 'title')
        elif search_type == 'sections':
            return cls._field_specific_search(queryset, query, 'sections')
        elif search_type == 'tags':
            return cls._field_specific_search(queryset, query, 'tags')
        elif search_type == 'jurisdiction':
            return cls._field_specific_search(queryset, query, 'jurisdiction')
        
        # Enhanced search for 'all' type
        return cls._full_text_search_with_ranking(queryset, query)
    
    @classmethod
    def _field_specific_search(cls, queryset, query, field_name):
        """Field-specific search with synonyms"""
        expanded_words = cls.expand_synonyms(query)
        
        # Create OR query for all expanded words
        field_query = Q()
        for word in expanded_words:
            if field_name == 'sections':
                field_query |= Q(sections__icontains=word)
            elif field_name == 'tags':
                field_query |= Q(tags__icontains=word)
            else:
                field_query |= Q(**{f"{field_name}__icontains": word})
        
        return queryset.filter(field_query)
    
    @classmethod
    def _full_text_search_with_ranking(cls, queryset, query):
        """Full-text search with ranking and intelligent relevance filtering"""
        
        # First try exact phrase search
        exact_results = queryset.filter(
            Q(title__icontains=query) |
            Q(sections__icontains=query) |
            Q(tags__icontains=query) |
            Q(jurisdiction__icontains=query) |
            Q(punishment_summary__icontains=query)
        )
        
        if exact_results.exists():
            return exact_results.annotate(
                relevance_score=Value(100, output_field=models.IntegerField())
            ).order_by('-relevance_score', 'title')
        
        # If no exact results, try intelligent search with context awareness
        expanded_words = cls.expand_synonyms(query)
        
        if not expanded_words:
            return queryset.none()
        
        # Filter search terms based on query context
        relevant_terms = cls._filter_relevant_terms(query, expanded_words)
        
        if not relevant_terms:
            return queryset.none()
        
        # Use intelligent search with context matching
        return cls._intelligent_context_search(queryset, query, relevant_terms)
    
    @classmethod
    def _filter_relevant_terms(cls, query, expanded_words):
        """Filter search terms based on query context to improve relevance"""
        
        # Define context-specific term filtering
        query_lower = query.lower()
        
        # For car/vehicle theft queries
        if any(word in query_lower for word in ['car', 'vehicle', 'motor', 'auto', 'stolen', 'theft']):
            # For car theft queries, we need to search for both theft and vehicle terms
            # Add relevant terms that should be searched
            relevant_terms = ['theft', 'motor vehicle', 'motor']
            
            # Also include any relevant terms from expanded words
            for word in expanded_words:
                if any(keyword in word.lower() for keyword in [
                    'theft', 'steal', 'robbery', 'burglary', 'larceny',
                    'vehicle', 'motor', 'car', 'auto', 'traffic',
                    'criminal', 'crime', 'offense', 'punishment',
                    'ppc', 'penal', 'code'
                ]):
                    if word not in relevant_terms:
                        relevant_terms.append(word)
            return relevant_terms
        
        # For murder/violence queries
        elif any(word in query_lower for word in ['murder', 'homicide', 'killing', 'violence', 'assault']):
            # For murder queries, focus on specific violence terms, not generic punishment terms
            relevant_terms = []
            for word in expanded_words:
                if any(keyword in word.lower() for keyword in [
                    'murder', 'homicide', 'killing', 'violence', 'assault', 'attack',
                    'criminal', 'penal', 'ppc', 'offense', 'crime'
                ]):
                    relevant_terms.append(word)
            return relevant_terms
        
        # For family law queries
        elif any(word in query_lower for word in ['family', 'marriage', 'divorce', 'custody', 'spouse']):
            relevant_terms = []
            for word in expanded_words:
                if any(keyword in word.lower() for keyword in [
                    'family', 'marriage', 'divorce', 'custody', 'spouse',
                    'children', 'domestic', 'matrimony', 'wedding'
                ]):
                    relevant_terms.append(word)
            return relevant_terms
        
        # For property law queries
        elif any(word in query_lower for word in ['property', 'land', 'ownership', 'possession']):
            relevant_terms = []
            for word in expanded_words:
                if any(keyword in word.lower() for keyword in [
                    'property', 'land', 'ownership', 'possession',
                    'real estate', 'asset', 'belongings'
                ]):
                    relevant_terms.append(word)
            return relevant_terms
        
        # For fraud/cheating queries
        elif any(word in query_lower for word in ['fraud', 'cheating', 'scam', 'deception']):
            relevant_terms = []
            for word in expanded_words:
                if any(keyword in word.lower() for keyword in [
                    'fraud', 'cheating', 'deception', 'scam', 'swindling',
                    'embezzlement', 'forgery', 'false'
                ]):
                    relevant_terms.append(word)
            return relevant_terms
        
        # Default: return all terms if no specific context
        return expanded_words
    
    @classmethod
    def _intelligent_context_search(cls, queryset, query, relevant_terms):
        """Intelligent search with context-aware matching"""
        
        if not relevant_terms:
            return queryset.none()
        
        # Create weighted search with context awareness using ALL relevant terms
        title_matches = Q()
        tag_matches = Q()
        section_matches = Q()
        
        # Build queries for all relevant terms
        for term in relevant_terms:
            title_matches |= Q(title__icontains=term)
            tag_matches |= Q(tags__icontains=term)
            section_matches |= Q(sections__icontains=term)
        
        # Priority 1: Title matches (highest relevance)
        title_results = queryset.filter(title_matches).annotate(
            relevance_score=Value(90, output_field=models.IntegerField())
        )
        
        # Priority 2: Tags matches (high relevance)
        tag_results = queryset.filter(tag_matches).annotate(
            relevance_score=Value(80, output_field=models.IntegerField())
        )
        
        # Priority 3: Sections matches (medium relevance)
        section_results = queryset.filter(section_matches).annotate(
            relevance_score=Value(70, output_field=models.IntegerField())
        )
        
        # Combine results and remove duplicates
        all_results = (title_results | tag_results | section_results).distinct()
        
        # Apply additional context filtering
        filtered_results = cls._apply_context_filter(all_results, query)
        
        return filtered_results.order_by('-relevance_score', 'title')
    
    @classmethod
    def _apply_context_filter(cls, queryset, query):
        """Apply additional context filtering to remove irrelevant results"""
        
        query_lower = query.lower()
        
        # For car/vehicle theft queries
        if any(word in query_lower for word in ['car', 'vehicle', 'motor', 'auto', 'stolen']):
            return cls._filter_vehicle_theft_queries(queryset, query_lower)
        
        # For murder/violence queries
        elif any(word in query_lower for word in ['murder', 'homicide', 'killing', 'violence', 'assault']):
            return cls._filter_murder_violence_queries(queryset, query_lower)
        
        # For family law queries
        elif any(word in query_lower for word in ['family', 'marriage', 'divorce', 'custody', 'spouse']):
            return cls._filter_family_law_queries(queryset, query_lower)
        
        # For property law queries
        elif any(word in query_lower for word in ['property', 'land', 'ownership', 'possession', 'real estate']):
            return cls._filter_property_law_queries(queryset, query_lower)
        
        # For fraud/cheating queries
        elif any(word in query_lower for word in ['fraud', 'cheating', 'scam', 'deception', 'embezzlement']):
            return cls._filter_fraud_queries(queryset, query_lower)
        
        # For traffic/accident queries
        elif any(word in query_lower for word in ['hit and run', 'accident', 'traffic', 'driving', 'rash', 'vehicle']):
            return cls._filter_traffic_queries(queryset, query_lower)
        
        # Default: return as is for other queries
        return queryset
    
    @classmethod
    def _filter_vehicle_theft_queries(cls, queryset, query_lower):
        """Filter for vehicle theft related queries"""
        # Exclude laws that are clearly not about vehicles or theft
        excluded_keywords = [
            'banking', 'bank', 'financial', 'agricultural', 'agriculture',
            'maritime', 'admiralty', 'shipping', 'naval', 'sea',
            'education', 'school', 'university', 'examination',
            'tax', 'revenue', 'customs', 'duty',
            'health', 'medical', 'hospital', 'pharmaceutical',
            'cotton', 'transport', 'cargo', 'hydrocarbon', 'port', 'trust',
            'meetings', 'public order', 'institute', 'development'
        ]
        
        # Filter out laws with excluded keywords in title
        for keyword in excluded_keywords:
            queryset = queryset.exclude(title__icontains=keyword)
        
        # Exclude laws that are about theft but not vehicle theft
        queryset = queryset.exclude(
            Q(title__icontains='gas') & Q(title__icontains='theft') |
            Q(title__icontains='electricity') & Q(title__icontains='theft') |
            Q(title__icontains='water') & Q(title__icontains='theft') |
            Q(title__icontains='oil') & Q(title__icontains='theft')
        )
        
        # Exclude laws that contain "car" but are not about vehicles (like "carriage")
        queryset = queryset.exclude(
            Q(title__icontains='carriage') |
            Q(title__icontains='air') |
            Q(title__icontains='shipping') |
            Q(title__icontains='transport') |
            Q(title__icontains='cargo')
        )
        
        # Only include laws that are actually about vehicles, theft, or criminal law
        vehicle_related_keywords = [
            'motor vehicle', 'motor', 'theft', 'steal', 'robbery', 'burglary'
        ]
        
        # Also check tags for relevance
        tag_query = Q()
        for keyword in vehicle_related_keywords:
            tag_query |= Q(tags__icontains=keyword)
        
        # If no vehicle-related keywords in title or tags, exclude it
        vehicle_query = Q()
        for keyword in vehicle_related_keywords:
            vehicle_query |= Q(title__icontains=keyword)
        
        # Combine title and tag queries
        combined_query = vehicle_query | tag_query
        queryset = queryset.filter(combined_query)
        
        return queryset
    
    @classmethod
    def _filter_murder_violence_queries(cls, queryset, query_lower):
        """Filter for murder/violence related queries"""
        # Exclude laws that are clearly not about murder or violence
        excluded_keywords = [
            'agricultural', 'agriculture', 'produce', 'grading', 'marketing',
            'blood', 'transfusion', 'medical', 'health', 'hospital',
            'banking', 'bank', 'financial', 'tax', 'revenue',
            'education', 'school', 'university', 'examination',
            'maritime', 'shipping', 'port', 'cargo'
        ]
        
        # Filter out laws with excluded keywords in title
        for keyword in excluded_keywords:
            queryset = queryset.exclude(title__icontains=keyword)
        
        # Only include laws that are actually about murder, violence, or criminal law
        violence_related_keywords = [
            'murder', 'homicide', 'killing', 'violence', 'assault', 'attack',
            'criminal', 'penal', 'ppc', 'offense', 'crime'
        ]
        
        # Check tags for relevance
        tag_query = Q()
        for keyword in violence_related_keywords:
            tag_query |= Q(tags__icontains=keyword)
        
        # If no violence-related keywords in title or tags, exclude it
        violence_query = Q()
        for keyword in violence_related_keywords:
            violence_query |= Q(title__icontains=keyword)
        
        # Combine title and tag queries
        combined_query = violence_query | tag_query
        queryset = queryset.filter(combined_query)
        
        return queryset
    
    @classmethod
    def _filter_family_law_queries(cls, queryset, query_lower):
        """Filter for family law related queries"""
        # Exclude laws that are clearly not about family law
        excluded_keywords = [
            'banking', 'bank', 'financial', 'tax', 'revenue',
            'agricultural', 'agriculture', 'produce', 'grading',
            'medical', 'health', 'hospital', 'blood',
            'maritime', 'shipping', 'port', 'cargo',
            'education', 'school', 'university', 'examination'
        ]
        
        # Filter out laws with excluded keywords in title
        for keyword in excluded_keywords:
            queryset = queryset.exclude(title__icontains=keyword)
        
        # Only include laws that are actually about family law
        family_related_keywords = [
            'family', 'marriage', 'divorce', 'custody', 'spouse',
            'children', 'domestic', 'matrimony', 'wedding'
        ]
        
        # Check tags for relevance
        tag_query = Q()
        for keyword in family_related_keywords:
            tag_query |= Q(tags__icontains=keyword)
        
        # If no family-related keywords in title or tags, exclude it
        family_query = Q()
        for keyword in family_related_keywords:
            family_query |= Q(title__icontains=keyword)
        
        # Combine title and tag queries
        combined_query = family_query | tag_query
        queryset = queryset.filter(combined_query)
        
        return queryset
    
    @classmethod
    def _filter_property_law_queries(cls, queryset, query_lower):
        """Filter for property law related queries"""
        # Exclude laws that are clearly not about property law
        excluded_keywords = [
            'banking', 'bank', 'financial', 'transfer', 'liabilities',
            'agricultural', 'agriculture', 'produce', 'grading',
            'medical', 'health', 'hospital', 'blood',
            'maritime', 'shipping', 'port', 'cargo',
            'education', 'school', 'university', 'examination'
        ]
        
        # Filter out laws with excluded keywords in title
        for keyword in excluded_keywords:
            queryset = queryset.exclude(title__icontains=keyword)
        
        # Only include laws that are actually about property law
        property_related_keywords = [
            'property', 'land', 'ownership', 'possession', 'real estate',
            'asset', 'belongings', 'abandoned', 'management'
        ]
        
        # Check tags for relevance
        tag_query = Q()
        for keyword in property_related_keywords:
            tag_query |= Q(tags__icontains=keyword)
        
        # If no property-related keywords in title or tags, exclude it
        property_query = Q()
        for keyword in property_related_keywords:
            property_query |= Q(title__icontains=keyword)
        
        # Combine title and tag queries
        combined_query = property_query | tag_query
        queryset = queryset.filter(combined_query)
        
        return queryset
    
    @classmethod
    def _filter_fraud_queries(cls, queryset, query_lower):
        """Filter for fraud/cheating related queries"""
        # Exclude laws that are clearly not about fraud
        excluded_keywords = [
            'agricultural', 'agriculture', 'produce', 'grading',
            'medical', 'health', 'hospital', 'blood',
            'maritime', 'shipping', 'port', 'cargo',
            'education', 'school', 'university', 'examination',
            'banking', 'bank', 'financial', 'transfer'
        ]
        
        # Filter out laws with excluded keywords in title
        for keyword in excluded_keywords:
            queryset = queryset.exclude(title__icontains=keyword)
        
        # Only include laws that are actually about fraud
        fraud_related_keywords = [
            'fraud', 'cheating', 'deception', 'scam', 'swindling',
            'embezzlement', 'forgery', 'false', 'counterfeit'
        ]
        
        # Check tags for relevance
        tag_query = Q()
        for keyword in fraud_related_keywords:
            tag_query |= Q(tags__icontains=keyword)
        
        # If no fraud-related keywords in title or tags, exclude it
        fraud_query = Q()
        for keyword in fraud_related_keywords:
            fraud_query |= Q(title__icontains=keyword)
        
        # Combine title and tag queries
        combined_query = fraud_query | tag_query
        queryset = queryset.filter(combined_query)
        
        return queryset
    
    @classmethod
    def _filter_traffic_queries(cls, queryset, query_lower):
        """Filter for traffic/accident related queries"""
        # Exclude laws that are clearly not about traffic
        excluded_keywords = [
            'agricultural', 'agriculture', 'produce', 'grading',
            'medical', 'health', 'hospital', 'blood',
            'maritime', 'shipping', 'port', 'cargo',
            'education', 'school', 'university', 'examination',
            'banking', 'bank', 'financial', 'transfer',
            'abandoned', 'property', 'management',
            'trafficking', 'human trafficking', 'persons'
        ]
        
        # Filter out laws with excluded keywords in title
        for keyword in excluded_keywords:
            queryset = queryset.exclude(title__icontains=keyword)
        
        # Only include laws that are actually about traffic
        traffic_related_keywords = [
            'motor vehicle', 'motor', 'traffic', 'driving', 'accident',
            'hit and run', 'rash', 'negligence', 'vehicle'
        ]
        
        # Check tags for relevance
        tag_query = Q()
        for keyword in traffic_related_keywords:
            tag_query |= Q(tags__icontains=keyword)
        
        # If no traffic-related keywords in title or tags, exclude it
        traffic_query = Q()
        for keyword in traffic_related_keywords:
            traffic_query |= Q(title__icontains=keyword)
        
        # Combine title and tag queries
        combined_query = traffic_query | tag_query
        queryset = queryset.filter(combined_query)
        
        return queryset
    
    @classmethod
    def _fallback_synonym_search(cls, queryset, search_terms):
        """Fallback search using synonyms with AND logic"""
        if len(search_terms) == 1:
            # Single word search
            word = search_terms[0]
            return queryset.filter(
                Q(title__icontains=word) |
                Q(sections__icontains=word) |
                Q(tags__icontains=word) |
                Q(jurisdiction__icontains=word) |
                Q(punishment_summary__icontains=word)
            ).annotate(
                relevance_score=Value(50, output_field=models.IntegerField())
            ).order_by('-relevance_score', 'title')
        
        # Multi-word search with AND logic
        combined_query = None
        for word in search_terms:
            word_query = (
                Q(title__icontains=word) |
                Q(sections__icontains=word) |
                Q(tags__icontains=word) |
                Q(jurisdiction__icontains=word) |
                Q(punishment_summary__icontains=word)
            )
            
            if combined_query is None:
                combined_query = word_query
            else:
                combined_query &= word_query
        
        return queryset.filter(combined_query).annotate(
            relevance_score=Value(25, output_field=models.IntegerField())
        ).order_by('-relevance_score', 'title')
    
    @classmethod
    def get_search_suggestions(cls, query, limit=10):
        """Get search suggestions based on query"""
        if len(query) < 2:
            return []
        
        # Get suggestions from titles and tags
        title_suggestions = []
        tag_suggestions = []
        
        # This would need to be implemented with actual database queries
        # For now, return empty list
        return []
