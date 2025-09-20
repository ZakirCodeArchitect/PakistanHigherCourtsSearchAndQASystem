#!/usr/bin/env python
import os
import sys
import django

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def check_law_tables():
    """Check what law-related tables exist in the database"""
    with connection.cursor() as cursor:
        # Check all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print("All tables in database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        print("\n" + "="*50)
        
        # Check law-related tables specifically
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%law%' OR table_name LIKE '%Law%')
            ORDER BY table_name;
        """)
        law_tables = cursor.fetchall()
        
        print("Law-related tables:")
        for table in law_tables:
            print(f"  - {table[0]}")
            
            # Check row count for each law table
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}";')
                count = cursor.fetchone()[0]
                print(f"    Rows: {count}")
            except Exception as e:
                print(f"    Error counting rows: {e}")
        
        print("\n" + "="*50)
        
        # Try to find tables with law data
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('laws', 'law_categories', 'law_information', 'law_data')
            ORDER BY table_name;
        """)
        specific_tables = cursor.fetchall()
        
        print("Specific law tables:")
        for table in specific_tables:
            print(f"  - {table[0]}")
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table[0]}";')
                count = cursor.fetchone()[0]
                print(f"    Rows: {count}")
            except Exception as e:
                print(f"    Error counting rows: {e}")

if __name__ == "__main__":
    check_law_tables()

