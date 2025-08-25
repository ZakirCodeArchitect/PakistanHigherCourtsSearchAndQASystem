"""
Django management command to clean case data
"""

from django.core.management.base import BaseCommand
from apps.cases.services.data_cleaner import DataCleaner


class Command(BaseCommand):
    help = 'Clean and normalize case data to improve quality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleaning even if data appears clean',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without making changes',
        )
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze data quality without cleaning',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        analyze_only = options['analyze_only']

        self.stdout.write(
            self.style.SUCCESS('🧹 Starting Case Data Cleaning Process')
        )
        self.stdout.write('=' * 60)

        cleaner = DataCleaner()

        if analyze_only:
            self._analyze_data_quality(cleaner)
        elif dry_run:
            self._dry_run_cleaning(cleaner)
        else:
            self._perform_cleaning(cleaner, force)

    def _analyze_data_quality(self, cleaner):
        """Analyze data quality without making changes"""
        self.stdout.write('📊 Analyzing data quality...')
        
        from apps.cases.models import Case, OrdersData, CommentsData, CaseDetail, PartiesDetailData
        
        # Analyze cases
        cases = Case.objects.all()
        total_cases = cases.count()
        
        # Sample analysis
        sample_case = cases.first()
        if sample_case:
            title_score = cleaner.get_data_quality_score(sample_case.case_title)
            status_score = cleaner.get_data_quality_score(sample_case.status)
            
            self.stdout.write(f'\n📋 Sample Case Analysis:')
            self.stdout.write(f'Case Number: {sample_case.case_number}')
            self.stdout.write(f'Case Title: "{sample_case.case_title}" (Quality: {title_score:.2f})')
            self.stdout.write(f'Status: "{sample_case.status}" (Quality: {status_score:.2f})')
            self.stdout.write(f'Bench: "{sample_case.bench}"')
        
        # Analyze orders
        orders = OrdersData.objects.all()
        total_orders = orders.count()
        
        if total_orders > 0:
            sample_order = orders.first()
            if sample_order:
                short_order_score = cleaner.get_data_quality_score(sample_order.short_order)
                
                self.stdout.write(f'\n📄 Sample Order Analysis:')
                self.stdout.write(f'SR Number: "{sample_order.sr_number}"')
                self.stdout.write(f'Short Order: "{sample_order.short_order[:100]}..." (Quality: {short_order_score:.2f})')
                self.stdout.write(f'Bench: "{sample_order.bench}"')
        
        self.stdout.write(f'\n📊 Summary:')
        self.stdout.write(f'Total Cases: {total_cases}')
        self.stdout.write(f'Total Orders: {total_orders}')
        self.stdout.write(f'Total Comments: {CommentsData.objects.count()}')
        self.stdout.write(f'Total Case Details: {CaseDetail.objects.count()}')
        self.stdout.write(f'Total Parties: {PartiesDetailData.objects.count()}')

    def _dry_run_cleaning(self, cleaner):
        """Show what would be cleaned without making changes"""
        self.stdout.write('🔍 Dry run - analyzing what would be cleaned...')
        
        from apps.cases.models import Case, OrdersData, CommentsData, CaseDetail, PartiesDetailData
        
        # Analyze what would be cleaned
        cases_to_clean = 0
        orders_to_clean = 0
        comments_to_clean = 0
        case_details_to_clean = 0
        parties_to_clean = 0
        
        # Check cases
        for case in Case.objects.all():
            original_title = case.case_title
            cleaned_title = cleaner._clean_case_title(original_title)
            if original_title != cleaned_title:
                cases_to_clean += 1
                self.stdout.write(f'  Case {case.id}: "{original_title}" → "{cleaned_title}"')
        
        # Check orders
        for order in OrdersData.objects.all():
            original_short_order = order.short_order
            cleaned_short_order = cleaner._clean_legal_text(original_short_order)
            if original_short_order != cleaned_short_order:
                orders_to_clean += 1
                self.stdout.write(f'  Order {order.id}: Short order would be cleaned')
        
        # Check comments
        for comment in CommentsData.objects.all():
            original_description = comment.description
            cleaned_description = cleaner._clean_legal_text(original_description)
            if original_description != cleaned_description:
                comments_to_clean += 1
        
        # Check case details
        for detail in CaseDetail.objects.all():
            original_status = detail.case_status
            cleaned_status = cleaner._normalize_status(original_status)
            if original_status != cleaned_status:
                case_details_to_clean += 1
        
        # Check parties
        for party in PartiesDetailData.objects.all():
            original_name = party.party_name
            cleaned_name = cleaner._clean_party_name(original_name)
            if original_name != cleaned_name:
                parties_to_clean += 1
        
        self.stdout.write(f'\n📊 Dry Run Summary:')
        self.stdout.write(f'Cases to clean: {cases_to_clean}')
        self.stdout.write(f'Orders to clean: {orders_to_clean}')
        self.stdout.write(f'Comments to clean: {comments_to_clean}')
        self.stdout.write(f'Case details to clean: {case_details_to_clean}')
        self.stdout.write(f'Parties to clean: {parties_to_clean}')
        
        total_to_clean = cases_to_clean + orders_to_clean + comments_to_clean + case_details_to_clean + parties_to_clean
        
        if total_to_clean == 0:
            self.stdout.write(self.style.SUCCESS('✅ No data needs cleaning!'))
        else:
            self.stdout.write(f'Total records to clean: {total_to_clean}')

    def _perform_cleaning(self, cleaner, force):
        """Perform actual data cleaning"""
        self.stdout.write('🧹 Performing data cleaning...')
        
        try:
            stats = cleaner.clean_all_data(force=force)
            
            self.stdout.write(f'\n📊 Cleaning Results:')
            self.stdout.write(f'Cases cleaned: {stats["cases_cleaned"]}')
            self.stdout.write(f'Orders cleaned: {stats["orders_cleaned"]}')
            self.stdout.write(f'Comments cleaned: {stats["comments_cleaned"]}')
            self.stdout.write(f'Case details cleaned: {stats["case_details_cleaned"]}')
            self.stdout.write(f'Parties cleaned: {stats["parties_cleaned"]}')
            
            total_cleaned = (
                stats["cases_cleaned"] + 
                stats["orders_cleaned"] + 
                stats["comments_cleaned"] + 
                stats["case_details_cleaned"] + 
                stats["parties_cleaned"]
            )
            
            if total_cleaned == 0:
                self.stdout.write(self.style.SUCCESS('✅ No data needed cleaning!'))
            else:
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully cleaned {total_cleaned} records!'))
            
            if stats["errors"]:
                self.stdout.write(self.style.WARNING(f'\n⚠️ Errors encountered:'))
                for error in stats["errors"]:
                    self.stdout.write(f'  - {error}')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during cleaning: {str(e)}')
            )
            raise
