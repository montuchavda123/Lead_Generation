from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from .decorators import role_required
from .models import Lead, Conversion, UploadedFile
from accounts.models import Company

User = get_user_model()

@login_required
@role_required('admin')
def admin_dashboard_view(request):
    """
    Renders the Admin Portal.
    Admin (Global) sees system-wide stats and list of all companies.
    Company (Tenant) sees their company stats, and list of sub-users.
    """
    user = request.user
    context = {'role': user.role}

    if user.role == 'admin':
        # Global Admin View
        companies = Company.objects.annotate(user_count=Count('users')).order_by('-created_at')
        
        context.update({
            'total_companies': companies.count(),
            'total_users': User.objects.count(),
            'total_leads': Lead.objects.count(),
            'total_extractions': UploadedFile.objects.filter(status='completed').count(),
            'companies': companies,
        })
    else:
        # Company User View
        company = user.company
        team_members = User.objects.filter(company=company).order_by('-created_at')
        
        # Company Stats
        company_leads = Lead.objects.filter(company=company)
        stats = company_leads.aggregate(revenues=Sum('conversion__revenue'))
        
        context.update({
            'company_name': company.name if company else "No Company",
            'total_team_members': team_members.count(),
            'total_leads': company_leads.count(),
            'total_revenue': stats['revenues'] or 0.0,
            'team_members': team_members,
        })

    return render(request, 'admin/dashboard.html', context)
