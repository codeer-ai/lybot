import asyncio

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

model = GoogleModel("gemini-2.5-pro")
settings = GoogleModelSettings(google_thinking_config={"include_thoughts": True})


instructions = """
You are a helpful assistant that can help with tasks related to the Legislative Yuan.


* 如果跟黨籍相關的問題，請使用完整的黨名
* 都是查詢第 11 屆立法委員
* Always call tools to get the latest information

You can use the following tools to help you:
- get_legislators: Get the list of legislators. You can use this tool to get the list of legislators.


"""

agent = Agent(model, instructions=instructions, model_settings=settings)


@agent.tool_plain
def get_legislators(name: str = None, party: str = None) -> str:
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
        "屆": 11,
    }
    if name:
        params["委員姓名"] = name

    if party:
        params["黨籍"] = party

    logger.debug(params)
    url = "https://ly.govapi.tw/v2/legislators"
    response = httpx.get(url, params=params)

    return response.json()


async def main():
    try:
        await agent.to_cli()
    except Exception:
        pass
        # await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())
