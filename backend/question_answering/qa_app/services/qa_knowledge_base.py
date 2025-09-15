"""
Enhanced Knowledge Base for Question-Answering System
Implements the complete KB architecture specifically for RAG and AI response generation
"""

import os
import re
import json
import hashlib
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from django.db import transaction, connection, models
from django.utils import timezone
from django.conf import settings

from qa_app.models import QAKnowledgeBase, QASession, QAQuery, QAResponse
# Note: Cases models are in search_module, we'll need to import them differently
# from apps.cases.models import Case, Document, DocumentText, UnifiedCaseView

logger = logging.getLogger(__name__)


@dataclass
class QAChunkingConfig:
    """Configuration for QA-specific document chunking"""
    chunk_size: int = 700  # Target 500-900 tokens for AI context
    chunk_overlap: int = 100  # 100-token overlap
    min_chunk_size: int = 200  # Minimum chunk size
    max_chunk_size: int = 1000  # Maximum chunk size
    token_ratio: float = 0.75  # Characters per token ratio
    legal_context_weight: float = 1.2  # Weight for legal context


@dataclass
class QAMetadata:
    """QA-specific metadata for chunks"""
    case_no: str
    court: str
    judges: List[str]
    year: int
    sections: List[str]
    paragraph_no: int
    url: Optional[str] = None
    page: Optional[int] = None
    document_type: str = "judgment"
    content_type: str = "text"
    legal_domain: str = "general"
    ai_context_score: float = 0.0  # Relevance for AI responses


class QALawReferenceNormalizer:
    """Normalizes law references specifically for QA context"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Comprehensive legal abbreviations mapping for Pakistani law
        self.legal_abbreviations = {
            # Core Legal Codes
            'ppc': 'Pakistan Penal Code',
            'crpc': 'Code of Criminal Procedure',
            'cpc': 'Code of Civil Procedure',
            'qso': 'Qanun-e-Shahadat Order',
            'constitution': 'Constitution of Pakistan',
            
            # Legal Procedures
            'fir': 'First Information Report',
            'bail': 'Bail Application',
            'writ': 'Writ Petition',
            'appeal': 'Criminal/Civil Appeal',
            'revision': 'Criminal/Civil Revision',
            'review': 'Review Petition',
            'suo_moto': 'Suo Motu Action',
            
            # Government Agencies
            'fia': 'Federal Investigation Agency',
            'nab': 'National Accountability Bureau',
            'fbr': 'Federal Board of Revenue',
            'secp': 'Securities and Exchange Commission of Pakistan',
            'sbp': 'State Bank of Pakistan',
            'pemra': 'Pakistan Electronic Media Regulatory Authority',
            'pta': 'Pakistan Telecommunication Authority',
            'ogra': 'Oil and Gas Regulatory Authority',
            'nepra': 'National Electric Power Regulatory Authority',
            'psra': 'Pakistan Software Export Board',
            
            # Courts
            'sc': 'Supreme Court of Pakistan',
            'ihc': 'Islamabad High Court',
            'lhc': 'Lahore High Court',
            'shc': 'Sindh High Court',
            'bhc': 'Balochistan High Court',
            'phc': 'Peshawar High Court',
            'fsc': 'Federal Shariat Court',
            'at': 'Appellate Tribunal',
            'cat': 'Customs Appellate Tribunal',
            'sat': 'Securities Appellate Tribunal',
            
            # Legal Publications
            'pld': 'Pakistan Legal Decisions',
            'plj': 'Pakistan Law Journal',
            'mld': 'Monthly Law Digest',
            'ylr': 'Yearly Law Reporter',
            'clj': 'Civil Law Journal',
            'clc': 'Civil Law Cases',
            'scr': 'Supreme Court Reports',
            'hcr': 'High Court Reports',
            
            # Legal Terms
            'art': 'Article',
            's': 'Section',
            'ss': 'Sections',
            'sub_s': 'Sub-section',
            'cl': 'Clause',
            'sch': 'Schedule',
            'rule': 'Rule',
            'order': 'Order',
            'act': 'Act',
            'ordinance': 'Ordinance',
            'regulation': 'Regulation',
            'notification': 'Notification',
            
            # Legal Domains
            'company': 'Company Law',
            'banking': 'Banking Law',
            'tax': 'Tax Law',
            'labor': 'Labor Law',
            'property': 'Property Law',
            'family': 'Family Law',
            'criminal': 'Criminal Law',
            'civil': 'Civil Law',
            'constitutional': 'Constitutional Law',
            'commercial': 'Commercial Law',
            'administrative': 'Administrative Law',
            'intellectual': 'Intellectual Property Law',
            'environmental': 'Environmental Law',
            'consumer': 'Consumer Protection Law',
            'immigration': 'Immigration Law',
            'corporate': 'Corporate Law',
            
            # Legal Actions
            'petition': 'Petition',
            'application': 'Application',
            'complaint': 'Complaint',
            'suit': 'Suit',
            'case': 'Case',
            'matter': 'Matter',
            'proceeding': 'Proceeding',
            'hearing': 'Hearing',
            'trial': 'Trial',
            'judgment': 'Judgment',
            'order': 'Order',
            'decree': 'Decree',
            'award': 'Award',
            'settlement': 'Settlement',
            
            # Legal Roles
            'judge': 'Judge',
            'justice': 'Justice',
            'advocate': 'Advocate',
            'lawyer': 'Lawyer',
            'counsel': 'Counsel',
            'attorney': 'Attorney',
            'prosecutor': 'Prosecutor',
            'plaintiff': 'Plaintiff',
            'defendant': 'Defendant',
            'appellant': 'Appellant',
            'respondent': 'Respondent',
            'petitioner': 'Petitioner',
            'complainant': 'Complainant',
            'accused': 'Accused',
            'witness': 'Witness',
            
            # Legal Concepts
            'jurisdiction': 'Jurisdiction',
            'precedent': 'Precedent',
            'ratio': 'Ratio Decidendi',
            'obiter': 'Obiter Dicta',
            'stare': 'Stare Decisis',
            'locus': 'Locus Standi',
            'limitation': 'Limitation',
            'prescription': 'Prescription',
            'estoppel': 'Estoppel',
            'res': 'Res Judicata',
            'subjudice': 'Sub Judice',
            'ex_parte': 'Ex Parte',
            'inter_parte': 'Inter Parte',
            'in_camera': 'In Camera',
            'ad_interim': 'Ad Interim',
            'ex_parte': 'Ex Parte',
            'prima_facie': 'Prima Facie',
            'bona_fide': 'Bona Fide',
            'mala_fide': 'Mala Fide',
            'ultra_vires': 'Ultra Vires',
            'intra_vires': 'Intra Vires',
            'mandamus': 'Mandamus',
            'certiorari': 'Certiorari',
            'prohibition': 'Prohibition',
            'quo_warranto': 'Quo Warranto',
            'habeas_corpus': 'Habeas Corpus'
        }
        
        # Enhanced section patterns for QA context
        self.section_patterns = [
            # Standard section patterns
            r's\.?\s*(\d+)\s+(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)',
            r'section\s+(\d+)\s+(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)',
            r'(\d+)\s+(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)',
            r'(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)\s+(\d+)',
            
            # Government agency specific patterns
            r'(fia|nab|fbr|secp|sbp|pemra|pta)\s+(investigation|notice|circular|regulation|order|act|ordinance)',
            r'(fia|nab|fbr|secp|sbp|pemra|pta)\s+(filed|issued|regulated|fined)',
            r'(federal\s+investigation\s+agency|national\s+accountability\s+bureau|federal\s+board\s+of\s+revenue)',
            r'(securities\s+and\s+exchange\s+commission|state\s+bank\s+of\s+pakistan|pakistan\s+electronic\s+media\s+regulatory\s+authority)',
            r's\.?\s*(\d+)',
            r'section\s+(\d+)',
            
            # Constitutional articles
            r'art\.?\s*(\d+)\s+constitution',
            r'article\s+(\d+)\s+constitution',
            r'constitution\s+art\.?\s*(\d+)',
            r'art\.?\s*(\d+)\s+of\s+constitution',
            r'article\s+(\d+)\s+of\s+constitution',
            r'art\.?\s*(\d+)\((\d+)\)\s+constitution',
            r'art\.?\s*(\d+)\((\d+)\)\s+of\s+constitution',
            r'constitution\s+art\.?\s*(\d+)\((\d+)\)',
            r'constitution\s+article\s+(\d+)',
            r'constitution\s+art\.?\s*(\d+)',
            
            # Court-specific patterns
            r'(sc|ihc|lhc|shc|bhc|phc|fsc)\s+(\d{4})\s+(\d+)',
            r'(supreme\s+court|islamabad\s+high\s+court|lahore\s+high\s+court|sindh\s+high\s+court|balochistan\s+high\s+court|peshawar\s+high\s+court|federal\s+shariat\s+court)\s+(\d{4})\s+(\d+)',
            
            # Case citation patterns
            r'(pld|plj|mld|ylr|clj|clc|scr|hcr)\s+(\d{4})\s+(sc|ihc|lhc|shc|bhc|phc|fsc)\s+(\d+)',
            r'(pld|plj|mld|ylr|clj|clc|scr|hcr)\s+(\d{4})\s+(\d+)',
            
            # Legal publication patterns
            r'(pld|plj|mld|ylr|clj|clc|scr|hcr)\s+(\d{4})\s+(supreme\s+court|islamabad\s+high\s+court|lahore\s+high\s+court|sindh\s+high\s+court|balochistan\s+high\s+court|peshawar\s+high\s+court|federal\s+shariat\s+court)\s+(\d+)',
            
            # Sub-section patterns
            r'sub-section\s+(\d+)\s+of\s+section\s+(\d+)',
            r'sub-s\.?\s*(\d+)\s+of\s+s\.?\s*(\d+)',
            r's\.?\s*(\d+)\s*\((\d+)\)',
            
            # Rule and order patterns
            r'rule\s+(\d+)\s+of\s+(ppc|crpc|cpc|qso)',
            r'order\s+(\d+)\s+of\s+(ppc|crpc|cpc|qso)',
            r'r\.?\s*(\d+)\s+(ppc|crpc|cpc|qso)',
            r'o\.?\s*(\d+)\s+(ppc|crpc|cpc|qso)',
            
            # Schedule patterns
            r'schedule\s+(\d+)\s+of\s+(ppc|crpc|cpc|qso)',
            r'sch\.?\s*(\d+)\s+(ppc|crpc|cpc|qso)',
            
            # Clause patterns
            r'clause\s+(\d+)\s+of\s+section\s+(\d+)',
            r'cl\.?\s*(\d+)\s+of\s+s\.?\s*(\d+)',
            
            # Ordinance and regulation patterns
            r'ordinance\s+(\d+)\s+of\s+(\d{4})',
            r'regulation\s+(\d+)\s+of\s+(\d{4})',
            r'notification\s+(\d+)\s+of\s+(\d{4})'
        ]
        
        self.logger.info("QALawReferenceNormalizer initialized for QA context")
    
    def normalize_reference(self, text: str) -> Dict[str, Any]:
        """
        Normalize law references in text for QA context
        
        Args:
            text: Input text containing law references
            
        Returns:
            Dict with normalized references and QA-specific context
        """
        try:
            start_time = time.time()
            normalized_refs = []
            processed_text = text
            
            # Step 1: Find all potential matches with their pattern priority
            all_matches = []
            
            # Pattern priority groups (higher number = higher priority)
            # Order: case_citation, constitutional_article, section, agency_reference, agency_reference
            pattern_priorities = {
                # Case citation patterns (highest priority - should come first)
                r'(pld|plj|mld|ylr|clj|clc|scr|hcr)\s+(\d{4})\s+(sc|ihc|lhc|shc|bhc|phc|fsc)\s+(\d+)': 6,
                r'(pld|plj|mld|ylr|clj|clc|scr|hcr)\s+(\d{4})\s+(\d+)': 5,
                
                # Constitutional articles (second priority)
                r'art\.?\s*(\d+)\((\d+)\)\s+constitution': 4,
                r'art\.?\s*(\d+)\((\d+)\)\s+of\s+constitution': 4,
                r'constitution\s+art\.?\s*(\d+)\((\d+)\)': 4,
                r'art\.?\s*(\d+)\s+constitution': 3,
                r'article\s+(\d+)\s+constitution': 3,
                r'constitution\s+art\.?\s*(\d+)': 3,
                r'art\.?\s*(\d+)\s+of\s+constitution': 3,
                r'article\s+(\d+)\s+of\s+constitution': 3,
                r'constitution\s+article\s+(\d+)': 3,
                
                # Standard section patterns (third priority)
                r'section\s+(\d+)\s+(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)': 2,
                r's\.?\s*(\d+)\s+(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)': 2,
                r'(\d+)\s+(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)': 1,
                r'(ppc|crpc|cpc|qso|fia|nab|fbr|secp|sbp|pemra|pta)\s+(\d+)': 1,
                
                # Government agency patterns (fourth priority - should come after sections)
                r'(fia)\s+(investigation|filed|charges)': 0,
                r'(nab)\s+(filed|charges|investigation)': 0,
                r'(fbr)\s+(issued|notice|regulations)': 0,
                r'(secp)\s+(regulated|regulations)': 0,
                r'(sbp)\s+(issued|circular)': 0,
                r'(pemra)\s+(fined|regulations)': 0,
                r'(pta)\s+(regulated|regulations)': 0,
                
                # Court-specific patterns
                r'(sc|ihc|lhc|shc|bhc|phc|fsc)\s+(\d{4})\s+(\d+)': 0,
                r'(supreme\s+court|islamabad\s+high\s+court|lahore\s+high\s+court|sindh\s+high\s+court|balochistan\s+high\s+court|peshawar\s+high\s+court|federal\s+shariat\s+court)\s+(\d{4})\s+(\d+)': 0,
                
                # Sub-section, rule, and other patterns
                r'sub-section\s+(\d+)\s+of\s+section\s+(\d+)': 0,
                r'sub-s\.?\s*(\d+)\s+of\s+s\.?\s*(\d+)': 0,
                r's\.?\s*(\d+)\s*\((\d+)\)': 0,
                r'rule\s+(\d+)\s+of\s+(ppc|crpc|cpc|qso)': 0,
                r'order\s+(\d+)\s+of\s+(ppc|crpc|cpc|qso)': 0,
                
                # Generic patterns (lowest priority)
                r's\.?\s*(\d+)': -1,
                r'section\s+(\d+)': -1,
            }
            
            # Find all potential matches
            for pattern, priority in pattern_priorities.items():
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    all_matches.append({
                        'match': match,
                        'priority': priority,
                        'start': match.start(),
                        'end': match.end(),
                        'text': match.group(0),
                        'pattern': pattern
                    })
            
            # Step 2: Apply duplicate detection FIRST, before sorting
            # Remove duplicates where the same reference is detected multiple times
            filtered_matches = []
            seen_references = set()
            
            for match_info in all_matches:
                match = match_info['match']
                match_text = match.group(0).lower().strip()
                
                # Create a normalized key for duplicate detection
                # Extract the core reference (section number + act)
                normalized_key = None
                
                # Check for section patterns (PPC, CrPC, CPC, etc.)
                # Use a more comprehensive pattern that catches both "section 302 ppc" and "s. 302 ppc"
                section_match = re.search(r'(?:section\s+|s\.?\s*)?(\d+)\s*(ppc|crpc|cpc|qso)', match_text)
                if section_match:
                    normalized_key = f"{section_match.group(1)}_{section_match.group(2)}"
                    self.logger.debug(f"Found section pattern: {match_text} -> {normalized_key}")
                
                # Check for constitutional articles
                elif 'constitution' in match_text:
                    art_match = re.search(r'art(?:icle)?\s*(\d+)', match_text)
                    if art_match:
                        normalized_key = f"art_{art_match.group(1)}_constitution"
                
                # Check for case citations
                elif any(pub in match_text for pub in ['pld', 'plj', 'mld', 'ylr', 'clj', 'clc']):
                    citation_match = re.search(r'(pld|plj|mld|ylr|clj|clc)\s+(\d{4})\s+(\w+)\s+(\d+)', match_text)
                    if citation_match:
                        normalized_key = f"{citation_match.group(1)}_{citation_match.group(2)}_{citation_match.group(3)}_{citation_match.group(4)}"
                
                # Check for agency references
                elif any(agency in match_text for agency in ['fia', 'nab', 'fbr', 'secp', 'sbp', 'pemra', 'pta']):
                    agency_match = re.search(r'(fia|nab|fbr|secp|sbp|pemra|pta)', match_text)
                    if agency_match:
                        normalized_key = f"agency_{agency_match.group(1)}"
                
                # If we have a normalized key and it's already seen, skip this match
                if normalized_key and normalized_key in seen_references:
                    self.logger.debug(f"Skipping duplicate: {match_text} -> {normalized_key}")
                    continue
                
                # Add to seen references and filtered matches
                if normalized_key:
                    seen_references.add(normalized_key)
                    self.logger.debug(f"Adding new reference: {match_text} -> {normalized_key}")
                filtered_matches.append(match_info)
            
            all_matches = filtered_matches
            
            # Step 3: Sort matches by priority (higher first) and position
            all_matches.sort(key=lambda x: (-x['priority'], x['start']))
            
            # Step 3.5: Ensure consistent ordering for same priority matches
            # Group by priority and sort each group by position
            priority_groups = {}
            for match in all_matches:
                priority = match['priority']
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(match)
            
            # Rebuild sorted list maintaining priority order
            all_matches = []
            for priority in sorted(priority_groups.keys(), reverse=True):
                priority_groups[priority].sort(key=lambda x: x['start'])
                all_matches.extend(priority_groups[priority])
            
            # Step 3: Process matches with overlap detection
            processed_spans = []  # List of (start, end) tuples for processed text spans
            
            for match_info in all_matches:
                match = match_info['match']
                start, end = match_info['start'], match_info['end']
                
                # Check if this match overlaps with any already processed span
                overlaps = False
                for span_start, span_end in processed_spans:
                    # Check for any overlap with more strict criteria
                    overlap_start = max(start, span_start)
                    overlap_end = min(end, span_end)
                    overlap_length = overlap_end - overlap_start
                    
                    # Consider it overlapping if more than 50% of the shorter span overlaps
                    shorter_length = min(end - start, span_end - span_start)
                    if overlap_length > (shorter_length * 0.5):
                        overlaps = True
                        break
                
                if not overlaps:
                    ref_info = self._extract_reference_info(match, text)
                    if ref_info:
                        normalized_refs.append(ref_info)
                        processed_spans.append((start, end))
                        
                        # Replace in text with normalized format
                        normalized_format = self._format_reference(ref_info)
                        # Use string slicing for precise replacement
                        processed_text = processed_text[:start] + normalized_format + processed_text[end:]
            
            processing_time = time.time() - start_time
            
            self.logger.debug(f"Normalized {len(normalized_refs)} references for QA in {processing_time:.3f}s")
            
            return {
                'original_text': text,
                'processed_text': processed_text,
                'normalized_references': normalized_refs,
                'processing_time': processing_time,
                'reference_count': len(normalized_refs),
                'qa_context': self._generate_qa_context(normalized_refs)
            }
            
        except Exception as e:
            self.logger.error(f"Error normalizing law references for QA: {str(e)}")
            return {
                'original_text': text,
                'processed_text': text,
                'normalized_references': [],
                'processing_time': 0,
                'reference_count': 0,
                'qa_context': {},
                'error': str(e)
            }
    
    def _extract_reference_info(self, match, text: str) -> Optional[Dict[str, Any]]:
        """Extract reference information from regex match"""
        try:
            groups = match.groups()
            section_num = None
            act_abbr = None
            year = None
            court = None
            reference_type = 'section'
            action = None
            
            # Extract information based on pattern type
            pattern_text = match.group(0).lower()
            
            # Handle different pattern types
            if any(term in pattern_text for term in ['pld', 'plj', 'mld', 'ylr', 'clj', 'clc', 'scr', 'hcr']):
                # Case citation pattern: PLD 2023 SC 123
                reference_type = 'case_citation'
                for i, group in enumerate(groups):
                    if group and group.isdigit() and len(group) == 4:
                        year = int(group)
                    elif group and group.isdigit() and len(group) < 4:
                        section_num = int(group)
                    elif group and group.lower() in ['sc', 'ihc', 'lhc', 'shc', 'bhc', 'phc', 'fsc']:
                        court = group.upper()
                    elif group and group.lower() in ['pld', 'plj', 'mld', 'ylr', 'clj', 'clc', 'scr', 'hcr']:
                        act_abbr = group.lower()
                        
            elif any(term in pattern_text for term in ['sc', 'ihc', 'lhc', 'shc', 'bhc', 'phc', 'fsc']):
                # Court pattern: SC 2023 123
                reference_type = 'court_reference'
                for group in groups:
                    if group and group.isdigit() and len(group) == 4:
                        year = int(group)
                    elif group and group.isdigit() and len(group) < 4:
                        section_num = int(group)
                    elif group and group.lower() in ['sc', 'ihc', 'lhc', 'shc', 'bhc', 'phc', 'fsc']:
                        court = group.upper()
                        
            elif 'article' in pattern_text or 'art' in pattern_text:
                # Constitutional article pattern
                reference_type = 'constitutional_article'
                for group in groups:
                    if group and group.isdigit():
                        section_num = int(group)
                act_abbr = 'constitution'
                
            elif 'sub-section' in pattern_text or 'sub-s' in pattern_text:
                # Sub-section pattern
                reference_type = 'sub_section'
                for group in groups:
                    if group and group.isdigit():
                        if section_num is None:
                            section_num = int(group)
                        else:
                            # This is the sub-section number
                            pass
                            
            elif 'rule' in pattern_text or 'order' in pattern_text:
                # Rule/Order pattern
                reference_type = 'rule_order'
            for group in groups:
                if group and group.isdigit():
                    section_num = int(group)
                elif group and group.lower() in self.legal_abbreviations:
                    act_abbr = group.lower()
            
            # Government agency pattern detection
            elif any(agency in pattern_text for agency in ['fia', 'nab', 'fbr', 'secp', 'sbp', 'pemra', 'pta']):
                reference_type = 'agency_reference'
                for i, group in enumerate(groups):
                    if group and group.lower() in ['fia', 'nab', 'fbr', 'secp', 'sbp', 'pemra', 'pta']:
                        act_abbr = group.lower()
                    elif group and group.lower() in ['investigation', 'filed', 'charges', 'issued', 'notice', 
                                                    'regulations', 'regulated', 'circular', 'fined']:
                        action = group.lower()
                
                # For agency references, we don't need a section number
                section_num = 0  # Use 0 as a placeholder
                        
            else:
                # Standard section pattern
                for group in groups:
                    if group and group.isdigit():
                        section_num = int(group)
                    elif group and group.lower() in self.legal_abbreviations:
                        act_abbr = group.lower()
            
            # Special handling for agency references
            if reference_type == 'agency_reference':
                if not act_abbr:
                    return None
            elif not section_num and not year:  # For other references
                return None
            
            # Get full act name
            if act_abbr:
                act_name = self.legal_abbreviations.get(act_abbr, act_abbr.upper())
            else:
                act_name = 'Unknown Act'
                act_abbr = 'unknown'
            
            # Get court name
            if court:
                court_name = self.legal_abbreviations.get(court.lower(), court)
            else:
                court_name = None
            
            return {
                'section_number': section_num,
                'act_abbreviation': act_abbr,
                'act_name': act_name,
                'year': year,
                'court': court,
                'court_name': court_name,
                'reference_type': reference_type,
                'action': action,  # New field for agency actions
                'original_match': match.group(0),
                'start_pos': match.start(),
                'end_pos': match.end(),
                'context': text[max(0, match.start()-50):match.end()+50],
                'qa_relevance': self._calculate_qa_relevance(act_abbr, section_num, reference_type)
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting reference info: {str(e)}")
            return None
    
    def _format_reference(self, ref_info: Dict[str, Any]) -> str:
        """Format reference in canonical format for QA"""
        reference_type = ref_info.get('reference_type', 'section')
        
        # Handle different reference types
        if reference_type == 'agency_reference':
            act_abbr = ref_info['act_abbreviation']
            action = ref_info.get('action', '')
            if action:
                return f"{act_abbr.upper()} {action}"
            else:
                return f"{act_abbr.upper()}"
                
        elif reference_type == 'case_citation':
            act_abbr = ref_info['act_abbreviation']
            section = ref_info['section_number']
            year = ref_info.get('year')
            court = ref_info.get('court')
            
            if year and court:
                return f"{act_abbr.upper()} {year} {court} {section}"
            elif year:
                return f"{act_abbr.upper()} {year} {section}"
            else:
                return f"{act_abbr.upper()} {section}"
                
        elif reference_type == 'court_reference':
            court = ref_info.get('court', '')
            year = ref_info.get('year')
            section = ref_info['section_number']
            
            if year:
                return f"{court} {year} {section}"
            else:
                return f"{court} {section}"
                
        elif reference_type == 'constitutional_article':
            section = ref_info['section_number']
            return f"Art. {section} Constitution"
            
        else:  # Standard section reference
        section = ref_info['section_number']
        act_abbr = ref_info['act_abbreviation']
        
            if act_abbr and act_abbr != 'unknown':
            return f"s. {section} {act_abbr.upper()}"
        else:
            return f"s. {section}"
    
    def _calculate_qa_relevance(self, act_abbr: str, section_num: int = None, reference_type: str = 'section') -> float:
        """Calculate relevance score for QA context"""
        # Higher relevance for common legal concepts
        high_relevance_acts = ['ppc', 'crpc', 'cpc', 'constitution']
        
        # Handle agency references specially
        if reference_type == 'agency_reference':
            if act_abbr in ['fia', 'nab']:  # Investigation agencies
                base_score = 0.85
            elif act_abbr in ['fbr', 'secp', 'sbp']:  # Regulatory agencies
                base_score = 0.80
            elif act_abbr in ['pemra', 'pta']:  # Media/telecom regulators
                base_score = 0.75
            else:
                base_score = 0.70
            return base_score
            
        # Handle other reference types
        if act_abbr in high_relevance_acts:
            base_score = 0.9
        elif act_abbr in ['fia', 'nab', 'fbr', 'secp', 'sbp']:
            base_score = 0.8
        elif act_abbr in ['pld', 'plj', 'mld', 'ylr', 'clj', 'clc', 'scr', 'hcr']:
            base_score = 0.85
        elif act_abbr:
            base_score = 0.7
        else:
            base_score = 0.5
        
        # Adjust based on reference type
        if reference_type == 'case_citation':
            base_score += 0.1  # Case citations are highly relevant for QA
        elif reference_type == 'constitutional_article':
            base_score += 0.05  # Constitutional articles are important
        elif reference_type == 'court_reference':
            base_score += 0.05  # Court references provide authority
        elif reference_type == 'sub_section':
            base_score += 0.02  # Sub-sections provide detailed context
        
        return min(base_score, 1.0)  # Cap at 1.0
    
    def _generate_qa_context(self, references: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate QA-specific context from references"""
        if not references:
            return {}
        
        # Group by act
        acts = {}
        courts = {}
        years = {}
        reference_types = {}
        
        for ref in references:
            act = ref['act_abbreviation'] or 'unknown'
            if act not in acts:
                acts[act] = []
            acts[act].append(ref['section_number'])
            
            # Group by court
            if ref.get('court'):
                court = ref['court']
                if court not in courts:
                    courts[court] = []
                courts[court].append(ref['section_number'])
            
            # Group by year
            if ref.get('year'):
                year = ref['year']
                if year not in years:
                    years[year] = []
                years[year].append(ref['section_number'])
            
            # Group by reference type
            ref_type = ref.get('reference_type', 'section')
            if ref_type not in reference_types:
                reference_types[ref_type] = []
            reference_types[ref_type].append(ref['section_number'])
        
        return {
            'acts_mentioned': list(acts.keys()),
            'sections_by_act': acts,
            'courts_mentioned': list(courts.keys()),
            'sections_by_court': courts,
            'years_mentioned': list(years.keys()),
            'sections_by_year': years,
            'reference_types': list(reference_types.keys()),
            'sections_by_type': reference_types,
            'total_references': len(references),
            'avg_relevance': sum(ref['qa_relevance'] for ref in references) / len(references),
            'has_case_citations': 'case_citation' in reference_types,
            'has_constitutional_refs': 'constitutional_article' in reference_types,
            'has_court_refs': 'court_reference' in reference_types
        }


class QAEnhancedChunkingService:
    """Enhanced document chunking specifically for QA/RAG context"""
    
    def __init__(self, config: QAChunkingConfig = None):
        self.config = config or QAChunkingConfig()
        self.normalizer = QALawReferenceNormalizer()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"QAEnhancedChunkingService initialized with config: {self.config}")
    
    def chunk_document_for_qa(self, 
                             case_id: int, 
                             document_id: Optional[int] = None,
                             text: str = None,
                             document_type: str = "judgment") -> List[Dict[str, Any]]:
        """
        Chunk a document specifically for QA/RAG context
        
        Args:
            case_id: Case ID
            document_id: Document ID (optional)
            text: Document text (if not provided, will fetch from DB)
            document_type: Type of document (judgment, order, etc.)
            
        Returns:
            List of chunk dictionaries optimized for QA context
        """
        try:
            start_time = time.time()
            self.logger.info(f"Starting QA chunking for case {case_id}, document {document_id}")
            
            # Get document text if not provided
            if not text:
                text = self._get_document_text(case_id, document_id)
            
            if not text:
                self.logger.warning(f"No text found for case {case_id}, document {document_id}")
                return []
            
            # Get case metadata
            case_metadata = self._get_case_metadata(case_id)
            if not case_metadata:
                self.logger.error(f"Could not retrieve metadata for case {case_id}")
                return []
            
            # Normalize law references for QA context
            normalization_result = self.normalizer.normalize_reference(text)
            processed_text = normalization_result['processed_text']
            
            # Split into chunks optimized for AI context
            chunks = self._split_text_for_qa_context(processed_text)
            
            # Enrich chunks with QA-specific metadata
            enriched_chunks = []
            for i, chunk_text in enumerate(chunks):
                chunk_metadata = self._create_qa_chunk_metadata(
                    case_metadata, i, chunk_text, document_type
                )
                
                # Calculate AI context score
                ai_context_score = self._calculate_ai_context_score(chunk_text, chunk_metadata)
                
                enriched_chunk = {
                    'chunk_id': self._generate_qa_chunk_id(case_id, document_id, i),
                    'chunk_index': i,
                    'chunk_text': chunk_text,
                    'token_count': self._estimate_token_count(chunk_text),
                    'metadata': chunk_metadata,
                    'normalized_references': self._extract_chunk_references(chunk_text),
                    'chunk_hash': hashlib.sha256(chunk_text.encode()).hexdigest(),
                    'ai_context_score': ai_context_score,
                    'qa_relevance': self._calculate_qa_relevance(chunk_text, chunk_metadata)
                }
                
                enriched_chunks.append(enriched_chunk)
            
            processing_time = time.time() - start_time
            
            self.logger.info(f"QA chunking completed: {len(enriched_chunks)} chunks in {processing_time:.3f}s")
            self.logger.debug(f"QA chunking details: case_id={case_id}, doc_id={document_id}, "
                            f"text_length={len(text)}, chunks={len(enriched_chunks)}")
            
            return enriched_chunks
            
        except Exception as e:
            self.logger.error(f"Error chunking document for QA: {str(e)}")
            return []
    
    def _get_document_text(self, case_id: int, document_id: Optional[int] = None) -> str:
        """Get document text from database"""
        try:
            if document_id:
                # Get specific document text
                doc_text = DocumentText.objects.filter(
                    document_id=document_id
                ).first()
                if doc_text:
                    return doc_text.clean_text or doc_text.raw_text
            else:
                # Get case text from unified view
                unified_view = UnifiedCaseView.objects.filter(case_id=case_id).first()
                if unified_view and unified_view.pdf_content_summary:
                    content = unified_view.pdf_content_summary
                    if isinstance(content, dict):
                        return content.get('full_text', '')
                    return str(content)
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error getting document text: {str(e)}")
            return ""
    
    def _get_case_metadata(self, case_id: int) -> Optional[Dict[str, Any]]:
        """Get case metadata for QA enrichment"""
        try:
            case = Case.objects.filter(id=case_id).first()
            if not case:
                return None
            
            # Get court information
            court_name = case.court.name if case.court else "Unknown Court"
            
            # Get judges
            judges = []
            if hasattr(case, 'judges_data'):
                judges = [judge.judge_name for judge in case.judges_data.all()]
            
            # Get year
            year = case.hearing_date.year if case.hearing_date else None
            
            return {
                'case_no': case.case_number or f"CASE-{case_id}",
                'court': court_name,
                'judges': judges,
                'year': year,
                'case_title': case.case_title or "",
                'status': case.status or "",
                'bench': case.bench or "",
                'hearing_date': case.hearing_date,
                'case_id': case_id
            }
            
        except Exception as e:
            self.logger.error(f"Error getting case metadata: {str(e)}")
            return None
    
    def _split_text_for_qa_context(self, text: str) -> List[str]:
        """Split text into chunks optimized for AI context"""
        try:
            chunks = []
            text_length = len(text)
            chunk_size_chars = int(self.config.chunk_size * self.config.token_ratio)
            overlap_chars = int(self.config.chunk_overlap * self.config.token_ratio)
            
            start = 0
            chunk_index = 0
            
            while start < text_length:
                # Calculate end position
                end = min(start + chunk_size_chars, text_length)
                
                # Try to break at sentence boundary for better AI context
                if end < text_length:
                    # Look for sentence endings within the last 200 characters
                    search_start = max(start, end - 200)
                    sentence_end = text.rfind('.', search_start, end)
                    if sentence_end > start + self.config.min_chunk_size * self.config.token_ratio:
                        end = sentence_end + 1
                
                chunk_text = text[start:end].strip()
                
                # Skip very small chunks
                if len(chunk_text) >= self.config.min_chunk_size * self.config.token_ratio:
                    chunks.append(chunk_text)
                    chunk_index += 1
                
                # Move start position with overlap
                start = max(start + 1, end - overlap_chars)
                
                # Prevent infinite loop
                if start >= end:
                    break
            
            self.logger.debug(f"Split text into {len(chunks)} QA-optimized chunks")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error splitting text for QA: {str(e)}")
            return [text]  # Fallback to single chunk
    
    def _create_qa_chunk_metadata(self, 
                                 case_metadata: Dict[str, Any], 
                                 chunk_index: int,
                                 chunk_text: str,
                                 document_type: str) -> QAMetadata:
        """Create QA-specific metadata for a chunk"""
        try:
            # Extract sections from chunk text
            sections = self._extract_sections_from_text(chunk_text)
            
            return QAMetadata(
                case_no=case_metadata['case_no'],
                court=case_metadata['court'],
                judges=case_metadata['judges'],
                year=case_metadata['year'],
                sections=sections,
                paragraph_no=chunk_index + 1,
                document_type=document_type,
                content_type="text",
                legal_domain=self._classify_legal_domain(chunk_text)
            )
            
        except Exception as e:
            self.logger.error(f"Error creating QA chunk metadata: {str(e)}")
            return QAMetadata(
                case_no="UNKNOWN",
                court="Unknown Court",
                judges=[],
                year=None,
                sections=[],
                paragraph_no=chunk_index + 1,
                document_type=document_type
            )
    
    def _extract_sections_from_text(self, text: str) -> List[str]:
        """Extract legal sections mentioned in text"""
        try:
            sections = []
            normalization_result = self.normalizer.normalize_reference(text)
            
            for ref in normalization_result['normalized_references']:
                section_str = f"s. {ref['section_number']} {ref['act_abbreviation'].upper()}"
                sections.append(section_str)
            
            return sections
            
        except Exception as e:
            self.logger.error(f"Error extracting sections: {str(e)}")
            return []
    
    def _classify_legal_domain(self, text: str) -> str:
        """Classify the legal domain of the text for QA context using weighted scoring"""
        try:
            text_lower = text.lower()
            
            # Define domain terms with weights (higher weight = stronger indicator)
            domain_terms = {
                'criminal': {
                    'high': ['murder', 'theft', 'robbery', 'criminal offense', 'accused', 'conviction', 
                            'imprisonment', 'prosecution', 'bail application', 'fir', 'charged under ppc', 
                            'criminal charges', 'criminal case', 'criminal proceedings'],
                    'medium': ['criminal', 'offence', 'offense', 'punishment', 'bail', 'ppc', 'crpc', 
                              'fraud', 'corruption', 'nab', 'fia', 'sentence', 'fine', 'penalty'],
                    'low': ['crime', 'illegal', 'arrest', 'police', 'jail']
                },
                
                'civil': {
                    'high': ['civil suit', 'specific performance', 'injunction granted', 'damages awarded', 
                            'breach of contract', 'civil procedure', 'decree passed', 'civil suit filed'],
                    'medium': ['civil', 'contract', 'tort', 'damages', 'cpc', 'suit', 'plaintiff', 
                              'defendant', 'compensation', 'injunction', 'breach', 'negligence', 'liability', 
                              'remedy', 'decree', 'judgment'],
                    'low': ['civil court', 'civil case', 'civil matter']
                },
                
                'constitutional': {
                    'high': ['fundamental rights', 'writ jurisdiction', 'article 199', 'constitutional petition',
                            'judicial review', 'mandamus', 'certiorari', 'quo warranto', 'habeas corpus'],
                    'medium': ['constitution', 'writ', 'article', 'prohibition', 
                              'supreme court', 'high court', 'federal shariat court', 'constitutional'],
                    'low': ['rights', 'constitutional law', 'constitutional matter']
                },
                
                'family': {
                    'high': ['divorce decree', 'child custody', 'guardianship', 'nikah', 'talaq', 'khula', 
                            'family laws', 'maintenance order', 'dower'],
                    'medium': ['marriage', 'divorce', 'custody', 'maintenance', 'family', 'adoption', 
                              'inheritance', 'alimony', 'child support'],
                    'low': ['matrimonial', 'spouse', 'husband', 'wife', 'children']
                },
                
                'commercial': {
                    'high': ['commercial transaction', 'business contract', 'partnership deed', 
                            'articles of association', 'board of directors', 'commercial agreement'],
                    'medium': ['company', 'corporation', 'partnership', 'business', 'commercial', 'trade', 
                              'commerce', 'merchant', 'sale', 'purchase', 'agreement', 'memorandum', 'shareholder'],
                    'low': ['commercial', 'business', 'trade', 'commercial activity']
                },
                
                'tax': {
                    'high': ['income tax', 'sales tax', 'customs duty', 'tax assessment', 'tax return', 
                            'tax exemption', 'tax deduction', 'fbr notice', 'tax levied', 'duty imposed'],
                    'medium': ['tax', 'fbr', 'revenue', 'assessment', 'withholding', 'advance tax', 
                              'federal excise', 'tax notice', 'tax order'],
                    'low': ['taxation', 'taxable', 'tax liability', 'tax law']
                },
                
                'labor': {
                    'high': ['workmen compensation', 'labor union', 'industrial dispute', 'strike', 'lockout',
                            'employment termination', 'worker dismissal', 'labor law', 'industrial relations'],
                    'medium': ['labor', 'labour', 'employment', 'worker', 'employee', 'employer', 'wages', 
                              'salary', 'bonus', 'overtime', 'leave', 'termination', 'dismissal', 'union'],
                    'low': ['workplace', 'job', 'work', 'employment law']
                },
                
                'property': {
                    'high': ['sale deed', 'property transfer', 'land partition', 'mortgage created', 
                            'property title', 'gift deed', 'real estate', 'land ownership'],
                    'medium': ['property', 'land', 'ownership', 'possession', 'title', 
                              'deed', 'mortgage', 'lease', 'rent', 'eviction', 'landlord', 'tenant'],
                    'low': ['property law', 'immovable property', 'premises']
                },
                
                'banking': {
                    'high': ['islamic banking', 'banking law', 'sbp circular', 'state bank', 'banking regulation',
                            'banking ordinance', 'banking act', 'banking company'],
                    'medium': ['banking', 'bank', 'loan', 'credit', 'debit', 'account', 'deposit', 
                              'withdrawal', 'interest', 'sbp', 'commercial bank'],
                    'low': ['financial', 'finance', 'banking sector']
                },
                
                'intellectual_property': {
                    'high': ['patent filed', 'trademark registered', 'copyright infringed', 'intellectual property',
                            'design protected', 'patent application', 'trademark application'],
                    'medium': ['patent', 'trademark', 'copyright', 'design', 'invention', 'brand', 'logo', 
                              'creative work', 'literary work', 'artistic work'],
                    'low': ['ip law', 'intellectual', 'innovation']
                },
                
                'corporate': {
                    'high': ['securities traded', 'stock exchange regulated', 'corporate governance', 
                            'board meeting', 'annual general meeting', 'corporate law', 'merger', 'acquisition'],
                    'medium': ['corporate', 'proxy', 'dividend', 'equity', 'takeover', 'insider trading', 
                              'securities', 'stock exchange', 'debt'],
                    'low': ['corporate entity', 'corporate affairs', 'corporate structure']
                }
            }
            
            # Calculate score for each domain
            domain_scores = {}
            for domain, term_categories in domain_terms.items():
                score = 0
                
                # High priority terms (weight = 3)
                for term in term_categories['high']:
                    if term in text_lower:
                        score += 3
                
                # Medium priority terms (weight = 2)
                for term in term_categories['medium']:
                    if term in text_lower:
                        score += 2
                
                # Low priority terms (weight = 1)
                for term in term_categories['low']:
                    if term in text_lower:
                        score += 1
                
                domain_scores[domain] = score
            
            # Find domain with highest score
            if not domain_scores:
                return 'general'
                
            max_score = max(domain_scores.values())
            if max_score == 0:
                return 'general'
            
            # Special handling for mixed criminal+civil cases
            # If both criminal and civil have scores, prioritize criminal for PPC-related cases
            if domain_scores.get('criminal', 0) > 0 and domain_scores.get('civil', 0) > 0:
                # Check if text contains PPC or criminal-specific terms
                criminal_indicators = ['ppc', 'charged under', 'criminal charges', 'accused', 'conviction']
                if any(indicator in text_lower for indicator in criminal_indicators):
                    return 'criminal'
            
            # Get domain with highest score
            for domain, score in domain_scores.items():
                if score == max_score:
                    return domain
            
            return 'general'
            
        except Exception as e:
            self.logger.error(f"Error classifying legal domain: {str(e)}")
            return 'general'
    
    def _calculate_ai_context_score(self, chunk_text: str, metadata: QAMetadata) -> float:
        """Calculate how relevant this chunk is for AI context"""
        try:
            score = 0.0
            
            # Base score
            score += 0.3
            
            # Legal domain bonus
            if metadata.legal_domain != 'general':
                score += 0.2
            
            # Sections mentioned bonus
            if metadata.sections:
                score += 0.2
            
            # Court level bonus (higher courts more relevant)
            if 'high court' in metadata.court.lower() or 'supreme court' in metadata.court.lower():
                score += 0.2
            
            # Text quality indicators
            if len(chunk_text) > 500:  # Substantial content
                score += 0.1
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            self.logger.error(f"Error calculating AI context score: {str(e)}")
            return 0.5
    
    def _calculate_qa_relevance(self, chunk_text: str, metadata: QAMetadata) -> float:
        """Calculate QA relevance score"""
        try:
            relevance = 0.0
            
            # Legal terminology presence
            legal_terms = ['court', 'judge', 'case', 'law', 'legal', 'section', 'act']
            term_count = sum(1 for term in legal_terms if term in chunk_text.lower())
            relevance += (term_count / len(legal_terms)) * 0.4
            
            # Metadata completeness
            if metadata.case_no and metadata.case_no != "UNKNOWN":
                relevance += 0.2
            if metadata.court and metadata.court != "Unknown Court":
                relevance += 0.2
            if metadata.judges:
                relevance += 0.1
            if metadata.sections:
                relevance += 0.1
            
            return min(relevance, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating QA relevance: {str(e)}")
            return 0.5
    
    def _generate_qa_chunk_id(self, case_id: int, document_id: Optional[int], chunk_index: int) -> str:
        """Generate unique chunk ID for QA context"""
        if document_id:
            return f"qa_case_{case_id}_doc_{document_id}_chunk_{chunk_index}"
        else:
            return f"qa_case_{case_id}_chunk_{chunk_index}"
    
    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for text"""
        return int(len(text) / self.config.token_ratio)
    
    def _extract_chunk_references(self, chunk_text: str) -> List[Dict[str, Any]]:
        """Extract law references from chunk text"""
        try:
            normalization_result = self.normalizer.normalize_reference(chunk_text)
            return normalization_result['normalized_references']
        except Exception as e:
            self.logger.error(f"Error extracting chunk references: {str(e)}")
            return []


class QAKnowledgeBaseService:
    """Main service for QA Knowledge Base operations"""
    
    def __init__(self):
        self.chunking_service = QAEnhancedChunkingService()
        self.normalizer = QALawReferenceNormalizer()
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("QAKnowledgeBaseService initialized")
    
    def process_case_for_qa(self, case_id: int, force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Process a case specifically for QA/RAG context
        
        Args:
            case_id: Case ID to process
            force_reprocess: Whether to reprocess existing chunks
            
        Returns:
            Processing results with QA-specific metrics
        """
        try:
            start_time = time.time()
            self.logger.info(f"Starting QA processing for case {case_id}")
            
            # Get case information
            case = Case.objects.filter(id=case_id).first()
            if not case:
                return {'error': f'Case {case_id} not found', 'success': False}
            
            # Check if already processed for QA
            existing_qa_kb = QAKnowledgeBase.objects.filter(source_case_id=case_id).count()
            if existing_qa_kb > 0 and not force_reprocess:
                self.logger.info(f"Case {case_id} already processed for QA with {existing_qa_kb} entries, skipping")
                return {
                    'success': True,
                    'message': f'Case already processed for QA with {existing_qa_kb} entries',
                    'qa_entries_count': existing_qa_kb
                }
            
            # Delete existing QA entries if reprocessing
            if force_reprocess and existing_qa_kb > 0:
                QAKnowledgeBase.objects.filter(source_case_id=case_id).delete()
                self.logger.info(f"Deleted {existing_qa_kb} existing QA entries for reprocessing")
            
            # Process case documents for QA
            processing_results = {
                'case_id': case_id,
                'case_title': case.case_title,
                'case_number': case.case_number,
                'qa_entries_created': 0,
                'documents_processed': 0,
                'errors': [],
                'processing_time': 0,
                'qa_metrics': {
                    'total_references': 0,
                    'normalized_references': 0,
                    'avg_ai_context_score': 0.0,
                    'avg_qa_relevance': 0.0
                }
            }
            
            # Process unified case view for QA
            unified_view = UnifiedCaseView.objects.filter(case_id=case_id).first()
            if unified_view:
                chunks = self.chunking_service.chunk_document_for_qa(
                    case_id=case_id,
                    document_type="judgment"
                )
                
                if chunks:
                    self._save_qa_chunks_to_kb(chunks, case_id)
                    processing_results['qa_entries_created'] += len(chunks)
                    processing_results['documents_processed'] += 1
                    
                    # Update QA metrics
                    for chunk in chunks:
                        processing_results['qa_metrics']['total_references'] += len(chunk.get('normalized_references', []))
                        processing_results['qa_metrics']['avg_ai_context_score'] += chunk.get('ai_context_score', 0)
                        processing_results['qa_metrics']['avg_qa_relevance'] += chunk.get('qa_relevance', 0)
            
            # Process individual documents for QA
            documents = Document.objects.filter(case_id=case_id)
            for document in documents:
                try:
                    chunks = self.chunking_service.chunk_document_for_qa(
                        case_id=case_id,
                        document_id=document.id,
                        document_type="document"
                    )
                    
                    if chunks:
                        self._save_qa_chunks_to_kb(chunks, case_id, document.id)
                        processing_results['qa_entries_created'] += len(chunks)
                        processing_results['documents_processed'] += 1
                        
                        # Update QA metrics
                        for chunk in chunks:
                            processing_results['qa_metrics']['total_references'] += len(chunk.get('normalized_references', []))
                            processing_results['qa_metrics']['avg_ai_context_score'] += chunk.get('ai_context_score', 0)
                            processing_results['qa_metrics']['avg_qa_relevance'] += chunk.get('qa_relevance', 0)
                
                except Exception as e:
                    error_msg = f"Error processing document {document.id} for QA: {str(e)}"
                    processing_results['errors'].append(error_msg)
                    self.logger.error(error_msg)
            
            # Calculate averages
            if processing_results['qa_entries_created'] > 0:
                processing_results['qa_metrics']['avg_ai_context_score'] /= processing_results['qa_entries_created']
                processing_results['qa_metrics']['avg_qa_relevance'] /= processing_results['qa_entries_created']
            
            processing_results['processing_time'] = time.time() - start_time
            processing_results['success'] = len(processing_results['errors']) == 0
            
            self.logger.info(f"QA processing completed for case {case_id}: "
                           f"{processing_results['qa_entries_created']} QA entries, "
                           f"{processing_results['documents_processed']} documents, "
                           f"{processing_results['processing_time']:.3f}s")
            
            return processing_results
            
        except Exception as e:
            self.logger.error(f"Error in QA processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'case_id': case_id
            }
    
    def _save_qa_chunks_to_kb(self, chunks: List[Dict[str, Any]], case_id: int, document_id: Optional[int] = None):
        """Save QA chunks to QAKnowledgeBase"""
        try:
            with transaction.atomic():
                for chunk_data in chunks:
                    metadata = chunk_data['metadata']
                    
                    # Create QA Knowledge Base entry
                    qa_entry = QAKnowledgeBase(
                        source_type="qa_chunk",
                        source_id=chunk_data['chunk_id'],
                        source_case_id=case_id,
                        source_document_id=document_id,
                        title=f"QA Chunk {chunk_data['chunk_index']} - {metadata.case_no}",
                        content_text=chunk_data['chunk_text'],
                        content_summary=chunk_data['chunk_text'][:200] + "...",
                        court=metadata.court,
                        case_number=metadata.case_no,
                        case_title=metadata.case_no,  # Will be updated with actual case title
                        judge_name=", ".join(metadata.judges) if metadata.judges else "Unknown",
                        date_decided=None,  # Will be updated if available
                        legal_domain=metadata.legal_domain,
                        legal_concepts=metadata.sections,
                        legal_entities=metadata.judges,
                        citations=chunk_data.get('normalized_references', []),
                        vector_id=chunk_data['chunk_id'],
                        embedding_model="all-MiniLM-L6-v2",
                        embedding_dimension=384,
                        content_quality_score=chunk_data.get('ai_context_score', 0.5),
                        legal_relevance_score=chunk_data.get('qa_relevance', 0.5),
                        completeness_score=0.8,  # Default completeness
                        is_indexed=False,  # Will be indexed separately
                        is_processed=True,
                        processing_error="",
                        content_hash=chunk_data['chunk_hash']
                    )
                    qa_entry.save()
                    
                    self.logger.debug(f"Saved QA entry {chunk_data['chunk_id']} with metadata: {metadata}")
            
            self.logger.info(f"Saved {len(chunks)} QA chunks to knowledge base")
            
        except Exception as e:
            self.logger.error(f"Error saving QA chunks to knowledge base: {str(e)}")
            raise
    
    def get_qa_processing_stats(self) -> Dict[str, Any]:
        """Get QA processing statistics"""
        try:
            # Get QA Knowledge Base statistics
            total_qa_entries = QAKnowledgeBase.objects.count()
            indexed_qa_entries = QAKnowledgeBase.objects.filter(is_indexed=True).count()
            
            # Get case statistics
            total_cases = Case.objects.count()
            processed_cases = QAKnowledgeBase.objects.values('source_case_id').distinct().count()
            
            # Get legal domain distribution
            domain_stats = {}
            for entry in QAKnowledgeBase.objects.values('legal_domain').distinct():
                domain = entry['legal_domain']
                count = QAKnowledgeBase.objects.filter(legal_domain=domain).count()
                domain_stats[domain] = count
            
            # Get average scores
            avg_quality = QAKnowledgeBase.objects.aggregate(
                avg_quality=models.Avg('content_quality_score')
            )['avg_quality'] or 0.0
            
            avg_relevance = QAKnowledgeBase.objects.aggregate(
                avg_relevance=models.Avg('legal_relevance_score')
            )['avg_relevance'] or 0.0
            
            return {
                'qa_knowledge_base': {
                    'total_entries': total_qa_entries,
                    'indexed_entries': indexed_qa_entries,
                    'indexing_coverage': (indexed_qa_entries / total_qa_entries * 100) if total_qa_entries > 0 else 0
                },
                'case_processing': {
                    'total_cases': total_cases,
                    'processed_cases': processed_cases,
                    'processing_coverage': (processed_cases / total_cases * 100) if total_cases > 0 else 0
                },
                'legal_domains': domain_stats,
                'quality_metrics': {
                    'avg_content_quality': float(avg_quality),
                    'avg_legal_relevance': float(avg_relevance)
                },
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting QA processing stats: {str(e)}")
            return {'error': str(e)}
