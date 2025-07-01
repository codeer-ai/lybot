import json
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger



def get_legislator_by_constituency(constituency: str) -> str:
    """
    Get legislators by electoral district.

    Args:
        constituency: Electoral district name (e.g., "台北市第七選區" or "臺北市北松山‧信義")

    Returns:
        JSON string containing legislator information for the constituency
    """
    logger.info(f"Getting legislators for constituency: {constituency}")

    params = {
        "limit": "200",
        "page": "1",
        "agg": "委員姓名",
        "屆": "11",
        "選區名稱": constituency,
    }

    logger.debug(f"Search params: {params}")
    url = "https://ly.govapi.tw/v2/legislators"
    response = httpx.get(url, params=params)

    data = response.json()
    if data.get("total", 0) == 0:
        # Try alternative search strategies
        logger.info("No results found, trying partial match...")
        # Remove params and search all, then filter
        params.pop("選區名稱")
        response = httpx.get(url, params=params)
        all_data = response.json()

        # Filter results
        filtered_legislators = []
        for legislator in all_data.get("legislators", []):
            if constituency in legislator.get("選區名稱", ""):
                filtered_legislators.append(legislator)

        data["legislators"] = filtered_legislators
        data["total"] = len(filtered_legislators)

    return json.dumps(data, ensure_ascii=False)


def get_legislator_details(term: int, name: str) -> str:
    """
    Get detailed information about a specific legislator.

    Args:
        term: Legislative term (屆)
        name: Legislator name

    Returns:
        JSON string containing detailed legislator information
    """
    logger.info(f"Getting details for legislator: {name} (term: {term})")

    url = f"https://ly.govapi.tw/v2/legislators/{term}/{name}"
    response = httpx.get(url)
    data = response.json()
    data["relations"] = [
        {
            "url": f"https://ly.govapi.tw/v2/legislators/{term}/{name}/propose_bills",
            "name": "propose_bills",
        },
        {
            "url": f"https://ly.govapi.tw/v2/legislators/{term}/{name}/cosign_bills",
            "name": "cosign_bills",
        },
        {
            "url": f"https://ly.govapi.tw/v2/legislators/{term}/{name}/meets",
            "name": "meets",
        },
        {
            "url": f"https://ly.govapi.tw/v2/legislators/{term}/{name}/interpellations",
            "name": "interpellations",
        },
    ]
    return data


def get_legislators_by_party(party: str, term: int = 11) -> str:
    """
    List all legislators from a specific party.

    Args:
        party: Party name (e.g., "中國國民黨", "民主進步黨", "台灣民眾黨")
        term: Legislative term (default: 11)

    Returns:
        JSON string containing all legislators from the party
    """
    logger.info(f"Getting legislators for party: {party}")

    params = {
        "limit": "200",
        "page": "1",
        "agg": "委員姓名",
        "屆": str(term),
        "黨籍": party,
    }

    url = "https://ly.govapi.tw/v2/legislators"
    response = httpx.get(url, params=params)

    return response.json()


def get_legislator_proposed_bills(
    term: int, name: str, bill_type: Optional[str] = None
) -> str:
    """
    Get bills proposed by a specific legislator.

    Args:
        term: Legislative term
        name: Legislator name
        bill_type: Optional bill type filter

    Returns:
        JSON string containing proposed bills
    """
    logger.info(f"Getting proposed bills for legislator: {name}")

    url = f"https://ly.govapi.tw/v2/legislators/{term}/{name}/propose_bills"
    params = {"limit": "200", "page": "1"}

    if bill_type:
        params["議案類別"] = bill_type

    response = httpx.get(url, params=params)
    return response.json()


def get_legislator_meetings(
    term: int,
    name: str,
    meeting_type: Optional[str] = None,
    session: Optional[int] = None,
) -> str:
    """
    Get meeting attendance records for a specific legislator.

    Args:
        term: Legislative term
        name: Legislator name
        meeting_type: Optional meeting type filter
        session: Optional session number filter

    Returns:
        JSON string containing meeting attendance records
    """
    logger.info(f"Getting meeting records for legislator: {name}")

    url = f"https://ly.govapi.tw/v2/legislators/{term}/{name}/meets"
    params = {"limit": "200", "page": "1"}

    if meeting_type:
        params["會議種類"] = meeting_type

    if session:
        params["會期"] = str(session)

    response = httpx.get(url, params=params)
    return response.json()


def get_party_seat_count(party: str, term: int = 11) -> Dict[str, Any]:
    """
    Get the total number of seats for a party across all constituencies.

    Args:
        party: Party name
        term: Legislative term (default: 11)

    Returns:
        Dictionary with party statistics
    """
    data = get_legislators_by_party(party, term)

    if isinstance(data, str):
        data = json.loads(data)

    total_seats = data.get("total", 0)

    # Group by constituency
    constituencies = {}
    for legislator in data.get("legislators", []):
        const = legislator.get("選區名稱", "未知")
        if const not in constituencies:
            constituencies[const] = []
        constituencies[const].append(legislator.get("委員姓名", ""))

    return {
        "黨籍": party,
        "總席次": total_seats,
        "各選區分布": constituencies,
        "選區數量": len(constituencies),
    }


def get_legislator_committees(term: int, name: str) -> List[Dict[str, str]]:
    """
    Get committee memberships for a specific legislator.

    Args:
        term: Legislative term
        name: Legislator name

    Returns:
        List of committee memberships with positions
    """
    details = get_legislator_details(term, name)

    if isinstance(details, str):
        details = json.loads(details)

    committees = []
    data = details.get("data", {})

    # Extract committee information from various fields
    for field in ["現任委員會", "歷屆委員會", "委員會"]:
        if field in data:
            committee_data = data[field]
            if isinstance(committee_data, list):
                committees.extend(committee_data)
            elif isinstance(committee_data, dict):
                committees.append(committee_data)

    return committees
