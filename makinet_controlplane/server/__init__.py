from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from yarl import URL

from .. import utils
from ..agent import Agent, AgentApiClient
from ..agent.manager import agent_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    utils.TASK_SCHEDULER.start()
    yield
    utils.TASK_SCHEDULER.shutdown()


api = FastAPI(title="MakiNet Control Plane", version="0.0.1-alpha.1", lifespan=lifespan)


@api.post("/agent/register", name="Agent 注册", response_model=Literal["ok"])
async def agent_register(slug: str, api_url: str, api_timeout: float = 30):
    agent = Agent(slug, AgentApiClient(URL(api_url), api_timeout))
    agent_manager.register_agent(agent)

    return "ok"
