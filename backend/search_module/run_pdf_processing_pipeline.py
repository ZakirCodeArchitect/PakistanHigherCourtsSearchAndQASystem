#!/usr/bin/env python
"""
Complete PDF Processing Pipeline Runner

This script runs the complete PDF processing pipeline for all cases in the database.
It handles downloading PDFs, extracting text, cleaning text, and creating unified views.

Usage:
    python run_pdf_processing_pipeline.py [options]

Options:
    --force              Force reprocessing even if already done
    --skip-download      Skip PDF download step
    --skip-extract       Skip text extraction step
    --skip-clean         Skip text cleaning step
    --skip-unified       Skip unified views creation step
    --validate-only      Only validate current state without processing
    --help               Show this help message

Examples:
    python run_pdf_processing_pipeline.py                    # Run complete pipeline
    python run_pdf_processing_pipeline.py --force           # Force reprocessing
    python run_pdf_processing_pipeline.py --validate-only   # Only check current state
    python run_pdf_processing_pipeline.py --skip-download   # Skip download step
"""

import os
import sys
import django
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import execute_from_command_line


def main():
    parser = argparse.ArgumentParser(
        description='Complete PDF Processing Pipeline Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing even if already done'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Skip PDF download step'
    )
    parser.add_argument(
        '--skip-extract',
        action='store_true',
        help='Skip text extraction step'
    )
    parser.add_argument(
        '--skip-clean',
        action='store_true',
        help='Skip text cleaning step'
    )
    parser.add_argument(
        '--skip-unified',
        action='store_true',
        help='Skip unified views creation step'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate current state without processing'
    )
    
    args = parser.parse_args()
    
    # Build Django management command arguments
    cmd_args = ['manage.py', 'run_complete_pipeline']
    
    if args.force:
        cmd_args.append('--force')
    if args.skip_download:
        cmd_args.append('--skip-download')
    if args.skip_extract:
        cmd_args.append('--skip-extract')
    if args.skip_clean:
        cmd_args.append('--skip-clean')
    if args.skip_unified:
        cmd_args.append('--skip-unified')
    if args.validate_only:
        cmd_args.append('--validate-only')
    
    # Execute the Django management command
    try:
        execute_from_command_line(cmd_args)
        print("\n✅ Pipeline completed successfully!")
        return 0
    except Exception as e:
        print(f"\n❌ Pipeline failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
