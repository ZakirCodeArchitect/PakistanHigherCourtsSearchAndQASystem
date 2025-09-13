#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check cases table structure
    cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'cases' ORDER BY ordinal_position")
    columns = cursor.fetchall()
    print("Cases table columns:")
    for col_name, data_type in columns:
        print(f"  - {col_name}: {data_type}")
    
    print("\nSample data from cases table:")
    cursor.execute("SELECT * FROM cases LIMIT 3")
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"  Row {i}: {row}")
