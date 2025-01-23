import asyncio

from aiohttp import ClientSession, TCPConnector
from yarl import URL

from makinet_controlplane import utils


class AgentApiClient:
    def __init__(self, url: URL) -> None:
        self.session = ClientSession(url, connector=TCPConnector(ssl=False, limit=10))

    def __del__(self):
        utils._BACKGROUND_TASKS.append(
            asyncio.create_task(self.session.close())
        )  # 保持一个引用，以免任务被垃圾回收而没有运行


class Agent:
    def __init__(self, slug: str, api: AgentApiClient) -> None:
        self.name = slug
        self.api = api
