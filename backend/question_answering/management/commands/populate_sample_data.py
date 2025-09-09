"""
Management command to populate sample legal data for testing
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import json
import os

class Command(BaseCommand):
    help = 'Populate the knowledge base with sample legal data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be populated without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No data will be actually populated')
            )
        
        # Sample legal data
        sample_data = [
            {
                'title': 'Bail Law in Pakistan',
                'content': 'Under Pakistani law, bail is a fundamental right. The Constitution of Pakistan guarantees the right to liberty. Bail can be granted in bailable and non-bailable offenses. For bailable offenses, bail is a matter of right, while for non-bailable offenses, it is at the discretion of the court.',
                'court': 'Supreme Court of Pakistan',
                'case_number': 'PLD 2023 SC 1',
                'category': 'Criminal Law',
                'keywords': ['bail', 'liberty', 'constitution', 'criminal law']
            },
            {
                'title': 'Writ Petition Procedure',
                'content': 'A writ petition is a formal written application to a court requesting judicial action. In Pakistan, writ petitions are filed under Article 199 of the Constitution. The procedure involves filing a petition with proper cause of action, supporting documents, and court fees.',
                'court': 'High Court',
                'case_number': 'W.P. No. 1234/2023',
                'category': 'Constitutional Law',
                'keywords': ['writ petition', 'article 199', 'constitution', 'judicial review']
            },
            {
                'title': 'Constitutional Rights',
                'content': 'The Constitution of Pakistan guarantees fundamental rights including right to life, liberty, equality, freedom of speech, and freedom of religion. These rights are enforceable through the courts and any law inconsistent with fundamental rights is void.',
                'court': 'Supreme Court of Pakistan',
                'case_number': 'PLD 2022 SC 45',
                'category': 'Constitutional Law',
                'keywords': ['fundamental rights', 'constitution', 'life', 'liberty', 'equality']
            },
            {
                'title': 'Criminal Appeal Procedure',
                'content': 'Criminal appeals in Pakistan are governed by the Code of Criminal Procedure. An appeal can be filed against conviction or sentence within 30 days. The appellate court can confirm, reverse, or modify the judgment of the lower court.',
                'court': 'Sessions Court',
                'case_number': 'Crl. A. No. 567/2023',
                'category': 'Criminal Law',
                'keywords': ['criminal appeal', 'conviction', 'sentence', 'criminal procedure']
            }
        ]
        
        if dry_run:
            self.stdout.write(f'Would populate {len(sample_data)} legal documents:')
            for i, doc in enumerate(sample_data, 1):
                self.stdout.write(f'{i}. {doc["title"]} - {doc["court"]}')
        else:
            # Create a simple JSON file with the sample data
            data_file = os.path.join(settings.BASE_DIR, 'sample_legal_data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created sample data file: {data_file}')
            )
            self.stdout.write(f'Populated {len(sample_data)} legal documents')
        
        self.stdout.write(
            self.style.SUCCESS('Sample data population completed!')
        )
