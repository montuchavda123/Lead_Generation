"""
AI Extraction Engine
Takes parsed text and intelligently extracts leads using dynamic context.
"""
import json
import re
import logging
from ..models import Lead, ProcessingLog

logger = logging.getLogger(__name__)

# NOTE: This is a robust mock AI implementation for MVP that simulates
# LLM parsing by using regex-based heuristics to find potential leads 
# in the parsed raw text. For production with an actual Provider (e.g. Gemini/OpenAI), 
# replace `_call_mock_ai` with your actual API call.

def extract_leads_from_text(uploaded_file, parsed_text):
    """
    Entry point for the AI extraction pipeline.
    """
    # 1. Ask "AI" to parse the text into a structured JSON list of leads
    extracted_data = _call_mock_ai(parsed_text)
    
    # 2. Process the results, validate, and save to database
    total_found = len(extracted_data)
    created_count = 0
    duplicate_count = 0
    
    for lead_data in extracted_data:
        email = lead_data.get('email', '').lower().strip()
        phone = lead_data.get('phone', '').strip()
        
        # Deduplication Rule: Check if it exists for this COMPANY
        if email and Lead.objects.filter(company=uploaded_file.company, email=email).exists():
            duplicate_count += 1
            continue
        elif phone and Lead.objects.filter(company=uploaded_file.company, phone=phone).exists():
            duplicate_count += 1
            continue
            
        # Create Lead
        Lead.objects.create(
            company=uploaded_file.company,
            user=uploaded_file.user,
            name=lead_data.get('name', 'Extracted Contact'),
            email=email,
            phone=phone,
            status=lead_data.get('intent', 'cold'),
            extra_data={
                'notes': lead_data.get('notes', ''),
                'location': lead_data.get('location', ''),
                'source_file': uploaded_file.original_name
            }
        )
        created_count += 1
        
    # Log the summary
    ProcessingLog.objects.create(
        company=uploaded_file.company,
        uploaded_file=uploaded_file,
        message=f"AI EXTRACTION COMPLETE: Found {total_found} contacts. Created {created_count} new leads. Skipped {duplicate_count} duplicates."
    )
    
    return {
        'total_found': total_found,
        'created': created_count,
        'duplicates': duplicate_count
    }


def _call_mock_ai(text):
    """
    MOCK AI SYSTEM:
    Simulates an LLM identifying names, emails, and phones from messy text.
    """
    # Extremely aggressive regex to find Name-like, Email-like, and Phone-like patterns
    # In production, `text` is passed in a prompt to an LLM like: "Extract leads from: {text}"
    
    leads = []
    
    # Find emails
    emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    
    # Find phones (generic match for sequences of 10+ digits with optional separators)
    phones = re.findall(r'(\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})', text)
    
    # Pair them up into mocked lead objects
    max_len = max(len(emails), len(phones))
    
    for i in range(max_len):
        email = emails[i] if i < len(emails) else ''
        phone = phones[i].strip() if i < len(phones) else ''
        name = email.split('@')[0].replace('.', ' ').title() if email else 'Extracted Contact'
        
        # Don't create empty leads
        if not email and not phone:
            continue
            
        leads.append({
            'name': name,
            'email': email,
            'phone': phone,
            'intent': 'cold',
            'location': 'Unknown',
            'notes': 'Automatically extracted by Engine'
        })
        
    return leads
