from typing import Optional


class AgentOfflineError(Exception):
    def __init__(self, slug: str, message: Optional[str] = None) -> None:
        self.slug = slug
        super().__init__(f"Agent {slug} is offline. {message if message else ''}")
