from abc import ABC, abstractmethod
from typing import Optional

from llm.api.chat import Message


class AbstractChat(ABC):
    @abstractmethod
    async def chat_completion(
        self, model: str, messages=list[Message], stream: Optional[bool] = False
    ):
        pass
