"""
Enhanced Metadata Service for Perfect Search Results
Extracts and indexes rich metadata from all case data sources
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.db import models
from apps.cases.models import Case, CaseDetail, OrdersData, CommentsData, CaseCmsData, PartiesDetailData

logger = logging.getLogger(__name__)


class EnhancedMetadataService:
    """Service to extract and index rich metadata for perfect search results"""
    
    def __init__(self):
        self.legal_entities = self._load_legal_entities()
        self.legal_concepts = self._load_legal_concepts()
        self.court_hierarchy = self._load_court_hierarchy()
    
    def extract_enhanced_metadata(self, case: Case) -> Dict[str, Any]:
        """Extract comprehensive metadata from all case sources"""
        try:
            metadata = {
                # Basic case info (already indexed)
                'basic_info': self._extract_basic_info(case),
                
                # NEW: Rich content extraction
                'legal_entities': self._extract_legal_entities(case),
                'legal_concepts': self._extract_legal_concepts(case),
                'case_type_classification': self._classify_case_type(case),
                'procedural_stage': self._determine_procedural_stage(case),
                'subject_matter': self._extract_subject_matter(case),
                'legal_provisions': self._extract_legal_provisions(case),
                
                # NEW: Parties intelligence
                'parties_intelligence': self._analyze_parties(case),
                'advocate_information': self._extract_advocate_info(case),
                
                # NEW: Procedural intelligence
                'case_timeline': self._build_case_timeline(case),
                'procedural_history': self._extract_procedural_history(case),
                'orders_summary': self._summarize_orders(case),
                
                # NEW: Content quality scores
                'content_richness_score': self._calculate_content_richness(case),
                'data_completeness_score': self._calculate_data_completeness(case),
                
                # NEW: Search optimization
                'searchable_keywords': self._generate_search_keywords(case),
                'semantic_tags': self._generate_semantic_tags(case),
                'relevance_boosters': self._identify_relevance_boosters(case)
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting enhanced metadata for case {case.id}: {str(e)}")
            return {}
    
    def _extract_basic_info(self, case: Case) -> Dict[str, Any]:
        """Extract basic case information"""
        return {
            'case_id': case.id,
            'case_number': case.case_number or '',
            'case_title': case.case_title or '',
            'court': getattr(case.court, 'name', 'Unknown Court') if case.court else 'Unknown Court',
            'status': case.status or '',
            'institution_date': case.institution_date.strftime('%Y-%m-%d') if hasattr(case.institution_date, 'strftime') and case.institution_date else str(case.institution_date) if case.institution_date else None,
            'disposal_date': case.disposal_date.strftime('%Y-%m-%d') if hasattr(case, 'disposal_date') and hasattr(case.disposal_date, 'strftime') and case.disposal_date else str(getattr(case, 'disposal_date', '')) if hasattr(case, 'disposal_date') and case.disposal_date else None,
            'hearing_date': case.hearing_date.strftime('%Y-%m-%d') if hasattr(case.hearing_date, 'strftime') and case.hearing_date else str(case.hearing_date) if case.hearing_date else None
        }
    
    def _extract_legal_concepts(self, case: Case) -> List[Dict[str, Any]]:
        """Extract legal concepts from case data"""
        concepts = []
        
        # Combine text sources
        text_sources = [
            case.case_title or '',
            case.case_number or '',
            case.status or ''
        ]
        
        combined_text = ' '.join(text_sources).lower()
        
        # Basic legal concept patterns
        concept_patterns = {
            'contract': ['contract', 'agreement', 'breach', 'performance'],
            'property': ['property', 'land', 'ownership', 'possession'],
            'criminal': ['criminal', 'offense', 'crime', 'violation'],
            'civil': ['civil', 'dispute', 'damages', 'compensation'],
            'constitutional': ['constitutional', 'fundamental rights', 'petition'],
            'family': ['marriage', 'divorce', 'custody', 'maintenance'],
            'commercial': ['commercial', 'business', 'trade', 'company']
        }
        
        for concept, keywords in concept_patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                concepts.append({
                    'concept': concept,
                    'confidence': 0.7,
                    'keywords_found': [kw for kw in keywords if kw in combined_text]
                })
        
        return concepts
    
    def _determine_procedural_stage(self, case: Case) -> str:
        """Determine the procedural stage of the case"""
        status = (case.status or '').lower()
        
        if 'pending' in status or 'under' in status:
            return 'pending'
        elif 'decided' in status or 'disposed' in status:
            return 'decided'
        elif 'dismissed' in status:
            return 'dismissed'
        elif 'withdrawn' in status:
            return 'withdrawn'
        else:
            return 'unknown'
    
    def _extract_legal_entities(self, case: Case) -> List[Dict[str, Any]]:
        """Extract legal entities (statutes, sections, acts, etc.)"""
        entities = []
        
        # Combine all text sources
        text_sources = [
            case.case_title or '',
            case.bench or '',
        ]
        
        # Add orders text
        for order in case.orders_data.all():
            text_sources.extend([
                order.order_passed or '',
                order.description or '',
                order.order_detail or ''
            ])
        
        # Add comments text
        for comment in case.comments_data.all():
            text_sources.extend([
                comment.case_no or '',
                comment.next_date or '',
                comment.compliance_date or ''
            ])
        
        # Extract entities from all text
        all_text = ' '.join(text_sources)
        
        # Legal statute patterns
        statute_patterns = [
            r'\b(PPC|CrPC|CPC|Constitution|Ordinance|Act)\s*(\d{4}|\d+)\b',
            r'\b(Section|Article|Rule|Order)\s+(\d+[A-Z]?)\b',
            r'\b\d{4}\s+(SCMR|PLD|YLR|CLR|PLJ)\s+\d+\b',
            r'\b(Qanun-e-Shahadat|Evidence Act|Contract Act)\b'
        ]
        
        for pattern in statute_patterns:
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'type': 'legal_statute',
                    'text': match.group(),
                    'position': match.span(),
                    'confidence': 0.9
                })
        
        return entities
    
    def _extract_legal_provisions(self, case: Case) -> List[Dict[str, Any]]:
        """Extract legal provisions (sections, acts, etc.)"""
        provisions = []
        
        # Combine text sources
        text_sources = [
            case.case_title or '',
            case.case_number or '',
            case.status or ''
        ]
        
        combined_text = ' '.join(text_sources)
        
        # Basic provision patterns
        import re
        section_pattern = r'section\s+(\d+[a-z]?)'
        article_pattern = r'article\s+(\d+[a-z]?)'
        act_pattern = r'(\w+\s+act\s+\d{4})'
        
        # Find sections
        sections = re.findall(section_pattern, combined_text, re.IGNORECASE)
        for section in sections:
            provisions.append({
                'type': 'section',
                'reference': f'Section {section}',
                'confidence': 0.8
            })
        
        # Find articles
        articles = re.findall(article_pattern, combined_text, re.IGNORECASE)
        for article in articles:
            provisions.append({
                'type': 'article',
                'reference': f'Article {article}',
                'confidence': 0.8
            })
        
        # Find acts
        acts = re.findall(act_pattern, combined_text, re.IGNORECASE)
        for act in acts:
            provisions.append({
                'type': 'act',
                'reference': act,
                'confidence': 0.9
            })
        
        return provisions
    
    def _extract_advocate_info(self, case: Case) -> Dict[str, Any]:
        """Extract advocate/lawyer information"""
        advocate_info = {
            'petitioner_advocates': [],
            'respondent_advocates': [],
            'total_advocates': 0
        }
        
        # Try to get advocate info from case title or other fields
        text_sources = [
            case.case_title or '',
            getattr(case, 'advocates_petitioner', '') if hasattr(case, 'advocates_petitioner') else '',
            getattr(case, 'advocates_respondent', '') if hasattr(case, 'advocates_respondent') else ''
        ]
        
        combined_text = ' '.join(text_sources)
        
        # Basic advocate patterns
        import re
        advocate_patterns = [
            r'advocate[s]?\s*:?\s*([A-Z][a-zA-Z\s\.]+)',
            r'counsel\s*:?\s*([A-Z][a-zA-Z\s\.]+)',
            r'lawyer[s]?\s*:?\s*([A-Z][a-zA-Z\s\.]+)'
        ]
        
        advocates_found = []
        for pattern in advocate_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            advocates_found.extend(matches[:3])  # Limit to 3 per pattern
        
        # Clean and deduplicate
        unique_advocates = list(set([adv.strip() for adv in advocates_found if len(adv.strip()) > 3]))
        
        advocate_info['petitioner_advocates'] = unique_advocates[:2]  # First 2 for petitioner
        advocate_info['respondent_advocates'] = unique_advocates[2:4]  # Next 2 for respondent
        advocate_info['total_advocates'] = len(unique_advocates)
        
        return advocate_info
    
    def _extract_procedural_history(self, case: Case) -> List[Dict[str, Any]]:
        """Extract procedural history and events"""
        history = []
        
        # Basic procedural events based on available data
        if hasattr(case, 'institution_date') and case.institution_date:
            history.append({
                'event': 'Case Filed',
                'date': case.institution_date.strftime('%Y-%m-%d') if hasattr(case.institution_date, 'strftime') else str(case.institution_date),
                'type': 'filing'
            })
        
        if hasattr(case, 'hearing_date') and case.hearing_date:
            history.append({
                'event': 'Hearing Scheduled',
                'date': case.hearing_date.strftime('%Y-%m-%d') if hasattr(case.hearing_date, 'strftime') else str(case.hearing_date),
                'type': 'hearing'
            })
        
        if hasattr(case, 'disposal_date') and case.disposal_date:
            history.append({
                'event': 'Case Disposed',
                'date': case.disposal_date.strftime('%Y-%m-%d') if hasattr(case.disposal_date, 'strftime') else str(case.disposal_date),
                'type': 'disposal'
            })
        
        # Sort by date if possible
        try:
            history.sort(key=lambda x: x['date'])
        except:
            pass  # Skip sorting if date format issues
        
        return history
    
    def _summarize_orders(self, case: Case) -> Dict[str, Any]:
        """Summarize orders and judgments"""
        summary = {
            'total_orders': 0,
            'order_types': [],
            'latest_order': None,
            'has_final_judgment': False
        }
        
        # Try to get orders from related models if they exist
        try:
            if hasattr(case, 'orders_data'):
                orders = case.orders_data.all()
                summary['total_orders'] = len(orders)
                
                if orders:
                    # Get latest order
                    latest = orders.first()
                    if hasattr(latest, 'order_date'):
                        summary['latest_order'] = latest.order_date.strftime('%Y-%m-%d') if hasattr(latest.order_date, 'strftime') else str(latest.order_date)
            
            # Check for judgments
            if hasattr(case, 'judgement_data'):
                judgments = case.judgement_data.all()
                summary['has_final_judgment'] = len(judgments) > 0
                
        except Exception:
            # If related models don't exist or have issues, use basic info
            status = (case.status or '').lower()
            if any(word in status for word in ['decided', 'disposed', 'dismissed']):
                summary['has_final_judgment'] = True
        
        return summary
    
    def _classify_case_type(self, case: Case) -> Dict[str, Any]:
        """Classify case type based on comprehensive analysis"""
        classification = {
            'primary_type': 'unknown',
            'secondary_types': [],
            'confidence': 0.0,
            'indicators': []
        }
        
        # Analyze case number
        case_number = case.case_number or ''
        
        # Criminal case indicators
        criminal_patterns = [
            r'\b(Crl|Criminal|FIR|Bail|Appeal|Revision)\b',
            r'\b(Murder|Theft|Fraud|Robbery|Assault)\b',
            r'\b(PPC|Police|Investigation)\b'
        ]
        
        # Civil case indicators
        civil_patterns = [
            r'\b(Civil|Contract|Property|Rent|Recovery)\b',
            r'\b(Suit|Damages|Injunction|Declaration)\b',
            r'\b(CPC|Plaintiff|Defendant)\b'
        ]
        
        # Constitutional case indicators
        constitutional_patterns = [
            r'\b(Writ|Petition|Constitutional|Fundamental Rights)\b',
            r'\b(Article \d+|Constitution|Due Process)\b',
            r'\b(Habeas Corpus|Mandamus|Certiorari)\b'
        ]
        
        # Score each category
        all_text = ' '.join([
            case_number, case.case_title or '', case.bench or ''
        ])
        
        criminal_score = sum(1 for pattern in criminal_patterns if re.search(pattern, all_text, re.IGNORECASE))
        civil_score = sum(1 for pattern in civil_patterns if re.search(pattern, all_text, re.IGNORECASE))
        constitutional_score = sum(1 for pattern in constitutional_patterns if re.search(pattern, all_text, re.IGNORECASE))
        
        # Determine primary type
        scores = {
            'criminal': criminal_score,
            'civil': civil_score,
            'constitutional': constitutional_score
        }
        
        if max(scores.values()) > 0:
            classification['primary_type'] = max(scores, key=scores.get)
            classification['confidence'] = max(scores.values()) / (sum(scores.values()) or 1)
            classification['indicators'] = [k for k, v in scores.items() if v > 0]
        
        return classification
    
    def _extract_subject_matter(self, case: Case) -> List[str]:
        """Extract legal subject matter from case content"""
        subject_matters = set()
        
        # Subject matter keywords mapping
        subject_mapping = {
            'property': ['property', 'land', 'plot', 'house', 'estate', 'ownership', 'title'],
            'contract': ['contract', 'agreement', 'breach', 'performance', 'damages'],
            'family': ['marriage', 'divorce', 'custody', 'maintenance', 'inheritance'],
            'commercial': ['business', 'trade', 'company', 'partnership', 'commercial'],
            'employment': ['employment', 'service', 'salary', 'termination', 'pension'],
            'tax': ['tax', 'income', 'sales tax', 'customs', 'revenue'],
            'banking': ['bank', 'loan', 'mortgage', 'finance', 'credit'],
            'insurance': ['insurance', 'policy', 'claim', 'coverage', 'premium'],
            'intellectual_property': ['patent', 'trademark', 'copyright', 'intellectual'],
            'environmental': ['environment', 'pollution', 'waste', 'green', 'climate']
        }
        
        # Analyze all text content
        all_text = ' '.join([
            case.case_title or '',
            case.bench or '',
            ' '.join([order.description or '' for order in case.orders_data.all()[:5]])  # Limit for performance
        ]).lower()
        
        # Match subject matters
        for subject, keywords in subject_mapping.items():
            if any(keyword in all_text for keyword in keywords):
                subject_matters.add(subject)
        
        return list(subject_matters)
    
    def _analyze_parties(self, case: Case) -> Dict[str, Any]:
        """Analyze parties for intelligent classification"""
        parties_info = {
            'party_types': [],
            'government_involved': False,
            'corporate_parties': [],
            'individual_parties': [],
            'legal_relationship': 'unknown'
        }
        
        # Extract parties from title
        case_title = case.case_title or ''
        
        # Government entity patterns
        govt_patterns = [
            r'\b(State|Government|Federal|Provincial|Commissioner|Collector)\b',
            r'\b(WAPDA|PTCL|Railways|PIA|Steel Mills)\b',
            r'\b(Secretary|Director|Minister|Department)\b'
        ]
        
        # Corporate patterns
        corporate_patterns = [
            r'\b\w+\s*(Pvt\.?\s*Ltd\.?|Limited|Corporation|Company|Bank|Industries)\b',
            r'\bM/[Ss]\.?\s*\w+',
            r'\b\w+\s*&\s*Co\.?\b'
        ]
        
        # Check for government involvement
        parties_info['government_involved'] = any(
            re.search(pattern, case_title, re.IGNORECASE) for pattern in govt_patterns
        )
        
        # Extract corporate parties
        for pattern in corporate_patterns:
            matches = re.finditer(pattern, case_title, re.IGNORECASE)
            for match in matches:
                parties_info['corporate_parties'].append(match.group().strip())
        
        # Determine legal relationship
        if 'VS' in case_title.upper() or 'V.' in case_title.upper():
            parties_info['legal_relationship'] = 'adversarial'
        elif 'AND' in case_title.upper():
            parties_info['legal_relationship'] = 'joint'
        
        return parties_info
    
    def _build_case_timeline(self, case: Case) -> List[Dict[str, Any]]:
        """Build comprehensive case timeline"""
        timeline = []
        
        # Add institution date
        if case.institution_date:
            timeline.append({
                'date': case.institution_date,
                'event': 'case_instituted',
                'description': 'Case instituted',
                'source': 'basic_info'
            })
        
        # Add orders
        for order in case.orders_data.all().order_by('created_at'):
            if order.order_date:
                timeline.append({
                    'date': order.order_date,
                    'event': 'order_passed',
                    'description': order.description or 'Order passed',
                    'source': 'orders_data',
                    'details': order.order_passed
                })
        
        # Add hearing dates from comments
        for comment in case.comments_data.all():
            if comment.next_date and comment.next_date != 'None':
                timeline.append({
                    'date': comment.next_date,
                    'event': 'hearing_scheduled',
                    'description': 'Hearing scheduled',
                    'source': 'comments_data'
                })
        
        # Sort timeline by date
        timeline.sort(key=lambda x: x.get('date', ''))
        
        return timeline
    
    def _calculate_content_richness(self, case: Case) -> float:
        """Calculate content richness score (0-1)"""
        score = 0.0
        max_score = 10.0
        
        # Basic info completeness
        if case.case_title: score += 1.0
        if case.case_number: score += 1.0
        if case.bench: score += 1.0
        if case.status: score += 1.0
        
        # Rich data availability
        if case.orders_data.exists(): score += 2.0
        if case.comments_data.exists(): score += 1.5
        if case.case_cms_data.exists(): score += 1.0
        if hasattr(case, 'judgement_data') and case.judgement_data.exists(): score += 1.5
        
        # PDF content
        try:
            from search_indexing.models import DocumentChunk
            if DocumentChunk.objects.filter(case_id=case.id).exists():
                score += 1.0
        except:
            pass
        
        return min(score / max_score, 1.0)
    
    def _calculate_data_completeness(self, case: Case) -> float:
        """Calculate data completeness score based on available fields"""
        total_fields = 0
        filled_fields = 0
        
        # Core case fields
        core_fields = [
            'case_number', 'case_title', 'status', 'institution_date'
        ]
        
        for field in core_fields:
            total_fields += 1
            if hasattr(case, field) and getattr(case, field):
                filled_fields += 1
        
        # Optional fields that boost completeness
        optional_fields = [
            'hearing_date', 'court', 'bench'
        ]
        
        for field in optional_fields:
            total_fields += 1
            if hasattr(case, field) and getattr(case, field):
                filled_fields += 1
        
        # Check for related data
        if hasattr(case, 'judgement_data'):
            total_fields += 1
            try:
                if case.judgement_data.exists():
                    filled_fields += 1
            except:
                pass
        
        if hasattr(case, 'documents'):
            total_fields += 1
            try:
                if case.documents.exists():
                    filled_fields += 1
            except:
                pass
        
        # Calculate completeness score
        if total_fields > 0:
            completeness_score = filled_fields / total_fields
        else:
            completeness_score = 0.0
        
        return min(1.0, completeness_score)
    
    def _generate_search_keywords(self, case: Case) -> List[str]:
        """Generate optimized search keywords"""
        keywords = set()
        
        # Extract from case title
        if case.case_title:
            # Split and clean title words
            title_words = re.findall(r'\b\w+\b', case.case_title.lower())
            keywords.update(word for word in title_words if len(word) > 2)
        
        # Extract from case number
        if case.case_number:
            # Extract meaningful parts from case number
            case_parts = re.findall(r'\b\w+\b', case.case_number.lower())
            keywords.update(case_parts)
        
        # Extract from orders
        for order in case.orders_data.all()[:3]:  # Limit for performance
            if order.description:
                desc_words = re.findall(r'\b\w{4,}\b', order.description.lower())
                keywords.update(desc_words[:10])  # Limit words per order
        
        # Remove common stop words
        stop_words = {'case', 'court', 'order', 'date', 'time', 'said', 'shall', 'said', 'matter'}
        keywords = keywords - stop_words
        
        return list(keywords)[:50]  # Limit total keywords
    
    def _generate_semantic_tags(self, case: Case) -> List[str]:
        """Generate semantic tags for better conceptual matching"""
        tags = set()
        
        # Legal procedure tags
        case_number = (case.case_number or '').lower()
        if 'appeal' in case_number: tags.add('appellate_proceedings')
        if 'revision' in case_number: tags.add('revisional_jurisdiction')
        if 'writ' in case_number: tags.add('constitutional_remedy')
        if 'bail' in case_number: tags.add('criminal_procedure')
        
        # Subject matter tags from title
        case_title = (case.case_title or '').lower()
        if any(word in case_title for word in ['murder', 'killing', 'death']): tags.add('homicide')
        if any(word in case_title for word in ['property', 'land', 'plot']): tags.add('property_dispute')
        if any(word in case_title for word in ['contract', 'agreement', 'breach']): tags.add('contract_law')
        if any(word in case_title for word in ['government', 'state', 'federal']): tags.add('public_law')
        
        # Court hierarchy tags
        if case.court:
            court_name = case.court.name.lower()
            if 'supreme' in court_name: tags.add('apex_court')
            elif 'high' in court_name: tags.add('high_court')
            elif 'district' in court_name: tags.add('trial_court')
        
        return list(tags)
    
    def _identify_relevance_boosters(self, case: Case) -> List[Dict[str, Any]]:
        """Identify factors that should boost search relevance"""
        boosters = []
        
        # Recent cases get boost
        if case.institution_date:
            try:
                # Simple year extraction
                year_match = re.search(r'\b(20\d{2})\b', case.institution_date)
                if year_match:
                    year = int(year_match.group())
                    if year >= 2020:
                        boosters.append({
                            'type': 'recency',
                            'factor': 'recent_case',
                            'boost': 1.2,
                            'reason': f'Case from {year}'
                        })
            except:
                pass
        
        # Cases with rich content get boost
        content_score = self._calculate_content_richness(case)
        if content_score > 0.7:
            boosters.append({
                'type': 'content_quality',
                'factor': 'rich_content',
                'boost': 1.1,
                'reason': f'High content richness ({content_score:.1%})'
            })
        
        # Decided cases get slight boost over pending
        if case.status and 'decided' in case.status.lower():
            boosters.append({
                'type': 'status',
                'factor': 'decided_case',
                'boost': 1.05,
                'reason': 'Decided case with final outcome'
            })
        
        return boosters
    
    def _load_legal_entities(self) -> Dict:
        """Load legal entities dictionary"""
        return {
            'statutes': ['PPC', 'CrPC', 'CPC', 'Constitution', 'Qanun-e-Shahadat'],
            'courts': ['Supreme Court', 'High Court', 'District Court', 'Sessions Court'],
            'procedures': ['Appeal', 'Revision', 'Writ', 'Bail', 'Petition']
        }
    
    def _load_legal_concepts(self) -> Dict:
        """Load legal concepts dictionary"""
        return {
            'criminal_law': ['murder', 'theft', 'fraud', 'assault', 'robbery'],
            'civil_law': ['contract', 'tort', 'property', 'damages', 'injunction'],
            'constitutional_law': ['fundamental rights', 'due process', 'equal protection']
        }
    
    def _load_court_hierarchy(self) -> Dict:
        """Load court hierarchy for authority scoring"""
        return {
            'supreme_court': {'level': 1, 'authority': 1.0},
            'high_court': {'level': 2, 'authority': 0.8},
            'district_court': {'level': 3, 'authority': 0.6},
            'sessions_court': {'level': 4, 'authority': 0.4}
        }
