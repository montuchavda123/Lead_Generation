from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Lead, Conversion, Campaign, FollowUp, UploadedFile

User = get_user_model()

# ─── Authentication ────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        from accounts.models import Company
        business_name = validated_data.get('business_name', 'Default Company')
        
        # Auto-provision Company workspace
        company = Company.objects.create(name=business_name)

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            business_name=business_name,
            company=company,
            role='company'
        )
        return user


# ─── Leads ─────────────────────────────────────────────────────

class ConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversion
        fields = ['converted', 'revenue', 'converted_at']

class LeadSerializer(serializers.ModelSerializer):
    conversion = ConversionSerializer(read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'phone', 'email', 'status',
            'last_contacted', 'created_at', 'conversion'
        ]
        read_only_fields = ['id', 'created_at']


class LeadUploadSerializer(serializers.Serializer):
    csv_file = serializers.FileField()

    def validate_csv_file(self, value):
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed.")
        if value.size > 10 * 1024 * 1024:  # 10MB limit
            raise serializers.ValidationError("File size must be under 10MB.")
        return value


class ConvertLeadSerializer(serializers.Serializer):
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)


# ─── Dashboard ─────────────────────────────────────────────────

class DashboardSerializer(serializers.Serializer):
    total_leads = serializers.IntegerField()
    converted_leads = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    leads_by_status = serializers.DictField()


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ['id', 'name', 'segment', 'message', 'sent', 'sent_count', 'created_at']
        read_only_fields = ['id', 'sent', 'sent_count', 'created_at']

class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = ['id', 'lead', 'message', 'scheduled_at', 'sent', 'sent_at', 'created_at']
        read_only_fields = ['id', 'sent', 'sent_at', 'created_at']

class ScheduleFollowUpSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    message = serializers.CharField()
    hours = serializers.IntegerField(min_value=1, max_value=720)  # Max 30 days

# ─── Extraction ────────────────────────────────────────────────

class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ['id', 'original_name', 'file_type', 'status', 'created_at', 'processed_at']
        read_only_fields = ['id', 'status', 'created_at', 'processed_at']
