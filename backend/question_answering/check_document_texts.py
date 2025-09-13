#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check document_texts table structure
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'document_texts' ORDER BY ordinal_position")
    columns = cursor.fetchall()
    print("Document_texts table columns:")
    for col_name, data_type in columns:
        print(f"  - {col_name}: {data_type}")
    
    print("\nSample data from document_texts table:")
    cursor.execute("SELECT * FROM document_texts LIMIT 3")
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"  Row {i}: {row[:2]}... (truncated)")
    
    # Check count
    cursor.execute("SELECT COUNT(*) FROM document_texts")
    count = cursor.fetchone()[0]
    print(f"\nTotal document_texts: {count}")
