import asyncio

from .. import utils
from .__init__ import Agent


class AgentManager:
    def __init__(self) -> None:
        self.agents: list[Agent] = []

        utils.TASK_SCHEDULER.add_job(self._check_agent_status, "interval", seconds=10)

    async def _check_agent_status(self):
        """检查所有 Agent 的状态"""
        await asyncio.gather(*[agent.ping() for agent in self.agents])

    def register_agent(self, agent: Agent):
        self.agents.append(agent)


agent_manager = AgentManager()
