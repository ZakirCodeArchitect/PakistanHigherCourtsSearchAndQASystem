"""
Data Cleaning Service for Case Data
Handles cleaning and normalization of scraped case data to improve quality.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
import logging

from ..models import Case, OrdersData, CommentsData, CaseDetail, PartiesDetailData

logger = logging.getLogger(__name__)


class DataCleaner:
    """Comprehensive data cleaning service for case data"""
    
    def __init__(self):
        # Common noise patterns
        self.noise_patterns = {
            'placeholder_values': r'\b(N/A|NA|None|null|undefined|NULL|NONE)\b',
            'html_tags': r'<[^>]+>',
            'excessive_spaces': r'\s{3,}',
            'repeated_chars': r'(.)\1{3,}',  # 4 or more repeated characters
            'leading_trailing_spaces': r'^\s+|\s+$',
            'multiple_newlines': r'\n{3,}',
            'multiple_dots': r'\.{3,}',
            'multiple_dashes': r'-{3,}',
        }
        
        # Text normalization patterns
        self.normalization_patterns = {
            'normalize_whitespace': r'\s+',
            'fix_hyphenation': r'(\w+)-\s*\n\s*(\w+)',
            'remove_extra_punctuation': r'([.!?])\1+',
            'fix_quotes': r'["""'']',
            'fix_dashes': r'[–—]',
        }
        
        # Legal text specific patterns
        self.legal_patterns = {
            'court_titles': [
                r'The Honorable Chief Justice',
                r'Honorable Chief Justice',
                r'Chief Justice',
                r'Justice',
                r'Judge',
            ],
            'case_types': [
                r'Writ Petition',
                r'Civil Appeal',
                r'Criminal Appeal',
                r'Constitutional Petition',
                r'Civil Revision',
                r'Criminal Revision',
                r'Civil Misc\.',
                r'Criminal Misc\.',
                r'Tax Appeal',
                r'Service Appeal',
                r'Customs Appeal',
                r'Income Tax Appeal',
                r'Sales Tax Appeal',
                r'Federal Excise Appeal',
                r'Anti-Narcotics Appeal',
                r'Anti-Terrorism Appeal',
                r'Family Appeal',
                r'Rent Appeal',
                r'Labour Appeal',
                r'Insurance Appeal',
            ],
            'status_values': [
                r'Pending',
                r'Disposed',
                r'Dismissed',
                r'Allowed',
                r'Rejected',
                r'Withdrawn',
                r'Adjourned',
                r'Fixed',
                r'Consigned',
            ]
        }

    def clean_all_data(self, force: bool = False) -> Dict[str, int]:
        """Clean all case data in the database"""
        stats = {
            'cases_cleaned': 0,
            'orders_cleaned': 0,
            'comments_cleaned': 0,
            'case_details_cleaned': 0,
            'parties_cleaned': 0,
            'errors': []
        }
        
        try:
            with transaction.atomic():
                # Clean cases
                stats['cases_cleaned'] = self._clean_cases(force)
                
                # Clean orders data
                stats['orders_cleaned'] = self._clean_orders_data(force)
                
                # Clean comments data
                stats['comments_cleaned'] = self._clean_comments_data(force)
                
                # Clean case details
                stats['case_details_cleaned'] = self._clean_case_details(force)
                
                # Clean parties data
                stats['parties_cleaned'] = self._clean_parties_data(force)
                
        except Exception as e:
            error_msg = f"Error during data cleaning: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats

    def _clean_cases(self, force: bool = False) -> int:
        """Clean case data"""
        cleaned_count = 0
        cases = Case.objects.all()
        
        for case in cases:
            try:
                original_data = {
                    'case_number': case.case_number,
                    'case_title': case.case_title,
                    'status': case.status,
                    'bench': case.bench,
                }
                
                # Clean individual fields
                case.case_number = self._clean_case_number(case.case_number)
                case.case_title = self._clean_case_title(case.case_title)
                case.status = self._normalize_status(case.status)
                case.bench = self._normalize_bench(case.bench)
                
                # Check if any changes were made
                if (original_data['case_number'] != case.case_number or
                    original_data['case_title'] != case.case_title or
                    original_data['status'] != case.status or
                    original_data['bench'] != case.bench):
                    
                    case.updated_at = timezone.now()
                    case.save()
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning case {case.id}: {str(e)}")
        
        return cleaned_count

    def _clean_orders_data(self, force: bool = False) -> int:
        """Clean orders data"""
        cleaned_count = 0
        orders = OrdersData.objects.all()
        
        for order in orders:
            try:
                original_data = {
                    'sr_number': order.sr_number,
                    'hearing_date': order.hearing_date,
                    'bench': order.bench,
                    'short_order': order.short_order,
                    'disposal_date': order.disposal_date,
                }
                
                # Clean individual fields
                order.sr_number = self._clean_sr_number(order.sr_number)
                order.hearing_date = self._normalize_date(order.hearing_date)
                order.bench = self._normalize_bench(order.bench)
                order.short_order = self._clean_legal_text(order.short_order)
                order.disposal_date = self._normalize_date(order.disposal_date)
                
                # Check if any changes were made
                if (original_data['sr_number'] != order.sr_number or
                    original_data['hearing_date'] != order.hearing_date or
                    original_data['bench'] != order.bench or
                    original_data['short_order'] != order.short_order or
                    original_data['disposal_date'] != order.disposal_date):
                    
                    order.save()
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning order {order.id}: {str(e)}")
        
        return cleaned_count

    def _clean_comments_data(self, force: bool = False) -> int:
        """Clean comments data"""
        cleaned_count = 0
        comments = CommentsData.objects.all()
        
        for comment in comments:
            try:
                original_data = {
                    'case_title': comment.case_title,
                    'parties': comment.parties,
                    'description': comment.description,
                    'doc_type': comment.doc_type,
                }
                
                # Clean individual fields
                comment.case_title = self._clean_case_title(comment.case_title)
                comment.parties = self._clean_parties_text(comment.parties)
                comment.description = self._clean_legal_text(comment.description)
                comment.doc_type = self._normalize_doc_type(comment.doc_type)
                
                # Check if any changes were made
                if (original_data['case_title'] != comment.case_title or
                    original_data['parties'] != comment.parties or
                    original_data['description'] != comment.description or
                    original_data['doc_type'] != comment.doc_type):
                    
                    comment.save()
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning comment {comment.id}: {str(e)}")
        
        return cleaned_count

    def _clean_case_details(self, force: bool = False) -> int:
        """Clean case details data"""
        cleaned_count = 0
        case_details = CaseDetail.objects.all()
        
        for detail in case_details:
            try:
                original_data = {
                    'case_status': detail.case_status,
                    'case_stage': detail.case_stage,
                    'short_order': detail.short_order,
                    'case_title_detailed': detail.case_title_detailed,
                    'advocates_petitioner': detail.advocates_petitioner,
                    'advocates_respondent': detail.advocates_respondent,
                }
                
                # Clean individual fields
                detail.case_status = self._normalize_status(detail.case_status)
                detail.case_stage = self._clean_legal_text(detail.case_stage)
                detail.short_order = self._clean_legal_text(detail.short_order)
                detail.case_title_detailed = self._clean_case_title(detail.case_title_detailed)
                detail.advocates_petitioner = self._clean_advocates_text(detail.advocates_petitioner)
                detail.advocates_respondent = self._clean_advocates_text(detail.advocates_respondent)
                
                # Check if any changes were made
                if (original_data['case_status'] != detail.case_status or
                    original_data['case_stage'] != detail.case_stage or
                    original_data['short_order'] != detail.short_order or
                    original_data['case_title_detailed'] != detail.case_title_detailed or
                    original_data['advocates_petitioner'] != detail.advocates_petitioner or
                    original_data['advocates_respondent'] != detail.advocates_respondent):
                    
                    detail.save()
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning case detail {detail.id}: {str(e)}")
        
        return cleaned_count

    def _clean_parties_data(self, force: bool = False) -> int:
        """Clean parties data"""
        cleaned_count = 0
        parties = PartiesDetailData.objects.all()
        
        for party in parties:
            try:
                original_data = {
                    'party_name': party.party_name,
                    'party_side': party.party_side,
                }
                
                # Clean individual fields
                party.party_name = self._clean_party_name(party.party_name)
                party.party_side = self._normalize_party_side(party.party_side)
                
                # Check if any changes were made
                if (original_data['party_name'] != party.party_name or
                    original_data['party_side'] != party.party_side):
                    
                    party.save()
                    cleaned_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning party {party.id}: {str(e)}")
        
        return cleaned_count

    # Individual field cleaning methods
    def _clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        if not text:
            return ""
        
        # Remove noise patterns
        for pattern_name, pattern in self.noise_patterns.items():
            if pattern_name == 'placeholder_values':
                # Replace placeholders with empty string
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            elif pattern_name == 'html_tags':
                # Remove HTML tags
                text = re.sub(pattern, '', text)
            elif pattern_name == 'excessive_spaces':
                # Replace with single space
                text = re.sub(pattern, ' ', text)
            elif pattern_name == 'repeated_chars':
                # Replace with single character
                text = re.sub(pattern, r'\1', text)
            elif pattern_name == 'leading_trailing_spaces':
                # Remove leading/trailing spaces
                text = re.sub(pattern, '', text)
            elif pattern_name == 'multiple_newlines':
                # Replace with double newline
                text = re.sub(pattern, '\n\n', text)
            elif pattern_name == 'multiple_dots':
                # Replace with single dot
                text = re.sub(pattern, '.', text)
            elif pattern_name == 'multiple_dashes':
                # Replace with single dash
                text = re.sub(pattern, '-', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize Unicode
        text = unicodedata.normalize('NFKC', text)
        
        return text.strip()

    def _clean_case_number(self, case_number: str) -> str:
        """Clean case number"""
        if not case_number:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(case_number)
        
        # Remove common prefixes/suffixes that might be noise
        cleaned = re.sub(r'^(Case|No|Number|#)\s*', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned

    def _clean_case_title(self, title: str) -> str:
        """Clean case title"""
        if not title:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(title)
        
        # Normalize party separators - first replace dashes with VS
        cleaned = re.sub(r'\s*[-–—]\s*', ' VS ', cleaned)
        
        # Then normalize multiple VS separators to single VS (more robust)
        while re.search(r'\s*VS\s+VS\s*', cleaned):
            cleaned = re.sub(r'\s*VS\s+VS\s*', ' VS ', cleaned)
        cleaned = re.sub(r'\s*VS\s*', ' VS ', cleaned)
        
        # Remove only standalone "etc." suffixes, not "& others" or similar
        cleaned = re.sub(r'\s*etc\.?\s*$', '', cleaned, flags=re.IGNORECASE)
        # But preserve "& others" and similar important information
        if "& others" in cleaned or "and others" in cleaned:
            # Don't remove these as they contain important party information
            pass
        
        return cleaned

    def _clean_legal_text(self, text: str) -> str:
        """Clean legal text (orders, descriptions, etc.)"""
        if not text:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(text)
        
        # Fix common legal abbreviations (more conservative)
        legal_abbreviations = {
            r'\bD&SJ\b': 'District & Sessions Judge',
            r'\bCJ\b': 'Chief Justice',
            # Don't expand single 'J' as it might be part of other words
            r'\bvs\b': 'VS',
            r'\bpet\b': 'Petition',
            r'\bapp\b': 'Appeal',
            r'\brev\b': 'Revision',
            r'\bmisc\b': 'Miscellaneous',
        }
        
        for pattern, replacement in legal_abbreviations.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned

    def _clean_parties_text(self, text: str) -> str:
        """Clean parties text"""
        if not text:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(text)
        
        # Normalize party separators
        cleaned = re.sub(r'\s*[,;]\s*', ', ', cleaned)
        
        return cleaned

    def _clean_party_name(self, name: str) -> str:
        """Clean party name"""
        if not name:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(name)
        
        # Remove common titles
        titles = r'\b(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Adv\.|Advocate)\b'
        cleaned = re.sub(titles, '', cleaned, flags=re.IGNORECASE)
        
        # Remove "The State" variations
        cleaned = re.sub(r'\bThe\s+State\b', 'The State', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def _clean_advocates_text(self, text: str) -> str:
        """Clean advocates text"""
        if not text:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(text)
        
        # Normalize advocate separators
        cleaned = re.sub(r'\s*[,;]\s*', ', ', cleaned)
        
        return cleaned

    def _clean_sr_number(self, sr_number: str) -> str:
        """Clean SR number"""
        if not sr_number:
            return ""
        
        # Basic cleaning
        cleaned = self._clean_text(sr_number)
        
        # Remove non-numeric characters except dots and dashes
        cleaned = re.sub(r'[^\d\.\-]', '', cleaned)
        
        return cleaned

    # Normalization methods
    def _normalize_status(self, status: str) -> str:
        """Normalize case status"""
        if not status:
            return ""
        
        status = status.strip()
        
        # Map common variations to standard values
        status_mapping = {
            'pending': 'Pending',
            'disposed': 'Disposed',
            'dismissed': 'Dismissed',
            'allowed': 'Allowed',
            'rejected': 'Rejected',
            'withdrawn': 'Withdrawn',
            'adjourned': 'Adjourned',
            'fixed': 'Fixed',
            'consigned': 'Consigned',
        }
        
        return status_mapping.get(status.lower(), status)

    def _normalize_bench(self, bench: str) -> str:
        """Normalize bench information"""
        if not bench:
            return ""
        
        bench = bench.strip()
        
        # Map common variations
        bench_mapping = {
            'n/a': 'N/A',
            'the honorable chief justice': 'The Honorable Chief Justice',
            'honorable chief justice': 'The Honorable Chief Justice',
            'chief justice': 'Chief Justice',
        }
        
        return bench_mapping.get(bench.lower(), bench)

    def _normalize_party_side(self, side: str) -> str:
        """Normalize party side"""
        if not side:
            return ""
        
        side = side.strip()
        
        # Map common variations
        side_mapping = {
            'petitioner': 'Petitioner',
            'respondent': 'Respondent',
            'appellant': 'Appellant',
            'defendant': 'Defendant',
            'plaintiff': 'Plaintiff',
        }
        
        return side_mapping.get(side.lower(), side)

    def _normalize_doc_type(self, doc_type: str) -> str:
        """Normalize document type"""
        if not doc_type:
            return ""
        
        doc_type = doc_type.strip()
        
        # Map common variations
        doc_type_mapping = {
            'petition': 'Petition',
            'appeal': 'Appeal',
            'revision': 'Revision',
            'miscellaneous': 'Miscellaneous',
            'misc': 'Miscellaneous',
        }
        
        return doc_type_mapping.get(doc_type.lower(), doc_type)

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date format"""
        if not date_str:
            return ""
        
        date_str = date_str.strip()
        
        # Try to standardize to DD-MM-YYYY format
        # This is a basic implementation - you might want to use dateutil for more robust parsing
        date_patterns = [
            r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.match(pattern, date_str)
            if match:
                if len(match.group(1)) == 4:  # YYYY-MM-DD format
                    year, month, day = match.groups()
                else:  # DD-MM-YYYY format
                    day, month, year = match.groups()
                
                return f"{day.zfill(2)}-{month.zfill(2)}-{year}"
        
        return date_str

    def get_data_quality_score(self, text: str) -> float:
        """Calculate data quality score (0-1)"""
        if not text:
            return 0.0
        
        score = 1.0
        
        # Penalize for noise patterns
        for pattern_name, pattern in self.noise_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                score -= 0.1
        
        # Penalize for very short or very long text
        if len(text) < 5:
            score -= 0.3
        elif len(text) > 1000:
            score -= 0.1
        
        # Penalize for excessive special characters
        special_char_ratio = len(re.findall(r'[^\w\s]', text)) / len(text)
        if special_char_ratio > 0.3:
            score -= 0.2
        
        return max(0.0, score)
