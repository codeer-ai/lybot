from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


def search_bills(
    term: int = 11,
    session: Optional[int] = None,
    bill_type: Optional[str] = None,
    proposer: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 200,
    include_aggs: bool = True,
) -> Dict[str, Any]:
    """
    Search bills with various filters.

    Args:
        term: Legislative term (default: 11)
        session: Session number (會期)
        bill_type: Bill type (議案類別)
        proposer: Proposer name (提案人)
        keyword: Keyword to search in bill titles
        limit: Maximum results to return
        include_aggs: Include aggregation data

    Returns:
        Dictionary containing bill search results
    """
    logger.info(
        f"Searching bills with filters - term: {term}, session: {session}, type: {bill_type}, proposer: {proposer}, keyword: {keyword}"
    )

    # Allow list[str] values (e.g., for repeated query parameters like "agg")
    params: dict[str, str | list[str]] = {
        "limit": str(limit),
        "page": "1",
        "屆": str(term),
    }

    if session:
        params["會期"] = str(session)

    if bill_type:
        params["議案類別"] = bill_type

    if proposer:
        params["提案人"] = proposer

    if keyword:
        params["q"] = f'"{keyword}"'

    # Add aggregation parameters
    if include_aggs:
        params["agg"] = "提案來源,議案類別,議案狀態"

    url = "https://ly.govapi.tw/v2/bills"

    try:
        response = httpx.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        return {"error": str(e), "bills": [], "total": 0}
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return {"error": str(e), "bills": [], "total": 0}


def get_bill_details(bill_no: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific bill.

    Args:
        bill_no: Bill number (議案編號)

    Returns:
        Dictionary containing detailed bill information
    """
    logger.info(f"Getting details for bill: {bill_no}")

    url = f"https://ly.govapi.tw/v2/bills/{bill_no}"

    try:
        response = httpx.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        return {"error": str(e), "data": {}}
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        return {"error": str(e), "data": {}}


def get_bill_cosigners(bill_no: str) -> List[str]:
    """
    Extract co-signers from bill details.

    Args:
        bill_no: Bill number

    Returns:
        List of co-signer names
    """
    details = get_bill_details(bill_no)

    data = details.get("data", {})
    cosigners = []

    # Extract from various possible fields
    for field in ["連署人", "共同提案人", "提案人及連署人"]:
        if field in data:
            signer_data = data[field]
            if isinstance(signer_data, list):
                cosigners.extend(signer_data)
            elif isinstance(signer_data, str):
                # Parse comma-separated names
                cosigners.extend([name.strip() for name in signer_data.split("、")])

    return list(set(cosigners))  # Remove duplicates


def analyze_legislator_bills(
    term: int, name: str, bill_type_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze bill proposal statistics for a legislator.

    Args:
        term: Legislative term
        name: Legislator name
        bill_type_filter: Optional filter for bill type

    Returns:
        Dictionary with bill statistics
    """
    # Get bills proposed by the legislator
    proposed = search_bills(term=term, proposer=name, bill_type=bill_type_filter)

    # Categorize bills
    bill_categories: Dict[str, List[Dict[str, Any]]] = {}
    for bill in proposed.get("bills", []):
        category = bill.get("議案類別", "其他")
        if category not in bill_categories:
            bill_categories[category] = []
        bill_categories[category].append(
            {
                "議案編號": bill.get("議案編號"),
                "議案名稱": bill.get("議案名稱"),
                "提案日期": bill.get("提案日期"),
                "議案狀態": bill.get("議案狀態"),
            }
        )

    return {
        "立委姓名": name,
        "屆": term,
        "提案總數": proposed.get("total", 0),
        "議案類別統計": {k: len(v) for k, v in bill_categories.items()},
        "議案詳情": bill_categories,
    }


def find_bills_by_keyword(
    keyword: str, term: int = 11, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Find bills containing specific keywords.

    Args:
        keyword: Keyword to search
        term: Legislative term
        limit: Maximum results

    Returns:
        List of bills matching the keyword
    """
    results = search_bills(term=term, keyword=keyword, limit=limit)

    bills = []
    for bill in results.get("bills", []):
        bills.append(
            {
                "議案編號": bill.get("議案編號"),
                "議案名稱": bill.get("議案名稱"),
                "提案人": bill.get("提案人"),
                "提案日期": bill.get("提案日期"),
                "議案狀態": bill.get("議案狀態"),
                "會期": bill.get("會期"),
            }
        )

    return bills


def get_bill_status_timeline(bill_no: str) -> List[Dict[str, str]]:
    """
    Get the status timeline of a bill.

    Args:
        bill_no: Bill number

    Returns:
        List of status changes with dates
    """
    details = get_bill_details(bill_no)

    data = details.get("data", {})
    timeline = []

    # Extract timeline from various status fields
    if "議案流程" in data:
        timeline = data["議案流程"]
    elif "歷程" in data:
        timeline = data["歷程"]
    else:
        # Construct basic timeline from available data
        if "提案日期" in data:
            timeline.append(
                {
                    "日期": data["提案日期"],
                    "狀態": "提案",
                    "說明": f"由 {data.get('提案人', '未知')} 提案",
                }
            )

        if "審查日期" in data:
            timeline.append(
                {
                    "日期": data["審查日期"],
                    "狀態": "審查",
                    "說明": data.get("審查結果", ""),
                }
            )

    return timeline
