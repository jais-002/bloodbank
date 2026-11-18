from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date


# --- DONOR PROFILE MODEL ---
class Donor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, null=True, blank=True)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    blood_group = models.CharField(max_length=5)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100, help_text="Home town or City")

    # Physical Metrics
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)

    # Clinical Details
    last_donation_date = models.DateField(null=True, blank=True)

    # Status
    is_available = models.BooleanField(default=True)
    profile_pic = models.ImageField(upload_to='donor_pics/', null=True, blank=True)
    is_emergency_available = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.blood_group})"

    @property
    def can_donate(self):
        """
        Logic: Donors must wait at least 90 days (3 months) between donations.
        """
        if not self.last_donation_date:
            return True
        days_since = (date.today() - self.last_donation_date).days
        return days_since >= 90


# --- BLOOD REQUEST MODEL ---
class BloodRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Donated', 'Donated'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    ]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name='received_requests')

    # Stores seeker location at time of request
    location_info = models.CharField(max_length=255, null=True, blank=True)

    # Corrected: Combined your two 'reason' fields into one
    reason = models.TextField(blank=True, null=True, help_text="Purpose of blood request")

    #Specific location / hospital for this request
    hospital_name = models.CharField(max_length=255, null=True, blank=True, help_text="Hospital name or location")


    # NEW: Contact number for the emergency (in case seeker isn't a donor)
    contact_number = models.CharField(max_length=15, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request from {self.requester.username} to {self.donor.name}"