from fastapi import HTTPException

from llm.api.chat import ChatRequest
from llm.provider_manager import provider_manager


async def api_chat_completion(body: ChatRequest):
    provider = provider_manager.get_provider(body.model)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Unsupported model {body.model}")

    resp = await provider.chat_completion(
        model=body.model, messages=body.messages, stream=body.stream
    )
    return resp
