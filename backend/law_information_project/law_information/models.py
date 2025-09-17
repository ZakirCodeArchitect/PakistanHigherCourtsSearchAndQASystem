"""
Law Information Resource Models
Based on the data model specification for public-friendly legal information
"""

from django.db import models
from django.utils import timezone
import uuid


class Law(models.Model):
    """
    Model for storing law information entries
    Based on the PostgreSQL data model specification
    """
    
    # Primary key - UUID for scalability
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # URL-safe identifier for public access
    slug = models.CharField(
        max_length=200, 
        unique=True, 
        help_text="URL-safe identifier (e.g., 'ppc-379-theft')"
    )
    
    # Law title
    title = models.CharField(
        max_length=500,
        help_text="Law title (e.g., 'Theft - PPC 379')"
    )
    
    # Applicable legal sections (array of text)
    sections = models.JSONField(
        default=list,
        help_text="Array of legal sections (e.g., ['PPC 379'])"
    )
    
    # Punishment summary
    punishment_summary = models.TextField(
        help_text="Summary of punishment for the offense"
    )
    
    # Jurisdiction information
    jurisdiction = models.CharField(
        max_length=300,
        help_text="Jurisdiction/body (e.g., 'Magistrate/Sessions Court')"
    )
    
    # Rights summary (newline-separated)
    rights_summary = models.TextField(
        help_text="Rights of complainant/accused (newline-separated bullets)"
    )
    
    # What to do steps (newline-separated)
    what_to_do = models.TextField(
        help_text="Checklist/steps for what to do (newline-separated)"
    )
    
    # Searchable tags (array of text)
    tags = models.JSONField(
        default=list,
        help_text="Searchable tags (e.g., ['theft', 'property', 'criminal'])"
    )
    
    # Category (optional)
    category = models.ForeignKey(
        'LawCategory', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Primary category for this law"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status fields
    is_active = models.BooleanField(default=True, help_text="Whether this law entry is active")
    is_featured = models.BooleanField(default=False, help_text="Whether to show in featured laws")
    
    class Meta:
        db_table = "laws"
        ordering = ['title']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        """Get the URL for this law entry"""
        from django.urls import reverse
        return reverse('law_information:law_detail', kwargs={'slug': self.slug})
    
    def get_sections_display(self):
        """Get formatted display of sections"""
        if not self.sections:
            return "No sections specified"
        return ", ".join(self.sections)
    
    def get_tags_display(self):
        """Get formatted display of tags"""
        if not self.tags:
            return []
        return self.tags
    
    def get_rights_list(self):
        """Get rights as a list (split by newlines)"""
        if not self.rights_summary:
            return []
        return [right.strip() for right in self.rights_summary.split('\n') if right.strip()]
    
    def get_steps_list(self):
        """Get steps as a list (split by newlines)"""
        if not self.what_to_do:
            return []
        return [step.strip() for step in self.what_to_do.split('\n') if step.strip()]


class LawCategory(models.Model):
    """
    Categories for organizing laws (optional enhancement)
    """
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#007bff", help_text="Hex color code")
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class name")
    
    # Ordering
    order = models.PositiveIntegerField(default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "law_categories"
        ordering = ['order', 'name']
        verbose_name_plural = "Law Categories"
    
    def __str__(self):
        return self.name


class LawSearchLog(models.Model):
    """
    Log search queries for analytics and improvement
    """
    
    query = models.CharField(max_length=500)
    results_count = models.PositiveIntegerField(default=0)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Search metadata
    search_type = models.CharField(
        max_length=50, 
        default="keyword",
        choices=[
            ('keyword', 'Keyword Search'),
            ('tag', 'Tag Search'),
            ('section', 'Section Search'),
        ]
    )
    
    # Results
    clicked_result = models.ForeignKey(
        Law, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Which result was clicked (if any)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "law_search_logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['created_at']),
            models.Index(fields=['search_type']),
        ]
    
    def __str__(self):
        return f"Search: {self.query[:50]}... ({self.results_count} results)"