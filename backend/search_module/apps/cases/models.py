from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import json
from datetime import datetime


class Court(models.Model):
    """Represents different courts in the system"""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "courts"


class Case(models.Model):
    """Main case model representing basic case information from scraper"""

    # Basic case information from scraper
    sr_number = models.CharField(max_length=20, db_index=True, blank=True, null=True)  # SR
    institution_date = models.CharField(max_length=20, blank=True, null=True)  # INSTITUTION
    case_number = models.CharField(max_length=300, db_index=True, blank=True, null=True)  # CASE_NO
    case_title = models.CharField(max_length=800, blank=True, null=True)  # CASE_TITLE
    bench = models.CharField(max_length=400, blank=True, null=True)  # BENCH
    hearing_date = models.CharField(max_length=300, blank=True, null=True)  # HEARING_DATE
    status = models.CharField(max_length=50, db_index=True, blank=True, null=True)  # STATUS
    # REMOVED: history_options (redundant UI text)
    # REMOVED: details (empty, redundant)

    # Court relationship
    court = models.ForeignKey(Court, on_delete=models.CASCADE, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.case_number} - {self.case_title[:50]}"

    # Computed properties for history data availability
    @property
    def has_orders(self):
        """Check if case has orders data"""
        return self.orders_data.exists()
    
    @property
    def has_comments(self):
        """Check if case has comments data"""
        return self.comments_data.exists()
    
    @property
    def has_case_cms(self):
        """Check if case has case CMs data"""
        return self.case_cms_data.exists()
    
    @property
    def has_judgement(self):
        """Check if case has judgement data"""
        return self.judgement_data.exists()
    
    @property
    def history_summary(self):
        """Return summary of available history data"""
        summary = []
        if self.has_orders:
            summary.append("Orders")
        if self.has_comments:
            summary.append("Comments")
        if self.has_case_cms:
            summary.append("Case CMs")
        if self.has_judgement:
            summary.append("Judgement")
        return " \n ".join(summary) if summary else "No history data"

    class Meta:
        db_table = "cases"  # Use the actual table name from database
        unique_together = []  # Removed due to nullable fields
        indexes = [
            models.Index(fields=["sr_number"]),
            models.Index(fields=["case_number"]),
            models.Index(fields=["status"]),
        ]


class CaseDetail(models.Model):
    """Detailed case information from case details modal (for 'Decided' cases)"""

    case = models.OneToOneField(
        Case, on_delete=models.CASCADE, related_name="case_detail"
    )

    # Detailed case information from scraper
    case_status = models.CharField(max_length=50, blank=True)  # CASE_STATUS
    hearing_date_detailed = models.CharField(
        max_length=200, blank=True
    )  # HEARING_DATE_DETAILED
    case_stage = models.CharField(max_length=100, blank=True)  # CASE_STAGE
    tentative_date = models.CharField(max_length=50, blank=True)  # TENTATIVE_DATE
    short_order = models.CharField(max_length=200, blank=True)  # SHORT_ORDER
    before_bench = models.CharField(max_length=400, blank=True)  # BEFORE_BENCH
    case_title_detailed = models.CharField(
        max_length=800, blank=True
    )  # CASE_TITLE_DETAILED
    advocates_petitioner = models.CharField(
        max_length=300, blank=True
    )  # ADVOCATES_PETITIONER
    advocates_respondent = models.CharField(
        max_length=300, blank=True
    )  # ADVOCATES_RESPONDENT
    case_description = models.TextField(blank=True)  # CASE_DESCRIPTION
    disposed_of_status = models.CharField(
        max_length=150, blank=True
    )  # DISPOSED_OF_STATUS
    case_disposal_date = models.CharField(
        max_length=20, blank=True
    )  # CASE_DISPOSAL_DATE
    disposal_bench = models.CharField(max_length=400, blank=True)  # DISPOSAL_BENCH
    consigned_date = models.CharField(max_length=20, blank=True)  # CONSIGNED_DATE
    
    # FIR information (for criminal cases)
    fir_number = models.CharField(max_length=50, blank=True)  # FIR_NUMBER
    fir_date = models.CharField(max_length=20, blank=True)  # FIR_DATE
    police_station = models.CharField(max_length=200, blank=True)  # POLICE_STATION
    under_section = models.CharField(max_length=200, blank=True)  # UNDER_SECTION
    incident = models.TextField(blank=True)  # INCIDENT
    name_of_accused = models.CharField(max_length=200, blank=True)  # NAME_OF_ACCUSED
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Details for {self.case.case_number}"

    class Meta:
        db_table = "case_details"  # Use the actual table name from database


class JudgementData(models.Model):
    """Judgement data from Judgement button in HISTORY column"""

    case = models.OneToOneField(
        Case, on_delete=models.CASCADE, related_name="judgement_data"
    )

    # Judgement information from scraper
    pdf_url = models.URLField(max_length=800, blank=True)  # pdf_url
    pdf_filename = models.CharField(max_length=300, blank=True)  # pdf_filename
    # REMOVED: page_title (empty, redundant)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Judgement for {self.case.case_number}"

    class Meta:
        db_table = "judgement_data"  # Use the actual table name from database


class OrdersData(models.Model):
    """Orders data from Orders button in HISTORY column (consolidated)"""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="orders_data")

    # Orders table data from scraper
    sr_number = models.CharField(max_length=20)  # row[0]
    hearing_date = models.CharField(max_length=50, blank=True)  # row[1]
    bench = models.CharField(max_length=400, blank=True)  # row[2]
    list_type = models.CharField(max_length=100, blank=True)  # row[3]
    case_stage = models.CharField(max_length=100, blank=True)  # row[4]
    short_order = models.CharField(max_length=200, blank=True)  # row[5]
    disposal_date = models.CharField(max_length=50, blank=True)  # row[6]
    view_link = models.JSONField(
        default=list, blank=True
    )  # row[7] (array of link objects)

    # Source identification
    source_type = models.CharField(max_length=20, default='main', choices=[
        ('main', 'Main Page'),
        ('detail', 'Detail Page'),
        ('hearing', 'Hearing Details'),
    ])

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.sr_number} for {self.case.case_number} ({self.source_type})"

    class Meta:
        db_table = "orders_data"  # Use the actual table name from database
        unique_together = ["case", "sr_number", "source_type"]


class CommentsData(models.Model):
    """Comments data from Comments button in HISTORY column (consolidated)"""

    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="comments_data"
    )

    # Comments table data from scraper
    compliance_date = models.CharField(max_length=50, blank=True)  # row[1]
    case_no = models.CharField(max_length=300, blank=True)  # row[2]
    case_title = models.CharField(max_length=800, blank=True)  # row[3]
    doc_type = models.CharField(max_length=100, blank=True)  # row[4]
    parties = models.CharField(max_length=300, blank=True)  # row[5]
    description = models.TextField(blank=True)  # row[6]
    view_link = models.JSONField(
        default=list, blank=True
    )  # row[7] (array of link objects)

    # Source identification
    source_type = models.CharField(max_length=20, default='main', choices=[
        ('main', 'Main Page'),
        ('detail', 'Detail Page'),
    ])

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment {self.compliance_date} for {self.case.case_number} ({self.source_type})"

    class Meta:
        db_table = "comments_data"  # Use the actual table name from database
        unique_together = ["case", "compliance_date", "case_no", "source_type"]


class CaseCmsData(models.Model):
    """Case CMs data from Case CMs button in HISTORY column (consolidated)"""

    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="case_cms_data"
    )

    # Case CMs table data from scraper
    sr_number = models.CharField(max_length=20)  # row[0]
    cm = models.CharField(max_length=300, blank=True)  # row[1]
    institution = models.CharField(max_length=50, blank=True)  # row[2]
    disposal_date = models.CharField(max_length=50, blank=True)  # row[3]
    order_passed = models.CharField(max_length=300, blank=True)  # row[4]
    description = models.CharField(max_length=300, blank=True)  # row[5]
    status = models.CharField(max_length=50, blank=True)  # row[6]

    # Source identification
    source_type = models.CharField(max_length=20, default='main', choices=[
        ('main', 'Main Page'),
        ('detail', 'Detail Page'),
    ])

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Case CM {self.sr_number} for {self.case.case_number} ({self.source_type})"

    class Meta:
        db_table = "case_cms_data"  # Use the actual table name from database
        unique_together = ["case", "sr_number", "source_type"]


class PartiesDetailData(models.Model):
    """Parties detail data from Parties button in case details modal"""

    case = models.ForeignKey(
        Case, on_delete=models.CASCADE, related_name="parties_detail_data"
    )

    # Parties table data from scraper
    party_number = models.CharField(max_length=20, blank=True)  # row[0]
    party_name = models.CharField(max_length=800, blank=True)  # row[1]
    party_side = models.CharField(max_length=100, blank=True)  # row[2]

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Party {self.party_number} for {self.case.case_number}"

    class Meta:
        db_table = "parties_detail_data"  # Use the actual table name from database
        unique_together = ["case", "party_number"]


# REMOVED: CaseHistoryData and CaseDetailOptionsData - redundant JSON storage
# These tables store the same data that's already in normalized tables


class Document(models.Model):
    """Model for storing PDF documents with metadata"""
    
    # File information
    file_path = models.CharField(max_length=1000, unique=True)  # Local file path
    file_name = models.CharField(max_length=255)  # Original filename
    file_size = models.BigIntegerField()  # File size in bytes
    sha256_hash = models.CharField(max_length=64, unique=True)  # SHA256 hash for deduplication
    total_pages = models.IntegerField(null=True, blank=True)  # Total pages in PDF
    
    # Source information
    original_url = models.URLField(max_length=1000)  # Original download URL
    download_date = models.DateTimeField(auto_now_add=True)
    
    # Processing status
    is_downloaded = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)  # Text extraction completed
    is_cleaned = models.BooleanField(default=False)  # Text cleaning completed
    
    # Error handling
    download_error = models.TextField(blank=True)  # Download error message
    processing_error = models.TextField(blank=True)  # Processing error message
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Document: {self.file_name} ({self.sha256_hash[:8]})"
    
    class Meta:
        db_table = "documents"
        indexes = [
            models.Index(fields=["sha256_hash"]),
            models.Index(fields=["is_downloaded"]),
            models.Index(fields=["is_processed"]),
            models.Index(fields=["is_cleaned"]),
        ]


class CaseDocument(models.Model):
    """Many-to-many relationship between cases and documents"""
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="case_documents")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="case_documents")
    
    # Source information (which table/row this document came from)
    source_table = models.CharField(max_length=50)  # 'orders_data', 'comments_data', etc.
    source_row_id = models.BigIntegerField()  # ID of the source row
    source_link_index = models.IntegerField(default=0)  # Index in the view_link array
    
    # Document context
    document_type = models.CharField(max_length=50, blank=True)  # 'order', 'judgment', 'comment', etc.
    document_title = models.CharField(max_length=500, blank=True)  # Title from link metadata
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Case {self.case.case_number} - Document {self.document.file_name}"
    
    class Meta:
        db_table = "case_documents"
        unique_together = ["case", "document", "source_table", "source_row_id", "source_link_index"]
        indexes = [
            models.Index(fields=["source_table"]),
            models.Index(fields=["document_type"]),
        ]


class DocumentText(models.Model):
    """Extracted and cleaned text from PDF documents"""
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="document_texts")
    
    # Page information
    page_number = models.IntegerField()  # Page number (1-based)
    
    # Text content
    raw_text = models.TextField()  # Raw extracted text
    clean_text = models.TextField(blank=True)  # Cleaned text (after processing)
    
    # Processing metadata
    extraction_method = models.CharField(max_length=20, default='pymupdf')  # 'pymupdf', 'ocr'
    confidence_score = models.FloatField(null=True, blank=True)  # OCR confidence if applicable
    processing_time = models.FloatField(null=True, blank=True)  # Processing time in seconds
    
    # Quality indicators
    has_text = models.BooleanField(default=True)  # Whether page has extractable text
    needs_ocr = models.BooleanField(default=False)  # Whether OCR was needed
    is_cleaned = models.BooleanField(default=False)  # Whether text has been cleaned
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Document {self.document.file_name} - Page {self.page_number}"
    
    class Meta:
        db_table = "document_texts"
        unique_together = ["document", "page_number"]
        indexes = [
            models.Index(fields=["page_number"]),
            models.Index(fields=["extraction_method"]),
            models.Index(fields=["has_text"]),
            models.Index(fields=["needs_ocr"]),
        ]


class UnifiedCaseView(models.Model):
    """Unified view combining case metadata and PDF content"""
    
    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="unified_view")
    
    # Case metadata (from existing tables)
    case_metadata = models.JSONField(default=dict)  # Structured case information
    
    # PDF content summary
    pdf_content_summary = models.JSONField(default=dict)  # Summary of PDF content
    
    # Status flags
    has_pdf = models.BooleanField(default=False)
    text_extracted = models.BooleanField(default=False)
    text_cleaned = models.BooleanField(default=False)
    metadata_complete = models.BooleanField(default=False)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Unified View: {self.case.case_number}"
    
    class Meta:
        db_table = "unified_case_views"
        indexes = [
            models.Index(fields=["has_pdf"]),
            models.Index(fields=["text_extracted"]),
            models.Index(fields=["text_cleaned"]),
            models.Index(fields=["metadata_complete"]),
            models.Index(fields=["is_processed"]),
        ]


class ViewLinkData(models.Model):
    """Dedicated model for VIEW column links from various tables"""

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="view_links", null=True, blank=True)

    # Link information
    href = models.URLField(max_length=800, null=True, blank=True)  # The actual URL
    title = models.CharField(max_length=200, blank=True)  # Link title/tooltip
    link_text = models.CharField(max_length=200, blank=True)  # Display text

    # Source information
    source_table = models.CharField(
        max_length=50, null=True, blank=True
    )  # 'orders', 'comments', 'hearing_details', etc.
    source_row_sr = models.CharField(
        max_length=20, blank=True
    )  # SR number from source row

    # File information
    file_type = models.CharField(max_length=20, blank=True)  # 'pdf', 'doc', etc.

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"View link {self.href[:50] if self.href else 'N/A'} for {self.case.case_number if self.case else 'N/A'}"

    class Meta:
        db_table = "view_link_data"
        unique_together = ["case", "href"]
        indexes = [
            models.Index(fields=["source_table"]),
            models.Index(fields=["file_type"]),
        ]


class Term(models.Model):
    """Extracted legal terms with canonical forms"""
    
    # Term identification
    type = models.CharField(max_length=50, db_index=True)  # 'section', 'statute', 'citation', 'court', 'judge'
    canonical = models.CharField(max_length=500, db_index=True)  # Normalized canonical form
    
    # Statute-specific fields (optional)
    statute_code = models.CharField(max_length=50, blank=True, null=True)  # 'ppc', 'crpc', 'cpc', etc.
    section_num = models.CharField(max_length=50, blank=True, null=True)  # '302-b', '497', etc.
    
    # Metadata
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    occurrence_count = models.IntegerField(default=0)  # Total occurrences across all cases
    
    def __str__(self):
        if self.statute_code and self.section_num:
            return f"{self.type}: {self.statute_code}:{self.section_num}"
        return f"{self.type}: {self.canonical}"
    
    class Meta:
        db_table = "terms"
        unique_together = ["type", "canonical"]
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["canonical"]),
            models.Index(fields=["statute_code", "section_num"]),
        ]


class TermOccurrence(models.Model):
    """Specific occurrences of terms in case documents"""
    
    # Relationships
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="occurrences")
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="term_occurrences")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="term_occurrences", null=True, blank=True)
    
    # Location information (mandatory)
    start_char = models.IntegerField()  # Character position where term starts
    end_char = models.IntegerField()    # Character position where term ends
    
    # Optional location information
    page_no = models.IntegerField(null=True, blank=True)  # Page number if available
    
    # Extraction metadata
    surface = models.CharField(max_length=500)  # Original text as found
    confidence = models.FloatField(default=0.0)  # Confidence score (0.0-1.0)
    source_rule = models.CharField(max_length=100)  # Which extraction rule matched
    rules_version = models.CharField(max_length=20)  # Version of rules used
    
    # Processing metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.term} in {self.case.case_number} at chars {self.start_char}-{self.end_char}"
    
    class Meta:
        db_table = "term_occurrences"
        unique_together = ["term", "case", "start_char", "end_char"]
        indexes = [
            models.Index(fields=["term_id"]),
            models.Index(fields=["case_id"]),
            models.Index(fields=["document_id"]),
            models.Index(fields=["page_no"]),
            models.Index(fields=["confidence"]),
            models.Index(fields=["rules_version"]),
        ]


class VocabularyProcessingLog(models.Model):
    """Log of vocabulary extraction processing for idempotency"""
    
    # Processing identification
    rules_version = models.CharField(max_length=20, db_index=True)
    text_hash = models.CharField(max_length=64, db_index=True)  # SHA256 hash of processed text
    
    # Processing metadata
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="vocab_processing_logs")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="vocab_processing_logs", null=True, blank=True)
    
    # Processing results
    terms_extracted = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0.0)  # Processing time in seconds
    
    # Status
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Vocab processing {self.rules_version} for {self.case.case_number} ({self.text_hash[:8]})"
    
    class Meta:
        db_table = "vocabulary_processing_logs"
        unique_together = ["rules_version", "text_hash", "case", "document"]
        indexes = [
            models.Index(fields=["rules_version"]),
            models.Index(fields=["text_hash"]),
            models.Index(fields=["is_successful"]),
        ]
