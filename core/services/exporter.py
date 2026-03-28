"""
Exports database Leads to Excel or CSV formats.
"""
import csv
import io
import openpyxl
from django.http import HttpResponse

def export_leads_csv(queryset):
    """
    Takes a QuerySet of Leads and returns a CSV HttpResponse.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leads_export.csv"'

    writer = csv.writer(response)
    # Headers
    writer.writerow(['Name', 'Email', 'Phone', 'Status', 'Notes', 'Location', 'Source File', 'Created At'])

    for lead in queryset:
        writer.writerow([
            lead.name,
            lead.email,
            lead.phone,
            lead.get_status_display(),
            lead.extra_data.get('notes', ''),
            lead.extra_data.get('location', ''),
            lead.extra_data.get('source_file', ''),
            lead.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response

def export_leads_excel(queryset):
    """
    Takes a QuerySet of Leads and returns an Excel (.xlsx) HttpResponse using openpyxl.
    """
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="leads_export.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Extracted Leads"

    # Define headers
    headers = ['Name', 'Email', 'Phone', 'Status', 'Notes', 'Location', 'Source File', 'Created At']
    ws.append(headers)

    # Make headers bold
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)

    # Append data
    for lead in queryset:
        ws.append([
            lead.name,
            lead.email,
            lead.phone,
            lead.get_status_display(),
            lead.extra_data.get('notes', ''),
            lead.extra_data.get('location', ''),
            lead.extra_data.get('source_file', ''),
            lead.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter # Get the column name
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    wb.save(response)
    return response
