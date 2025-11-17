import logging
import re
from collections import Counter
from typing import Dict, List, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Prefetch, Q

from apps.cases.models import (
    Case,
    CaseDocument,
    CaseSearchProfile,
    DocumentText,
    PartiesDetailData,
)

logger = logging.getLogger(__name__)


SUBJECT_KEYWORDS: Dict[str, List[str]] = {
    "criminal_murder": [
        "murder",
        "homicide",
        "section 302",
        "302",
        "punishment for qatl",
        "intentional murder",
    ],
    "criminal_harassment": [
        "harassment",
        "harass",
        "sexual harassment",
        "workplace harassment",
        "cyber harassment",
    ],
    "criminal_bail": [
        "bail",
        "remand",
        "custody",
        "anticipatory bail",
        "post arrest bail",
        "pre arrest bail",
    ],
    "criminal_general": [
        "fir",
        "ppc",
        "crpc",
        "charge",
        "conviction",
        "acquittal",
        "criminal revision",
        "remand report",
        "remand application",
    ],
    "anti_terrorism": [
        "anti-terrorism",
        "ata",
        "7 ata",
        "terrorism",
        "anti terrorism court",
    ],
    "narcotics": ["narcotics", "cns", "15 cns", "drug", "drug trafficking"],
    "tax": [
        "tax",
        "fbr",
        "federal board of revenue",
        "income tax",
        "sales tax",
        "customs",
        "revenue",
        "withholding",
        "assessment order",
    ],
    "banking": [
        "banking",
        "finance facility",
        "loan",
        "mortgage",
        "recovery of finance",
        "default",
        "markup",
    ],
    "company": [
        "secp",
        "corporate",
        "company",
        "winding up",
        "scheme of arrangement",
        "shareholder",
        "director",
        "board meeting",
    ],
    "constitutional": [
        "writ petition",
        "constitutional",
        "fundamental rights",
        "article 199",
        "jurisdiction",
        "mandamus",
        "certiorari",
        "habeas corpus",
    ],
    "administrative": [
        "administrative decision",
        "regulatory",
        "authority",
        "discretion",
        "blacklisting",
        "show cause notice",
    ],
    "labour": [
        "service",
        "employment",
        "appointment",
        "termination",
        "seniority",
        "pension",
        "dismissal",
        "reinstatement",
    ],
    "family": [
        "custody",
        "guardianship",
        "marriage",
        "divorce",
        "maintenance",
        "khula",
        "dower",
        "guardians and wards",
    ],
    "property": [
        "property",
        "land",
        "title",
        "ownership",
        "possession",
        "encroachment",
        "demarcation",
        "mutation",
        "benami",
    ],
    "tenancy": [
        "rent",
        "tenant",
        "landlord",
        "eviction",
        "rental ordinance",
        "ejectment",
    ],
    "anti_corruption": [
        "nab",
        "national accountability bureau",
        "corruption",
        "misuse of authority",
        "plea bargain",
    ],
    "commercial": [
        "contract",
        "agreement",
        "specific performance",
        "commercial dispute",
        "damages",
        "breach",
        "supply of goods",
    ],
    "intellectual_property": [
        "trademark",
        "copyright",
        "patent",
        "passing off",
        "intellectual property",
    ],
    "environmental": [
        "environment",
        "pollution",
        "epa",
        "environmental protection agency",
        "environmental impact",
        "waste",
    ],
    "education": [
        "university",
        "school",
        "student",
        "admission",
        "exam",
        "board of intermediate",
    ],
    "healthcare": [
        "hospital",
        "medical",
        "doctor",
        "pmc",
        "medical negligence",
        "drug regulatory authority",
    ],
    "public_interest": [
        "public interest",
        "suo motu",
        "environmental justice",
        "fundamental rights",
        "public at large",
    ],
    "election": [
        "election",
        "nomination papers",
        "returning officer",
        "delimitation",
        "election tribunal",
    ],
}

SUBJECT_LABELS: Dict[str, str] = {
    "criminal_murder": "Criminal: Murder",
    "criminal_harassment": "Criminal: Harassment",
    "criminal_bail": "Criminal: Bail & Custody",
    "criminal_general": "Criminal: General",
    "anti_terrorism": "Criminal: Anti-terrorism",
    "narcotics": "Criminal: Narcotics",
    "tax": "Taxation & Revenue",
    "banking": "Banking & Finance",
    "company": "Company & Corporate",
    "constitutional": "Constitutional & Writs",
    "administrative": "Administrative Law",
    "labour": "Labour & Service",
    "family": "Family & Guardianship",
    "property": "Property & Land",
    "tenancy": "Tenancy & Rent",
    "anti_corruption": "Anti-Corruption / NAB",
    "commercial": "Commercial & Contracts",
    "intellectual_property": "Intellectual Property",
    "environmental": "Environmental Law",
    "education": "Education",
    "healthcare": "Healthcare & Medical",
    "public_interest": "Public Interest Litigation",
    "election": "Election Matters",
}

KEYWORD_STOPWORDS = {
    "the",
    "and",
    "of",
    "for",
    "with",
    "that",
    "this",
    "from",
    "shall",
    "thereof",
    "whereas",
    "being",
    "under",
    "court",
    "case",
    "order",
    "bench",
    "petition",
    "respondent",
    "petitioner",
    "versus",
    "vs",
    "etc",
}

SECTION_PATTERN = re.compile(
    r"((section|article|order|rule)\s+\d+[a-z]?(\(\d+\))?|"
    r"\b\d+\s*ppc\b|\bppc\s*\d+|\bcr\.p\.c\.?\s*\d+|\bs\.?\s*\d+\b|\b\d+\s*c\.p\.c\b)",
    re.IGNORECASE,
)

CASE_NUMBER_SPLIT = re.compile(r"[\/\-\s\(\)\.]+")

BOILERPLATE_PATTERNS = [
    re.compile(r"\bIN THE ISLAMABAD HIGH COURT\b", re.IGNORECASE),
    re.compile(r"\bJUDICIAL DEPARTMENT\b", re.IGNORECASE),
    re.compile(r"\bORDER SHEET\b", re.IGNORECASE),
    re.compile(r"\bS\. No\. of order/ proceedings\b", re.IGNORECASE),
    re.compile(r"\bDate of order/ Proceedings\b", re.IGNORECASE),
    re.compile(r"\bOrder with signature of Judge\b", re.IGNORECASE),
]

SECTION_HEADER_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bheld[:\-]?", re.IGNORECASE), "Held"),
    (re.compile(r"\brelief[:\-]?", re.IGNORECASE), "Relief"),
    (re.compile(r"\border[:\-]?", re.IGNORECASE), "Order"),
    (re.compile(r"\border sheet", re.IGNORECASE), "Order Sheet"),
    (re.compile(r"\bjudgment[:\-]?", re.IGNORECASE), "Judgment"),
    (re.compile(r"\bobservation[:\-]?", re.IGNORECASE), "Observations"),
    (re.compile(r"\bfacts[:\-]?", re.IGNORECASE), "Facts"),
    (re.compile(r"\bbackground[:\-]?", re.IGNORECASE), "Background"),
    (re.compile(r"\barguments[:\-]?", re.IGNORECASE), "Arguments"),
    (re.compile(r"\bcontentions[:\-]?", re.IGNORECASE), "Contentions"),
    (re.compile(r"\bissues for determination", re.IGNORECASE), "Issues for Determination"),
    (re.compile(r"\bquestions for determination", re.IGNORECASE), "Questions for Determination"),
    (re.compile(r"\bstatutory framework", re.IGNORECASE), "Statutory Framework"),
    (re.compile(r"\bcitation[:\-]?", re.IGNORECASE), "Citations"),
]


class Command(BaseCommand):
    help = "Generate cleaned titles, party tokens, and subject tags for cases with PDF text."

    def add_arguments(self, parser):
        parser.add_argument(
            "--case-id",
            type=int,
            help="Process a specific case id.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of cases processed.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show computed profiles without saving them.",
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Force regeneration even if a profile already exists.",
        )

    def handle(self, *args, **options):
        case_id = options.get("case_id")
        limit = options.get("limit")
        dry_run = options.get("dry_run")
        refresh = options.get("refresh")

        cases = self._select_cases(case_id, limit, refresh)

        if not cases:
            self.stdout.write(self.style.WARNING("No cases found to enrich."))
            return

        processed = 0
        created = 0
        updated = 0

        for case in cases:
            profile_payload = self._build_profile_payload(case)
            processed += 1

            if dry_run:
                self._print_preview(case, profile_payload)
                continue

            with transaction.atomic():
                defaults = {
                    "clean_case_title": profile_payload["clean_case_title"],
                    "normalized_case_title": profile_payload["normalized_case_title"],
                    "party_tokens": profile_payload["party_tokens"],
                    "subject_tags": profile_payload["subject_tags"],
                    "keyword_highlights": profile_payload["keyword_highlights"],
                    "summary_text": profile_payload["summary_text"],
                    "metadata": profile_payload["metadata"],
                    "case_number_tokens": profile_payload["case_number_tokens"],
                    "section_tags": profile_payload["section_tags"],
                }

                profile, created_flag = CaseSearchProfile.objects.update_or_create(
                    case=case,
                    defaults=defaults,
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed} cases. Created {created} profiles, updated {updated}."
            )
        )

    def _select_cases(
        self, case_id: Optional[int], limit: Optional[int], refresh: bool
    ) -> List[Case]:
        qs = (
            Case.objects.filter(
                case_documents__document__document_texts__clean_text__isnull=False
            )
            .annotate(text_pages=Count("case_documents__document__document_texts"))
            .prefetch_related(
                Prefetch(
                    "parties_detail_data",
                    queryset=PartiesDetailData.objects.all(),
                ),
                Prefetch(
                    "case_documents",
                    queryset=CaseDocument.objects.select_related("document"),
                ),
            )
            .distinct()
        )

        if case_id:
            qs = qs.filter(id=case_id)

        if not refresh:
            qs = qs.filter(Q(search_profile__isnull=True))

        if limit:
            qs = qs[:limit]

        return list(qs)

    def _build_profile_payload(self, case: Case) -> Dict[str, any]:
        title_original = case.case_title or ""
        clean_title = self._clean_title(title_original)
        parties = self._extract_parties(case, clean_title)
        normalized_title = clean_title.lower()

        text_blob, text_sample = self._collect_document_text(case)
        subject_tags, keyword_matches = self._detect_subject_tags(text_blob)
        section_tags = self._extract_section_tags(text_blob, keyword_matches)
        section_headers = self._extract_section_headers(text_blob)
        keyword_highlights = self._select_highlights(keyword_matches, text_blob)
        abstract_text, abstract_sentences = self._generate_abstract(
            text_blob, subject_tags, section_tags, parties
        )

        summary_text = self._compose_summary(
            case,
            clean_title,
            parties,
            subject_tags,
            section_tags,
            abstract_text,
            keyword_highlights,
            text_sample,
        )

        metadata = {
            "original_title": title_original,
            "text_sample": text_sample,
            "subject_matches": keyword_matches,
            "pages_indexed": len(text_blob["pages"]),
            "subject_labels": self._format_subject_labels(subject_tags),
            "section_headers": section_headers,
            "abstract_text": abstract_text,
            "abstract_sentences": abstract_sentences,
        }

        return {
            "clean_case_title": clean_title,
            "normalized_case_title": normalized_title,
            "party_tokens": parties,
            "subject_tags": subject_tags,
            "keyword_highlights": keyword_highlights,
            "summary_text": summary_text,
            "case_number_tokens": self._extract_case_number_tokens(case),
            "section_tags": section_tags,
            "metadata": metadata,
        }

    def _clean_title(self, title: str) -> str:
        if not title or title.strip() == ".":
            return ""

        cleaned = re.sub(r"\s+", " ", title).strip(" ,.;-")
        cleaned = re.sub(r"\b(vs|v\.?)\b", "vs", cleaned, flags=re.IGNORECASE)

        # Collapse duplicate spacing around VS
        cleaned = cleaned.replace(" vs ", " vs ")

        # Avoid all lower / all upper by using title-case heuristics
        if cleaned.isupper():
            cleaned = cleaned.title()

        return cleaned

    def _extract_parties(self, case: Case, cleaned_title: str) -> List[str]:
        parties: List[str] = []

        def normalize_party(value: str) -> str:
            value = value.strip(" ,.;:-")
            value = re.sub(r"\s+", " ", value)
            value = re.sub(r"\betc\b\.?", "", value, flags=re.IGNORECASE)
            return value.strip()

        if cleaned_title:
            segments = re.split(r"\bvs\b", cleaned_title, flags=re.IGNORECASE)
            for segment in segments:
                segment = normalize_party(segment)
                if len(segment) >= 3:
                    parties.append(segment)

        # Fallback to parties table
        if not parties and hasattr(case, "parties_detail_data"):
            for entry in case.parties_detail_data.all():
                candidate = normalize_party(entry.party_name or "")
                if len(candidate) >= 3:
                    parties.append(candidate)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for party in parties:
            key = party.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(party)

        return deduped[:8]

    def _collect_document_text(self, case: Case) -> Tuple[Dict[str, any], str]:
        page_texts: List[str] = []
        filters = Q(document__case_documents__case=case)

        documents = DocumentText.objects.filter(filters).select_related("document")
        documents = documents.order_by("document__id", "page_number")

        max_chars = 6000
        total_chars = 0
        sample_parts: List[str] = []

        for doc_text in documents:
            snippet_raw = doc_text.clean_text or doc_text.raw_text or ""
            snippet = self._sanitize_text(snippet_raw)
            if not snippet:
                continue

            page_texts.append(snippet)

            if total_chars < max_chars:
                available = max_chars - total_chars
                excerpt = snippet[:available]
                sample_parts.append(excerpt)
                total_chars += len(excerpt)

            if total_chars >= max_chars:
                break

        blob = " ".join(page_texts)
        text_sample = " ".join(sample_parts)

        return {"text": blob, "pages": page_texts}, text_sample

    def _detect_subject_tags(self, text_blob: Dict[str, any]) -> Tuple[List[str], Dict[str, List[str]]]:
        lowered = text_blob["text"].lower()
        subject_matches: Dict[str, List[str]] = {}

        for tag, keywords in SUBJECT_KEYWORDS.items():
            matches = [kw for kw in keywords if kw.lower() in lowered]
            if matches:
                subject_matches[tag] = matches

        # Expand subject tags with inferred offence keywords
        inferred_tags = set()
        offense_keywords = {
            "criminal_murder": ["murder", "qatl", "section 302", "302"],
            "criminal_harassment": ["harassment", "sexual harassment", "harass"],
            "anti_terrorism": ["anti-terrorism", "ata", "7 ata", "terrorism"],
            "criminal_bail": ["pre arrest", "post arrest", "protective bail", "anticipatory bail"],
            "narcotics": ["narcotics", "control of narcotic", "cns", "drug trafficking"],
            "constitutional": ["fundamental right", "article 199", "constitutional jurisdiction"],
            "public_interest": ["public interest", "suo motu", "public at large"],
        }
        for tag, triggers in offense_keywords.items():
            if any(keyword in lowered for keyword in triggers):
                inferred_tags.add(tag)

        combined_tags = sorted(set(subject_matches.keys()) | inferred_tags)
        return combined_tags, subject_matches

    def _select_highlights(
        self, keyword_matches: Dict[str, List[str]], text_blob: Dict[str, any]
    ) -> List[str]:
        highlights = set()
        for matches in keyword_matches.values():
            highlights.update(matches)

        # include section tags
        for section in self._extract_section_tags(text_blob, keyword_matches):
            highlights.add(section.lower())

        if len(highlights) < 8:
            token_counter = Counter()
            for page in text_blob["pages"]:
                for token in re.findall(r"\b[A-Za-z]{4,}\b", page):
                    token_lower = token.lower()
                    if token_lower in KEYWORD_STOPWORDS:
                        continue
                    token_counter[token_lower] += 1

            for token, _ in token_counter.most_common(20):
                if len(highlights) >= 8:
                    break
                highlights.add(token)

        return sorted(highlights)[:8]

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        lines: List[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if any(pattern.search(line) for pattern in BOILERPLATE_PATTERNS):
                continue
            lines.append(line)
        cleaned = " ".join(lines)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    def _compose_summary(
        self,
        case: Case,
        clean_title: str,
        parties: List[str],
        subject_tags: List[str],
        section_tags: List[str],
        abstract_text: str,
        keyword_highlights: List[str],
        text_sample: str,
    ) -> str:
        parts: List[str] = []

        if case.case_number:
            parts.append(f"Case Number: {case.case_number}")

        if clean_title:
            parts.append(f"Title: {clean_title}")

        if parties:
            if len(parties) >= 2:
                parts.append(f"Parties: {parties[0]} vs {parties[1]}")
            else:
                parts.append(f"Parties: {parties[0]}")

        if case.status:
            parts.append(f"Status: {case.status}")

        if subject_tags:
            labels = self._format_subject_labels(subject_tags)
            parts.append(f"Subjects: {', '.join(labels)}")

        if section_tags:
            parts.append(f"Sections: {', '.join(section_tags[:5])}")

        if abstract_text:
            parts.append(f"Abstract: {abstract_text}")

        if keyword_highlights:
            parts.append(f"Keywords: {', '.join(keyword_highlights[:6])}")

        if text_sample:
            snippet = re.sub(r"\s+", " ", text_sample.strip())
            parts.append(f"Summary Snippet: {snippet[:400]}{'...' if len(snippet) > 400 else ''}")

        return " | ".join(parts)

    def _print_preview(self, case: Case, payload: Dict[str, any]) -> None:
        self.stdout.write("-" * 80)
        self.stdout.write(f"Case ID: {case.id}  Case Number: {case.case_number}")
        self.stdout.write(f"Clean Title: {payload['clean_case_title']}")
        self.stdout.write(f"Parties: {', '.join(payload['party_tokens'])}")
        self.stdout.write(f"Subject Tags: {', '.join(payload['subject_tags'])}")
        self.stdout.write(f"Keywords: {', '.join(payload['keyword_highlights'])}")
        self.stdout.write(f"Summary: {payload['summary_text'][:200]}...")

    def _extract_case_number_tokens(self, case: Case) -> List[str]:
        case_number = case.case_number or ""
        raw_tokens = [t for t in CASE_NUMBER_SPLIT.split(case_number) if t]
        normalized = []
        for token in raw_tokens:
            token = token.strip()
            if not token or len(token) < 2:
                continue
            normalized.append(token.upper())
        return normalized

    def _extract_section_tags(
        self, text_blob: Dict[str, any], subject_matches: Dict[str, List[str]]
    ) -> List[str]:
        section_hits = set()
        for match in SECTION_PATTERN.finditer(text_blob["text"]):
            normalized = self._normalize_section_reference(match.group(0))
            if normalized:
                section_hits.add(normalized)

        # include keywords that already mention sections/articles
        for matches in subject_matches.values():
            for keyword in matches:
                normalized = self._normalize_section_reference(keyword)
                if normalized:
                    section_hits.add(normalized)

        return sorted(section_hits)

    def _extract_section_headers(self, text_blob: Dict[str, any]) -> List[str]:
        headers: Dict[str, int] = {}
        for page in text_blob["pages"]:
            lowered = page.lower()
            for pattern, label in SECTION_HEADER_PATTERNS:
                if pattern.search(lowered):
                    headers[label] = headers.get(label, 0) + 1

        # keep headers that appear at least once, sorted by frequency desc then name
        sorted_headers = sorted(headers.items(), key=lambda item: (-item[1], item[0]))
        return [label for label, _ in sorted_headers][:10]

    def _normalize_section_reference(self, raw_value: str) -> str:
        if not raw_value:
            return ""

        cleaned = re.sub(r"\s+", " ", raw_value.strip().lower())
        if not cleaned:
            return ""

        number_match = re.search(r"(\d+[a-z]?(?:\(\d+\))?)", cleaned)
        if not number_match:
            return cleaned.title()

        number = number_match.group(1).upper()
        prefix = "Section"
        if cleaned.startswith("article"):
            prefix = "Article"
        elif cleaned.startswith("order"):
            prefix = "Order"
        elif cleaned.startswith("rule"):
            prefix = "Rule"

        act = ""
        if "ppc" in cleaned:
            act = "PPC"
        elif "c.p.c" in cleaned or "cpc" in cleaned:
            act = "CPC"
        elif "cr.p.c" in cleaned or "crpc" in cleaned:
            act = "Cr.P.C"

        reference = f"{prefix} {number}"
        if act:
            reference = f"{reference} {act}"

        return reference

    def _format_subject_labels(self, subject_tags: List[str]) -> List[str]:
        labels = []
        for tag in subject_tags:
            label = SUBJECT_LABELS.get(tag, tag.replace("_", " ").title())
            labels.append(label)
        return labels

    def _generate_abstract(
        self,
        text_blob: Dict[str, any],
        subject_tags: List[str],
        section_tags: List[str],
        parties: List[str],
    ) -> Tuple[str, List[str]]:
        text = text_blob.get("text", "")
        sentences = self._split_sentences(text)
        if not sentences:
            return "", []

        subject_terms = set()
        for tag in subject_tags:
            for keyword in SUBJECT_KEYWORDS.get(tag, []):
                subject_terms.add(keyword.lower())
            subject_terms.update(tag.replace("_", " ").lower().split())

        section_terms = {tag.lower() for tag in section_tags}
        party_terms = {part.lower() for part in parties}

        scored: List[Tuple[float, int, str]] = []
        for idx, sentence in enumerate(sentences):
            sentence_clean = sentence.strip()
            if len(sentence_clean) < 40 or len(sentence_clean) > 350:
                continue

            lowered = sentence_clean.lower()
            score = 0.0

            score += sum(1.0 for term in subject_terms if term and term in lowered)
            score += sum(1.2 for term in section_terms if term and term in lowered)
            score += sum(1.1 for term in party_terms if term and term in lowered)

            if idx == 0:
                score += 1.0
            elif idx == 1:
                score += 0.5

            if score > 0:
                scored.append((score, idx, sentence_clean))

        if not scored:
            fallback = [s.strip() for s in sentences[:2] if len(s.strip()) > 0]
            abstract = " ".join(fallback[:2]).strip()
            return abstract[:600], fallback[:2]

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = []
        for score, idx, sentence_clean in scored:
            if len(selected) >= 3:
                break
            if sentence_clean not in selected:
                selected.append(sentence_clean)

        abstract_text = " ".join(selected).strip()
        if len(abstract_text) > 600:
            abstract_text = abstract_text[:597].rstrip() + "..."

        return abstract_text, selected

    def _split_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        raw_sentences = re.split(r"(?<=[\.!?])\s+", text)
        sentences = []
        for sentence in raw_sentences:
            cleaned = sentence.strip()
            if cleaned:
                sentences.append(cleaned)
        return sentences

