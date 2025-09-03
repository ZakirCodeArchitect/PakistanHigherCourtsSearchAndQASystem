#!/usr/bin/env python3
"""
Script to create an admin user for the Pakistan Higher Courts Search & QA System
Run this script to create a test admin user with credentials: admin/admin123
"""

import os
import sys
import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

if __name__ == '__main__':
    print("🏛️ Pakistan Higher Courts Search & QA System")
    print("=" * 50)
    print("Creating admin user...")
    print()
    
    create_admin_user()
    
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
