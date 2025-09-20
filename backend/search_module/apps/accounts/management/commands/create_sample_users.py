#!/usr/bin/env python3
"""
Management command to create sample users for testing
Creates both lawyer and general public users with appropriate credentials
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Create sample users for testing the role-based authentication system'

    def handle(self, *args, **options):
        """Create sample users with different roles"""
        
        # Create a lawyer user
        lawyer_username = 'lawyer1'
        lawyer_password = 'lawyer123'
        lawyer_license = 'ADV-2023-001'
        
        try:
            if not User.objects.filter(username=lawyer_username).exists():
                lawyer_user = User.objects.create_user(
                    username=lawyer_username,
                    email='lawyer1@pakistancourts.com',
                    password=lawyer_password,
                    first_name='Ahmed',
                    last_name='Khan'
                )
                
                UserProfile.objects.create(
                    user=lawyer_user,
                    role='lawyer',
                    advocate_license_number=lawyer_license,
                    full_name='Ahmed Khan',
                    phone_number='+92-300-1234567',
                    address='Lahore High Court, Lahore'
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Lawyer user created successfully!')
                )
                self.stdout.write(f'   Username: {lawyer_username}')
                self.stdout.write(f'   Password: {lawyer_password}')
                self.stdout.write(f'   License: {lawyer_license}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Lawyer user "{lawyer_username}" already exists!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating lawyer user: {str(e)}')
            )
        
        # Create a general public user
        public_username = 'public1'
        public_password = 'public123'
        public_cnic = '12345-1234567-1'
        
        try:
            if not User.objects.filter(username=public_username).exists():
                public_user = User.objects.create_user(
                    username=public_username,
                    email='public1@example.com',
                    password=public_password,
                    first_name='Fatima',
                    last_name='Ali'
                )
                
                UserProfile.objects.create(
                    user=public_user,
                    role='general_public',
                    cnic=public_cnic,
                    full_name='Fatima Ali',
                    phone_number='+92-300-7654321',
                    address='Karachi, Pakistan'
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ General Public user created successfully!')
                )
                self.stdout.write(f'   Username: {public_username}')
                self.stdout.write(f'   Password: {public_password}')
                self.stdout.write(f'   CNIC: {public_cnic}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  General Public user "{public_username}" already exists!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating general public user: {str(e)}')
            )
        
        # Create another lawyer for testing
        lawyer2_username = 'lawyer2'
        lawyer2_password = 'lawyer456'
        lawyer2_license = 'ADV-2023-002'
        
        try:
            if not User.objects.filter(username=lawyer2_username).exists():
                lawyer2_user = User.objects.create_user(
                    username=lawyer2_username,
                    email='lawyer2@pakistancourts.com',
                    password=lawyer2_password,
                    first_name='Sara',
                    last_name='Ahmed'
                )
                
                UserProfile.objects.create(
                    user=lawyer2_user,
                    role='lawyer',
                    advocate_license_number=lawyer2_license,
                    full_name='Sara Ahmed',
                    phone_number='+92-300-9876543',
                    address='Islamabad High Court, Islamabad'
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Second Lawyer user created successfully!')
                )
                self.stdout.write(f'   Username: {lawyer2_username}')
                self.stdout.write(f'   Password: {lawyer2_password}')
                self.stdout.write(f'   License: {lawyer2_license}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Second Lawyer user "{lawyer2_username}" already exists!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating second lawyer user: {str(e)}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Sample users creation completed!')
        )
        self.stdout.write('\n📋 Test Credentials:')
        self.stdout.write('   Lawyer 1: lawyer1 / lawyer123 / ADV-2023-001')
        self.stdout.write('   Lawyer 2: lawyer2 / lawyer456 / ADV-2023-002')
        self.stdout.write('   General Public: public1 / public123 / 12345-1234567-1')
        self.stdout.write('\n💡 Note: Lawyers can access all modules, General Public can only access Law Information.')
