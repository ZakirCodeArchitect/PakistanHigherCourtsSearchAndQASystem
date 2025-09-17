"""
Management command to create comprehensive categories from all tags in the 733 laws
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from law_information.models import Law, LawCategory
from collections import defaultdict

class Command(BaseCommand):
    help = 'Creates comprehensive LawCategory entries from all unique tags in existing laws'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting comprehensive category creation from law tags...'))

        # 1. Collect all unique tags from all 733 laws
        all_laws = Law.objects.all()
        unique_tags = set()
        tag_counts = defaultdict(int)
        
        for law in all_laws:
            for tag in law.tags:
                if tag and tag.strip():  # Only process non-empty tags
                    normalized_tag = tag.strip().lower()
                    unique_tags.add(normalized_tag)
                    tag_counts[normalized_tag] += 1

        self.stdout.write(f'Found {len(unique_tags)} unique tags across {all_laws.count()} laws.')
        
        # Show top tags by frequency
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        self.stdout.write('Top 20 tags by frequency:')
        for tag, count in top_tags:
            self.stdout.write(f'  {tag}: {count} laws')

        # 2. Create new LawCategory entries for unique tags
        created_categories_count = 0
        existing_categories_map = {c.name.lower(): c for c in LawCategory.objects.all()}

        # Sort tags by frequency (most common first) for better organization
        sorted_tags = sorted(unique_tags, key=lambda x: tag_counts[x], reverse=True)

        for tag_name in sorted_tags:
            if tag_name and tag_name not in existing_categories_map:
                # Create a new category
                category, created = LawCategory.objects.get_or_create(
                    name=tag_name.capitalize(),
                    defaults={
                        'slug': slugify(tag_name),
                        'description': f'Laws related to {tag_name} ({tag_counts[tag_name]} laws)',
                        'color': self._get_color_for_tag(tag_name),
                        'icon': self._get_icon_for_tag(tag_name),
                        'order': created_categories_count + 1,
                    }
                )
                if created:
                    created_categories_count += 1
                    existing_categories_map[tag_name] = category
                    self.stdout.write(self.style.SUCCESS(f'Created category: {category.name} ({tag_counts[tag_name]} laws)'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_categories_count} new categories.'))
        self.stdout.write(f'Total categories now: {LawCategory.objects.count()}')

        # 3. Re-assign primary categories for laws based on their most relevant tag
        updated_laws_count = 0
        
        for law in all_laws:
            original_category = law.category
            best_category = None
            best_tag_count = 0
            
            # Find the most relevant category based on tags
            for tag in law.tags:
                if tag and tag.strip():
                    normalized_tag = tag.strip().lower()
                    if normalized_tag in existing_categories_map:
                        category = existing_categories_map[normalized_tag]
                        # Prefer categories with more laws (more established)
                        if tag_counts[normalized_tag] > best_tag_count:
                            best_category = category
                            best_tag_count = tag_counts[normalized_tag]
            
            # Update law category if we found a better match
            if best_category and law.category != best_category:
                law.category = best_category
                law.save()
                updated_laws_count += 1
                if updated_laws_count <= 10:  # Show first 10 updates
                    self.stdout.write(f'Updated "{law.title[:50]}..." to category "{best_category.name}"')

        self.stdout.write(self.style.SUCCESS(f'Updated categories for {updated_laws_count} laws.'))
        
        # 4. Show final statistics
        self.stdout.write(self.style.SUCCESS('\n=== FINAL STATISTICS ==='))
        self.stdout.write(f'Total Laws: {Law.objects.count()}')
        self.stdout.write(f'Total Categories: {LawCategory.objects.count()}')
        self.stdout.write(f'Laws with categories: {Law.objects.exclude(category__isnull=True).count()}')
        self.stdout.write(f'Laws without categories: {Law.objects.filter(category__isnull=True).count()}')
        
        # Show top categories by law count
        self.stdout.write('\nTop 15 categories by law count:')
        category_counts = defaultdict(int)
        for law in Law.objects.exclude(category__isnull=True):
            category_counts[law.category.name] += 1
        
        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        for category_name, count in top_categories:
            self.stdout.write(f'  {category_name}: {count} laws')

        self.stdout.write(self.style.SUCCESS('\nComprehensive category creation completed!'))

    def _get_color_for_tag(self, tag):
        """Assign colors based on tag type"""
        color_map = {
            'criminal': '#dc3545',  # Red
            'civil': '#28a745',     # Green
            'family': '#17a2b8',    # Cyan
            'property': '#ffc107',  # Yellow
            'labor': '#6f42c1',     # Purple
            'contract': '#fd7e14',  # Orange
            'act': '#007bff',       # Blue
            'ordinance': '#20c997', # Teal
            'ppc': '#e83e8c',       # Pink
            'serious': '#dc3545',   # Red
            'religious': '#6f42c1', # Purple
            'blasphemy': '#dc3545', # Red
            'breach': '#fd7e14',    # Orange
            'theft': '#dc3545',     # Red
            'murder': '#dc3545',    # Red
            'fraud': '#ffc107',     # Yellow
            'assault': '#dc3545',   # Red
            'rape': '#dc3545',      # Red
            'trust': '#28a745',     # Green
            'counterfeit': '#dc3545', # Red
        }
        return color_map.get(tag, '#6c757d')  # Default gray

    def _get_icon_for_tag(self, tag):
        """Assign icons based on tag type"""
        icon_map = {
            'criminal': 'fas fa-gavel',
            'civil': 'fas fa-balance-scale',
            'family': 'fas fa-users',
            'property': 'fas fa-home',
            'labor': 'fas fa-briefcase',
            'contract': 'fas fa-file-contract',
            'act': 'fas fa-scroll',
            'ordinance': 'fas fa-clipboard-list',
            'ppc': 'fas fa-book',
            'serious': 'fas fa-exclamation-triangle',
            'religious': 'fas fa-mosque',
            'blasphemy': 'fas fa-exclamation-triangle',
            'breach': 'fas fa-handshake',
            'theft': 'fas fa-lock',
            'murder': 'fas fa-skull-crossbones',
            'fraud': 'fas fa-user-secret',
            'assault': 'fas fa-fist-raised',
            'rape': 'fas fa-shield-alt',
            'trust': 'fas fa-handshake',
            'counterfeit': 'fas fa-money-bill-wave',
        }
        return icon_map.get(tag, 'fas fa-gavel')  # Default gavel
