#!/usr/bin/env python3
"""
Script to create an admin user for the Pakistan Higher Courts Search & QA System
This script works with PostgreSQL database
Run this script to create a test admin user with credentials: admin/admin123
"""

import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin_user():
    """Create admin user if it doesn't exist"""
    username = 'admin'
    email = 'admin@pakistancourts.com'
    password = 'admin123'

    try:
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"User '{username}' already exists!")
            return

        # Create superuser
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )

        print(f"✅ Admin user created successfully!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Is Superuser: {user.is_superuser}")

    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        print(f"   This might be due to database connection issues.")
        print(f"   Please ensure PostgreSQL is running and accessible.")

def test_database_connection():
    """Test if we can connect to the database"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        print("✅ Database connection successful!")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🏛️ Pakistan Higher Courts Search & QA System")
    print("=" * 50)
    print("Testing database connection...")
    
    if test_database_connection():
        print("Creating admin user...")
        print()
        create_admin_user()
    else:
        print("\nPlease check your PostgreSQL configuration:")
        print("1. Ensure PostgreSQL service is running")
        print("2. Verify database 'ihc_cases_db' exists")
        print("3. Check username/password in settings.py")
        print("4. Ensure PostgreSQL is accessible on localhost:5432")
    
    print()
    print("=" * 50)
    print("You can now login to the system with:")
    print("   Username: admin")
    print("   Password: admin123")
    print()
    print("Run the Django server with:")
    print("   python manage.py runserver")
    print()
    print("Then visit: http://localhost:8000")
