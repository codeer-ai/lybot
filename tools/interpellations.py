import json
from typing import Optional, List, Dict, Any
import httpx
from loguru import logger


def search_interpellations(
    legislator: Optional[str] = None,
    keyword: Optional[str] = None,
    term: int = 11,
    session: Optional[int] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    limit: int = 200
) -> str:
    """
    Search interpellation records with various filters.
    
    Args:
        legislator: Legislator name to filter by
        keyword: Keyword to search in interpellation content
        term: Legislative term (default: 11)
        session: Session number
        date_start: Start date (YYYY-MM-DD)
        date_end: End date (YYYY-MM-DD)
        limit: Maximum results
        
    Returns:
        JSON string containing interpellation search results
    """
    logger.info(f"Searching interpellations - legislator: {legislator}, keyword: {keyword}")
    
    params = {
        "limit": str(limit),
        "page": "1",
        "屆": str(term)
    }
    
    if legislator:
        params["委員名稱"] = legislator
    
    if keyword:
        params["q"] = keyword
    
    if session:
        params["會期"] = str(session)
    
    if date_start:
        params["質詢日期_gte"] = f"{date_start}T00:00:00.000Z"
    
    if date_end:
        params["質詢日期_lte"] = f"{date_end}T23:59:59.999Z"
    
    url = "https://ly.govapi.tw/v2/interpellations"
    response = httpx.get(url, params=params)
    
    return response.json()


def get_interpellation_details(interpellation_id: str) -> str:
    """
    Get full interpellation content and details.
    
    Args:
        interpellation_id: Interpellation ID
        
    Returns:
        JSON string containing interpellation details
    """
    logger.info(f"Getting interpellation details for ID: {interpellation_id}")
    
    url = f"https://ly.govapi.tw/v2/interpellations/{interpellation_id}"
    response = httpx.get(url)
    
    return response.json()


def get_meeting_interpellations(meeting_id: str) -> str:
    """
    Get interpellations from a specific meeting.
    
    Args:
        meeting_id: Meeting ID
        
    Returns:
        JSON string containing interpellations from the meeting
    """
    logger.info(f"Getting interpellations for meeting: {meeting_id}")
    
    url = f"https://ly.govapi.tw/v2/meets/{meeting_id}/interpellations"
    response = httpx.get(url)
    
    return response.json()


def get_legislator_interpellations(
    term: int,
    name: str,
    keyword: Optional[str] = None
) -> str:
    """
    Get all interpellations by a specific legislator.
    
    Args:
        term: Legislative term
        name: Legislator name
        keyword: Optional keyword filter
        
    Returns:
        JSON string containing legislator's interpellations
    """
    logger.info(f"Getting interpellations for legislator: {name}")
    
    url = f"https://ly.govapi.tw/v2/legislators/{term}/{name}/interpellations"
    params = {
        "limit": "200",
        "page": "1"
    }
    
    if keyword:
        params["q"] = keyword
    
    response = httpx.get(url, params=params)
    return response.json()


def analyze_legislator_positions(
    legislator: str,
    topic: str,
    term: int = 11
) -> Dict[str, Any]:
    """
    Analyze a legislator's position on a specific topic based on interpellations.
    
    Args:
        legislator: Legislator name
        topic: Topic to analyze (e.g., "環保議題", "核電")
        term: Legislative term
        
    Returns:
        Dictionary with position analysis
    """
    # Search for interpellations on the topic
    results = search_interpellations(
        legislator=legislator,
        keyword=topic,
        term=term
    )
    
    if isinstance(results, str):
        results = json.loads(results)
    
    positions = {
        "立委": legislator,
        "議題": topic,
        "質詢次數": results.get("total", 0),
        "質詢記錄": [],
        "關鍵論述": []
    }
    
    # Analyze each interpellation
    for interp in results.get("interpellations", []):
        interp_id = interp.get("質詢_id")
        if not interp_id:
            continue
        
        # Get detailed content
        details = get_interpellation_details(interp_id)
        if isinstance(details, str):
            details = json.loads(details)
        
        data = details.get("data", {})
        content = data.get("質詢內容", "")
        
        # Extract key statements
        key_statements = extract_key_statements(content, topic)
        
        positions["質詢記錄"].append({
            "日期": data.get("質詢日期"),
            "會議": data.get("會議名稱"),
            "對象": data.get("答詢人"),
            "摘要": data.get("質詢摘要", "")[:200] + "..."
        })
        
        positions["關鍵論述"].extend(key_statements)
    
    return positions


def extract_key_statements(content: str, topic: str) -> List[str]:
    """
    Extract key statements related to a topic from interpellation content.
    
    Args:
        content: Full interpellation content
        topic: Topic to focus on
        
    Returns:
        List of key statements
    """
    if not content:
        return []
    
    statements = []
    sentences = content.split("。")
    
    for sentence in sentences:
        if topic in sentence and len(sentence) > 20:
            # Clean and add the statement
            clean_sentence = sentence.strip() + "。"
            if len(clean_sentence) < 300:  # Reasonable length
                statements.append(clean_sentence)
    
    return statements[:5]  # Return top 5 most relevant


def find_legislators_by_position(
    topic: str,
    position_keywords: List[str],
    term: int = 11,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Find legislators who support/oppose a specific position.
    
    Args:
        topic: Topic to search for
        position_keywords: Keywords indicating the position (e.g., ["支持", "贊成"])
        term: Legislative term
        limit: Maximum legislators to analyze
        
    Returns:
        List of legislators with their positions
    """
    # First, search for all interpellations on the topic
    all_interpellations = search_interpellations(
        keyword=topic,
        term=term,
        limit=limit * 5  # Get more to ensure coverage
    )
    
    if isinstance(all_interpellations, str):
        all_interpellations = json.loads(all_interpellations)
    
    # Group by legislator
    legislator_positions = {}
    
    for interp in all_interpellations.get("interpellations", []):
        legislator = interp.get("委員名稱")
        if not legislator:
            continue
        
        if legislator not in legislator_positions:
            legislator_positions[legislator] = {
                "立委": legislator,
                "質詢次數": 0,
                "支持度": 0,
                "相關發言": []
            }
        
        legislator_positions[legislator]["質詢次數"] += 1
        
        # Check if interpellation contains position keywords
        content = interp.get("質詢摘要", "")
        for keyword in position_keywords:
            if keyword in content:
                legislator_positions[legislator]["支持度"] += 1
                legislator_positions[legislator]["相關發言"].append({
                    "日期": interp.get("質詢日期"),
                    "摘要": content[:100] + "..."
                })
                break
    
    # Convert to list and sort by support
    result = list(legislator_positions.values())
    result.sort(key=lambda x: x["支持度"], reverse=True)
    
    return result


def get_interpellation_statistics(
    term: int = 11,
    session: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get overall interpellation statistics.
    
    Args:
        term: Legislative term
        session: Optional session number
        
    Returns:
        Dictionary with interpellation statistics
    """
    # This would need to aggregate data across multiple queries
    # For now, return a structure that could be filled
    return {
        "屆": term,
        "會期": session,
        "總質詢次數": 0,
        "參與立委數": 0,
        "熱門議題": [],
        "最活躍立委": []
    }