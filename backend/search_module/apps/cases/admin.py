from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Court, Case, CaseDetail, JudgementData, OrdersData, CommentsData,
    CaseCmsData, PartiesDetailData, CaseHistoryData, CaseDetailOptionsData, ViewLinkData
)

# Inline classes to show related data
class OrdersDataInline(admin.TabularInline):
    model = OrdersData
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['sr_number', 'hearing_date', 'bench', 'list_type', 'case_stage', 'short_order', 'disposal_date']

class CommentsDataInline(admin.TabularInline):
    model = CommentsData
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['compliance_date', 'case_no', 'case_title', 'doc_type', 'parties', 'description']

class PartiesDetailDataInline(admin.TabularInline):
    model = PartiesDetailData
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['party_number', 'party_name', 'party_side']



class CaseCmsDataInline(admin.TabularInline):
    model = CaseCmsData
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['sr_number', 'cm', 'institution', 'disposal_date', 'order_passed', 'description', 'status']

@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    # Show more columns in the list view
    list_display = [
        'sr_number', 
        'case_number', 
        'case_title_short', 
        'institution_date',
        'bench',
        'hearing_date',
        'status', 
        'court', 
        'related_data_count',
        'created_at'
    ]
    
    # Make columns clickable for sorting
    list_display_links = ['sr_number', 'case_number']
    
    # Add filters
    list_filter = ['status', 'court', 'created_at', 'institution_date']
    
    # Add search
    search_fields = ['sr_number', 'case_number', 'case_title', 'bench']
    
    # Show more items per page
    list_per_page = 50
    
    # Make fields readonly
    readonly_fields = ['created_at', 'updated_at']
    
    # Add inline related data
    inlines = [
        OrdersDataInline,
        CommentsDataInline,
        PartiesDetailDataInline,
        CaseCmsDataInline,
    ]
    
    # Custom methods for display
    def case_title_short(self, obj):
        """Show shortened case title"""
        return obj.case_title[:50] + "..." if len(obj.case_title) > 50 else obj.case_title
    case_title_short.short_description = 'Case Title'
    
    def related_data_count(self, obj):
        """Show count of related data"""
        orders_count = obj.orders_data.count()
        comments_count = obj.comments_data.count()
        parties_count = obj.parties_detail_data.count()
        
        return format_html(
            '<span style="color: #007cba;">Orders: {}</span><br>'
            '<span style="color: #28a745;">Comments: {}</span><br>'
            '<span style="color: #dc3545;">Parties: {}</span>',
            orders_count, comments_count, parties_count
        )
    related_data_count.short_description = 'Related Data'

@admin.register(CaseDetail)
class CaseDetailAdmin(admin.ModelAdmin):
    list_display = [
        'case', 
        'case_status', 
        'case_stage', 
        'case_disposal_date',
        'disposed_of_status',
        'created_at'
    ]
    list_filter = ['case_status', 'case_stage', 'created_at']
    search_fields = ['case__sr_number', 'case__case_number', 'case_title_detailed']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(OrdersData)
class OrdersDataAdmin(admin.ModelAdmin):
    list_display = [
        'case', 
        'sr_number', 
        'hearing_date', 
        'bench', 
        'list_type', 
        'case_stage', 
        'short_order',
        'disposal_date'
    ]
    list_filter = ['list_type', 'case_stage', 'created_at']
    search_fields = ['case__sr_number', 'case__case_number', 'short_order']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CommentsData)
class CommentsDataAdmin(admin.ModelAdmin):
    list_display = [
        'case', 
        'compliance_date', 
        'case_no', 
        'doc_type', 
        'parties', 
        'description_short'
    ]
    list_filter = ['doc_type', 'compliance_date', 'created_at']
    search_fields = ['case__sr_number', 'case__case_number', 'parties', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def description_short(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

@admin.register(PartiesDetailData)
class PartiesDetailDataAdmin(admin.ModelAdmin):
    list_display = ['case', 'party_number', 'party_name', 'party_side', 'created_at']
    list_filter = ['party_side', 'created_at']
    search_fields = ['case__sr_number', 'case__case_number', 'party_name']
    readonly_fields = ['created_at', 'updated_at']



@admin.register(CaseCmsData)
class CaseCmsDataAdmin(admin.ModelAdmin):
    list_display = [
        'case', 
        'sr_number', 
        'cm', 
        'institution', 
        'disposal_date', 
        'order_passed',
        'status'
    ]
    list_filter = ['status', 'institution', 'created_at']
    search_fields = ['case__sr_number', 'case__case_number', 'cm', 'order_passed']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(JudgementData)
class JudgementDataAdmin(admin.ModelAdmin):
    list_display = ['case', 'pdf_filename', 'page_title', 'pdf_url_link', 'created_at']
    search_fields = ['case__sr_number', 'case__case_number', 'pdf_filename']
    readonly_fields = ['created_at', 'updated_at']
    
    def pdf_url_link(self, obj):
        if obj.pdf_url:
            return format_html('<a href="{}" target="_blank">View PDF</a>', obj.pdf_url)
        return "No PDF"
    pdf_url_link.short_description = 'PDF Link'





@admin.register(CaseHistoryData)
class CaseHistoryDataAdmin(admin.ModelAdmin):
    list_display = [
        'case', 
        'has_orders_data', 
        'has_comments_data', 
        'has_case_cms_data', 
        'has_judgement_data',
        'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['case__sr_number', 'case__case_number']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_orders_data(self, obj):
        return "Yes" if obj.orders_data else "No"
    has_orders_data.short_description = 'Has Orders'
    
    def has_comments_data(self, obj):
        return "Yes" if obj.comments_data else "No"
    has_comments_data.short_description = 'Has Comments'
    
    def has_case_cms_data(self, obj):
        return "Yes" if obj.case_cms_data else "No"
    has_case_cms_data.short_description = 'Has Case CMs'
    
    def has_judgement_data(self, obj):
        return "Yes" if obj.judgement_data else "No"
    has_judgement_data.short_description = 'Has Judgement'

@admin.register(CaseDetailOptionsData)
class CaseDetailOptionsDataAdmin(admin.ModelAdmin):
    list_display = [
        'case', 
        'has_parties_detail_data', 
        'has_comments_detail_data', 
        'has_case_cms_detail_data', 
        'has_hearing_details_detail_data',
        'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['case__sr_number', 'case__case_number']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_parties_detail_data(self, obj):
        return "Yes" if obj.parties_detail_data else "No"
    has_parties_detail_data.short_description = 'Has Parties Detail'
    
    def has_comments_detail_data(self, obj):
        return "Yes" if obj.comments_detail_data else "No"
    has_comments_detail_data.short_description = 'Has Comments Detail'
    
    def has_case_cms_detail_data(self, obj):
        return "Yes" if obj.case_cms_detail_data else "No"
    has_case_cms_detail_data.short_description = 'Has Case CMs Detail'
    
    def has_hearing_details_detail_data(self, obj):
        return "Yes" if obj.hearing_details_detail_data else "No"
    has_hearing_details_detail_data.short_description = 'Has Hearing Details Detail'

# Register ViewLinkData with basic admin (since it has schema issues)
admin.site.register(ViewLinkData)
