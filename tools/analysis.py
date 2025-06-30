import json
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
import httpx
from loguru import logger

from tools.legislators import get_legislators_by_party, get_legislator_proposed_bills
from tools.bills import search_bills, get_bill_details
from tools.interpellations import search_interpellations, analyze_legislator_positions
from tools.meetings import calculate_attendance_rate
from tools.gazettes import find_voting_records_for_bill


def analyze_party_statistics(party: str, term: int = 11) -> Dict[str, Any]:
    """
    Comprehensive analysis of a political party's performance.
    
    Args:
        party: Party name
        term: Legislative term
        
    Returns:
        Dictionary with comprehensive party statistics
    """
    stats = {
        "黨籍": party,
        "屆": term,
        "基本統計": {},
        "提案統計": {},
        "出席統計": {},
        "活躍立委": []
    }
    
    # Get party members
    party_data = get_legislators_by_party(party, term)
    if isinstance(party_data, str):
        party_data = json.loads(party_data)
    
    legislators = party_data.get("legislators", [])
    stats["基本統計"]["總人數"] = len(legislators)
    
    # Constituency distribution
    constituency_count = defaultdict(int)
    for leg in legislators:
        const = leg.get("選區名稱", "未知")
        constituency_count[const] += 1
    
    stats["基本統計"]["選區分布"] = dict(constituency_count)
    stats["基本統計"]["不分區人數"] = constituency_count.get("全國不分區", 0)
    
    # Analyze bills
    total_bills = 0
    bill_types = defaultdict(int)
    
    for leg in legislators[:10]:  # Sample first 10 to avoid too many requests
        name = leg.get("委員姓名")
        if not name:
            continue
        
        bills = search_bills(term=term, proposer=name)
        if isinstance(bills, str):
            bills = json.loads(bills)
        
        bill_count = bills.get("total", 0)
        total_bills += bill_count
        
        for bill in bills.get("bills", []):
            bill_type = bill.get("議案類別", "其他")
            bill_types[bill_type] += 1
    
    stats["提案統計"]["平均提案數"] = total_bills / min(10, len(legislators)) if legislators else 0
    stats["提案統計"]["議案類型分布"] = dict(bill_types)
    
    return stats


def analyze_voting_alignment(
    legislator: str,
    party: str,
    term: int = 11,
    sample_bills: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze how often a legislator votes with their party.
    
    Args:
        legislator: Legislator name
        party: Party name
        term: Legislative term
        sample_bills: Optional list of specific bills to analyze
        
    Returns:
        Dictionary with voting alignment analysis
    """
    alignment = {
        "立委": legislator,
        "黨籍": party,
        "分析議案數": 0,
        "一致投票數": 0,
        "一致率": "0%",
        "投票細節": []
    }
    
    # If no specific bills provided, get recent important bills
    if not sample_bills:
        # Search for recent bills (this is a simplified approach)
        bills_data = search_bills(term=term, limit=20)
        if isinstance(bills_data, str):
            bills_data = json.loads(bills_data)
        
        sample_bills = [
            bill.get("議案名稱") for bill in bills_data.get("議案資料", [])[:5]
        ]
    
    # Analyze each bill
    for bill_name in sample_bills:
        if not bill_name:
            continue
        
        # Find voting records
        voting_records = find_voting_records_for_bill(bill_name)
        
        for record in voting_records:
            individual_votes = record.get("individual_votes", {})
            
            if legislator in individual_votes:
                legislator_vote = individual_votes[legislator]
                
                # Count party votes
                party_votes = defaultdict(int)
                for voter, vote in individual_votes.items():
                    # Would need to lookup voter's party
                    # For now, this is a simplified analysis
                    party_votes[vote] += 1
                
                # Determine party majority position
                party_position = max(party_votes.items(), key=lambda x: x[1])[0]
                
                aligned = legislator_vote == party_position
                alignment["分析議案數"] += 1
                if aligned:
                    alignment["一致投票數"] += 1
                
                alignment["投票細節"].append({
                    "議案": bill_name,
                    "個人投票": legislator_vote,
                    "黨團多數": party_position,
                    "是否一致": aligned
                })
    
    # Calculate alignment rate
    if alignment["分析議案數"] > 0:
        rate = alignment["一致投票數"] / alignment["分析議案數"] * 100
        alignment["一致率"] = f"{rate:.1f}%"
    
    return alignment


def find_cross_party_cooperation(
    topic: str,
    term: int = 11
) -> Dict[str, Any]:
    """
    Find instances of cross-party cooperation on specific topics.
    
    Args:
        topic: Topic to analyze
        term: Legislative term
        
    Returns:
        Dictionary with cross-party cooperation analysis
    """
    cooperation = {
        "議題": topic,
        "跨黨派法案": [],
        "共同連署統計": defaultdict(int)
    }
    
    # Search bills related to the topic
    bills = search_bills(term=term, keyword=topic, limit=50)
    if isinstance(bills, str):
        bills = json.loads(bills)
    
    for bill in bills.get("bills", []):
        bill_no = bill.get("議案編號")
        if not bill_no:
            continue
        
        # Get bill details to find co-signers
        details = get_bill_details(bill_no)
        if isinstance(details, str):
            details = json.loads(details)
        
        # Analyze proposers and co-signers
        # (Would need to cross-reference with legislator party data)
        proposers = details.get("data", {}).get("提案人", "").split("、")
        cosigners = details.get("data", {}).get("連署人", "").split("、")
        
        all_supporters = proposers + cosigners
        
        # Count unique parties (simplified - would need party lookup)
        if len(set(all_supporters)) > 5:  # Likely cross-party if many supporters
            cooperation["跨黨派法案"].append({
                "議案名稱": bill.get("議案名稱"),
                "提案人數": len(proposers),
                "連署人數": len(cosigners),
                "總支持人數": len(all_supporters)
            })
    
    return cooperation


def rank_legislators_by_activity(
    metric: str = "bills",  # "bills", "interpellations", "attendance"
    term: int = 11,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Rank legislators by various activity metrics.
    
    Args:
        metric: Metric to rank by
        term: Legislative term
        limit: Number of top legislators to return
        
    Returns:
        List of top legislators by the specified metric
    """
    rankings = []
    
    # Get all legislators
    all_legislators = []
    for party in ["中國國民黨", "民主進步黨", "台灣民眾黨"]:
        party_data = get_legislators_by_party(party, term)
        if isinstance(party_data, str):
            party_data = json.loads(party_data)
        all_legislators.extend(party_data.get("委員資料", []))
    
    # Calculate metric for each legislator
    for leg in all_legislators[:30]:  # Sample to avoid too many requests
        name = leg.get("委員姓名")
        if not name:
            continue
        
        if metric == "bills":
            bills = search_bills(term=term, proposer=name)
            if isinstance(bills, str):
                bills = json.loads(bills)
            score = bills.get("總筆數", 0)
            
        elif metric == "interpellations":
            interps = search_interpellations(legislator=name, term=term)
            if isinstance(interps, str):
                interps = json.loads(interps)
            score = interps.get("總筆數", 0)
            
        elif metric == "attendance":
            stats = calculate_attendance_rate(name, term)
            score = float(stats["出席率"].rstrip('%'))
        
        else:
            score = 0
        
        rankings.append({
            "立委": name,
            "黨籍": leg.get("黨籍"),
            "分數": score,
            "指標": metric
        })
    
    # Sort by score
    rankings.sort(key=lambda x: x["分數"], reverse=True)
    
    return rankings[:limit]


def analyze_topic_focus(
    legislator: str,
    topics: List[str],
    term: int = 11
) -> Dict[str, Any]:
    """
    Analyze which topics a legislator focuses on most.
    
    Args:
        legislator: Legislator name
        topics: List of topics to analyze
        term: Legislative term
        
    Returns:
        Dictionary with topic focus analysis
    """
    focus_analysis = {
        "立委": legislator,
        "議題關注度": {},
        "總質詢數": 0,
        "總提案數": 0
    }
    
    for topic in topics:
        # Count interpellations
        interps = search_interpellations(
            legislator=legislator,
            keyword=topic,
            term=term
        )
        if isinstance(interps, str):
            interps = json.loads(interps)
        
        interp_count = interps.get("總筆數", 0)
        
        # Count related bills
        bills = search_bills(
            term=term,
            proposer=legislator,
            keyword=topic
        )
        if isinstance(bills, str):
            bills = json.loads(bills)
        
        bill_count = bills.get("total", 0)
        
        focus_analysis["議題關注度"][topic] = {
            "質詢次數": interp_count,
            "相關提案": bill_count,
            "總計": interp_count + bill_count
        }
        
        focus_analysis["總質詢數"] += interp_count
        focus_analysis["總提案數"] += bill_count
    
    # Sort topics by total activity
    sorted_topics = sorted(
        focus_analysis["議題關注度"].items(),
        key=lambda x: x[1]["總計"],
        reverse=True
    )
    
    focus_analysis["最關注議題"] = sorted_topics[0][0] if sorted_topics else None
    
    return focus_analysis


def compare_legislators_performance(
    legislators: List[str],
    term: int = 11,
    session: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Compare multiple legislators across various metrics.
    
    Args:
        legislators: List of legislator names to compare
        term: Legislative term
        session: Optional session number
        
    Returns:
        List of performance comparisons
    """
    comparisons = []
    
    for legislator in legislators:
        # Get basic info
        perf = {
            "立委": legislator,
            "出席率": "0%",
            "提案數": 0,
            "質詢數": 0,
            "主要關注": []
        }
        
        # Attendance
        attendance = calculate_attendance_rate(legislator, term, session)
        perf["出席率"] = attendance["出席率"]
        
        # Bills
        bills = search_bills(term=term, proposer=legislator)
        if isinstance(bills, str):
            bills = json.loads(bills)
        perf["提案數"] = bills.get("總筆數", 0)
        
        # Interpellations
        interps = search_interpellations(legislator=legislator, term=term)
        if isinstance(interps, str):
            interps = json.loads(interps)
        perf["質詢數"] = interps.get("總筆數", 0)
        
        comparisons.append(perf)
    
    return comparisons