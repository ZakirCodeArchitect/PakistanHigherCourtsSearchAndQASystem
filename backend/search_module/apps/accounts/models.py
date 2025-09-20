from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


class UserProfile(models.Model):
    """Extended user profile with role-based information"""
    
    USER_ROLES = [
        ('general_public', 'General Public'),
        ('lawyer', 'Lawyer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=USER_ROLES, default='general_public')
    
    # For General Public users
    cnic = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        validators=[RegexValidator(
            regex=r'^\d{5}-\d{7}-\d{1}$',
            message='CNIC must be in format: 12345-1234567-1'
        )],
        help_text="CNIC format: 12345-1234567-1"
    )
    
    # For Lawyer users
    advocate_license_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Advocate license number"
    )
    
    # Additional fields
    full_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    @property
    def is_lawyer(self):
        return self.role == 'lawyer'
    
    @property
    def is_general_public(self):
        return self.role == 'general_public'
    
    def get_identifier(self):
        """Get the appropriate identifier based on role"""
        if self.is_lawyer:
            return self.advocate_license_number
        elif self.is_general_public:
            return self.cnic
        return None
    
    class Meta:
        db_table = "user_profiles"
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['cnic']),
            models.Index(fields=['advocate_license_number']),
        ]


class LoginSession(models.Model):
    """Track user login sessions for analytics"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_sessions')
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"
    
    class Meta:
        db_table = "login_sessions"
        ordering = ['-login_time']
