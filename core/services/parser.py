"""
File Parsers for the Universal Lead Extraction System.
Detects file types and extracts raw unstructured text or tabular data.
"""
import json
import logging
import pandas as pd
from bs4 import BeautifulSoup
import pdfplumber
import os

logger = logging.getLogger(__name__)

def parse_file(uploaded_file):
    """
    Takes an UploadedFile instance and routes to the correct parser based on extension.
    Returns extracted raw text or a stringified table representation.
    """
    if not uploaded_file.file or not os.path.exists(uploaded_file.file.path):
        logger.error(f"File not found: {uploaded_file.file.name if uploaded_file.file else 'None'}")
        return ""

    path = uploaded_file.file.path
    ext = uploaded_file.file_type.lower().strip('.')
    
    logger.info(f"Starting parse for {uploaded_file.original_name} (ext: {ext})")
    
    logger.info(f"--- STEP 5 & 8: Parsing Started for {uploaded_file.original_name} ---")
    
    try:
        if ext == 'pdf':
            logger.info("Step 5: Routing to PDF parser")
            return _parse_pdf(path)
        elif ext in ['csv', 'xlsx', 'xls']:
            logger.info(f"Step 5: Routing to Spreadsheet parser (format: {ext})")
            return _parse_spreadsheet(path, ext)
        elif ext in ['html', 'htm']:
            logger.info("Step 5: Routing to HTML parser")
            return _parse_html(path)
        elif ext == 'json':
            logger.info("Step 5: Routing to JSON parser")
            return _parse_json(path)
        else:
            logger.info(f"Step 5: Falling back to TXT parser for ext: {ext}")
            return _parse_txt(path)
    except Exception as e:
        logger.error(f"--- STEP 8: PARSING FAILURE for {path}: {str(e)} ---", exc_info=True)
        raise e


def _parse_pdf(path):
    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            content = page.extract_text()
            if content:
                text.append(content)
            # Try to grab tables too
            tables = page.extract_tables()
            for table in tables:
                if not table: continue
                for row in table:
                    row_data = [str(cell).strip() for cell in row if cell is not None]
                    if row_data:
                        text.append(' | '.join(row_data))
    return '\n'.join(text)


def _parse_spreadsheet(path, ext):
    """
    Parses CSV and Excel files. 
    For Excel, iterates through all sheets.
    """
    results = []
    try:
        if ext == 'csv':
            df = pd.read_csv(path)
            results.append(("Main", df))
        else:
            # sheet_name=None reads all sheets into a dictionary {sheet_name: df}
            engine = 'openpyxl' if ext == 'xlsx' else 'xlrd'
            sheets_dict = pd.read_excel(path, sheet_name=None, engine=engine)
            for sheet_name, df in sheets_dict.items():
                results.append((sheet_name, df))
                
    except Exception as e:
        logger.error(f"Spreadsheet read failed for {path}: {e}")
        raise e
        
    final_text = []
    for sheet_name, df in results:
        if df.empty:
            continue
            
        final_text.append(f"--- SHEET: {sheet_name} ---")
        headers = [str(h) for h in df.columns]
        final_text.append("COLUMNS: " + ", ".join(headers))
        
        # Limit rows per sheet to 500 to keep context window manageable
        for i, row in df.head(500).iterrows():
            row_str = " | ".join(f"{headers[j]}: {val}" for j, val in enumerate(row) if pd.notnull(val))
            if row_str.strip():
                final_text.append(f"ROW {i+1}: {row_str}")
                
    return '\n'.join(final_text)


def _parse_html(path):
    """
    Cleans HTML and extracts structural text content.
    """
    # Try different encodings
    html_content = ""
    for enc in ['utf-8', 'latin-1', 'windows-1252']:
        try:
            with open(path, 'r', encoding=enc) as f:
                html_content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if not html_content:
        # Fallback
        with open(path, 'rb') as f:
            html_content = f.read().decode('utf-8', errors='ignore')

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, and navigation elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()
        
    lines = []
    # Extract headers, paragraphs, and list items
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'tr', 'li', 'td']):
        t = tag.get_text(strip=True)
        if t and len(t) > 2: # Ignore single chars or empty tags
            lines.append(t)
    
    if not lines:
        # Final fallback: text only
        return soup.get_text(separator='\n', strip=True)
        
    return '\n'.join(lines)


def _parse_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return json.dumps(data, indent=2)


def _parse_txt(path):
    for enc in ['utf-8', 'latin-1', 'windows-1252']:
        try:
            with open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', errors='ignore')
