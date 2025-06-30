import json
import re
from typing import Optional, List, Dict, Any
import httpx
from loguru import logger
from markitdown import MarkItDown


md = MarkItDown()


def search_gazettes(
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    keywords: Optional[str] = None,
    limit: int = 100
) -> str:
    """
    Search gazettes by date range and keywords.
    
    Args:
        date_start: Start date (YYYY-MM-DD format)
        date_end: End date (YYYY-MM-DD format)
        keywords: Keywords to search
        limit: Maximum results
        
    Returns:
        JSON string containing gazette search results
    """
    logger.info(f"Searching gazettes - dates: {date_start} to {date_end}, keywords: {keywords}")
    
    params = {
        "limit": str(limit),
        "page": "1"
    }
    
    if keywords:
        params["q"] = keywords
    
    # Add date filters if provided
    if date_start:
        params["日期_gte"] = f"{date_start}T00:00:00.000Z"
    
    if date_end:
        params["日期_lte"] = f"{date_end}T23:59:59.999Z"
    
    url = "https://ly.govapi.tw/v2/gazettes"
    response = httpx.get(url, params=params)
    
    return response.json()


def get_gazette_details(gazette_id: str) -> str:
    """
    Get detailed information about a specific gazette.
    
    Args:
        gazette_id: Gazette ID
        
    Returns:
        JSON string containing gazette details with PDF links
    """
    logger.info(f"Getting details for gazette: {gazette_id}")
    
    url = f"https://ly.govapi.tw/v2/gazettes/{gazette_id}"
    response = httpx.get(url)
    
    return response.json()


def get_gazette_agendas(gazette_id: str) -> str:
    """
    Get agenda items from a gazette.
    
    Args:
        gazette_id: Gazette ID
        
    Returns:
        JSON string containing agenda items
    """
    logger.info(f"Getting agendas for gazette: {gazette_id}")
    
    url = f"https://ly.govapi.tw/v2/gazettes/{gazette_id}/agendas"
    response = httpx.get(url)
    
    return response.json()


def extract_voting_records_from_pdf(pdf_url: str, bill_identifier: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract voting records from gazette PDF.
    
    Args:
        pdf_url: URL of the PDF document
        bill_identifier: Optional bill name or number to search for
        
    Returns:
        Dictionary containing voting records with legislator names and votes
    """
    logger.info(f"Extracting voting records from PDF: {pdf_url}")
    
    # Get PDF content as markdown
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")
    ssl_context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    with httpx.Client(verify=ssl_context, headers=headers) as client:
        response = client.get(pdf_url)
        response.raise_for_status()
        
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        try:
            result = md.convert(temp_file_path)
            markdown_content = result.text_content
        finally:
            os.unlink(temp_file_path)
    
    # Parse voting records from markdown
    voting_records = parse_voting_records(markdown_content, bill_identifier)
    
    return voting_records


def parse_voting_records(content: str, bill_identifier: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse voting records from markdown content.
    
    Args:
        content: Markdown content from PDF
        bill_identifier: Optional bill identifier to search for
        
    Returns:
        Dictionary with parsed voting records
    """
    records = {
        "bill": bill_identifier,
        "voting_summary": {},
        "individual_votes": {},
        "raw_sections": []
    }
    
    # Common patterns for voting results
    voting_patterns = [
        r"表決結果[:：]\s*贊成\s*(\d+)\s*[票人].*反對\s*(\d+)\s*[票人].*棄權\s*(\d+)\s*[票人]",
        r"贊成者\s*(\d+)\s*[票人].*反對者\s*(\d+)\s*[票人].*棄權者\s*(\d+)\s*[票人]",
        r"出席委員\s*(\d+)\s*人.*贊成者\s*(\d+)\s*人.*反對者\s*(\d+)\s*人"
    ]
    
    # Find voting sections
    lines = content.split('\n')
    in_voting_section = False
    current_section = []
    
    for i, line in enumerate(lines):
        # Check if this line contains bill identifier
        if bill_identifier and bill_identifier in line:
            in_voting_section = True
            current_section = [line]
            continue
        
        # Check for voting result patterns
        for pattern in voting_patterns:
            match = re.search(pattern, line)
            if match:
                in_voting_section = True
                if bill_identifier is None or bill_identifier in '\n'.join(lines[max(0, i-5):i+1]):
                    records["voting_summary"] = {
                        "贊成": int(match.group(1)),
                        "反對": int(match.group(2)),
                        "棄權": int(match.group(3)) if len(match.groups()) >= 3 else 0
                    }
        
        # Collect voting section content
        if in_voting_section:
            current_section.append(line)
            
            # Check for section end
            if "表決結果" in line or (i < len(lines) - 1 and "議案" in lines[i + 1]):
                records["raw_sections"].append('\n'.join(current_section))
                in_voting_section = False
                current_section = []
    
    # Parse individual votes
    records["individual_votes"] = parse_individual_votes(records["raw_sections"])
    
    return records


def parse_individual_votes(sections: List[str]) -> Dict[str, str]:
    """
    Parse individual legislator votes from voting sections.
    
    Args:
        sections: List of voting section texts
        
    Returns:
        Dictionary mapping legislator names to their votes
    """
    votes = {}
    
    for section in sections:
        lines = section.split('\n')
        current_vote_type = None
        
        for line in lines:
            # Detect vote type sections
            if "贊成者" in line or "贊成委員" in line:
                current_vote_type = "贊成"
            elif "反對者" in line or "反對委員" in line:
                current_vote_type = "反對"
            elif "棄權者" in line or "棄權委員" in line:
                current_vote_type = "棄權"
            
            # Extract names
            if current_vote_type:
                # Remove common prefixes and clean the line
                clean_line = re.sub(r'(贊成者|反對者|棄權者|贊成委員|反對委員|棄權委員)[:：]?', '', line)
                clean_line = re.sub(r'[（(]\d+[人位][)）]', '', clean_line)
                
                # Split by common delimiters
                names = re.split(r'[、，,\s]+', clean_line.strip())
                
                for name in names:
                    name = name.strip()
                    # Filter out non-name strings
                    if len(name) >= 2 and len(name) <= 4 and not name.isdigit():
                        if all(c not in name for c in ['表決', '議案', '委員會', '主席']):
                            votes[name] = current_vote_type
    
    return votes


def find_voting_records_for_bill(bill_name: str, date_range: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """
    Find voting records for a specific bill across multiple gazettes.
    
    Args:
        bill_name: Name of the bill
        date_range: Optional tuple of (start_date, end_date) in YYYY-MM-DD format
        
    Returns:
        List of voting records found
    """
    # Search gazettes
    date_start, date_end = date_range if date_range else (None, None)
    gazettes = search_gazettes(
        date_start=date_start,
        date_end=date_end,
        keywords=bill_name
    )
    
    if isinstance(gazettes, str):
        gazettes = json.loads(gazettes)
    
    all_records = []
    
    for gazette in gazettes.get("gazettes", [])[:10]:  # Limit to 10 most relevant
        gazette_id = gazette.get("公報_id")
        if not gazette_id:
            continue
        
        # Get gazette details to find PDF links
        details = get_gazette_details(gazette_id)
        if isinstance(details, str):
            details = json.loads(details)
        
        pdf_urls = extract_pdf_urls(details)
        
        for pdf_url in pdf_urls:
            try:
                records = extract_voting_records_from_pdf(pdf_url, bill_name)
                if records["voting_summary"] or records["individual_votes"]:
                    records["gazette_id"] = gazette_id
                    records["gazette_date"] = gazette.get("日期")
                    records["pdf_url"] = pdf_url
                    all_records.append(records)
            except Exception as e:
                logger.error(f"Error extracting from {pdf_url}: {e}")
    
    return all_records


def extract_pdf_urls(gazette_details: Dict[str, Any]) -> List[str]:
    """
    Extract PDF URLs from gazette details.
    
    Args:
        gazette_details: Gazette details dictionary
        
    Returns:
        List of PDF URLs
    """
    urls = []
    data = gazette_details.get("data", {})
    
    # Check various fields for PDF links
    for field in ["附件", "相關檔案", "檔案連結", "pdf_url", "連結"]:
        if field in data:
            field_data = data[field]
            if isinstance(field_data, str) and field_data.endswith('.pdf'):
                urls.append(field_data)
            elif isinstance(field_data, list):
                for item in field_data:
                    if isinstance(item, str) and item.endswith('.pdf'):
                        urls.append(item)
                    elif isinstance(item, dict):
                        for key in ["url", "連結", "檔案"]:
                            if key in item and item[key].endswith('.pdf'):
                                urls.append(item[key])
    
    return urls