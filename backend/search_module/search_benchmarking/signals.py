"""
Search Benchmarking Signals
Django signals for the search benchmarking module.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from .models import BenchmarkExecution, BenchmarkResult

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BenchmarkExecution)
def execution_saved(sender, instance, created, **kwargs):
    """Signal fired when a benchmark execution is saved"""
    if created:
        logger.info(f"New benchmark execution created: {instance.execution_name}")
    else:
        logger.info(f"Benchmark execution updated: {instance.execution_name} (status: {instance.status})")


@receiver(post_save, sender=BenchmarkResult)
def result_saved(sender, instance, created, **kwargs):
    """Signal fired when a benchmark result is saved"""
    if created:
        logger.info(f"New benchmark result saved for execution {instance.execution.id}: {instance.query.query_text[:50]}...")

