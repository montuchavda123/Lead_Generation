import csv
import io
import json
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from .models import Lead, Conversion, UploadedFile
from .forms import RegistrationForm, LoginForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('dashboard')
    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Account created! Please log in.')
        return redirect('login')
    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    company = request.user.company
    if request.user.role == 'admin':
        leads = Lead.objects.select_related('conversion').all()
    else:
        leads = Lead.objects.select_related('conversion').filter(company=company)
        
    total = leads.count()
    stats = leads.aggregate(
        converted_total=Count('conversion'),
        revenue_total=Sum('conversion__revenue')
    )
    converted = stats['converted_total'] or 0
    total_revenue = stats['revenue_total'] or 0
    rate = round((converted / total * 100), 1) if total > 0 else 0

    status_counts = dict(leads.values_list('status').annotate(c=Count('id')).values_list('status', 'c'))
    
    from django.db.models.functions import TruncMonth
    monthly = (
        leads.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )[:6]
    
    chart_labels = [m['month'].strftime('%b %Y') if m['month'] else '' for m in monthly]
    chart_data = [m['count'] for m in monthly]

    context = {
        'total_leads': total,
        'converted_leads': converted,
        'conversion_rate': rate,
        'total_revenue': total_revenue,
        'hot': status_counts.get('hot', 0),
        'warm': status_counts.get('warm', 0),
        'cold': status_counts.get('cold', 0),
        'converted_count': converted,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def leads_view(request):
    if request.user.role == 'admin':
        leads = Lead.objects.select_related('conversion').all()
    else:
        leads = Lead.objects.select_related('conversion').filter(company=request.user.company)
        
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')
    
    if status_filter:
        leads = leads.filter(status=status_filter)
    if search:
        leads = leads.filter(Q(name__icontains=search) | Q(phone__icontains=search))
    
    return render(request, 'leads/table.html', {
        'leads': leads,
        'current_status': status_filter,
        'search_query': search,
    })


@login_required
def upload_view(request):
    """
    Standard Lead Importer supporting CSV, Excel (XLSX/XLS), and JSON.
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        uploaded_file = request.FILES['csv_file']
        filename = uploaded_file.name.lower()
        
        try:
            rows = []
            headers = []
            
            # Handle different formats
            if filename.endswith('.csv'):
                decoded = uploaded_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(decoded))
                headers = reader.fieldnames or []
                rows = list(reader)
            
            elif filename.endswith(('.xlsx', '.xls')):
                engine = 'openpyxl' if filename.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(uploaded_file, engine=engine)
                headers = list(df.columns)
                # Convert NaNs to empty strings for cleaner lead creation
                df = df.fillna('')
                rows = df.to_dict('records')
            
            elif filename.endswith('.json'):
                data = json.load(uploaded_file)
                if isinstance(data, list):
                    rows = data
                    if rows:
                        headers = list(rows[0].keys())
                else:
                    return JsonResponse({'error': 'JSON must be a list of lead objects.'}, status=400)
            
            else:
                return JsonResponse({'error': 'Unsupported file format. Use CSV, Excel, or JSON.'}, status=400)
            
            # AJAX Preview Request
            if 'preview' in request.POST:
                return JsonResponse({
                    'headers': headers,
                    'rows': rows[:5],
                    'count': len(rows)
                })
            
            # Actual Data Import
            count = 0
            
            # Determine target company
            target_company = request.user.company
            if not target_company and request.user.role == 'admin':
                from accounts.models import Company
                target_company = Company.objects.first()
            
            if not target_company:
                return JsonResponse({'error': 'No company found. Please ensure a company exists before uploading leads.'}, status=400)

            for row in rows:
                # Normalizing keys (handle 'Name' vs 'name', etc.)
                def get_val(keys):
                    for k in keys:
                        if k in row: return str(row[k]).strip()
                        if k.lower() in row: return str(row[k.lower()]).strip()
                        if k.capitalize() in row: return str(row[k.capitalize()]).strip()
                    return ""

                name = get_val(['name', 'Name', 'Full Name', 'Contact'])
                phone = get_val(['phone', 'Phone', 'Mobile', 'Contact Number'])
                email = get_val(['email', 'Email', 'Email Address'])
                status_val = get_val(['status', 'Status']).lower() or 'cold'
                
                if name or phone or email:
                    Lead.objects.create(
                        company=target_company,
                        user=request.user,
                        name=name,
                        phone=phone,
                        email=email,
                        status=status_val if status_val in ['hot', 'warm', 'cold'] else 'cold',
                    )
                    count += 1
            
            return JsonResponse({'success': True, 'count': count})
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Manual upload error: {e}", exc_info=True)
            return JsonResponse({'error': f"Error processing file: {str(e)}"}, status=400)
    
    return render(request, 'leads/upload.html')


@login_required
def campaigns_view(request):
    from .forms import CampaignForm
    from .models import Campaign
    form = CampaignForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        campaign = form.save(commit=False)
        
        # Target company fallback for admin
        target_company = request.user.company
        if not target_company and request.user.role == 'admin':
            from accounts.models import Company
            target_company = Company.objects.first()
        
        if not target_company:
            messages.error(request, "No company found. Create a company first.")
            return redirect('campaigns')

        campaign.company = target_company
        campaign.user = request.user
        campaign.save()
        messages.success(request, 'Campaign created successfully!')
        return redirect('campaigns')
    
    if request.user.role == 'admin':
        campaigns = Campaign.objects.all()
    else:
        campaigns = Campaign.objects.filter(company=request.user.company)
        
    return render(request, 'campaigns/index.html', {
        'form': form,
        'campaigns': campaigns,
    })


@login_required
def extraction_upload_view(request):
    if request.user.role == 'admin':
        files = UploadedFile.objects.all().order_by('-created_at')
    else:
        files = UploadedFile.objects.filter(company=request.user.company).order_by('-created_at')
    return render(request, 'extraction/upload.html', {'files': files})

@login_required
def extraction_preview_view(request, file_id):
    if request.user.role == 'admin':
        f = UploadedFile.objects.get(id=file_id)
        leads = Lead.objects.filter(extra_data__source_file=f.original_name)
    else:
        f = UploadedFile.objects.get(id=file_id, company=request.user.company)
        leads = Lead.objects.filter(company=request.user.company, extra_data__source_file=f.original_name)
        
    return render(request, 'extraction/preview.html', {
        'file': f,
        'leads': leads,
    })
