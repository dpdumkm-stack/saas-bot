"""
CSV Handler for Broadcast System
Parses and validates CSV files with phone numbers
"""
import csv
import io
import re
from typing import List, Dict

class CSVValidationError(Exception):
    """Custom exception for CSV validation errors"""
    pass

def robust_decode(content_bytes: bytes) -> str:
    """
    Robustly decode bytes to string using multiple encodings.
    Handles UTF-8, UTF-8-SIG (with BOM), and Latin-1.
    """
    if not content_bytes:
        return ""
        
    # Order: UTF-8-SIG (detects BOM), UTF-8, Latin-1
    encodings = ['utf-8-sig', 'utf-8', 'latin-1']
    
    for enc in encodings:
        try:
            return content_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
            
    # Final fallback if all else fails
    return content_bytes.decode('utf-8', errors='replace')

from app.utils import normalize_phone_number

def clean_phone_number(phone: str) -> str:
    """
    Clean and validate Indonesian phone number using central utility
    """
    return normalize_phone_number(phone, validate_indonesia=True)

def parse_csv_content(content: str, max_rows: int = 10000) -> List[Dict]:
    """
    Parse CSV content and extract valid phone numbers with names
    
    Args:
        content: CSV file content as string
        max_rows: Maximum number of rows to process (safety limit)
        
    Returns:
        List of dicts with 'phone' and 'name' keys
        
    Raises:
        CSVValidationError: If CSV is invalid or exceeds limits
    """
    if not content:
        raise CSVValidationError("CSV content is empty")
    
    if len(content) > 5_000_000:  # 5MB limit
        raise CSVValidationError("CSV file too large (max 5MB)")
    
    targets = []
    seen_phones = set()  # Deduplicate
    
    try:
        # Detect delimiter and headers
        lines = content.strip().split('\n')
        if not lines:
            raise CSVValidationError("CSV is empty")
        
        # Sniff delimiter if more than one line
        delimiter = ','
        try:
            sample = '\n'.join(lines[:5])
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=',;\t|')
            delimiter = dialect.delimiter
        except:
            # Fallback for small or simple files
            if ';' in lines[0] and ',' not in lines[0]:
                delimiter = ';'
            elif '\t' in lines[0]:
                delimiter = '\t'

        # Check if first line is header
        first_line = lines[0].lower()
        keywords = ['phone', 'nomor', 'number', 'wa', 'whatsapp', 'name', 'nama']
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        has_header = bool(re.search(pattern, first_line))
        
        # Use StringIO for csv reader
        stream = io.StringIO(content)
        if has_header:
            reader = csv.DictReader(stream, delimiter=delimiter)
        else:
            reader = csv.reader(stream, delimiter=delimiter)
        
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                raise CSVValidationError(f"Too many rows (max {max_rows:,})")
            
            # Extract phone number and name from row
            if isinstance(row, dict):
                # Header-based CSV
                phone_raw = (
                    row.get('phone') or 
                    row.get('nomor') or 
                    row.get('number') or 
                    row.get('Phone') or 
                    row.get('Nomor') or
                    row.get('wa') or
                    row.get('whatsapp') or
                    ''
                ).strip()
                
                name_raw = (
                    row.get('name') or
                    row.get('nama') or
                    row.get('Name') or
                    row.get('Nama') or
                    ''
                ).strip()
            else:
                # No header - assume first column is phone, second is name (if exists)
                phone_raw = row[0].strip() if row else ''
                name_raw = row[1].strip() if len(row) > 1 else ''
            
            if not phone_raw:
                continue
            
            # Clean and validate phone
            clean = clean_phone_number(phone_raw)
            if clean and clean not in seen_phones:
                targets.append({
                    'phone': clean,
                    'name': name_raw or ''  # Default to empty string if no name
                })
                seen_phones.add(clean)
        
        if not targets:
            raise CSVValidationError("No valid phone numbers found in CSV")
        
        return targets
        
    except csv.Error as e:
        raise CSVValidationError(f"Invalid CSV format: {str(e)}")
    except Exception as e:
        if isinstance(e, CSVValidationError):
            raise
        raise CSVValidationError(f"CSV processing error: {str(e)}")

def validate_csv_file(file_url: str, headers: dict) -> Dict:
    """
    Download and validate CSV file from URL
    
    Args:
        file_url: URL to CSV file
        headers: HTTP headers for request
        
    Returns:
        Dict with status and targets or error message
    """
    import requests
    
    try:
        # Download file
        response = requests.get(file_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return {
                'status': 'error',
                'message': f'Failed to download CSV (HTTP {response.status_code})'
            }
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if 'csv' not in content_type and 'text' not in content_type:
            return {
                'status': 'error',
                'message': f'Invalid file type: {content_type}. Please upload CSV file.'
            }
        
        # Decode content using robust helper
        content = robust_decode(response.content)
        
        # Parse CSV
        targets = parse_csv_content(content)
        
        return {
            'status': 'success',
            'targets': targets,
            'count': len(targets)
        }
        
    except CSVValidationError as e:
        return {
            'status': 'error',
            'message': str(e)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }
