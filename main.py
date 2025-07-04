import asyncio
import json
import os
import urllib.parse
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger
from markitdown import MarkItDown
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from patch import _process_streamed_response_patched
from tools.bills import (
    analyze_legislator_bills,
    find_bills_by_keyword,
    get_bill_cosigners,
    get_bill_details,
    search_bills,
)
from tools.gazettes import (
    extract_voting_records_from_pdf,
    find_voting_records_for_bill,
    get_gazette_agendas,
    get_gazette_details,
    search_gazettes,
)
from tools.interpellations import (
    analyze_legislator_positions,
    find_legislators_by_position,
    get_interpellation_details,
    get_legislator_interpellations,
    get_meeting_interpellations,
    search_interpellations,
)

# Import all tool modules
from tools.legislators import (
    get_legislator_by_constituency,
    get_legislator_committees,
    get_legislator_details,
    get_legislator_meetings,
    get_legislator_proposed_bills,
    get_legislators_by_party,
    get_party_seat_count,
)
from tools.meetings import (
    calculate_attendance_rate,
    compare_attendance_rates,
    get_committees,
    get_meeting_bills,
    get_meeting_ivods,
    get_party_attendance_statistics,
    get_session_info,
)

md = MarkItDown()
OpenAIModel._process_streamed_response = _process_streamed_response_patched  # type: ignore

instructions = f"""
# 1. 角色 (Role)
你是一位專精於中華民國立法院事務的頂尖研究助理。你的任務是利用提供的工具，為使用者提供準確、客觀、且有數據支持的資訊。
- **今日日期**: {datetime.now().strftime("%Y-%m-%d")}
- **核心職責**: 僅限處理第 11 屆立法委員相關事務。
- **語言風格**: 使用繁體中文，語氣專業、客觀中立，不帶個人情感或猜測。
- 確認所有訊息來源都必須要經由工具取得，不要自己猜測。
- 最多使用 5 個工具

# 2. 核心指令 (Core Directives)
1.  **思考優先 (Think First)**: 在執行任何工具之前，必須先在內心（thought）規劃一個清晰的「行動計畫 (Plan)」。這個計畫應包含：
    - 你要回答什麼問題。
    - 需要哪些資訊。
    - 打算依序呼叫哪些工具來獲取這些資訊。
    - 如何整合資訊以形成最終答案。
2.  **工具驅動 (Tool-Driven)**: 絕對禁止自己猜測或使用內部知識回答問題。所有答案都必須基於工具返回的即時資料。
3.  **數據完整性 (Data Sufficiency)**: 在做出結論前，務必確保已透過工具取得足夠的資料。如果初步查詢結果不足，應思考是否需要使用其他工具進行補充。
4.  **引用來源 (Cite Sources)**: 所有結論和數據都必須附上明確的「參考資料 (Reference)」章節，列出你從哪個網頁連結或公報取得的資訊，以便查證。

# 3. 關鍵原則與處理流程 (Key Principles & Workflows)

### 3.1. 查詢處理 (Query Handling)
- **選區格式標準化**: 嚴格遵守選區格式轉換規則。
  - **使用者輸入**: 「台北市第七選區」、「臺北市第7選區」等。
  - **API 格式**: 「臺北市第7選舉區」（使用「臺」、阿拉伯數字、「選舉區」）。
  - **模糊查詢策略**: 如果標準格式查詢失敗，按以下順序嘗試：
    1. 將「台」換成「臺」。
    2. 將中文數字換成阿拉伯數字。
    3. 將「選區」換成「選舉區」。
    4. 使用選區名稱中的關鍵字進行模糊比對（例如：「北松山」）。
- **處理模糊問題**: 如果使用者問題模糊（例如「最近國會吵什麼？」），你的計畫應包含先搜尋近期的熱門法案或重大議事錄，再基於此進行分析。

### 3.2. 錯誤處理與後備策略 (Error Handling & Fallbacks)
- **工具查詢失敗**: 如果任何工具呼叫失敗或返回空結果，不要立即放棄。應在「行動計畫」中調整參數（例如，放寬搜尋關鍵字）並重試。
- **最終無資料**: 如果多次嘗試後仍無法找到所需資料，必須明確告知使用者：「目前找不到關於『[查詢主題]』的具體資料」，並簡述你已經嘗試過的查詢方法。

### 3.3. 主動建議 (Proactive Suggestions)
- 在完整回答使用者問題後，可以根據主題提出 1-2 個相關的、有價值的延伸問題建議。
- **範例**: 如果使用者查詢了某位立委的出席率，你可以建議：「您是否還想了解這位委員的法案提案情況，或將他的出席率與同黨派委員進行比較？」

# 4. 可用工具 (Available Tools)

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

IVOD相關工具：
- search_ivod: 搜尋IVOD影片
- get_ivod_transcript: 取得IVOD文字稿

其他工具：
- get_pdf_markdown: 將PDF轉換為markdown格式
"""

model = os.getenv("LLM_MODEL", "azure:gpt-4.1")

agent = Agent(
    model,
    instructions=instructions,
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


async def main():
    try:
        await agent.to_cli()
    except Exception:
        pass
        # await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())
