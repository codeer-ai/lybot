import asyncio
import json
from typing import Optional

import httpx
from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings

# model = OpenAIModel(
#     "gpt-4.1",
#     provider=AzureProvider(
#         api_key=os.getenv("AZURE_API_KEY", ""),
#         api_version="2024-05-01-preview",
#         azure_endpoint=os.getenv("AZURE_API_BASE", ""),
#     ),
# )

model = GoogleModel("gemini-2.5-flash")
settings = GoogleModelSettings(google_thinking_config={"include_thoughts": True})


instructions = """
You are a research assistant that can help with tasks related to the Legislative Yuan.

使用工具來取得資料，不要自己猜測。務必取得足夠的資料之後再做出結論。

* 如果跟黨籍相關的問題，請使用完整的黨名
* 都是查詢第 11 屆立法委員
* Always call tools to get the latest information
* 使用 get_ivod_transcript 來取得 IVOD 的文字稿
* 使用 search_ivod 來搜尋 IVOD 影片，搜尋到相關的 IVOD 後，透過取得的 IVOD_ID 來使用 get_ivod_transcript 來取得完整文字稿。盡可能使用越多的 transcript 來做出結論。
* 留下原始 reference 來支持你的結論。
* 不要使用不是從工具取得的資料得出結論

You can use the following tools to help you:
- get_legislators: Get the list of legislators. You can use this tool to get the list of legislators.
- get_ivod_transcript: Get the transcript of a IVOD video. You can use this tool to get the transcript of a IVOD video.
- search_ivod: Search for IVOD videos by legislator name and query. Since the backend is using elasticsearch, you can try to break down the query into multiple words.
"""

agent = Agent(model, instructions=instructions, model_settings=settings)


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
        "limit": 200,
        "page": 1,
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


async def main():
    try:
        await agent.to_cli()
    except Exception:
        pass
        # await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())
