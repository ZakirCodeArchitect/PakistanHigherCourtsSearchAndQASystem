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
    sr_number = models.CharField(max_length=20, db_index=True)  # SR
    institution_date = models.CharField(max_length=20, blank=True)  # INSTITUTION
    case_number = models.CharField(max_length=300, db_index=True)  # CASE_NO
    case_title = models.CharField(max_length=800)  # CASE_TITLE
    bench = models.CharField(max_length=400, blank=True)  # BENCH
    hearing_date = models.CharField(max_length=300, blank=True)  # HEARING_DATE
    status = models.CharField(max_length=50, db_index=True)  # STATUS
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
        unique_together = ["sr_number", "case_number"]
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
