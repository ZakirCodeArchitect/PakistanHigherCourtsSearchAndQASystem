"""
Django Admin interface for Law Information Resource
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Law, LawCategory, LawSearchLog


@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    """Admin interface for Law entries"""
    
    list_display = [
        'title', 
        'slug', 
        'get_sections_display', 
        'jurisdiction', 
        'is_active', 
        'is_featured',
        'updated_at'
    ]
    
    list_filter = [
        'is_active', 
        'is_featured', 
        'jurisdiction',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'title', 
        'slug', 
        'punishment_summary',
        'jurisdiction',
        'rights_summary',
        'what_to_do'
    ]
    
    list_editable = ['is_active', 'is_featured']
    
    readonly_fields = ['id', 'created_at', 'updated_at', 'preview_url']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'sections', 'jurisdiction')
        }),
        ('Content', {
            'fields': ('punishment_summary', 'rights_summary', 'what_to_do')
        }),
        ('Organization', {
            'fields': ('tags', 'is_active', 'is_featured')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'preview_url'),
            'classes': ('collapse',)
        }),
    )
    
    def get_sections_display(self, obj):
        """Display sections as comma-separated list"""
        return ", ".join(obj.sections) if obj.sections else "No sections"
    get_sections_display.short_description = "Sections"
    
    def preview_url(self, obj):
        """Show preview URL"""
        if obj.pk:
            url = obj.get_absolute_url()
            return format_html(
                '<a href="{}" target="_blank">View Law Entry</a>',
                url
            )
        return "Save first to generate URL"
    preview_url.short_description = "Preview URL"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related()


@admin.register(LawCategory)
class LawCategoryAdmin(admin.ModelAdmin):
    """Admin interface for Law Categories"""
    
    list_display = [
        'name', 
        'slug', 
        'color_preview', 
        'order', 
        'is_active',
        'law_count'
    ]
    
    list_filter = ['is_active', 'created_at']
    
    search_fields = ['name', 'description']
    
    list_editable = ['order', 'is_active']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Display', {
            'fields': ('color', 'icon', 'order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = "Color"
    
    def law_count(self, obj):
        """Show count of laws in this category"""
        count = Law.objects.filter(tags__contains=[obj.name]).count()
        return count
    law_count.short_description = "Laws Count"


@admin.register(LawSearchLog)
class LawSearchLogAdmin(admin.ModelAdmin):
    """Admin interface for Search Logs"""
    
    list_display = [
        'query', 
        'search_type', 
        'results_count', 
        'clicked_result',
        'user_ip',
        'created_at'
    ]
    
    list_filter = [
        'search_type', 
        'created_at',
        'results_count'
    ]
    
    search_fields = ['query', 'user_ip']
    
    readonly_fields = ['created_at']
    
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('clicked_result')
    
    def has_add_permission(self, request):
        """Disable adding search logs manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing search logs"""
        return False


# Customize admin site
admin.site.site_header = "Law Information Resource Admin"
admin.site.site_title = "Law Info Admin"
admin.site.index_title = "Manage Law Information"