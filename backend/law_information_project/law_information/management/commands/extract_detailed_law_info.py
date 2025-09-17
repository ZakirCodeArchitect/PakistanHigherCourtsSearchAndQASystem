"""
Management command to extract detailed information from PDF data and update law fields
"""

from django.core.management.base import BaseCommand
from law_information.models import Law
import re
import json

class Command(BaseCommand):
    help = 'Extract detailed information from PDF data and update law fields with actual content'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting detailed law information extraction...'))
        
        # Load the original PDF data
        try:
            with open('Law Data/pdf_data.json', 'r', encoding='utf-8') as f:
                pdf_data = json.load(f)
            self.stdout.write(f'Loaded {len(pdf_data)} PDF documents')
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('PDF data file not found. Please ensure Law Data/pdf_data.json exists.'))
            return
        
        updated_count = 0
        skipped_count = 0
        
        # Process each law
        for law in Law.objects.all():
            try:
                # Find matching PDF data by searching through all documents
                matching_text = None
                law_title_lower = law.title.lower()
                
                # Search through all PDF documents for matching content
                for item in pdf_data:
                    text = item.get('text', '')
                    if self.is_law_match(law_title_lower, text):
                        matching_text = text
                        break
                
                if matching_text:
                    # Extract detailed information
                    extracted_info = self.extract_detailed_info(matching_text, law.title)
                    
                    # Update law fields
                    updated = False
                    if extracted_info['punishment_summary'] and extracted_info['punishment_summary'] != law.punishment_summary:
                        law.punishment_summary = extracted_info['punishment_summary']
                        updated = True
                    
                    if extracted_info['jurisdiction'] and extracted_info['jurisdiction'] != law.jurisdiction:
                        law.jurisdiction = extracted_info['jurisdiction']
                        updated = True
                    
                    if extracted_info['rights_summary'] and extracted_info['rights_summary'] != law.rights_summary:
                        law.rights_summary = extracted_info['rights_summary']
                        updated = True
                    
                    if extracted_info['what_to_do'] and extracted_info['what_to_do'] != law.what_to_do:
                        law.what_to_do = extracted_info['what_to_do']
                        updated = True
                    
                    if updated:
                        law.save()
                        updated_count += 1
                        if updated_count <= 10:  # Show first 10 updates
                            self.stdout.write(f'Updated: {law.title[:50]}...')
                    else:
                        skipped_count += 1
                else:
                    # Generate generic content based on law title
                    extracted_info = self.generate_generic_content(law.title)
                    
                    updated = False
                    if extracted_info['punishment_summary'] != law.punishment_summary:
                        law.punishment_summary = extracted_info['punishment_summary']
                        updated = True
                    
                    if extracted_info['jurisdiction'] != law.jurisdiction:
                        law.jurisdiction = extracted_info['jurisdiction']
                        updated = True
                    
                    if extracted_info['rights_summary'] != law.rights_summary:
                        law.rights_summary = extracted_info['rights_summary']
                        updated = True
                    
                    if extracted_info['what_to_do'] != law.what_to_do:
                        law.what_to_do = extracted_info['what_to_do']
                        updated = True
                    
                    if updated:
                        law.save()
                        updated_count += 1
                        if updated_count <= 10:  # Show first 10 updates
                            self.stdout.write(f'Generated generic content for: {law.title[:50]}...')
                    else:
                        skipped_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error processing {law.title}: {e}'))
                skipped_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\nExtraction completed!'))
        self.stdout.write(f'Updated: {updated_count} laws')
        self.stdout.write(f'Skipped: {skipped_count} laws')
        self.stdout.write(f'Total laws: {Law.objects.count()}')

    def is_law_match(self, law_title, text):
        """Check if law title matches the text content"""
        # Extract key words from law title
        law_words = set(re.findall(r'\b\w+\b', law_title.lower()))
        
        # Remove common words
        common_words = {'the', 'act', 'ordinance', 'code', 'law', 'of', 'and', 'in', 'for', 'to', 'a', 'an', 'pakistan'}
        law_words -= common_words
        
        # Check if significant words from title appear in text
        text_lower = text.lower()
        matches = 0
        for word in law_words:
            if len(word) > 3 and word in text_lower:  # Only check words longer than 3 characters
                matches += 1
        
        # If at least 2 significant words match, consider it a match
        return matches >= 2

    def extract_detailed_info(self, text, law_title):
        """Extract detailed information from law text"""
        info = {
            'punishment_summary': '',
            'jurisdiction': '',
            'rights_summary': '',
            'what_to_do': ''
        }
        
        # Extract punishment information
        punishment_patterns = [
            r'punishment.*?shall be.*?(?:imprisonment|fine|death|life).*?(?:\n|\.)',
            r'penalty.*?shall be.*?(?:imprisonment|fine|death|life).*?(?:\n|\.)',
            r'shall be punished.*?(?:imprisonment|fine|death|life).*?(?:\n|\.)',
            r'punishable.*?(?:imprisonment|fine|death|life).*?(?:\n|\.)'
        ]
        
        for pattern in punishment_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                info['punishment_summary'] = match.group(0).strip()
                break
        
        # Extract jurisdiction information
        jurisdiction_patterns = [
            r'jurisdiction.*?(?:court|tribunal|authority).*?(?:\n|\.)',
            r'competent.*?(?:court|tribunal|authority).*?(?:\n|\.)',
            r'(?:magistrate|sessions|high court|supreme court).*?(?:court|tribunal)',
            r'try.*?(?:court|tribunal|authority)'
        ]
        
        for pattern in jurisdiction_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                info['jurisdiction'] = match.group(0).strip()
                break
        
        # Extract rights information
        rights_patterns = [
            r'right.*?(?:accused|complainant|person).*?(?:\n|\.)',
            r'entitled.*?(?:right|benefit).*?(?:\n|\.)',
            r'privilege.*?(?:accused|complainant|person).*?(?:\n|\.)'
        ]
        
        rights_found = []
        for pattern in rights_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            rights_found.extend(matches)
        
        if rights_found:
            info['rights_summary'] = '\n'.join(rights_found[:5])  # Limit to 5 rights
        
        # Extract procedural information
        procedure_patterns = [
            r'procedure.*?(?:\n|\.)',
            r'steps.*?(?:\n|\.)',
            r'process.*?(?:\n|\.)',
            r'file.*?(?:complaint|fir|suit).*?(?:\n|\.)',
            r'report.*?(?:police|authority).*?(?:\n|\.)'
        ]
        
        procedures_found = []
        for pattern in procedure_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            procedures_found.extend(matches)
        
        if procedures_found:
            info['what_to_do'] = '\n'.join(procedures_found[:5])  # Limit to 5 procedures
        
        # If no specific information found, generate generic content
        if not info['punishment_summary']:
            info['punishment_summary'] = self.generate_generic_punishment(law_title)
        
        if not info['jurisdiction']:
            info['jurisdiction'] = self.generate_generic_jurisdiction(law_title)
        
        if not info['rights_summary']:
            info['rights_summary'] = self.generate_generic_rights(law_title)
        
        if not info['what_to_do']:
            info['what_to_do'] = self.generate_generic_procedures(law_title)
        
        return info

    def generate_generic_content(self, law_title):
        """Generate generic content based on law title"""
        return {
            'punishment_summary': self.generate_generic_punishment(law_title),
            'jurisdiction': self.generate_generic_jurisdiction(law_title),
            'rights_summary': self.generate_generic_rights(law_title),
            'what_to_do': self.generate_generic_procedures(law_title)
        }

    def generate_generic_punishment(self, law_title):
        """Generate generic punishment based on law title"""
        title_lower = law_title.lower()
        
        if any(word in title_lower for word in ['murder', 'homicide']):
            return "Death penalty or imprisonment for life, and fine."
        elif any(word in title_lower for word in ['theft', 'robbery']):
            return "Imprisonment up to 3-7 years, or fine, or both."
        elif any(word in title_lower for word in ['fraud', 'cheating']):
            return "Imprisonment up to 7 years, and fine."
        elif any(word in title_lower for word in ['assault', 'hurt']):
            return "Imprisonment up to 3-10 years, or fine, or both."
        elif any(word in title_lower for word in ['rape', 'sexual']):
            return "Imprisonment for life or 10-25 years, and fine."
        elif any(word in title_lower for word in ['narcotics', 'drugs']):
            return "Imprisonment up to 14 years, and fine."
        elif any(word in title_lower for word in ['terrorism', 'anti-terrorism']):
            return "Imprisonment up to 14 years, and fine."
        elif any(word in title_lower for word in ['blasphemy', 'religious']):
            return "Imprisonment up to 2 years, or fine, or both."
        elif any(word in title_lower for word in ['counterfeit', 'currency']):
            return "Imprisonment for life or up to 10 years, and fine."
        elif any(word in title_lower for word in ['breach', 'trust']):
            return "Imprisonment up to 3 years, or fine, or both."
        else:
            return "Punishment as prescribed under the relevant provisions of the law."

    def generate_generic_jurisdiction(self, law_title):
        """Generate generic jurisdiction based on law title"""
        title_lower = law_title.lower()
        
        if any(word in title_lower for word in ['murder', 'rape', 'terrorism', 'narcotics', 'blasphemy']):
            return "Sessions Court/High Court"
        elif any(word in title_lower for word in ['theft', 'fraud', 'assault', 'hurt', 'breach']):
            return "Magistrate/Sessions Court"
        elif any(word in title_lower for word in ['family', 'marriage', 'divorce']):
            return "Family Court"
        elif any(word in title_lower for word in ['labor', 'employment', 'worker']):
            return "Labor Court"
        elif any(word in title_lower for word in ['civil', 'contract', 'property']):
            return "Civil Court"
        elif any(word in title_lower for word in ['tax', 'revenue', 'customs']):
            return "Tax Tribunal/Revenue Court"
        elif any(word in title_lower for word in ['banking', 'finance', 'companies']):
            return "Banking Court/Commercial Court"
        elif any(word in title_lower for word in ['environment', 'pollution']):
            return "Environmental Tribunal"
        else:
            return "Relevant Court as per law"

    def generate_generic_rights(self, law_title):
        """Generate generic rights based on law title"""
        title_lower = law_title.lower()
        
        if any(word in title_lower for word in ['criminal', 'penal', 'offence', 'murder', 'theft', 'fraud', 'assault']):
            return "Right to legal representation\nRight to fair trial\nRight to bail (except in certain cases)\nRight to remain silent\nRight to appeal"
        elif any(word in title_lower for word in ['family', 'marriage', 'divorce']):
            return "Right to maintenance\nRight to custody of children\nRight to legal representation\nRight to appeal\nRight to property"
        elif any(word in title_lower for word in ['labor', 'employment', 'worker']):
            return "Right to fair wages\nRight to safe working conditions\nRight to legal representation\nRight to compensation\nRight to appeal"
        elif any(word in title_lower for word in ['civil', 'contract', 'property']):
            return "Right to legal representation\nRight to compensation\nRight to specific performance\nRight to appeal\nRight to property"
        elif any(word in title_lower for word in ['tax', 'revenue', 'customs']):
            return "Right to legal representation\nRight to appeal\nRight to refund\nRight to hearing\nRight to documentation"
        elif any(word in title_lower for word in ['banking', 'finance', 'companies']):
            return "Right to legal representation\nRight to appeal\nRight to compensation\nRight to hearing\nRight to documentation"
        else:
            return "Right to legal representation\nRight to fair trial\nRight to appeal\nRight to compensation\nRight to due process"

    def generate_generic_procedures(self, law_title):
        """Generate generic procedures based on law title"""
        title_lower = law_title.lower()
        
        if any(word in title_lower for word in ['criminal', 'penal', 'offence', 'murder', 'theft', 'fraud', 'assault']):
            return "File FIR at nearest police station\nGather evidence and witnesses\nCooperate with investigation\nSeek legal counsel\nAttend court proceedings"
        elif any(word in title_lower for word in ['family', 'marriage', 'divorce']):
            return "Consult family lawyer\nFile application with relevant court\nAttend reconciliation proceedings\nComplete legal formalities\nRegister changes"
        elif any(word in title_lower for word in ['labor', 'employment', 'worker']):
            return "File complaint with Labor Department\nGather employment documents\nAttend conciliation proceedings\nSeek legal advice\nConsider legal action"
        elif any(word in title_lower for word in ['civil', 'contract', 'property']):
            return "Send legal notice\nGather evidence\nFile civil suit\nSeek legal advice\nConsider mediation"
        elif any(word in title_lower for word in ['tax', 'revenue', 'customs']):
            return "File return/declaration\nGather supporting documents\nRespond to notices\nSeek legal advice\nAppeal if necessary"
        elif any(word in title_lower for word in ['banking', 'finance', 'companies']):
            return "File application/complaint\nGather financial documents\nRespond to notices\nSeek legal advice\nAppeal if necessary"
        else:
            return "Consult legal expert\nGather relevant documents\nFile appropriate application\nSeek legal advice\nFollow legal procedures"