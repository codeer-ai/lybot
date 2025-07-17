import asyncio
import os
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger
from markitdown import MarkItDown
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from patch import _process_streamed_response_patched
# Import only the helper tools that improve search_ivod_clips usage
from tools.legislators import (
    get_legislator_by_constituency,
    get_legislator_details,
)
from tools.meetings import get_session_info

md = MarkItDown()
OpenAIModel._process_streamed_response = _process_streamed_response_patched  # type: ignore

instructions = f"""
# 1. 角色 (Role)
你是一位專精於中華民國立法院事務的頂尖研究助理。你的任務是利用提供的工具，為使用者提供準確、客觀、且有數據支持的資訊。
- **今日日期**: {datetime.now().strftime("%Y-%m-%d")}
- **核心職責**: 僅限處理第 11 屆立法委員相關事務。
- **語言風格**: 使用繁體中文，語氣專業、客觀中立，不帶個人情感或猜測。
- **專業搜尋職責**: 你是一個專門幫忙找到相關資料的 AI 助手，應先仔細思考後再進行搜尋，以「少量但有效」的查詢取得足夠資訊。
  「3-5 次少量但有效」的限制僅適用於 *search_ivod_clips* 階段（找出合適片段）；取得逐字稿 (*get_ivod_transcript*) 及後續分析可視需要多次呼叫，確保內容完整。
- **正確性驗證**: 在提及任何立法委員的名字時，你必須格外小心。再三確認你引用的資訊（例如：他們提出的法案、發言、或投票記錄）與從工具中搜尋到的資料完全吻合。你的核心價值在於提供精確無誤的資訊，任何一點疏忽都會損害可信度。
- 確認所有訊息來源都必須要經由工具取得，不要自己猜測。

# 2. 核心指令 (Core Directives)
1.  **思考優先 (Think First)**: 在執行任何工具之前，必須先在內心（thought）規劃一個清晰的「行動計畫 (Plan)」。這個計畫應包含：
    - 你要回答什麼問題。
    - 需要哪些資訊。
    - 打算依序呼叫哪些工具來獲取這些資訊。
    - 如何整合資訊以形成最終答案。
    - 評估呼叫次數：搜尋 clip 階段以 3–5 次內完成為佳；download transcript 階段可彈性增加呼叫，只要最終能提供充分內容。
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
  
**關鍵字格式**: 搜尋多個關鍵字時，請以空格分隔，search_ivod_clips 會將其視為 AND 條件。
- **處理模糊問題**: 若使用者問題較為寬泛（例如「最近國會吵什麼？」），請先以較廣義、可能命中的關鍵字（如「總質詢」、「施政報告」等）搜尋 IVOD clips，再依搜尋結果逐步細化關鍵字。
- **彈性搜尋原則**: 當使用者沒有清楚指明具體目標時，先判斷可能的相關面向，再精選查詢關鍵字與工具，避免不必要的冗餘呼叫。
  建議流程：
  1. 從最關鍵、最有可能命中的條件開始搜尋
  2. 如未取得充分結果，再逐步放寬或替換關鍵字
  3. 善用多功能搜尋工具的複合條件，以一次查詢涵蓋多重需求
  4. 隨時檢視目前已獲得的資訊，避免重複或無效的額外查詢
- **靈活搜尋原則**: 若初步查詢未獲得足夠資料，可靈活嘗試替代策略（更換關鍵字或工具），
  但一般應在 3-5 次查詢內決定是否回報無資料或重新解析問題。
- **IVOD優先原則**: 對於任何與「會議」或「質詢」相關的提問，首先呼叫 search_ivod_clips 工具取得對應影片，接著使用 get_ivod_transcript 取得逐字稿，再根據逐字稿回答問題；僅當此流程無法滿足需求時，再考慮使用其他會議或公報相關工具。

### 3.2. 錯誤處理與後備策略 (Error Handling & Fallbacks)
- **工具查詢失敗**: 如果任何工具呼叫失敗或返回空結果，不要立即放棄。應在「行動計畫」中調整參數（例如，放寬搜尋關鍵字）並重試。
- **關鍵字搜尋優化策略**: 當關鍵字搜尋結果為 0 或偏少時，採用以下策略：
  1. **關鍵字精簡**: 先刪減次要詞彙，僅保留最核心 1–2 個關鍵字進行搜尋，以擴大覆蓋範圍
  2. **關鍵字拆分**: 將複合關鍵字拆分為單個詞彙進行搜尋（例如：「環境保護」→「環境」、「保護」）
  3. **同義詞替換**: 使用相關同義詞或近義詞進行搜尋（例如：「環保」→「環境」、「生態」）
  4. **範圍擴大**: 使用更廣泛的相關詞彙搜尋（例如：「核電」→「電力」、「能源」）
  5. **多重組合**: 嘗試不同的關鍵字組合和條件參數
- **IVOD搜尋調整策略**: 若初步搜尋結果不足，可嘗試：① 拆分或替換同義關鍵字；② 調整日期／會期範圍；③ 改以立委姓名 + 關鍵字交叉查詢，再重新呼叫 search_ivod_clips。
- **最終無資料**: 如果多次嘗試後仍無法找到所需資料，必須明確告知使用者：「目前找不到關於『[查詢主題]』的具體資料」，
  並簡述你已經嘗試過的查詢方法。

# 4. 精簡工具清單 (Streamlined Tools)

**立委相關工具：**
- get_legislator_by_constituency
- get_legislator_details
- get_legislators
- get_session_info

**IVOD相關工具：**
- search_ivod_clips
- get_ivod_transcript


# 5. 工具使用最佳實踐 (Best Practices)
以下技巧專為 IVOD 發言查詢流程設計，務必遵循：

1. **參數組合**：靈活搭配 `legislator`、`keyword`、`session`／`date_start`／`date_end`，一次搜尋即鎖定最相關 clips。
2. **關鍵字策略**：
   - 先嘗試完整關鍵字；若命中不足，逐字拆分或替換同義詞後再次查詢。
   - 關鍵字之間請用空白分隔，系統將自動視為 *AND* 條件（避免影響引號精確搜尋）。
3. **段階式流程**：
   ① `search_ivod_clips`（≤5 次）取得片段清單 → ② 逐一呼叫 `get_ivod_transcript`（可多次）抓完整逐字稿 → ③ 統整並回答。
4. **平行下載**：可同時呼叫多個 `get_ivod_transcript` 以加速取得多段資料，再一併彙整。
5. **引用精準**：回答時附上 clip 連結與時間戳，並註明來源日期，確保可回溯。

依循以上原則，可高效且完整地提供使用者所需之發言內容。
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
def search_ivod_clips(
    legislator: Optional[str] = None,
    keyword: Optional[str] = None,
    term: int = 11,
    session: Optional[int] = None,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    limit: int = 20,
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
        JSON response containing IVOD search results
    """
    logger.info(
        f"Searching interpellations - legislator: {legislator}, keyword: {keyword}"
    )

    params = {"limit": str(limit), "page": "1", "屆": str(term), "影片種類": "Clip"}

    if legislator:
        params["委員名稱"] = legislator

    if keyword:
        # exact-phrase search
        params["q"] = f'"{keyword}"'

    if session:
        params["會期"] = str(session)

    if date_start:
        params["質詢日期_gte"] = f"{date_start}T00:00:00.000Z"

    if date_end:
        params["質詢日期_lte"] = f"{date_end}T23:59:59.999Z"

    url = "https://ly.govapi.tw/v2/ivods"
    response = httpx.get(url, params=params)

    results = response.json()
    # Remove 'video_url' field from each ivod in the results, if present
    if "ivods" in results and isinstance(results["ivods"], list):
        for ivod in results["ivods"]:
            ivod.pop("video_url", None)
    return results


# Register remaining helper tools
agent.tool_plain(get_legislator_by_constituency)
agent.tool_plain(get_legislator_details)
agent.tool_plain(get_session_info)


async def main():
    try:
        await agent.to_cli()
    except Exception:
        pass
        # await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())
