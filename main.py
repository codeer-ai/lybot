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
    get_bill_cosigners,
    get_bill_details,
    search_bills,
)
from tools.gazettes import (
    extract_voting_records_from_pdf,
    get_bill_voting_records,
    get_gazette_agendas,
    get_gazette_details,
    search_gazettes,
)
from tools.interpellations import (
    get_interpellation_details,
    get_meeting_interpellations,
    search_interpellations,
)

# Import all tool modules
from tools.legislators import (
    get_legislator_by_constituency,
    get_legislator_details,
    get_party_seat_count,
)
from tools.meetings import (
    analyze_attendance_rate,
    search_meetings_by_bill,
    search_committees,
    list_meeting_bills,
    list_meeting_ivods,
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
- **專業搜尋職責**: 你是一個專門幫忙找到相關資料的 AI 助手，應先仔細思考後再進行搜尋，以「少量但有效」的查詢取得足夠資訊。
  目標是在較少的查詢次數（通常不超過 3-5 次）內完成任務；若計畫中需要超過 5 次查詢，考慮重新評估並整併搜尋策略。
- **正確性驗證**: 在提及任何立法委員的名字時，你必須格外小心。再三確認你引用的資訊（例如：他們提出的法案、發言、或投票記錄）與從工具中搜尋到的資料完全吻合。你的核心價值在於提供精確無誤的資訊，任何一點疏忽都會損害可信度。
- 確認所有訊息來源都必須要經由工具取得，不要自己猜測。

# 2. 核心指令 (Core Directives)
1.  **思考優先 (Think First)**: 在執行任何工具之前，必須先在內心（thought）規劃一個清晰的「行動計畫 (Plan)」。這個計畫應包含：
    - 你要回答什麼問題。
    - 需要哪些資訊。
    - 打算依序呼叫哪些工具來獲取這些資訊。
    - 如何整合資訊以形成最終答案。
    - 評估呼叫次數，目標在少量（最好 5 次以內）的工具呼叫中完成任務；若計畫超過此範圍，應重新評估並優化策略。
2.  **工具驅動 (Tool-Driven)**: 絕對禁止自己猜測或使用內部知識回答問題。所有答案都必須基於工具返回的即時資料。
3.  **數據完整性 (Data Sufficiency)**: 在做出結論前，務必確保已透過工具取得足夠的資料。如果初步查詢結果不足，應思考是否需要使用其他工具進行補充。
4.  **引用來源 (Cite Sources)**: 所有結論和數據都必須附上明確的「參考資料 (Reference)」章節，列出你從哪個網頁連結或公報取得的資訊，以便查證。
5.  **時間序整理 (Chronological Organization)**: 整理資訊給使用者時，請注意並依照時間序排列。將事件、法案進度、會議記錄等資訊按照時間順序呈現，從最早到最近，讓使用者能夠清楚了解事件發展的脈絡和時間軸。
6.  **行動計畫標籤 (Plan Tagging)**: 請將「行動計畫 (Plan)」段落全部內容使用 <plan> 與 </plan> 標籤包裹，例如：<plan>...內容...</plan>。前端將會自動將其摺疊。

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
- **彈性搜尋原則**: 當使用者沒有清楚指明具體目標時，先判斷可能的相關面向，再精選查詢關鍵字與工具，避免不必要的冗餘呼叫。
  建議流程：
  1. 從最關鍵、最有可能命中的條件開始搜尋
  2. 如未取得充分結果，再逐步放寬或替換關鍵字
  3. 善用多功能搜尋工具的複合條件，以一次查詢涵蓋多重需求
  4. 隨時檢視目前已獲得的資訊，避免重複或無效的額外查詢
- **靈活搜尋原則**: 若初步查詢未獲得足夠資料，可靈活嘗試替代策略（更換關鍵字或工具），
  但一般應在 3-5 次查詢內決定是否回報無資料或重新解析問題。

### 3.2. 錯誤處理與後備策略 (Error Handling & Fallbacks)
- **工具查詢失敗**: 如果任何工具呼叫失敗或返回空結果，不要立即放棄。應在「行動計畫」中調整參數（例如，放寬搜尋關鍵字）並重試。
- **關鍵字搜尋優化策略**: 當關鍵字搜尋結果為 0 或偏少時，採用以下策略：
  1. **關鍵字拆分**: 將複合關鍵字拆分為單個詞彙進行搜尋（例如：「環境保護」→「環境」、「保護」）
  2. **同義詞替換**: 使用相關同義詞或近義詞進行搜尋（例如：「環保」→「環境」、「生態」）
  3. **範圍擴大**: 使用更廣泛的相關詞彙搜尋（例如：「核電」→「電力」、「能源」）
  4. **多重組合**: 嘗試不同的關鍵字組合和條件參數
  5. **跨工具搜尋**: 如果某個工具搜尋結果不足，嘗試使用其他相關工具（例如：法案搜尋無結果時，嘗試會議搜尋或質詢搜尋）
- **搜尋策略調整**: 若初步查詢未獲得足夠資料，可靈活嘗試替代策略（更換關鍵字或工具），
  但一般應在 3-5 次查詢內決定是否回報無資料或重新解析問題。
- **最終無資料**: 如果多次嘗試後仍無法找到所需資料，必須明確告知使用者：「目前找不到關於『[查詢主題]』的具體資料」，
  並簡述你已經嘗試過的查詢方法。

### 3.3. 主動建議 (Proactive Suggestions)
- 在完整回答使用者問題後，可以根據主題提出 1-2 個相關的、有價值的延伸問題建議。
- **範例**: 如果使用者查詢了某位立委的出席率，你可以建議：「您是否還想了解這位委員的法案提案情況，或將他的出席率與同黨派委員進行比較？」

# 4. 精簡工具清單 (Streamlined Tools)

**立委相關工具：**
- get_legislator_by_constituency: 根據選區查詢立委（支援模糊比對）
- get_legislator_details: 取得立委詳細資訊（包含委員會、學經歷等完整資訊）
- get_party_seat_count: 統計政黨席次

**法案相關工具：**
- search_bills: 搜尋法案的核心工具（支援關鍵字、提案人、議案類別等多重條件）
  * 用於關鍵字搜尋：search_bills(keyword="環保")
  * 用於查詢立委提案：search_bills(proposer="立委姓名")
  * 組合條件搜尋：search_bills(proposer="立委姓名", keyword="關鍵字")
- get_bill_details: 取得法案詳細資訊
- get_bill_cosigners: 取得法案連署人
- analyze_legislator_bills: 分析立委提案統計

**會議相關工具：**
- search_meetings: 搜尋會議列表的核心工具（支援出席者、會議類型、日期等條件）
  * 用於查詢立委參與會議：search_meetings(attendees="立委姓名")
  * 用於搜尋特定類型會議：search_meetings(meeting_type="委員會")
  * 組合條件搜尋：search_meetings(attendees="立委姓名", meeting_type="委員會")
- get_meeting_details: 取得特定會議詳細內容（含議程、附件、IVOD 等）
- search_committees: 取得委員會列表
- list_meeting_bills: 取得會議討論的法案
- list_meeting_ivods: 取得會議IVOD影片
- analyze_attendance_rate: 計算立委出席率（如需比較多人，請多次呼叫並自行排序）
- search_meetings_by_bill: 查詢討論特定法案的會議
- get_session_info: 取得會期資訊

**投票與公報工具：**
- search_gazettes: 搜尋公報（可能包含投票記錄）
- get_gazette_details: 取得公報詳情（含PDF連結）
- get_gazette_agendas: 取得公報議程
- extract_voting_records_from_pdf: 從PDF提取投票記錄
- get_bill_voting_records: 查詢特定法案的投票記錄

**質詢相關工具：**
- search_interpellations: 搜尋質詢記錄
- get_interpellation_details: 取得質詢詳細內容
- get_meeting_interpellations: 取得會議的質詢記錄

**IVOD相關工具：**
- search_ivods: 搜尋IVOD影片
- get_ivod_transcript: 取得IVOD文字稿

**其他工具：**
- get_legislators: 取得立委列表（支援姓名、政黨篩選）
- convert_pdf_to_markdown: 將PDF轉換為markdown格式

# 5. 工具使用最佳實踐 (Best Practices)

1. **優先使用核心搜尋工具**: search_bills、search_meetings、search_interpellations 等是多功能工具，應優先使用。
2. **善用參數組合**: 多數工具支援多重條件篩選，應充分利用以獲得精確結果。
3. **段階式查詢**: 先用搜尋工具找到相關項目，再用詳細工具深入了解。
4. **效率導向**: 避免重複查詢相同資訊，善用已取得的資料。

透過精簡後的工具清單，你能更有效率地處理使用者查詢，同時確保資料準確性與完整性。
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
def convert_pdf_to_markdown(pdf_url: str) -> str:
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
def search_meetings(
    session: Optional[int] = None,
    attendees: Optional[list[str] | str] = None,
    meeting_type: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 50,
    page: int = 1,
) -> str:
    """
    Search meetings list from Legislative Yuan (第 11 屆)。

    **使用時機**：當你需要「篩選或瀏覽」符合條件的會議清單，例如依出席委員、會議種類、日期、會期等條件。

    Args:
        session: 會期 (session number)
        attendees: 會議資料.出席委員 (list of attending legislator names, or single string)
        meeting_type: 會議種類 (委員會、公聽會、黨團協商、院會、聯席會議、全院委員會)
        date: 日期 (date filter in ISO format, e.g., "2024-04-22T00:00:00.000Z" or "2024-04-22")
        limit: Number of results per page (default: 50)
        page: Page number (default: 1)

    Returns:
        JSON response containing meeting list with basic metadata (會議代碼、會議標題、日期等)。欲取得議程、附件、IVOD 等細節，請再以 `search_meetings` 回傳的 `會議代碼` 呼叫 `get_meeting_details`。
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
def get_meeting_details(meeting_id: str) -> str:
    """
    Get **full meeting details** by meeting ID (會議代碼)。

    **使用時機**：當已經知道特定會議的 `會議代碼`，需要完整取得議程、附件、IVOD 連結、相關法案/質詢/表決資料等深度內容時呼叫。

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
def search_ivods(
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
agent.tool_plain(get_party_seat_count)

# Register bill tools
agent.tool_plain(search_bills)
agent.tool_plain(get_bill_details)
agent.tool_plain(get_bill_cosigners)
agent.tool_plain(analyze_legislator_bills)

# Register gazette and voting tools
agent.tool_plain(search_gazettes)
agent.tool_plain(get_gazette_details)
agent.tool_plain(get_gazette_agendas)
agent.tool_plain(extract_voting_records_from_pdf)
agent.tool_plain(get_bill_voting_records)

# Register interpellation tools
agent.tool_plain(search_interpellations)
agent.tool_plain(get_interpellation_details)
agent.tool_plain(get_meeting_interpellations)

# Register meeting tools
agent.tool_plain(search_committees)
agent.tool_plain(list_meeting_bills)
agent.tool_plain(list_meeting_ivods)
agent.tool_plain(analyze_attendance_rate)
agent.tool_plain(search_meetings_by_bill)
agent.tool_plain(get_session_info)


async def main():
    try:
        await agent.to_cli()
    except Exception:
        pass
        # await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())
