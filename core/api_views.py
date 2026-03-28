"""
ConvertOS REST API Views.
All endpoints are prefixed with /api/.
"""
import csv
import io
import threading
from django.utils import timezone
from django.db.models import Count, Sum
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser

from .models import Lead, Conversion, Campaign, FollowUp, UploadedFile
from .serializers import (
    RegisterSerializer, LeadSerializer, LeadUploadSerializer,
    ConvertLeadSerializer, DashboardSerializer,
    CampaignSerializer, ScheduleFollowUpSerializer, UploadedFileSerializer
)
from .services import segment_leads, trigger_campaign, schedule_followup
from .services.parser import parse_file
from .services.extractor import extract_leads_from_text
from .services.exporter import export_leads_csv, export_leads_excel
from .permissions import IsGlobalAdmin, IsCompanyUser, IsAuthenticatedUser

User = get_user_model()

def _get_tenant_filter(user):
    """Helper to return the base query kwargs or an empty dict if global admin"""
    if user.role == 'admin':
        return {}
    return {'company': user.company}


# ═══════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════

class RegisterAPIView(APIView):
    """POST /api/auth/register/ — Create a new user account + company."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'message': 'Account created successfully.',
            'user': {
                'id': user.id,
                'email': user.email,
                'business_name': user.business_name,
                'role': user.role,
                'company': user.company.id if user.company else None
            }
        }, status=status.HTTP_201_CREATED)


# ═══════════════════════════════════════════════════════════════
# LEADS
# ═══════════════════════════════════════════════════════════════

class LeadListAPIView(APIView):
    """
    GET  /api/leads/          — List leads (filter: ?status=hot)
    POST /api/leads/          — Create a single lead
    """
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def get(self, request):
        leads = Lead.objects.prefetch_related('conversion').filter(**_get_tenant_filter(request.user))
        status_filter = request.query_params.get('status')
        if status_filter:
            leads = leads.filter(status=status_filter)

        serializer = LeadSerializer(leads, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Ensure company is set for 'company' users
        company = request.user.company if request.user.role == 'company' else None
        serializer.save(user=request.user, company=company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeadUploadAPIView(APIView):
    """POST /api/leads/upload/ — Upload CSV file of leads."""
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = LeadUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        csv_file = serializer.validated_data['csv_file']
        decoded = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        company = request.user.company if request.user.role == 'company' else None
        created = 0
        errors = []
        for i, row in enumerate(reader, start=2):
            try:
                Lead.objects.create(
                    company=company,
                    user=request.user,
                    name=row.get('name', row.get('Name', '')).strip(),
                    phone=row.get('phone', row.get('Phone', '')).strip(),
                    email=row.get('email', row.get('Email', '')).strip(),
                    status=row.get('status', row.get('Status', 'cold')).strip().lower(),
                )
                created += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        return Response({
            'created': created,
            'errors': errors,
        }, status=status.HTTP_201_CREATED)


class ConvertLeadAPIView(APIView):
    """PATCH /api/leads/<id>/convert/ — Mark lead as converted."""
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def patch(self, request, lead_id):
        try:
            lead = Lead.objects.get(id=lead_id, **_get_tenant_filter(request.user))
        except Lead.DoesNotExist:
            return Response({'error': 'Lead not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ConvertLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        revenue = serializer.validated_data.get('revenue', 0)
        
        Conversion.objects.update_or_create(
            lead=lead,
            defaults={
                'converted': True,
                'revenue': revenue,
                'converted_at': timezone.now()
            }
        )
        return Response(LeadSerializer(lead).data)


class SegmentLeadsAPIView(APIView):
    """POST /api/leads/segment/ — Run rule-based segmentation."""
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def post(self, request):
        counts = segment_leads(request.user)
        return Response({
            'message': 'Segmentation complete.',
            'updated': counts,
        })


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

class DashboardAPIView(APIView):
    """GET /api/dashboard/ — Dashboard statistics."""
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def get(self, request):
        leads = Lead.objects.select_related('conversion').filter(**_get_tenant_filter(request.user))
        total = leads.count()
        
        stats = leads.aggregate(
            converted_total=Count('conversion'),
            revenue_total=Sum('conversion__revenue')
        )
        converted = stats['converted_total'] or 0
        total_revenue = stats['revenue_total'] or 0
        rate = round((converted / total * 100), 1) if total > 0 else 0.0

        status_counts = dict(
            leads.values_list('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        data = {
            'total_leads': total,
            'converted_leads': converted,
            'conversion_rate': rate,
            'total_revenue': total_revenue,
            'leads_by_status': {
                'hot': status_counts.get('hot', 0),
                'warm': status_counts.get('warm', 0),
                'cold': status_counts.get('cold', 0),
                'converted': converted,
            },
        }
        serializer = DashboardSerializer(data)
        return Response(serializer.data)


# ═══════════════════════════════════════════════════════════════
# CAMPAIGNS
# ═══════════════════════════════════════════════════════════════

class CampaignListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def get(self, request):
        campaigns = Campaign.objects.filter(**_get_tenant_filter(request.user))
        serializer = CampaignSerializer(campaigns, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CampaignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = request.user.company if request.user.role == 'company' else None
        serializer.save(user=request.user, company=company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TriggerCampaignAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def post(self, request, campaign_id):
        try:
            campaign = Campaign.objects.get(id=campaign_id, **_get_tenant_filter(request.user))
        except Campaign.DoesNotExist:
            return Response({'error': 'Campaign not found.'}, status=status.HTTP_404_NOT_FOUND)

        if campaign.sent:
            return Response({'error': 'Campaign already sent.'}, status=status.HTTP_400_BAD_REQUEST)

        count = trigger_campaign(campaign)
        return Response({
            'message': f'Campaign triggered. Sent to {count} leads.',
            'sent_count': count,
        })


class ScheduleFollowUpAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def post(self, request):
        serializer = ScheduleFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lead = Lead.objects.get(
                id=serializer.validated_data['lead_id'],
                **_get_tenant_filter(request.user)
            )
        except Lead.DoesNotExist:
            return Response({'error': 'Lead not found.'}, status=status.HTTP_404_NOT_FOUND)

        followup = schedule_followup(
            lead=lead,
            hours=serializer.validated_data['hours'],
            message=serializer.validated_data['message'],
        )
        return Response({
            'message': 'Follow-up scheduled.',
            'followup_id': followup.id,
            'scheduled_at': followup.scheduled_at.isoformat(),
        }, status=status.HTTP_201_CREATED)


# ═══════════════════════════════════════════════════════════════
# UNIVERSAL EXTRACTION SYSTEM
# ═══════════════════════════════════════════════════════════════

def process_upload_task(uploaded_file_id):
    try:
        f = UploadedFile.objects.get(id=uploaded_file_id)
        f.status = 'processing'
        f.save()

        text = parse_file(f)
        extract_leads_from_text(f, text)

        f.status = 'completed'
        f.processed_at = timezone.now()
        f.save()
    except Exception as e:
        f.status = 'failed'
        f.save()
        from .models import ProcessingLog
        ProcessingLog.objects.create(company=f.company, uploaded_file=f, message=f"SYSTEM ERROR: {str(e)}", is_error=True)


class ExtractionUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]
    parser_classes = [MultiPartParser]

    def post(self, request):
        # Step 3: Log all file details
        if 'raw_file' not in request.FILES:
            logger.error("No file in request.FILES")
            return Response({'error': 'No file reached the server.'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['raw_file']
        logger.info(f"--- STEP 1 & 3: File Upload Received ---")
        logger.info(f"Name: {file_obj.name}")
        logger.info(f"Size: {file_obj.size} bytes")
        logger.info(f"MIME Type: {file_obj.content_type}")

        # Step 6: Size Limit Check
        if file_obj.size > 50 * 1024 * 1024: # 50MB
            logger.error(f"File too large: {file_obj.size}")
            return Response({'error': 'File too large (max 50MB).'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Extension & Fallback Validation
        allowed_extensions = ['pdf', 'csv', 'xlsx', 'xls', 'json', 'html', 'htm', 'txt']
        ext = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else 'txt'
        
        # Log extension detection
        logger.info(f"Step 4: Detected Extension: {ext}")

        if ext not in allowed_extensions:
            logger.warning(f"Rejected extension: {ext}")
            return Response({'error': f'Unsupported file format: .{ext}'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Remove overly strict MIME check - just log it
        logger.info(f"Step 1 & 4: Allowing upload for {file_obj.name} based on extension .{ext}")

        company = request.user.company if request.user.role == 'company' else None
        uploaded = UploadedFile.objects.create(
            company=company,
            user=request.user,
            file=file_obj,
            original_name=file_obj.name,
            file_type=ext,
            status='pending'
        )

        logger.info(f"Step 7: Valid POST request. Record created with ID {uploaded.id}")
        threading.Thread(target=process_upload_task, args=(uploaded.id,)).start()

        serializer = UploadedFileSerializer(uploaded)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExtractionStatusAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def get(self, request, file_id):
        try:
            f = UploadedFile.objects.get(id=file_id, **_get_tenant_filter(request.user))
            serializer = UploadedFileSerializer(f)
            return Response(serializer.data)
        except UploadedFile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class ExtractionDownloadExcelAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def get(self, request):
        file_id = request.query_params.get('file_id')
        leads = Lead.objects.filter(**_get_tenant_filter(request.user))
        if file_id:
            try:
                f = UploadedFile.objects.get(id=file_id, **_get_tenant_filter(request.user))
                leads = leads.filter(extra_data__source_file=f.original_name)
            except UploadedFile.DoesNotExist:
                pass
                
        return export_leads_excel(leads)

class ExtractionDownloadCSVAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAuthenticatedUser]

    def get(self, request):
        file_id = request.query_params.get('file_id')
        leads = Lead.objects.filter(**_get_tenant_filter(request.user))
        if file_id:
            try:
                f = UploadedFile.objects.get(id=file_id, **_get_tenant_filter(request.user))
                leads = leads.filter(extra_data__source_file=f.original_name)
            except UploadedFile.DoesNotExist:
                pass
                
        return export_leads_csv(leads)
