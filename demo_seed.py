import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'convertos.settings')
django.setup()

from accounts.models import User, Company
from core.models import Campaign, Lead

def seed():
    print("🌱 Starting database seeding...")

    # 1. Create Default Company
    company, created = Company.objects.get_or_create(
        name="Acme Corp",
        defaults={'address': '123 Business Rd', 'website': 'https://acme.com'}
    )
    if created:
        print(f"✅ Created Company: {company.name}")

    # 2. Create Global Admin
    admin_email = 'admin@convertos.com'
    if not User.objects.filter(email=admin_email).exists():
        admin = User.objects.create_superuser(
            email=admin_email,
            password='admin@123',
            first_name='Global',
            last_name='Admin',
            role='admin',
            company=company  # Associate admin with the default company
        )
        print(f"✅ Created Superuser: {admin_email}")
    else:
        # Ensure existing admin is linked to the company
        admin = User.objects.get(email=admin_email)
        admin.company = company
        admin.save()
        print(f"ℹ️ Superuser {admin_email} already exists. Linked to {company.name}.")

    # 3. Create Standard Company User
    user_email = 'company@acme.com'
    if not User.objects.filter(email=user_email).exists():
        user = User.objects.create_user(
            email=user_email,
            password='company@123',
            first_name='Acme',
            last_name='User',
            role='company',
            company=company
        )
        print(f"✅ Created Company User: {user_email}")

    # 4. Create a Sample Campaign
    campaign, created = Campaign.objects.get_or_create(
        name="Spring Outreach 2026",
        company=company,
        defaults={'description': 'Demo campaign for lead generation.'}
    )
    if created:
        print(f"✅ Created Sample Campaign: {campaign.name}")

    print("🚀 Seeding complete!")

if __name__ == '__main__':
    seed()
