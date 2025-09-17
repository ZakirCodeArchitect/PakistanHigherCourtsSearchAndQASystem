"""
Management command to load sample law data
"""

from django.core.management.base import BaseCommand
from law_information.models import Law, LawCategory


class Command(BaseCommand):
    help = 'Load sample law data for testing'

    def handle(self, *args, **options):
        """Load sample law entries"""
        
        # Create categories first
        categories = [
            {
                'name': 'Criminal Law',
                'slug': 'criminal-law',
                'description': 'Laws related to crimes and criminal offenses',
                'color': '#dc3545',
                'icon': 'fas fa-gavel',
                'order': 1,
            },
            {
                'name': 'Property Law',
                'slug': 'property-law',
                'description': 'Laws related to property rights and ownership',
                'color': '#28a745',
                'icon': 'fas fa-home',
                'order': 2,
            },
            {
                'name': 'Family Law',
                'slug': 'family-law',
                'description': 'Laws related to family matters and relationships',
                'color': '#17a2b8',
                'icon': 'fas fa-users',
                'order': 3,
            },
            {
                'name': 'Contract Law',
                'slug': 'contract-law',
                'description': 'Laws related to contracts and agreements',
                'color': '#ffc107',
                'icon': 'fas fa-file-contract',
                'order': 4,
            },
            {
                'name': 'Labor Law',
                'slug': 'labor-law',
                'description': 'Laws related to employment and workers rights',
                'color': '#6f42c1',
                'icon': 'fas fa-briefcase',
                'order': 5,
            },
        ]
        
        for cat_data in categories:
            category, created = LawCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {category.name}')
                )
        
        sample_laws = [
            {
                'slug': 'ppc-379-theft',
                'title': 'Theft - PPC 379',
                'sections': ['PPC 379'],
                'punishment_summary': 'Whoever commits theft shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.',
                'jurisdiction': 'Magistrate/Sessions Court',
                'rights_summary': 'Right to file FIR\nRight to legal representation\nRight to bail (except in certain cases)\nRight to fair trial\nRight to appeal',
                'what_to_do': 'File FIR at nearest police station\nGather evidence (witnesses, documents)\nReport to police within reasonable time\nCooperate with investigation\nSeek legal advice if needed',
                'tags': ['theft', 'property', 'criminal', 'ppc'],
                'is_featured': True,
            },
            {
                'slug': 'ppc-302-murder',
                'title': 'Murder - PPC 302',
                'sections': ['PPC 302'],
                'punishment_summary': 'Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.',
                'jurisdiction': 'Sessions Court/High Court',
                'rights_summary': 'Right to legal representation\nRight to bail (except in certain cases)\nRight to fair trial\nRight to appeal\nRight to remain silent',
                'what_to_do': 'File FIR immediately\nPreserve crime scene\nGather evidence\nReport to police\nSeek legal counsel immediately',
                'tags': ['murder', 'criminal', 'ppc', 'serious'],
                'is_featured': True,
            },
            {
                'slug': 'ppc-420-fraud',
                'title': 'Cheating and Fraud - PPC 420',
                'sections': ['PPC 420'],
                'punishment_summary': 'Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.',
                'jurisdiction': 'Magistrate/Sessions Court',
                'rights_summary': 'Right to file complaint\nRight to legal representation\nRight to compensation\nRight to fair trial\nRight to appeal',
                'what_to_do': 'File complaint with police\nGather evidence of fraud\nDocument financial losses\nReport to relevant authorities\nSeek legal advice',
                'tags': ['fraud', 'cheating', 'criminal', 'ppc'],
                'is_featured': True,
            },
            {
                'slug': 'ppc-324-assault',
                'title': 'Voluntarily Causing Hurt - PPC 324',
                'sections': ['PPC 324'],
                'punishment_summary': 'Whoever, except in the case provided for by section 334, voluntarily causes hurt by means of any instrument for shooting, stabbing or cutting, or any instrument which, used as a weapon of offence, is likely to cause death, shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.',
                'jurisdiction': 'Magistrate Court',
                'rights_summary': 'Right to file FIR\nRight to medical examination\nRight to legal representation\nRight to compensation\nRight to fair trial',
                'what_to_do': 'File FIR at police station\nGet medical examination\nGather witness statements\nPreserve evidence\nSeek legal advice',
                'tags': ['assault', 'hurt', 'criminal', 'ppc'],
                'is_featured': False,
            },
            {
                'slug': 'ppc-376-rape',
                'title': 'Rape - PPC 376',
                'sections': ['PPC 376'],
                'punishment_summary': 'Whoever commits rape shall be punished with imprisonment for life or with imprisonment of either description for a term which shall not be less than ten years or more than twenty-five years, and shall also be liable to fine.',
                'jurisdiction': 'Sessions Court',
                'rights_summary': 'Right to file FIR\nRight to medical examination\nRight to legal representation\nRight to privacy\nRight to fair trial',
                'what_to_do': 'File FIR immediately\nGet medical examination\nPreserve evidence\nReport to police\nSeek legal and psychological support',
                'tags': ['rape', 'sexual', 'criminal', 'ppc', 'serious'],
                'is_featured': True,
            },
            {
                'slug': 'ppc-406-criminal-breach-trust',
                'title': 'Criminal Breach of Trust - PPC 406',
                'sections': ['PPC 406'],
                'punishment_summary': 'Whoever commits criminal breach of trust shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.',
                'jurisdiction': 'Magistrate/Sessions Court',
                'rights_summary': 'Right to file complaint\nRight to legal representation\nRight to recovery of property\nRight to fair trial\nRight to appeal',
                'what_to_do': 'File complaint with police\nGather evidence of breach\nDocument property/money involved\nReport to relevant authorities\nSeek legal advice',
                'tags': ['breach', 'trust', 'criminal', 'ppc'],
                'is_featured': False,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for law_data in sample_laws:
            law, created = Law.objects.get_or_create(
                slug=law_data['slug'],
                defaults=law_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created law: {law.title}')
                )
            else:
                # Update existing law
                for key, value in law_data.items():
                    setattr(law, key, value)
                law.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated law: {law.title}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSample data loading completed!\n'
                f'Created: {created_count} laws\n'
                f'Updated: {updated_count} laws\n'
                f'Total laws in database: {Law.objects.count()}'
            )
        )
