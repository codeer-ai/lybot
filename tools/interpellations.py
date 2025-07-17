from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


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


def get_interpellation_statistics(
    term: int = 11, session: Optional[int] = None
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
        "最活躍立委": [],
    }
