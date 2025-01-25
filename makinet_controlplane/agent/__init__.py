import asyncio
from typing import Literal

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from loguru import logger
from yarl import URL

from makinet_controlplane import utils

from ..exceptions import AgentOfflineError
from ..models.agent import AgentInfo


class AgentApiClient:
    def __init__(self, url: URL, timeout: float = 30) -> None:
        self.session = ClientSession(
            url,
            connector=TCPConnector(ssl=False, limit=10),
            timeout=ClientTimeout(total=timeout),
        )

    async def ping(self) -> AgentInfo:
        return AgentInfo.model_validate(await (await self.session.get("/ping")).json())


class Agent:
    def __init__(self, slug: str, api: AgentApiClient) -> None:
        self.slug = slug
        self.api = api
        self.status: Literal["online", "offline"] = "offline"
        self.info: AgentInfo | None = None

    async def ping(self):
        """对 Agent 发送 ping 请求，并根据响应更新 Agent 的状态和信息

        Raises:
            AgentOfflineError: Agent 离线

        Returns:
            AgentInfo: Agent 信息
        """

        try:
            agent_info = await self.api.ping()
            self.info = agent_info
            self.status = "online"
            return agent_info
        except asyncio.TimeoutError:
            logger.warning("Agent %s ping timeout", self.slug)
            logger.debug(f"Set agent {self.slug} status to offline")
            self.status = "offline"
            raise AgentOfflineError(self.slug)
