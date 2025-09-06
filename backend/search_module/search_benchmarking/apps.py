"""
Search Benchmarking Django App Configuration
"""

from django.apps import AppConfig


class SearchBenchmarkingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search_benchmarking'
    verbose_name = 'Search Benchmarking'
    
    def ready(self):
        """Initialize the benchmarking module when Django starts"""
        import search_benchmarking.signals

