from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class UploadedFile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='uploaded_files', db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_files', db_index=True)
    file = models.FileField(upload_to='extraction/uploads/')
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'uploaded_files'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_name} ({self.status})"

class ProcessingLog(models.Model):
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='processing_logs', db_index=True)
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='logs', db_index=True)
    message = models.TextField()
    is_error = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'processing_logs'
        ordering = ['created_at']

    def __str__(self):
        return f"Log for {self.uploaded_file.original_name} - {'Error' if self.is_error else 'Info'}"


class Lead(models.Model):
    STATUS_CHOICES = [
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ]

    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='leads', db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads', db_index=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True, default='', db_index=True)
    email = models.EmailField(blank=True, default='', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cold', db_index=True)
    extra_data = models.JSONField(default=dict, blank=True)
    last_contacted = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Conversion(models.Model):
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='conversion', primary_key=True)
    converted = models.BooleanField(default=False, db_index=True)
    revenue = models.FloatField(default=0.0)
    converted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"Conversion for {self.lead.name}"


class Campaign(models.Model):
    SEGMENT_CHOICES = [
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ]

    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='campaigns', db_index=True)
    name = models.CharField(max_length=200)
    segment = models.CharField(max_length=20, choices=SEGMENT_CHOICES)
    message = models.TextField()
    sent = models.BooleanField(default=False)
    sent_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns', db_index=True)

    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'created_at']),
        ]

    def __str__(self):
        return self.name


class FollowUp(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups', db_index=True)
    message = models.TextField()
    scheduled_at = models.DateTimeField(db_index=True)
    sent = models.BooleanField(default=False, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'followups'
        ordering = ['scheduled_at']

    def __str__(self):
        return f"FollowUp for {self.lead.name} @ {self.scheduled_at}"
