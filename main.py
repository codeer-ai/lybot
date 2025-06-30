import asyncio
import json
import urllib.parse
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger
from markitdown import MarkItDown
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings

# Import all tool modules
from tools.legislators import (
    get_legislator_by_constituency,
    get_legislator_details,
    get_legislators_by_party,
    get_legislator_proposed_bills,
    get_legislator_meetings,
    get_party_seat_count,
    get_legislator_committees
)
from tools.bills import (
    search_bills,
    get_bill_details,
    get_bill_cosigners,
    analyze_legislator_bills,
    find_bills_by_keyword
)
from tools.gazettes import (
    search_gazettes,
    get_gazette_details,
    get_gazette_agendas,
    extract_voting_records_from_pdf,
    find_voting_records_for_bill
)
from tools.interpellations import (
    search_interpellations,
    get_interpellation_details,
    get_meeting_interpellations,
    get_legislator_interpellations,
    analyze_legislator_positions,
    find_legislators_by_position
)
from tools.meetings import (
    get_committees,
    get_meeting_bills,
    get_meeting_ivods,
    calculate_attendance_rate,
    compare_attendance_rates,
    get_session_info,
    get_party_attendance_statistics
)
from tools.analysis import (
    analyze_party_statistics,
    analyze_voting_alignment,
    find_cross_party_cooperation,
    rank_legislators_by_activity,
    analyze_topic_focus,
    compare_legislators_performance
)

md = MarkItDown()
# model = OpenAIModel(
#     "gpt-4.1",
#     provider=AzureProvider(
#         api_key=os.getenv("AZURE_API_KEY", ""),
#         api_version="2024-05-01-preview",
#         azure_endpoint=os.getenv("AZURE_API_BASE", ""),
#     ),
# )

model = GoogleModel("gemini-2.5-pro")
settings = GoogleModelSettings(google_thinking_config={"include_thoughts": True})


instructions = f"""
You are a research assistant that can help with tasks related to the Legislative Yuan.
Today is {datetime.now().strftime("%Y-%m-%d")}.

使用工具來取得資料，不要自己猜測。務必取得足夠的資料之後再做出結論。

重要原則：
* 如果跟黨籍相關的問題，請使用完整的黨名（例如：中國國民黨、民主進步黨、台灣民眾黨）
* 都是查詢第 11 屆立法委員
* Always call tools to get the latest information
* 處理選區查詢時，工具會自動處理「台北市第七選區」和「臺北市北松山‧信義」等不同格式
* 查詢投票記錄時，先用 find_voting_records_for_bill 或從公報中提取
* 分析立委立場時，結合質詢記錄和投票記錄
* 計算出席率時使用 calculate_attendance_rate
* 留下原始 reference 來支持你的結論

立委相關工具：
- get_legislator_by_constituency: 根據選區查詢立委（支援模糊比對）
- get_legislator_details: 取得立委詳細資訊（包含委員會）
- get_legislators_by_party: 取得特定政黨所有立委
- get_legislator_proposed_bills: 取得立委提案的法案
- get_legislator_meetings: 取得立委參加的會議
- get_party_seat_count: 統計政黨席次
- get_legislator_committees: 取得立委委員會資訊

法案相關工具：
- search_bills: 搜尋法案（可用關鍵字、提案人等）
- get_bill_details: 取得法案詳細資訊
- get_bill_cosigners: 取得法案連署人
- analyze_legislator_bills: 分析立委提案統計
- find_bills_by_keyword: 用關鍵字搜尋法案

投票與公報工具：
- search_gazettes: 搜尋公報（可能包含投票記錄）
- get_gazette_details: 取得公報詳情（含PDF連結）
- get_gazette_agendas: 取得公報議程
- extract_voting_records_from_pdf: 從PDF提取投票記錄
- find_voting_records_for_bill: 查詢特定法案的投票記錄

質詢相關工具：
- search_interpellations: 搜尋質詢記錄
- get_interpellation_details: 取得質詢詳細內容
- get_legislator_interpellations: 取得立委所有質詢
- analyze_legislator_positions: 分析立委對特定議題立場
- find_legislators_by_position: 找出支持/反對特定立場的立委

會議相關工具：
- get_committees: 取得委員會列表
- get_meeting_info: 取得會議資訊
- get_meeting_info_by_id: 取得特定會議詳情
- get_meeting_bills: 取得會議討論的法案
- get_meeting_ivods: 取得會議IVOD影片
- calculate_attendance_rate: 計算立委出席率
- compare_attendance_rates: 比較多位立委出席率
- get_session_info: 取得會期資訊
- get_party_attendance_statistics: 統計政黨出席率

綜合分析工具：
- analyze_party_statistics: 分析政黨整體表現
- analyze_voting_alignment: 分析立委與黨團投票一致性
- find_cross_party_cooperation: 找出跨黨派合作案例
- rank_legislators_by_activity: 依活躍度排名立委
- analyze_topic_focus: 分析立委關注議題
- compare_legislators_performance: 比較多位立委表現

IVOD相關工具：
- search_ivod: 搜尋IVOD影片
- get_ivod_transcript: 取得IVOD文字稿

其他工具：
- get_pdf_markdown: 將PDF轉換為markdown格式
"""

agent = Agent(
    model,
    instructions=instructions,
    model_settings=settings,
)


@agent.tool_plain
def get_legislators(name: Optional[str] = None, party: Optional[str] = None) -> str:
    """
    Get the list of legislators. (第 11 屆立法委員)

    Args:
        name: The name of the legislator.
        party: The party of the legislator.

    Returns:
        The list of legislators.
        The list of legislators is a list of dictionaries, each dictionary contains the following information:
            委員姓名、黨籍、選區名稱、聯絡資訊、委員會、性別、學經歷、是否離職

    """
    logger.info("Getting legislators.")
    params = {
        "limit": "200",
        "page": "1",
        "agg": "委員姓名",
        "屆": "11",
    }
    if name:
        params["委員姓名"] = name

    if party:
        params["黨籍"] = party

    logger.debug(params)
    url = "https://ly.govapi.tw/v2/legislators"
    response = httpx.get(url, params=params)

    return response.json()


@agent.tool_plain
def get_pdf_markdown(pdf_url: str) -> str:
    """
    Get the markdown of a PDF url.
    """
    logger.info(f"Getting markdown of {pdf_url}.")

    # Create a custom SSL context that allows legacy renegotiation
    import ssl

    ssl_context = ssl.create_default_context()
    ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")
    ssl_context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    # Use httpx with custom SSL context
    with httpx.Client(verify=ssl_context, headers=headers) as client:
        response = client.get(pdf_url)
        response.raise_for_status()
        # Write response content to a temporary file
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".pdf", delete=False
        ) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        try:
            # Convert the PDF file to markdown using MarkItDown
            result = md.convert(temp_file_path)
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)

        # Convert the PDF content to markdown

        # Return the text content from MarkItDown result
        return result.text_content


@agent.tool_plain
def get_ivod_transcript(ivod_id: str) -> str:
    """
    Get the transcript of a IVOD video.
    """
    logger.info(f"Getting transcript of {ivod_id}.")
    url = f"https://ly.govapi.tw/v2/ivod/{ivod_id}"

    response = httpx.get(url)
    data = response.json()["data"]
    if "transcript" in data and data["transcript"]:
        combined_transcript = "\n".join(
            [item["text"] for item in data["transcript"]["whisperx"]]
        )
        # logger.info(f"Combined transcript: {combined_transcript}")
        data["transcript"] = combined_transcript
    else:
        # logger.info(f"No transcript found for {ivod_id}.")
        data["transcript"] = ""

    return data


@agent.tool_plain
def get_meeting_info(
    session: Optional[int] = None,
    attendees: Optional[list[str] | str] = None,
    meeting_type: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 50,
    page: int = 1,
) -> str:
    """
    Get meeting information from Legislative Yuan (第 11 屆).

    Args:
        session: 會期 (session number)
        attendees: 會議資料.出席委員 (list of attending legislator names, or single string)
        meeting_type: 會議種類 (委員會、公聽會、黨團協商、院會、聯席會議、全院委員會)
        date: 日期 (date filter in ISO format, e.g., "2024-04-22T00:00:00.000Z" or "2024-04-22")
        limit: Number of results per page (default: 50)
        page: Page number (default: 1)

    Returns:
        JSON response containing meeting information
    """
    logger.info("Getting meeting information.")

    # Build URL query parts manually to handle repeated parameters
    url = "https://ly.govapi.tw/v2/meets"
    query_parts = []

    # Add basic parameters
    query_parts.append(f"limit={limit}")
    query_parts.append(f"page={page}")
    query_parts.append(f"{urllib.parse.quote('屆')}=11")  # Fixed to 11th term

    if session:
        query_parts.append(f"{urllib.parse.quote('會期')}={session}")

    if meeting_type:
        query_parts.append(
            f"{urllib.parse.quote('會議種類')}={urllib.parse.quote(meeting_type)}"
        )

    if date:
        # Handle date format - if it's just a date (YYYY-MM-DD), convert to ISO format
        if len(date) == 10 and date.count("-") == 2:  # Simple date format YYYY-MM-DD
            date_formatted = f"{date}T00:00:00.000Z"
        else:
            date_formatted = date
        query_parts.append(
            f"{urllib.parse.quote('日期')}={urllib.parse.quote(date_formatted)}"
        )

    # Handle attendees (single string or list of strings)
    if attendees:
        # Convert single string to list for uniform handling
        attendee_list = [attendees] if isinstance(attendees, str) else attendees
        for attendee in attendee_list:
            query_parts.append(
                f"{urllib.parse.quote('會議資料.出席委員')}={urllib.parse.quote(attendee)}"
            )

    # Add aggregation parameters
    query_parts.append("agg=" + urllib.parse.quote("會期"))
    query_parts.append("agg=" + urllib.parse.quote("會議種類"))

    full_url = f"{url}?{'&'.join(query_parts)}"
    logger.debug(f"Meeting search URL: {full_url}")

    response = httpx.get(full_url)
    return response.json()


@agent.tool_plain
def get_meeting_info_by_id(meeting_id: str) -> str:
    """
    Get detailed meeting information by meeting ID.

    Args:
        meeting_id: 會議代碼 (meeting code/ID, e.g., "黨團協商-2025060995")

    Returns:
        JSON response containing detailed meeting information including:
        - 會議基本資料 (basic meeting info)
        - 議事網資料 (parliamentary data)
        - 關係文書 (related documents)
        - 附件 (attachments)
        - 連結 (links to videos, documents)
        - 相關資料 (related data like IVODs, bills, interpellations)
    """

    logger.info(f"Getting detailed meeting information for ID: {meeting_id}")

    # URL encode the meeting ID to handle Chinese characters and special characters
    encoded_meeting_id = urllib.parse.quote(meeting_id)
    url = f"https://ly.govapi.tw/v2/meet/{encoded_meeting_id}"

    logger.debug(f"Meeting detail URL: {url}")

    response = httpx.get(url)
    return response.json()


@agent.tool_plain
def search_ivod(
    legislator_name: str,
    query: str,
) -> str:
    """
    Search for IVOD videos by legislator name and query.
    Backend 是使用 elasticsearch.

    Args:
        legislator_name: The name of the legislator (委員名稱)
        query: The search query (q)

    Returns:
        JSON response containing IVOD search results
    """
    logger.info(
        f"Searching IVOD for legislator '{legislator_name}' with query '{query}'."
    )

    params = {
        "limit": str(200),
        "q": f'"{query}"',  # 用雙引號包住查詢字串，如同範例 URL
        "agg": "影片種類",
        "屆": "11",
        "委員名稱": legislator_name,
    }

    logger.debug(f"Search params: {params}")
    url = "https://ly.govapi.tw/v2/ivods"
    response = httpx.get(url, params=params)
    data = response.json()
    r = json.dumps(
        [
            {
                "IVOD_ID": str(ivod["IVOD_ID"]),
                "IVOD_URL": ivod["IVOD_URL"],
                "日期": ivod["日期"],
                "會議資料": ivod["會議資料"],
                "委員名稱": ivod["委員名稱"],
                "會議名稱": ivod["會議名稱"],
            }
            for ivod in data["ivods"]
        ],
        ensure_ascii=False,
    )
    logger.info(f"Search results: {r}")
    return r


# Register enhanced legislator tools
agent.tool_plain(get_legislator_by_constituency)
agent.tool_plain(get_legislator_details)
agent.tool_plain(get_legislators_by_party)
agent.tool_plain(get_legislator_proposed_bills)
agent.tool_plain(get_legislator_meetings)
agent.tool_plain(get_party_seat_count)
agent.tool_plain(get_legislator_committees)

# Register bill tools
agent.tool_plain(search_bills)
agent.tool_plain(get_bill_details)
agent.tool_plain(get_bill_cosigners)
agent.tool_plain(analyze_legislator_bills)
agent.tool_plain(find_bills_by_keyword)

# Register gazette and voting tools
agent.tool_plain(search_gazettes)
agent.tool_plain(get_gazette_details)
agent.tool_plain(get_gazette_agendas)
agent.tool_plain(extract_voting_records_from_pdf)
agent.tool_plain(find_voting_records_for_bill)

# Register interpellation tools
agent.tool_plain(search_interpellations)
agent.tool_plain(get_interpellation_details)
agent.tool_plain(get_meeting_interpellations)
agent.tool_plain(get_legislator_interpellations)
agent.tool_plain(analyze_legislator_positions)
agent.tool_plain(find_legislators_by_position)

# Register meeting tools
agent.tool_plain(get_committees)
agent.tool_plain(get_meeting_bills)
agent.tool_plain(get_meeting_ivods)
agent.tool_plain(calculate_attendance_rate)
agent.tool_plain(compare_attendance_rates)
agent.tool_plain(get_session_info)
agent.tool_plain(get_party_attendance_statistics)

# Register analysis tools
agent.tool_plain(analyze_party_statistics)
agent.tool_plain(analyze_voting_alignment)
agent.tool_plain(find_cross_party_cooperation)
agent.tool_plain(rank_legislators_by_activity)
agent.tool_plain(analyze_topic_focus)
agent.tool_plain(compare_legislators_performance)


async def main():
    try:
        await agent.to_cli()
    except Exception:
        pass
        # await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())
