"""
Management command to improve search capabilities by adding synonyms and related terms
"""

from django.core.management.base import BaseCommand
from law_information.models import Law
import re

class Command(BaseCommand):
    help = 'Improve search capabilities by adding synonyms and related terms to law tags'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Improving search capabilities...'))
        
        # Define search synonyms and related terms
        search_improvements = {
            # Traffic and Vehicle related
            'hit and run': ['traffic', 'vehicle', 'accident', 'collision', 'motor', 'road'],
            'car accident': ['traffic', 'vehicle', 'accident', 'collision', 'motor'],
            'traffic accident': ['traffic', 'vehicle', 'accident', 'collision', 'motor'],
            'road accident': ['traffic', 'vehicle', 'accident', 'collision', 'motor'],
            
            # Theft related
            'theft': ['stealing', 'robbery', 'burglary', 'larceny', 'property'],
            'stealing': ['theft', 'robbery', 'burglary', 'larceny', 'property'],
            'robbery': ['theft', 'stealing', 'burglary', 'larceny', 'property'],
            
            # Violence related
            'assault': ['attack', 'violence', 'battery', 'hurt', 'injury'],
            'attack': ['assault', 'violence', 'battery', 'hurt', 'injury'],
            'violence': ['assault', 'attack', 'battery', 'hurt', 'injury'],
            
            # Fraud related
            'fraud': ['cheating', 'deception', 'scam', 'swindling', 'embezzlement'],
            'cheating': ['fraud', 'deception', 'scam', 'swindling', 'embezzlement'],
            'scam': ['fraud', 'cheating', 'deception', 'swindling', 'embezzlement'],
            
            # Family related
            'divorce': ['separation', 'dissolution', 'marriage', 'family'],
            'separation': ['divorce', 'dissolution', 'marriage', 'family'],
            'custody': ['children', 'guardianship', 'family', 'parental'],
            
            # Property related
            'property': ['land', 'real estate', 'ownership', 'possession'],
            'land': ['property', 'real estate', 'ownership', 'possession'],
            'ownership': ['property', 'land', 'possession', 'title'],
            
            # Employment related
            'employment': ['job', 'work', 'labor', 'worker', 'employee'],
            'job': ['employment', 'work', 'labor', 'worker', 'employee'],
            'workplace': ['employment', 'job', 'work', 'labor', 'worker'],
            
            # Court related
            'court': ['tribunal', 'judge', 'judiciary', 'legal'],
            'judge': ['court', 'tribunal', 'judiciary', 'legal'],
            'tribunal': ['court', 'judge', 'judiciary', 'legal'],
        }
        
        updated_count = 0
        
        # Update laws with improved tags
        for law in Law.objects.all():
            original_tags = set(law.tags)
            new_tags = set(law.tags)
            
            # Add synonyms based on existing tags
            for tag in law.tags:
                tag_lower = tag.lower()
                if tag_lower in search_improvements:
                    new_tags.update(search_improvements[tag_lower])
            
            # Add synonyms based on title content
            title_lower = law.title.lower()
            for phrase, synonyms in search_improvements.items():
                if phrase in title_lower:
                    new_tags.update(synonyms)
            
            # Convert back to list and update if changed
            if new_tags != original_tags:
                law.tags = list(new_tags)
                law.save()
                updated_count += 1
                if updated_count <= 10:  # Show first 10 updates
                    self.stdout.write(f'Updated tags for: {law.title[:50]}...')
        
        self.stdout.write(self.style.SUCCESS(f'\nSearch improvement completed!'))
        self.stdout.write(f'Updated: {updated_count} laws with improved tags')
        self.stdout.write(f'Total laws: {Law.objects.count()}')
        
        # Test the improvements
        self.stdout.write(self.style.SUCCESS('\nTesting improved search capabilities:'))
        
        test_queries = ['hit and run', 'car accident', 'stealing', 'attack', 'scam', 'separation', 'job', 'court']
        for query in test_queries:
            count = Law.objects.filter(tags__icontains=query).count()
            if count > 0:
                self.stdout.write(f'✅ {query}: {count} results')
            else:
                self.stdout.write(f'❌ {query}: 0 results')
