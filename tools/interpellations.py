from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
import json


def search_interpellations(
    legislator: Optional[str] = None,
    keyword: Optional[str] = None,
    term: int = 11,
    session: Optional[int] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    limit: int = 200,
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
    logger.info(
        f"Searching interpellations - legislator: {legislator}, keyword: {keyword}"
    )

    params = {"limit": str(limit), "page": "1", "屆": str(term)}

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
    term: int, name: str, keyword: Optional[str] = None
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
    params = {"limit": "200", "page": "1"}

    if keyword:
        params["q"] = keyword

    response = httpx.get(url, params=params)
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


# ---------------------------------------------------------------------------
# Utility: find_legislators_by_position
# ---------------------------------------------------------------------------


def find_legislators_by_position(
    keyword: str,
    position: str,
    *,
    term: int = 11,
    limit: int = 200,
) -> str:
    """Find legislators who explicitly express a given *position* toward a *keyword* in interpellation records.

    This is a lightweight heuristic implementation that scans the interpellation text returned
    by :func:`search_interpellations` and counts how many times each legislator appears to take
    the specified *position* (e.g. "支持", "贊成", "反對") in sentences that also contain the
    *keyword*.

    Args:
        keyword: The topic or bill keyword to search for.
        position: The stance string to look for, such as "支持" or "反對".
        term: Legislative term to search within. Defaults to 11.
        limit: Maximum number of interpellation records to fetch.

    Returns
    -------
    str
        JSON-encoded list of objects with two keys::

            [{"委員名稱": "...", "次數": 3}, ...]
    """

    logger.info(
        f"Finding legislators by position – keyword={keyword!r}, position={position!r}, term={term}"
    )

    # Re-use the existing search function to obtain raw records.
    raw = search_interpellations(keyword=keyword, term=term, limit=limit)

    # search_interpellations currently returns a JSON string, but we guard for dict as well.
    data: dict[str, Any]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("search_interpellations returned malformed JSON")
            return "[]"
    else:
        data = raw  # type: ignore[assignment]

    counter: dict[str, int] = {}

    for record in data.get("interpellations", []):
        legislator = record.get("委員名稱")
        content = record.get("質詢內容", "")

        if not legislator or not content:
            continue

        # Simple heuristic: the sentence must contain both the keyword and the position string.
        if keyword in content and position in content:
            counter[legislator] = counter.get(legislator, 0) + 1

    # Transform into a serialisable structure sorted by occurrence count.
    result = [
        {"委員名稱": name, "次數": count}
        for name, count in sorted(counter.items(), key=lambda x: x[1], reverse=True)
    ]

    return json.dumps(result, ensure_ascii=False)
