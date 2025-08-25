from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Court,
    Case,
    CaseDetail,
    JudgementData,
    OrdersData,
    CommentsData,
    CaseCmsData,
    PartiesDetailData,
    ViewLinkData,
    # REMOVED: CaseHistoryData, CaseDetailOptionsData - redundant models
)


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'sr_number', 
        'case_title_short', 
        'status', 
        'bench_short',
        'has_orders_display',
        'has_comments_display',
        'has_case_cms_display',
        'has_judgement_display',
        'created_at'
    ]
    list_filter = ['status', 'court', 'created_at']
    search_fields = ['case_number', 'sr_number', 'case_title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('sr_number', 'case_number', 'case_title', 'status')
        }),
        ('Court Information', {
            'fields': ('court', 'bench', 'hearing_date', 'institution_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def case_title_short(self, obj):
        return obj.case_title[:50] + "..." if len(obj.case_title) > 50 else obj.case_title
    case_title_short.short_description = 'Case Title'
    
    def bench_short(self, obj):
        return obj.bench[:30] + "..." if len(obj.bench) > 30 else obj.bench
    bench_short.short_description = 'Bench'
    
    def has_orders_display(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if obj.has_orders else 'red',
            '✓' if obj.has_orders else '✗'
        )
    has_orders_display.short_description = 'Orders'
    
    def has_comments_display(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if obj.has_comments else 'red',
            '✓' if obj.has_comments else '✗'
        )
    has_comments_display.short_description = 'Comments'
    
    def has_case_cms_display(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if obj.has_case_cms else 'red',
            '✓' if obj.has_case_cms else '✗'
        )
    has_case_cms_display.short_description = 'Case CMs'
    
    def has_judgement_display(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if obj.has_judgement else 'red',
            '✓' if obj.has_judgement else '✗'
        )
    has_judgement_display.short_description = 'Judgement'


@admin.register(CaseDetail)
class CaseDetailAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'case_status', 
        'case_stage', 
        'case_disposal_date',
        'created_at'
    ]
    list_filter = ['case_status', 'case_stage', 'created_at']
    search_fields = ['case__case_number', 'case_title_detailed']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    fieldsets = (
        ('Case Information', {
            'fields': ('case', 'case_status', 'case_stage')
        }),
        ('Hearing Information', {
            'fields': ('hearing_date_detailed', 'tentative_date', 'before_bench')
        }),
        ('Case Details', {
            'fields': ('case_title_detailed', 'case_description', 'short_order')
        }),
        ('Advocates', {
            'fields': ('advocates_petitioner', 'advocates_respondent')
        }),
        ('Disposal Information', {
            'fields': ('disposed_of_status', 'case_disposal_date', 'disposal_bench', 'consigned_date')
        }),
        ('FIR Information', {
            'fields': ('fir_number', 'fir_date', 'police_station', 'under_section', 'incident', 'name_of_accused'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JudgementData)
class JudgementDataAdmin(admin.ModelAdmin):
    list_display = ['case_number', 'pdf_filename_short', 'pdf_url_short', 'created_at']
    search_fields = ['case__case_number', 'pdf_filename']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    def pdf_filename_short(self, obj):
        return obj.pdf_filename[:30] + "..." if len(obj.pdf_filename) > 30 else obj.pdf_filename
    pdf_filename_short.short_description = 'PDF Filename'
    
    def pdf_url_short(self, obj):
        return obj.pdf_url[:50] + "..." if len(obj.pdf_url) > 50 else obj.pdf_url
    pdf_url_short.short_description = 'PDF URL'


@admin.register(OrdersData)
class OrdersDataAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'sr_number', 
        'hearing_date', 
        'case_stage', 
        'source_type',
        'created_at'
    ]
    list_filter = ['source_type', 'case_stage', 'created_at']
    search_fields = ['case__case_number', 'sr_number', 'short_order']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('case', 'sr_number', 'source_type')
        }),
        ('Hearing Information', {
            'fields': ('hearing_date', 'bench', 'list_type', 'case_stage')
        }),
        ('Order Details', {
            'fields': ('short_order', 'disposal_date', 'view_link')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CommentsData)
class CommentsDataAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'compliance_date', 
        'case_no', 
        'doc_type', 
        'source_type',
        'created_at'
    ]
    list_filter = ['source_type', 'doc_type', 'created_at']
    search_fields = ['case__case_number', 'case_no', 'case_title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('case', 'compliance_date', 'case_no', 'source_type')
        }),
        ('Document Information', {
            'fields': ('case_title', 'doc_type', 'parties', 'description')
        }),
        ('Links', {
            'fields': ('view_link',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CaseCmsData)
class CaseCmsDataAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'sr_number', 
        'cm_short', 
        'institution', 
        'status',
        'source_type',
        'created_at'
    ]
    list_filter = ['source_type', 'status', 'created_at']
    search_fields = ['case__case_number', 'sr_number', 'cm', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    def cm_short(self, obj):
        return obj.cm[:30] + "..." if len(obj.cm) > 30 else obj.cm
    cm_short.short_description = 'CM'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('case', 'sr_number', 'source_type')
        }),
        ('CM Information', {
            'fields': ('cm', 'institution', 'disposal_date', 'order_passed')
        }),
        ('Details', {
            'fields': ('description', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PartiesDetailData)
class PartiesDetailDataAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'party_number', 
        'party_name_short', 
        'party_side',
        'created_at'
    ]
    list_filter = ['party_side', 'created_at']
    search_fields = ['case__case_number', 'party_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    def party_name_short(self, obj):
        return obj.party_name[:30] + "..." if len(obj.party_name) > 30 else obj.party_name
    party_name_short.short_description = 'Party Name'


@admin.register(ViewLinkData)
class ViewLinkDataAdmin(admin.ModelAdmin):
    list_display = [
        'case_number', 
        'source_table', 
        'link_text_short', 
        'file_type',
        'created_at'
    ]
    list_filter = ['source_table', 'file_type', 'created_at']
    search_fields = ['case__case_number', 'link_text', 'href']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def case_number(self, obj):
        return obj.case.case_number
    case_number.short_description = 'Case Number'
    
    def link_text_short(self, obj):
        return obj.link_text[:30] + "..." if len(obj.link_text) > 30 else obj.link_text
    link_text_short.short_description = 'Link Text'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('case', 'source_table', 'source_row_sr')
        }),
        ('Link Information', {
            'fields': ('href', 'title', 'link_text')
        }),
        ('File Information', {
            'fields': ('file_type',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
