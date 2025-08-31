import re
import hashlib
import time
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from django.db import transaction
from django.db.models import Q

from ..models import (
    Case, Document, DocumentText, Term, TermOccurrence, 
    VocabularyProcessingLog, UnifiedCaseView
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTerm:
    """Represents an extracted term with its metadata"""
    type: str
    canonical: str
    surface: str
    start_char: int
    end_char: int
    confidence: float
    source_rule: str
    statute_code: Optional[str] = None
    section_num: Optional[str] = None


class VocabularyExtractor:
    """High-precision legal vocabulary extraction system"""
    
    def __init__(self, rules_version: str = "1.0", min_confidence: float = 0.85):
        self.rules_version = rules_version
        self.min_confidence = min_confidence
        
        # Gazetteers for normalization
        self.court_gazetteer = {
            'supreme court': 'SC',
            'federal shariat court': 'FSC',
            'islamabad high court': 'IHC',
            'lahore high court': 'LHC',
            'sindh high court': 'SHC',
            'balochistan high court': 'BHC',
            'peshawar high court': 'PHC',
            'federal court': 'FC',
            'high court': 'HC',
        }
        
        self.judge_honorifics = {
            'honorable', 'honourable', 'hon', 'mr', 'mrs', 'ms', 'dr', 'professor', 'prof',
            'chief justice', 'justice', 'judge', 'acting chief justice', 'senior judge'
        }
        
        # Statute codes mapping
        self.statute_codes = {
            'ppc': 'Pakistan Penal Code',
            'crpc': 'Code of Criminal Procedure',
            'cpc': 'Code of Civil Procedure',
            'qso': 'Qanun-e-Shahadat Order',
            'constitution': 'Constitution of Pakistan',
            'constitutional': 'Constitution of Pakistan',
            'const': 'Constitution of Pakistan',
        }
        
        # Compile regex patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns for extraction"""
        
        # Section + Statute patterns (with ±40 character window)
        self.section_patterns = [
            # PPC sections: section 302-b, s.302-b, etc.
            r'(?:section|s\.)\s*(\d+[a-z]?)\s*(?:of\s+)?(?:the\s+)?(?:Pakistan\s+Penal\s+Code|PPC)',
            r'(?:Pakistan\s+Penal\s+Code|PPC)\s+(?:section|s\.)\s*(\d+[a-z]?)',
            
            # CrPC sections: section 497, s.497, etc.
            r'(?:section|s\.)\s*(\d+[a-z]?)\s*(?:of\s+)?(?:the\s+)?(?:Code\s+of\s+Criminal\s+Procedure|CrPC)',
            r'(?:Code\s+of\s+Criminal\s+Procedure|CrPC)\s+(?:section|s\.)\s*(\d+[a-z]?)',
            
            # CPC sections: section 151, s.151, etc.
            r'(?:section|s\.)\s*(\d+[a-z]?)\s*(?:of\s+)?(?:the\s+)?(?:Code\s+of\s+Civil\s+Procedure|CPC)',
            r'(?:Code\s+of\s+Civil\s+Procedure|CPC)\s+(?:section|s\.)\s*(\d+[a-z]?)',
            
            # QSO sections: section 17, s.17, etc.
            r'(?:section|s\.)\s*(\d+[a-z]?)\s*(?:of\s+)?(?:the\s+)?(?:Qanun-e-Shahadat\s+Order|QSO)',
            r'(?:Qanun-e-Shahadat\s+Order|QSO)\s+(?:section|s\.)\s*(\d+[a-z]?)',
        ]
        
        # Case citation patterns
        self.citation_patterns = [
            # PLD citations: PLD 2019 SC 123, PLD 2019 Lahore 456, etc.
            r'(PLD|MLD|CLC|SCMR|YLR)\s+(\d{4})\s+(SC|FSC|IHC|LHC|SHC|BHC|PHC|FC|HC)\s+(\d+)',
            # Alternative format: PLD 2019 Supreme Court 123
            r'(PLD|MLD|CLC|SCMR|YLR)\s+(\d{4})\s+(Supreme\s+Court|Federal\s+Shariat\s+Court|Islamabad\s+High\s+Court|Lahore\s+High\s+Court|Sindh\s+High\s+Court|Balochistan\s+High\s+Court|Peshawar\s+High\s+Court|Federal\s+Court|High\s+Court)\s+(\d+)',
        ]
        
        # Judge name patterns
        self.judge_patterns = [
            # Honorable Justice Name, Hon. Justice Name, etc.
            r'(?:Honorable|Honourable|Hon\.)\s+(?:Justice|Chief\s+Justice|Acting\s+Chief\s+Justice)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            # Justice Name, Chief Justice Name, etc.
            r'(?:Justice|Chief\s+Justice|Acting\s+Chief\s+Justice)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            # Mr. Justice Name, Dr. Justice Name, etc.
            r'(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+(?:Justice|Chief\s+Justice)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        # Compile all patterns
        self.compiled_section_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.section_patterns]
        self.compiled_citation_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.citation_patterns]
        self.compiled_judge_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.judge_patterns]
    
    def extract_from_unified_views(self, only_new: bool = True) -> Dict:
        """Extract vocabulary from unified case views"""
        logger.info(f"Starting vocabulary extraction with rules version {self.rules_version}")
        
        # Get cases to process
        queryset = Case.objects.all()
        if only_new:
            # Skip cases already processed with current rules version
            processed_cases = VocabularyProcessingLog.objects.filter(
                rules_version=self.rules_version
            ).values_list('case_id', flat=True)
            queryset = queryset.exclude(id__in=processed_cases)
        
        total_cases = queryset.count()
        logger.info(f"Processing {total_cases} cases for vocabulary extraction")
        
        stats = {
            'total_cases': total_cases,
            'processed_cases': 0,
            'skipped_cases': 0,
            'total_terms': 0,
            'errors': [],
            'processing_time': 0.0
        }
        
        start_time = time.time()
        
        for case in queryset:
            try:
                case_stats = self._process_case(case)
                stats['processed_cases'] += 1
                stats['total_terms'] += case_stats['terms_extracted']
                
                if case_stats['skipped']:
                    stats['skipped_cases'] += 1
                    
            except Exception as e:
                error_msg = f"Error processing case {case.case_number}: {str(e)}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        stats['processing_time'] = time.time() - start_time
        logger.info(f"Vocabulary extraction completed: {stats}")
        
        return stats
    
    def _process_case(self, case: Case) -> Dict:
        """Process a single case for vocabulary extraction"""
        
        # Get text from unified view or fallback to document texts
        text, document = self._get_case_text(case)
        
        if not text:
            return {'terms_extracted': 0, 'skipped': True}
        
        # Check if already processed (idempotency)
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        existing_log = VocabularyProcessingLog.objects.filter(
            rules_version=self.rules_version,
            text_hash=text_hash,
            case=case,
            document=document
        ).first()
        
        if existing_log:
            logger.debug(f"Case {case.case_number} already processed with current rules version")
            return {'terms_extracted': existing_log.terms_extracted, 'skipped': True}
        
        # Extract terms
        start_time = time.time()
        extracted_terms = self._extract_terms_from_text(text, case)
        processing_time = time.time() - start_time
        
        # Store terms and occurrences
        terms_stored = self._store_terms_and_occurrences(extracted_terms, case, document, text)
        
        # Log processing
        VocabularyProcessingLog.objects.create(
            rules_version=self.rules_version,
            text_hash=text_hash,
            case=case,
            document=document,
            terms_extracted=terms_stored,
            processing_time=processing_time,
            is_successful=True
        )
        
        return {'terms_extracted': terms_stored, 'skipped': False}
    
    def _get_case_text(self, case: Case) -> Tuple[Optional[str], Optional[Document]]:
        """Get comprehensive text from unified view or fallback to document texts"""
        
        # Try unified view first (comprehensive data source)
        try:
            unified_view = UnifiedCaseView.objects.get(case=case)
            return self._build_comprehensive_text(unified_view), None
        except UnifiedCaseView.DoesNotExist:
            pass
        
        # Fallback to document texts
        document_texts = DocumentText.objects.filter(
            document__case_documents__case=case,
            is_cleaned=True
        ).exclude(clean_text='').order_by('document_id', 'page_number')
        
        if not document_texts.exists():
            return None, None
        
        # Concatenate all clean text
        text_parts = []
        document = None
        
        for doc_text in document_texts:
            if doc_text.clean_text:
                text_parts.append(doc_text.clean_text)
                if not document:
                    document = doc_text.document
        
        return '\n\n--- Page Break ---\n\n'.join(text_parts), document
    
    def _build_comprehensive_text(self, unified_view: UnifiedCaseView) -> str:
        """Build comprehensive text from all available data in unified view"""
        text_parts = []
        
        # 1. PDF Content (Primary source)
        if unified_view.pdf_content_summary and 'complete_pdf_content' in unified_view.pdf_content_summary:
            pdf_content = unified_view.pdf_content_summary['complete_pdf_content']
            if pdf_content:
                text_parts.append(f"=== PDF CONTENT ===\n{pdf_content}")
        
        # 2. Case Metadata (Structured data)
        if unified_view.case_metadata:
            metadata = unified_view.case_metadata
            
            # Basic case info
            basic_info = metadata.get('basic_info', {})
            if basic_info:
                basic_text = []
                for key, value in basic_info.items():
                    if value:
                        basic_text.append(f"{key.replace('_', ' ').title()}: {value}")
                if basic_text:
                    text_parts.append(f"=== CASE INFO ===\n{'\n'.join(basic_text)}")
            
            # Case details (rich source for legal terms)
            case_detail = metadata.get('case_detail', {})
            if case_detail:
                detail_text = []
                for key, value in case_detail.items():
                    if value:
                        detail_text.append(f"{key.replace('_', ' ').title()}: {value}")
                if detail_text:
                    text_parts.append(f"=== CASE DETAILS ===\n{'\n'.join(detail_text)}")
            
            # Orders data (excellent source for legal terminology)
            orders = metadata.get('orders', [])
            if orders:
                orders_text = []
                for i, order in enumerate(orders, 1):
                    order_parts = []
                    for key, value in order.items():
                        if value and key not in ['view_links']:
                            order_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                    if order_parts:
                        orders_text.append(f"Order {i}:\n" + '\n'.join(order_parts))
                if orders_text:
                    text_parts.append(f"=== ORDERS ===\n{'\n\n'.join(orders_text)}")
            
            # Comments data (additional legal context)
            comments = metadata.get('comments', [])
            if comments:
                comments_text = []
                for i, comment in enumerate(comments, 1):
                    comment_parts = []
                    for key, value in comment.items():
                        if value and key not in ['view_links']:
                            comment_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                    if comment_parts:
                        comments_text.append(f"Comment {i}:\n" + '\n'.join(comment_parts))
                if comments_text:
                    text_parts.append(f"=== COMMENTS ===\n{'\n\n'.join(comments_text)}")
            
            # Case CMs data
            case_cms = metadata.get('case_cms', [])
            if case_cms:
                cms_text = []
                for i, cm in enumerate(case_cms, 1):
                    cm_parts = []
                    for key, value in cm.items():
                        if value:
                            cm_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                    if cm_parts:
                        cms_text.append(f"CM {i}:\n" + '\n'.join(cm_parts))
                if cms_text:
                    text_parts.append(f"=== CASE CMS ===\n{'\n\n'.join(cms_text)}")
            
            # Parties data (for names, advocates)
            parties = metadata.get('parties', [])
            if parties:
                parties_text = []
                for party in parties:
                    party_parts = []
                    for key, value in party.items():
                        if value:
                            party_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                    if party_parts:
                        parties_text.append("Party: " + ' | '.join(party_parts))
                if parties_text:
                    text_parts.append(f"=== PARTIES ===\n{'\n'.join(parties_text)}")
        
        return '\n\n'.join(text_parts) if text_parts else ""
    
    def _extract_terms_from_text(self, text: str, case: Case) -> List[ExtractedTerm]:
        """Extract all terms from comprehensive text using various patterns"""
        extracted_terms = []
        
        # Extract sections and statutes
        sections = self._extract_sections_and_statutes(text)
        extracted_terms.extend(sections)
        
        # Extract case citations
        citations = self._extract_case_citations(text)
        extracted_terms.extend(citations)
        
        # Extract courts
        courts = self._extract_courts(text, case)
        extracted_terms.extend(courts)
        
        # Extract judges
        judges = self._extract_judges(text)
        extracted_terms.extend(judges)
        
        # Extract advocates and parties from structured data
        advocates = self._extract_advocates_and_parties(text)
        extracted_terms.extend(advocates)
        
        # Extract case types
        case_types = self._extract_case_types(text, case)
        extracted_terms.extend(case_types)
        
        # Extract years
        years = self._extract_years(text, case)
        extracted_terms.extend(years)
        
        # Extract status
        statuses = self._extract_status(text, case)
        extracted_terms.extend(statuses)
        
        # Extract bench types
        bench_types = self._extract_bench_types(text)
        extracted_terms.extend(bench_types)
        
        # Extract appeals
        appeals = self._extract_appeals(text)
        extracted_terms.extend(appeals)
        
        # Extract petitioners
        petitioners = self._extract_petitioners(text, case)
        extracted_terms.extend(petitioners)
        
        # Extract legal issues
        legal_issues = self._extract_legal_issues(text)
        extracted_terms.extend(legal_issues)
        
        return extracted_terms
    
    def _extract_sections_and_statutes(self, text: str) -> List[ExtractedTerm]:
        """Extract sections and statutes with ±40 character window"""
        terms = []
        
        for pattern in self.compiled_section_patterns:
            for match in pattern.finditer(text):
                section_num = match.group(1)
                statute_code = self._identify_statute_code(match.group(0))
                
                # Check ±40 character window for statute reference
                start_pos = max(0, match.start() - 40)
                end_pos = min(len(text), match.end() + 40)
                context = text[start_pos:end_pos]
                
                # Look for statute code in context
                if not statute_code:
                    statute_code = self._find_statute_in_context(context)
                
                if statute_code:
                    canonical = f"{statute_code}:{section_num}"
                    confidence = self._calculate_section_confidence(match.group(0), context)
                    
                    terms.append(ExtractedTerm(
                        type='section',
                        canonical=canonical,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=confidence,
                        source_rule='section_statute_pattern',
                        statute_code=statute_code,
                        section_num=section_num
                    ))
        
        return terms
    
    def _extract_case_citations(self, text: str) -> List[ExtractedTerm]:
        """Extract case citations matching PLD|MLD|CLC|SCMR|YLR patterns"""
        terms = []
        
        for pattern in self.compiled_citation_patterns:
            for match in pattern.finditer(text):
                reporter = match.group(1)
                year = match.group(2)
                court = match.group(3)
                page = match.group(4)
                
                # Normalize court code
                court_code = self._normalize_court(court)
                
                canonical = f"{reporter}:{year}:{court_code}:{page}"
                confidence = self._calculate_citation_confidence(match.group(0))
                
                terms.append(ExtractedTerm(
                    type='citation',
                    canonical=canonical,
                    surface=match.group(0),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=confidence,
                    source_rule='case_citation_pattern'
                ))
        
        return terms
    
    def _extract_courts(self, text: str, case: Case) -> List[ExtractedTerm]:
        """Extract court names from comprehensive data sources"""
        terms = []
        
        # 1. Use court from case if available (highest confidence)
        if case.court and case.court.name:
            court_name = case.court.name.strip()
            if court_name:
                canonical = self._normalize_court(court_name)
                confidence = 1.0  # Highest confidence for structured data
                
                terms.append(ExtractedTerm(
                    type='court',
                    canonical=canonical,
                    surface=court_name,
                    start_char=0,  # Not from text, so use 0
                    end_char=0,
                    confidence=confidence,
                    source_rule='unified_view_court'
                ))
        
        # 2. Extract courts from comprehensive text using gazetteer
        for court_name, court_code in self.court_gazetteer.items():
            pattern = re.compile(rf'\b{re.escape(court_name)}\b', re.IGNORECASE)
            for match in pattern.finditer(text):
                confidence = self._calculate_court_confidence(match.group(0))
                
                terms.append(ExtractedTerm(
                    type='court',
                    canonical=court_code,
                    surface=match.group(0),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=confidence,
                    source_rule='court_gazetteer'
                ))
        
        return terms
    
    def _extract_judges(self, text: str) -> List[ExtractedTerm]:
        """Extract judge names and normalize via gazetteer"""
        terms = []
        
        for pattern in self.compiled_judge_patterns:
            for match in pattern.finditer(text):
                judge_name = match.group(1).strip()
                if judge_name:
                    canonical = self._normalize_judge_name(judge_name)
                    confidence = self._calculate_judge_confidence(match.group(0))
                    
                    terms.append(ExtractedTerm(
                        type='judge',
                        canonical=canonical,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=confidence,
                        source_rule='judge_pattern'
                    ))
        
        return terms
    
    def _extract_advocates_and_parties(self, text: str) -> List[ExtractedTerm]:
        """Extract advocates and parties from structured data"""
        terms = []
        
        # Patterns for advocates and parties
        advocate_patterns = [
            r'Advocates Petitioner:\s*([^,\n]+)',
            r'Advocates Respondent:\s*([^,\n]+)',
            r'Advocate:\s*([^,\n]+)',
            r'Counsel:\s*([^,\n]+)',
            r'Attorney:\s*([^,\n]+)',
        ]
        
        party_patterns = [
            r'Party Name:\s*([^,\n]+)',
            r'Petitioner:\s*([^,\n]+)',
            r'Respondent:\s*([^,\n]+)',
            r'Applicant:\s*([^,\n]+)',
            r'Defendant:\s*([^,\n]+)',
        ]
        
        # Extract advocates
        for pattern in advocate_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                advocate_name = match.group(1).strip()
                if advocate_name and len(advocate_name) > 2:
                    canonical = self._normalize_person_name(advocate_name)
                    confidence = self._calculate_advocate_confidence(match.group(0))
                    
                    terms.append(ExtractedTerm(
                        type='advocate',
                        canonical=canonical,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=confidence,
                        source_rule='advocate_pattern'
                    ))
        
        # Extract parties
        for pattern in party_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                party_name = match.group(1).strip()
                if party_name and len(party_name) > 2:
                    canonical = self._normalize_person_name(party_name)
                    confidence = self._calculate_party_confidence(match.group(0))
                    
                    terms.append(ExtractedTerm(
                        type='party',
                        canonical=canonical,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=confidence,
                        source_rule='party_pattern'
                    ))
        
        return terms
    
    def _identify_statute_code(self, text: str) -> Optional[str]:
        """Identify statute code from text"""
        text_lower = text.lower()
        
        if 'pakistan penal code' in text_lower or 'ppc' in text_lower:
            return 'ppc'
        elif 'code of criminal procedure' in text_lower or 'crpc' in text_lower:
            return 'crpc'
        elif 'code of civil procedure' in text_lower or 'cpc' in text_lower:
            return 'cpc'
        elif 'qanun-e-shahadat order' in text_lower or 'qso' in text_lower:
            return 'qso'
        
        return None
    
    def _find_statute_in_context(self, context: str) -> Optional[str]:
        """Find statute code in ±40 character context"""
        context_lower = context.lower()
        
        for code, full_name in self.statute_codes.items():
            if code in context_lower or full_name.lower() in context_lower:
                return code
        
        return None
    
    def _normalize_court(self, court_name: str) -> str:
        """Normalize court name using gazetteer"""
        court_lower = court_name.lower().strip()
        
        for name, code in self.court_gazetteer.items():
            if name in court_lower:
                return code
        
        # Return original if no match found
        return court_name.upper()
    
    def _normalize_judge_name(self, judge_name: str) -> str:
        """Normalize judge name by stripping honorifics"""
        words = judge_name.split()
        normalized_words = []
        
        for word in words:
            if word.lower() not in self.judge_honorifics:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def _normalize_person_name(self, person_name: str) -> str:
        """Normalize person name (advocate, party) by cleaning"""
        # Remove common prefixes/suffixes
        name = person_name.strip()
        
        # Remove common legal prefixes
        prefixes_to_remove = ['mr', 'mrs', 'ms', 'dr', 'adv', 'advocate', 'counsel', 'attorney']
        words = name.split()
        cleaned_words = []
        
        for word in words:
            if word.lower() not in prefixes_to_remove:
                cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    def _calculate_section_confidence(self, match_text: str, context: str) -> float:
        """Calculate confidence for section extraction"""
        confidence = 0.8  # Base confidence
        
        # Boost confidence if statute code is found in context
        if self._find_statute_in_context(context):
            confidence += 0.1
        
        # Boost confidence for exact section patterns
        if re.search(r'section\s+\d+[a-z]?', match_text, re.IGNORECASE):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _calculate_citation_confidence(self, match_text: str) -> float:
        """Calculate confidence for citation extraction"""
        confidence = 0.9  # High base confidence for citations
        
        # Boost confidence for standard format
        if re.match(r'^[A-Z]{3,4}\s+\d{4}\s+[A-Z]+\s+\d+$', match_text):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _extract_case_types(self, text: str, case: Case) -> List[ExtractedTerm]:
        """Extract case types from case data and text"""
        terms = []
        
        # Extract from case title and description
        case_type_patterns = [
            r'(?:case\s+type|type\s+of\s+case):\s*([^,\n]+)',
            r'(?:writ\s+petition|civil\s+petition|criminal\s+petition|constitutional\s+petition)',
            r'(?:appeal|review|revision|reference)',
            r'(?:suo\s+moto|suo\s+motu)',
            r'(?:constitutional\s+petition|writ\s+petition)',
        ]
        
        for pattern in case_type_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                case_type = match.group(1) if match.groups() else match.group(0)
                case_type = self._normalize_case_type(case_type)
                
                if case_type:
                    terms.append(ExtractedTerm(
                        type='case_type',
                        canonical=case_type,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=self._calculate_case_type_confidence(match.group(0)),
                        source_rule='case_type_pattern'
                    ))
        
        return terms
    
    def _extract_years(self, text: str, case: Case) -> List[ExtractedTerm]:
        """Extract years from case data and text"""
        terms = []
        
        # Extract from case institution date
        if case.institution_date:
            # Handle both string and datetime objects
            if hasattr(case.institution_date, 'year'):
                year = str(case.institution_date.year)
            else:
                # Try to extract year from string format
                year_match = re.search(r'\b(19|20)\d{2}\b', str(case.institution_date))
                if year_match:
                    year = year_match.group(0)
                else:
                    year = None
            
            if year and 1900 <= int(year) <= 2025:
                terms.append(ExtractedTerm(
                    type='year',
                    canonical=year,
                    surface=year,
                    start_char=0,
                    end_char=len(year),
                    confidence=0.95,
                    source_rule='case_institution_date'
                ))
        
        # Extract years from text (4-digit years)
        year_pattern = r'\b(19|20)\d{2}\b'
        for match in re.finditer(year_pattern, text):
            year = match.group(0)
            # Only add if it's a reasonable year (1900-2025)
            if 1900 <= int(year) <= 2025:
                terms.append(ExtractedTerm(
                    type='year',
                    canonical=year,
                    surface=match.group(0),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=0.9,
                    source_rule='year_pattern'
                ))
        
        return terms
    
    def _extract_status(self, text: str, case: Case) -> List[ExtractedTerm]:
        """Extract case status from case data and text"""
        terms = []
        
        # Extract from case status field
        if case.status:
            status = case.status.strip()
            if status:
                terms.append(ExtractedTerm(
                    type='status',
                    canonical=status,
                    surface=status,
                    start_char=0,
                    end_char=len(status),
                    confidence=0.95,
                    source_rule='case_status_field'
                ))
        
        # Extract status from text
        status_patterns = [
            r'(?:case\s+status|status):\s*([^,\n]+)',
            r'\b(pending|decided|disposed|dismissed|allowed|rejected|withdrawn)\b',
        ]
        
        for pattern in status_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                status = match.group(1) if match.groups() else match.group(0)
                status = self._normalize_status(status)
                
                if status:
                    terms.append(ExtractedTerm(
                        type='status',
                        canonical=status,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=self._calculate_status_confidence(match.group(0)),
                        source_rule='status_pattern'
                    ))
        
        return terms
    
    def _extract_bench_types(self, text: str) -> List[ExtractedTerm]:
        """Extract bench types from text"""
        terms = []
        
        bench_patterns = [
            r'(?:the\s+)?(?:honorable|honourable)\s+(?:chief\s+)?justice',
            r'(?:acting\s+)?(?:chief\s+)?justice',
            r'(?:senior\s+)?(?:puisne\s+)?judge',
            r'(?:division\s+)?bench',
            r'(?:full\s+)?bench',
            r'(?:constitutional\s+)?bench',
        ]
        
        for pattern in bench_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                bench_type = self._normalize_bench_type(match.group(0))
                
                if bench_type:
                    terms.append(ExtractedTerm(
                        type='bench_type',
                        canonical=bench_type,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=self._calculate_bench_type_confidence(match.group(0)),
                        source_rule='bench_type_pattern'
                    ))
        
        return terms
    
    def _extract_appeals(self, text: str) -> List[ExtractedTerm]:
        """Extract appeal types from text"""
        terms = []
        
        appeal_patterns = [
            r'\b(appeal|review|revision|reference|petition|application)\b',
            r'(?:civil\s+|criminal\s+|constitutional\s+)?(?:appeal|review|revision)',
            r'(?:special\s+)?(?:leave\s+)?(?:to\s+)?(?:appeal|review)',
        ]
        
        for pattern in appeal_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                appeal = self._normalize_appeal(match.group(0))
                
                if appeal:
                    terms.append(ExtractedTerm(
                        type='appeal',
                        canonical=appeal,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=self._calculate_appeal_confidence(match.group(0)),
                        source_rule='appeal_pattern'
                    ))
        
        return terms
    
    def _extract_petitioners(self, text: str, case: Case) -> List[ExtractedTerm]:
        """Extract petitioners from case data and text"""
        terms = []
        
        # Extract from case title (petitioner is usually first)
        if case.case_title:
            # Look for petitioner in case title (before "vs" or "v.")
            title = case.case_title
            vs_pattern = r'\s+(?:vs?\.?|versus)\s+'
            vs_match = re.search(vs_pattern, title, re.IGNORECASE)
            
            if vs_match:
                petitioner = title[:vs_match.start()].strip()
                if petitioner:
                    terms.append(ExtractedTerm(
                        type='petitioner',
                        canonical=petitioner,
                        surface=petitioner,
                        start_char=0,
                        end_char=len(petitioner),
                        confidence=0.9,
                        source_rule='case_title_petitioner'
                    ))
        
        # Extract from text patterns
        petitioner_patterns = [
            r'(?:petitioner|applicant):\s*([^,\n]+)',
            r'(?:petitioner|applicant)\s+([^,\n]+?)(?:\s+vs?\.?|$)',
        ]
        
        for pattern in petitioner_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                petitioner = match.group(1).strip()
                if petitioner:
                    terms.append(ExtractedTerm(
                        type='petitioner',
                        canonical=petitioner,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=self._calculate_petitioner_confidence(match.group(0)),
                        source_rule='petitioner_pattern'
                    ))
        
        return terms
    
    def _extract_legal_issues(self, text: str) -> List[ExtractedTerm]:
        """Extract legal issues from text"""
        terms = []
        
        # Legal issue patterns
        issue_patterns = [
            r'(?:legal\s+)?(?:issue|question):\s*([^,\n]+)',
            r'(?:constitutional\s+)?(?:question|issue)\s+of\s+([^,\n]+)',
            r'\b(constitutional|criminal|civil|administrative|tax|banking|family|property|contract|tort)\b',
            r'(?:matter\s+of|regarding|concerning)\s+([^,\n]+)',
        ]
        
        for pattern in issue_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                issue = match.group(1) if match.groups() else match.group(0)
                issue = self._normalize_legal_issue(issue)
                
                if issue:
                    terms.append(ExtractedTerm(
                        type='legal_issue',
                        canonical=issue,
                        surface=match.group(0),
                        start_char=match.start(),
                        end_char=match.end(),
                        confidence=self._calculate_legal_issue_confidence(match.group(0)),
                        source_rule='legal_issue_pattern'
                    ))
        
        return terms
    
    def _calculate_court_confidence(self, match_text: str) -> float:
        """Calculate confidence for court extraction"""
        confidence = 0.85  # Base confidence
        
        # Boost confidence for exact matches
        if match_text.lower() in self.court_gazetteer:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_judge_confidence(self, match_text: str) -> float:
        """Calculate confidence for judge extraction"""
        confidence = 0.8  # Base confidence
        
        # Boost confidence for honorifics
        if any(honorific in match_text.lower() for honorific in ['justice', 'chief justice']):
            confidence += 0.1
        
        # Boost confidence for proper name format
        if re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', match_text):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _calculate_advocate_confidence(self, match_text: str) -> float:
        """Calculate confidence for advocate extraction"""
        confidence = 0.85  # Base confidence for structured data
        
        # Boost confidence for structured format
        if re.search(r'advocates?\s+(petitioner|respondent):', match_text, re.IGNORECASE):
            confidence += 0.1
        
        # Boost confidence for proper name format
        if re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', match_text):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _calculate_party_confidence(self, match_text: str) -> float:
        """Calculate confidence for party extraction"""
        confidence = 0.85  # Base confidence for structured data
        
        # Boost confidence for structured format
        if re.search(r'(petitioner|respondent|applicant|defendant):', match_text, re.IGNORECASE):
            confidence += 0.1
        
        # Boost confidence for proper name format
        if re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', match_text):
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _calculate_case_type_confidence(self, match_text: str) -> float:
        """Calculate confidence for case type extraction"""
        confidence = 0.85  # Base confidence
        
        # Boost confidence for specific case types
        case_types = ['writ petition', 'civil petition', 'criminal petition', 'constitutional petition', 'appeal', 'review']
        if any(ct in match_text.lower() for ct in case_types):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_status_confidence(self, match_text: str) -> float:
        """Calculate confidence for status extraction"""
        confidence = 0.85  # Base confidence
        
        # Boost confidence for specific statuses
        statuses = ['pending', 'decided', 'disposed', 'dismissed', 'allowed', 'rejected', 'withdrawn']
        if any(status in match_text.lower() for status in statuses):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_bench_type_confidence(self, match_text: str) -> float:
        """Calculate confidence for bench type extraction"""
        confidence = 0.8  # Base confidence
        
        # Boost confidence for specific bench types
        bench_types = ['chief justice', 'justice', 'judge', 'bench']
        if any(bt in match_text.lower() for bt in bench_types):
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def _calculate_appeal_confidence(self, match_text: str) -> float:
        """Calculate confidence for appeal extraction"""
        confidence = 0.85  # Base confidence
        
        # Boost confidence for specific appeal types
        appeal_types = ['appeal', 'review', 'revision', 'reference', 'petition', 'application']
        if any(at in match_text.lower() for at in appeal_types):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_petitioner_confidence(self, match_text: str) -> float:
        """Calculate confidence for petitioner extraction"""
        confidence = 0.8  # Base confidence
        
        # Boost confidence for structured format
        if re.search(r'(petitioner|applicant):', match_text, re.IGNORECASE):
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def _calculate_legal_issue_confidence(self, match_text: str) -> float:
        """Calculate confidence for legal issue extraction"""
        confidence = 0.8  # Base confidence
        
        # Boost confidence for specific legal areas
        legal_areas = ['constitutional', 'criminal', 'civil', 'administrative', 'tax', 'banking', 'family', 'property']
        if any(area in match_text.lower() for area in legal_areas):
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    # Normalization methods for new facet types
    def _normalize_case_type(self, case_type: str) -> str:
        """Normalize case type"""
        case_type = case_type.strip().lower()
        
        # Map variations to standard forms
        case_type_mapping = {
            'writ petition': 'Writ Petition',
            'civil petition': 'Civil Petition',
            'criminal petition': 'Criminal Petition',
            'constitutional petition': 'Constitutional Petition',
            'appeal': 'Appeal',
            'review': 'Review',
            'revision': 'Revision',
            'reference': 'Reference',
            'suo moto': 'Suo Moto',
            'suo motu': 'Suo Moto',
        }
        
        return case_type_mapping.get(case_type, case_type.title())
    
    def _normalize_status(self, status: str) -> str:
        """Normalize case status"""
        status = status.strip().lower()
        
        # Map variations to standard forms
        status_mapping = {
            'pending': 'Pending',
            'decided': 'Decided',
            'disposed': 'Disposed',
            'dismissed': 'Dismissed',
            'allowed': 'Allowed',
            'rejected': 'Rejected',
            'withdrawn': 'Withdrawn',
        }
        
        return status_mapping.get(status, status.title())
    
    def _normalize_bench_type(self, bench_type: str) -> str:
        """Normalize bench type"""
        bench_type = bench_type.strip().lower()
        
        # Map variations to standard forms
        bench_mapping = {
            'chief justice': 'Chief Justice',
            'acting chief justice': 'Acting Chief Justice',
            'justice': 'Justice',
            'senior judge': 'Senior Judge',
            'puisne judge': 'Puisne Judge',
            'division bench': 'Division Bench',
            'full bench': 'Full Bench',
            'constitutional bench': 'Constitutional Bench',
        }
        
        return bench_mapping.get(bench_type, bench_type.title())
    
    def _normalize_appeal(self, appeal: str) -> str:
        """Normalize appeal type"""
        appeal = appeal.strip().lower()
        
        # Map variations to standard forms
        appeal_mapping = {
            'appeal': 'Appeal',
            'review': 'Review',
            'revision': 'Revision',
            'reference': 'Reference',
            'petition': 'Petition',
            'application': 'Application',
            'civil appeal': 'Civil Appeal',
            'criminal appeal': 'Criminal Appeal',
            'constitutional appeal': 'Constitutional Appeal',
        }
        
        return appeal_mapping.get(appeal, appeal.title())
    
    def _normalize_legal_issue(self, issue: str) -> str:
        """Normalize legal issue"""
        issue = issue.strip().lower()
        
        # Map variations to standard forms
        issue_mapping = {
            'constitutional': 'Constitutional',
            'criminal': 'Criminal',
            'civil': 'Civil',
            'administrative': 'Administrative',
            'tax': 'Tax',
            'banking': 'Banking',
            'family': 'Family',
            'property': 'Property',
            'contract': 'Contract',
            'tort': 'Tort',
        }
        
        return issue_mapping.get(issue, issue.title())
    
    @transaction.atomic
    def _store_terms_and_occurrences(self, extracted_terms: List[ExtractedTerm], 
                                   case: Case, document: Optional[Document], text: str) -> int:
        """Store extracted terms and their occurrences in database"""
        terms_stored = 0
        
        for term_data in extracted_terms:
            # Filter by minimum confidence
            if term_data.confidence < self.min_confidence:
                continue
            
            # Get or create term
            term, created = Term.objects.get_or_create(
                type=term_data.type,
                canonical=term_data.canonical,
                defaults={
                    'statute_code': term_data.statute_code,
                    'section_num': term_data.section_num,
                }
            )
            
            # Update occurrence count
            if not created:
                term.occurrence_count += 1
                term.save()
            
            # Create occurrence record
            occurrence, created = TermOccurrence.objects.get_or_create(
                term=term,
                case=case,
                start_char=term_data.start_char,
                end_char=term_data.end_char,
                defaults={
                    'document': document,
                    'surface': term_data.surface,
                    'confidence': term_data.confidence,
                    'source_rule': term_data.source_rule,
                    'rules_version': self.rules_version,
                }
            )
            
            if created:
                terms_stored += 1
        
        return terms_stored
    
    def validate_extraction(self, sample_size: int = 25) -> Dict:
        """Validate extracted vocabulary with sample data"""
        logger.info(f"Validating vocabulary extraction with sample size {sample_size}")
        
        # Get sample of recent extractions
        recent_occurrences = TermOccurrence.objects.filter(
            rules_version=self.rules_version
        ).order_by('-created_at')[:sample_size]
        
        validation_results = {
            'total_occurrences': recent_occurrences.count(),
            'by_type': {},
            'top_sections': [],
            'mean_confidence': 0.0,
            'validation_checks': {
                'spans_in_range': True,
                'sections_have_statute': True,
                'no_duplicates': True,
            },
            'issues': []
        }
        
        if not recent_occurrences.exists():
            return validation_results
        
        # Calculate statistics
        total_confidence = 0.0
        type_counts = {}
        section_terms = []
        
        for occurrence in recent_occurrences:
            # Type statistics
            term_type = occurrence.term.type
            type_counts[term_type] = type_counts.get(term_type, 0) + 1
            
            # Confidence statistics
            total_confidence += occurrence.confidence
            
            # Section statistics
            if term_type == 'section':
                section_terms.append(occurrence.term.canonical)
            
            # Validation checks
            if occurrence.start_char < 0 or occurrence.end_char < occurrence.start_char:
                validation_results['validation_checks']['spans_in_range'] = False
                validation_results['issues'].append(f"Invalid span for occurrence {occurrence.id}")
            
            if term_type == 'section' and not occurrence.term.statute_code:
                validation_results['validation_checks']['sections_have_statute'] = False
                validation_results['issues'].append(f"Section {occurrence.term.canonical} missing statute code")
        
        # Calculate mean confidence
        validation_results['mean_confidence'] = total_confidence / recent_occurrences.count()
        
        # Get top sections
        from collections import Counter
        section_counter = Counter(section_terms)
        validation_results['top_sections'] = section_counter.most_common(10)
        
        # Type breakdown
        validation_results['by_type'] = type_counts
        
        # Check for duplicates
        from django.db import models
        duplicate_check = TermOccurrence.objects.filter(
            rules_version=self.rules_version
        ).values('term', 'case', 'start_char', 'end_char').annotate(
            count=models.Count('id')
        ).filter(count__gt=1)
        
        if duplicate_check.exists():
            validation_results['validation_checks']['no_duplicates'] = False
            validation_results['issues'].append(f"Found {duplicate_check.count()} duplicate occurrences")
        
        logger.info(f"Validation completed: {validation_results}")
        return validation_results
