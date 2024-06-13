from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from llm.api.chat import ChatRequest
from llm.provider_manager import provider_manager


async def api_chat_completion(body: ChatRequest):
    provider = provider_manager.get_provider(body.model)
    if not provider:
        err = {
            "status": False,
            "error": {
                "message": f"The model `{body.model}` does not exist or you do not have access to it.",
                "type": "invalid_request_error",
                "param": None,
                "code": "model_not_found",
            },
            "support": "https://github.com/adryfish/llm-web-api",
        }

        return JSONResponse(status_code=404, content=jsonable_encoder(err))

    resp = await provider.chat_completion(
        model=body.model, messages=body.messages, stream=body.stream
    )
    return resp
