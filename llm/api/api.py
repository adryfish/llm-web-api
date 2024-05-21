import datetime
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

import llm.shared as shared
from llm.logger import logger
from llm.views.chat import api_chat_completion


def api_middleware(app: FastAPI):
    @app.middleware("http")
    async def log_and_time(req: Request, call_next):
        ts = time.time()
        res: Response = await call_next(req)
        duration = str(round(time.time() - ts, 4))
        res.headers["X-Process-Time"] = duration
        endpoint = req.scope.get("path", "err")
        if shared.cmd_opts.api_log:
            print(
                "API {t} {code} {prot}/{ver} {method} {endpoint} {cli} {duration}".format(
                    t=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                    code=res.status_code,
                    ver=req.scope.get("http_version", "0.0"),
                    cli=req.scope.get("client", ("0:0.0.0", 0))[0],
                    prot=req.scope.get("scheme", "err"),
                    method=req.scope.get("method", "err"),
                    endpoint=endpoint,
                    duration=duration,
                )
            )
        return res

    def handle_exception(request: Request, e: Exception):
        message = f"API error: {request.method}: {request.url} {str(e)}"
        # 打印异常堆栈
        logger.error(message, exc_info=True)

        err = {
            "status": False,
            "error": {
                "message": "An error occurred. please try again. Additionally, ensure that your request complies with OpenAI's policy.",
                "type": "invalid_request_error",
            },
            "support": "https://github.com/adryfish/llm-web-api",
        }
        return JSONResponse(status_code=500, content=jsonable_encoder(err))

    @app.middleware("http")
    async def exception_handling(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            return handle_exception(request, e)

    @app.exception_handler(Exception)
    async def fastapi_exception_handler(request: Request, e: Exception):
        return handle_exception(request, e)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, e: HTTPException):
        return handle_exception(request, e)


class Api:
    def __init__(self, app: FastAPI):
        self.router = APIRouter()
        self.app = app

        api_middleware(self.app)

        self.add_api_route(
            "/v1/chat/completions", api_chat_completion, methods=["POST"]
        )

    def add_api_route(self, path: str, endpoint, **kwargs):
        return self.app.add_api_route(path, endpoint, **kwargs)

    # def auth(self, credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    #     if credentials.username in self.credentials:
    #         if compare_digest(
    #             credentials.password, self.credentials[credentials.username]
    #         ):
    #             return True

    #     raise HTTPException(
    #         status_code=401,
    #         detail="Incorrect username or password",
    #         headers={"WWW-Authenticate": "Basic"},
    #     )

    def launch(self, server_name, port):
        self.app.include_router(self.router)
        uvicorn.run(
            self.app,
            host=server_name,
            port=port,
            timeout_keep_alive=shared.cmd_opts.timeout_keep_alive,
        )
