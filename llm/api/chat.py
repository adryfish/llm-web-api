from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False

# Response
class ChoiceModel(BaseModel):
    index: int
    message: Message
    finish_reason: str

class UsageModel(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletion(BaseModel):
    id: str
    model: str
    object: str
    choices: List[ChoiceModel]
    usage: UsageModel
    created: int