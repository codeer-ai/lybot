import json
from typing import Optional, List, Dict, Any
import httpx
from loguru import logger


def get_committees(committee_type: Optional[str] = None) -> str:
    """
    Get list of all committees.

    Args:
        committee_type: Optional committee type filter

    Returns:
        JSON string containing committee list
    """
    logger.info("Getting committee list")

    params = {"limit": "200", "page": "1"}

    if committee_type:
        params["委員會類別"] = committee_type

    url = "https://ly.govapi.tw/v2/committees"
    response = httpx.get(url, params=params)

    return response.json()


def get_meeting_bills(meeting_id: str) -> str:
    """
    Get bills discussed in a specific meeting.

    Args:
        meeting_id: Meeting ID

    Returns:
        JSON string containing bills from the meeting
    """
    logger.info(f"Getting bills for meeting: {meeting_id}")

    url = f"https://ly.govapi.tw/v2/meets/{meeting_id}/bills"
    response = httpx.get(url)

    return response.json()


def get_meeting_ivods(meeting_id: str) -> str:
    """
    Get IVOD recordings for a specific meeting.

    Args:
        meeting_id: Meeting ID

    Returns:
        JSON string containing IVOD links
    """
    logger.info(f"Getting IVODs for meeting: {meeting_id}")

    url = f"https://ly.govapi.tw/v2/meets/{meeting_id}/ivods"
    response = httpx.get(url)

    return response.json()


def calculate_attendance_rate(
    legislator: str,
    term: int = 11,
    session: Optional[int] = None,
    meeting_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate attendance rate for a legislator. Use this for individual legislator analysis.
    For comparing multiple legislators, call this function multiple times and sort results.

    Args:
        legislator: Legislator name
        term: Legislative term (default: 11)
        session: Optional session number filter
        meeting_type: Optional meeting type filter (委員會、公聽會、黨團協商、院會、聯席會議、全院委員會)

    Returns:
        Dictionary with attendance statistics including:
        - 出席會議數: Number of meetings attended
        - 總會議數: Total meetings in the period
        - 出席率: Attendance rate percentage
        - 會議類型統計: Breakdown by meeting type

    Note: For party statistics, call this for each party member and aggregate results.
    """
    logger.info(f"Calculating attendance rate for: {legislator}")

    # Get legislator's meetings using the general meeting search
    # This replaces the deleted get_legislator_meetings function
    import urllib.parse

    url = "https://ly.govapi.tw/v2/meets"
    query_parts = []

    # Add basic parameters
    query_parts.append("limit=200")
    query_parts.append("page=1")
    query_parts.append(f"{urllib.parse.quote('屆')}={term}")

    if session:
        query_parts.append(f"{urllib.parse.quote('會期')}={session}")

    if meeting_type:
        query_parts.append(
            f"{urllib.parse.quote('會議種類')}={urllib.parse.quote(meeting_type)}"
        )

    # Add attendee filter
    query_parts.append(
        f"{urllib.parse.quote('會議資料.出席委員')}={urllib.parse.quote(legislator)}"
    )

    full_url = f"{url}?{'&'.join(query_parts)}"
    response = httpx.get(full_url)
    meetings_data = response.json()

    attended_meetings = meetings_data.get("總筆數", 0)

    # Get total meetings for the period
    total_params = {"limit": "1000", "page": "1", "屆": str(term)}

    if session:
        total_params["會期"] = str(session)

    if meeting_type:
        total_params["會議種類"] = meeting_type

    response = httpx.get(url, params=total_params)
    total_data = response.json()

    total_meetings = total_data.get("總筆數", 0)

    # Calculate rate
    attendance_rate = (
        (attended_meetings / total_meetings * 100) if total_meetings > 0 else 0
    )

    # Analyze by meeting type
    meeting_breakdown = {}
    for meeting in meetings_data.get("meets", []):
        m_type = meeting.get("會議種類", "其他")
        if m_type not in meeting_breakdown:
            meeting_breakdown[m_type] = 0
        meeting_breakdown[m_type] += 1

    return {
        "立委": legislator,
        "屆": term,
        "會期": session,
        "出席會議數": attended_meetings,
        "總會議數": total_meetings,
        "出席率": f"{attendance_rate:.1f}%",
        "會議類型統計": meeting_breakdown,
    }


def get_session_info(term: int = 11) -> Dict[str, Any]:
    """
    Get session information including dates.

    Args:
        term: Legislative term

    Returns:
        Dictionary with session information
    """
    # Get meetings to infer session dates
    params = {"limit": "1000", "page": "1", "屆": str(term), "agg": "會期"}

    url = "https://ly.govapi.tw/v2/meets"
    response = httpx.get(url, params=params)
    data = response.json()

    # Extract session info from aggregations
    sessions = {}
    for meeting in data.get("meets", []):
        session_num = meeting.get("會期")
        if session_num and session_num not in sessions:
            sessions[session_num] = {
                "會期": session_num,
                "會議數": 0,
                "最早日期": None,
                "最晚日期": None,
            }

        if session_num:
            sessions[session_num]["會議數"] += 1
            meeting_date = meeting.get("日期")
            if meeting_date:
                if (
                    not sessions[session_num]["最早日期"]
                    or meeting_date < sessions[session_num]["最早日期"]
                ):
                    sessions[session_num]["最早日期"] = meeting_date
                if (
                    not sessions[session_num]["最晚日期"]
                    or meeting_date > sessions[session_num]["最晚日期"]
                ):
                    sessions[session_num]["最晚日期"] = meeting_date

    return {"屆": term, "會期資訊": list(sessions.values())}


def find_meetings_by_bill(bill_name: str, term: int = 11) -> List[Dict[str, Any]]:
    """
    Find meetings where a specific bill was discussed.

    Args:
        bill_name: Name of the bill
        term: Legislative term

    Returns:
        List of meetings discussing the bill
    """
    # Search meetings that might contain the bill
    params = {
        "limit": "200",
        "page": "1",
        "屆": str(term),
        # exact-phrase search for the bill name
        "q": f'"{bill_name}"',
    }

    url = "https://ly.govapi.tw/v2/meets"
    response = httpx.get(url, params=params)
    data = response.json()

    relevant_meetings = []

    for meeting in data.get("meets", []):
        meeting_info = {
            "會議代碼": meeting.get("會議代碼"),
            "會議名稱": meeting.get("會議名稱"),
            "日期": meeting.get("日期"),
            "會議種類": meeting.get("會議種類"),
        }

        # Get bills from this meeting to confirm
        meeting_id = meeting.get("會議代碼")
        if meeting_id:
            bills_data = get_meeting_bills(meeting_id)
            if isinstance(bills_data, str):
                bills_data = json.loads(bills_data)

            for bill in bills_data.get("bills", []):
                if bill_name in bill.get("議案名稱", ""):
                    meeting_info["相關議案"] = bill.get("議案名稱")
                    relevant_meetings.append(meeting_info)
                    break

    return relevant_meetings
