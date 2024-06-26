import asyncio
import base64
import json
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import Request
from playwright.async_api import Page, Response, Route

from llm import config
from llm.logger import logger
from llm.provider.openai.login import OpenAILogin
from llm.provider.openai.playwright_utils import get_svg_button, screenshot


class AsyncGenerator:
    def __init__(self, timeout=60):
        self._queue = asyncio.Queue()
        self._finished = False
        self._timeout = timeout
        self._data = []

    async def write(self, item):
        if self._finished:
            return
        self._data.append(item)
        await self._queue.put(item)

    async def get_all_data(self):
        return "".join(self._data)

    def finish(self):
        self._queue.put_nowait("data: [DONE]")
        self._finished = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._finished and self._queue.empty():
            raise StopAsyncIteration

        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=self._timeout)
            return item
        except asyncio.TimeoutError:
            logger.info("[AsyncGenerator] Timeout occurred while waiting for data")
            raise


@dataclass
class ConversationResponse:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    # 流式响应，不断追加
    stream: list = field(default_factory=list)
    # 完整响应，可能是error，也可能是websocket json
    content: Optional[str] = None
    is_websocket: bool = field(default=False)


class OpenAIClient:
    def __init__(
        self,
        timeout=120,
        proxy=None,
        *,
        playwright_page: Page,
    ):
        self.proxies = proxy
        self.timeout = timeout
        self._host = "https://chatgpt.com"
        self.playwright_page = playwright_page

        self.openai_login = OpenAILogin(
            context_page=self.playwright_page,
            login_type=config.OPENAI_LOGIN_TYPE,
            email=config.OPENAI_LOGIN_EMAIL,
            password=config.OPENAI_LOGIN_PASSWORD,
            proxies=self.proxies,
        )

        self.active = True

        self.messages = None
        self.ready_to_read = asyncio.Event()  # 事件：通知开始读取
        self.data_generator: AsyncGenerator = None
        self.conversation_response: ConversationResponse = None
        self.forward_request = False

        # 登录账户类型，如果是免费用户，没有切换模型的必要
        self.account_type = None
        # gpt-4o, gpt-4, text-davinci-002-render-sha
        self.current_model = None

        # 刚开始先设置默认值
        if config.OPENAI_LOGIN_TYPE == "nologin":
            self._supported_model = ["gpt-3.5-turbo"]
        else:
            self._supported_model = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]

        # gpt-4o模型可使用时间
        self.reset_after = None

    async def post_init(self):
        await self.setup_expose_function()
        await self.setup_websocket()
        await self.setup_listener()
        await self.setup_route()

        await self.openai_login.post_init()
        await self.openai_login.begin()
        await self.openai_login.setup_listener()

    def supported_model(self) -> list[str]:
        if self.reset_after != None and datetime.now(timezone.utc) > self.reset_after:
            if self.account_type == "chatgptfreeplan":
                self._supported_model = ["gpt-3.5-turbo", "gpt-4o"]
            else:
                self._supported_model = ["gpt-3.5-turbo", "gpt-4o", "gpt-4"]
            self.reset_after = None

        return self._supported_model

    async def setup_expose_function(self):
        def on_start(status: int, headers: dict, content: str, is_websocket: bool):
            self.conversation_response = ConversationResponse(
                status=status,
                headers=headers,
                stream=[],
                content=content,
                is_websocket=is_websocket,
            )

            self.ready_to_read.set()
            if status != 200:
                logger.error(
                    f"[OpenAIClient.on_start] HTTP request failed. status: {str(status)}. message: {content}",
                )
            elif is_websocket:
                logger.info(
                    f"[OpenAIClient.on_start] Get websocket response: {content}"
                )
            else:
                logger.info("[OpenAIClient.on_start] Get event-stream Response")

        async def on_data(data):
            self.conversation_response.stream.append(data)
            await self.data_generator.write(data)

        def on_complete():
            logger.info("[OpenAIClient.on_complete] Event-stream end fetch")
            self.data_generator.finish()
            self.active = True

        async def on_exception(error):
            logger.info(f"[OpenAIClient.on_exception] exception {error}")
            self.data_generator.finish()
            self.active = True

        async def on_abort():
            logger.info("[OpenAIClient.on_abort] abort")
            self.data_generator.finish()
            self.active = True

        await self.playwright_page.expose_function("handleStart", on_start)
        await self.playwright_page.expose_function("handleData", on_data)
        await self.playwright_page.expose_function("handleComplete", on_complete)
        await self.playwright_page.expose_function("handleException", on_exception)
        await self.playwright_page.expose_function("handleAbort", on_abort)

    async def __process_frame(self, frame):
        _json = json.loads(frame)
        # 非message的frame不处理
        if _json.get("type") != "message":
            return

        _body = _json.get("data", {}).get("body")
        real_body = base64.b64decode(_body).decode("utf-8")

        # if config.env == "dev":
        #     _json["data"]["body"] = real_body
        #     logger.debug(f"Frame: {json.dumps(_json, ensure_ascii=False)}")

        if real_body.startswith("data: [DONE]"):
            logger.info("[OpenAIClient.__handle_route] Websocket end fetch")
            self.data_generator.finish()
            self.active = True

        self.conversation_response.stream.append(real_body)
        await self.data_generator.write(real_body)

    async def setup_websocket(self):
        # 监听 WebSocket 事件
        self.playwright_page.on(
            "websocket", lambda ws: logger.info(f"WebSocket connected: {ws.url}")
        )
        self.playwright_page.on(
            "websocket",
            lambda ws: ws.on("framereceived", self.__process_frame),
        )
        # self.playwright_page.on(
        #     "websocket",
        #     lambda ws: ws.on("framesent", lambda frame: print(f"Frame sent: {frame}")),
        # )
        self.playwright_page.on(
            "websocket",
            lambda ws: ws.on(
                "close", lambda: logger.info(f"WebSocket closed: {ws.url}")
            ),
        )

        async def on_stop_conversation(request: Request):
            path = urlparse(request.url).path
            if path in [
                "/backend-api/stop_conversation",
                "/backend-anon/stop_conversation",
            ]:
                logger.info("[OpenAIClient.on_stop_conversation] End conversation")
                self.data_generator.finish()
                await asyncio.sleep(random.uniform(0.5, 2))
                await self.new_conversation()
                self.active = True

        self.playwright_page.on("request", on_stop_conversation)

    async def __handle_request(self, request: Request):
        url_path = urlparse(request.url).path

        ignore_suffixes = {
            ".css",
            ".js",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".ico",
            ".woff2",
            # 统计接口
            "/v1/rgstr",
            "/ces/v1/t",
            "/ces/v1/p",
        }

        if not any(url_path.endswith(suffix) for suffix in ignore_suffixes):
            logger.debug(f"{request.method} {request.url}")

    async def __handle_response(self, response: Response):
        path = urlparse(response.url).path
        if path.startswith("/backend-api/accounts/check"):
            # 获取模型限制情况
            # 获取账户类型 chatgptfreeplan, chatgptplusplan

            # 不要用 await response.finish()等待response完成，有时会死循环,报错就等下一次
            _body = await response.json()

            default_account = _body.get("accounts").get("default")

            # 获取账户类型 chatgptfreeplan, chatgptplusplan
            if self.account_type == None:
                entitlement = default_account.get("entitlement")
                self.account_type = entitlement.get("subscription_plan")
                logger.info(
                    f"[OpenAIClient.__handle_response] Your acount is {self.account_type}"
                )

                if self.account_type != "chatgptfreeplan":
                    model_locator = self.playwright_page.locator(
                        'div[type="button"][aria-haspopup="menu"]', has_text="ChatGPT"
                    )
                    if model_locator and await model_locator.is_visible():
                        _text_content = await model_locator.text_content()
                        self.current_model = {
                            "ChatGPT 4o": "gpt-4o",
                            "ChatGPT 4": "gpt-4",
                            "ChatGPT 3.5": "text-davinci-002-render-sha",
                        }.get(_text_content, "gpt-4o")

            # 获取模型限制情况
            rate_limits = default_account.get("rate_limits", [])
            rate_limits = [
                _
                for _ in rate_limits
                if _.get("limit_details", {}).get("type", "") == "model_limit"
            ]
            if len(rate_limits) == 0:
                # 没有限制
                if self.account_type == "chatgptfreeplan":
                    self._supported_model = ["gpt-3.5-turbo", "gpt-4o"]
                else:
                    self._supported_model = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
            else:
                self.reset_after = datetime.fromisoformat(
                    next(_.get("resets_after") for _ in rate_limits)
                )
                if self.account_type == "chatgptfreeplan":
                    self._supported_model = ["gpt-3.5-turbo"]
                else:
                    # TODO
                    self._supported_model = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]

    async def setup_listener(self):
        if config.OPENAI_LOGIN_TYPE == "email":
            self.playwright_page.on("response", self.__handle_response)

        if config.env == "dev":
            self.playwright_page.on("request", self.__handle_request)

    async def __handle_route(self, route: Route):
        # 重入的请求，是自己使用Fetch API发送的
        if self.forward_request:
            await route.continue_()
            return

        request = route.request
        url = urlparse(request.url).path
        self.forward_request = True

        request_headers = await request.all_headers()
        headers_str = json.dumps(request_headers)
        try:
            json_body = request.post_data_json
            # 多轮对话
            if config.ENABLE_MULTI_TURN_CONVERSATION:
                if self.messages and len(self.messages) > 1:
                    json_body["messages"] = [
                        {
                            "author": {"role": message["role"]},
                            "content": {
                                "content_type": "text",
                                "parts": [message["content"]],
                            },
                        }
                        for message in self.messages
                    ]
            json_body_str = json.dumps(json_body)

            javascript_code = (
                """
                (async () => {
                    try {
                        const response = await fetch("{url}", {
                            method: 'POST',
                            headers: {headers},
                            body: JSON.stringify({body}),
                        })
                        const responseHeaders = Object.fromEntries(response.headers.entries())

                        // 错误处理
                        if (!response.ok) {
                            const text = await response.text()
                            await window.handleStart(response.status, responseHeaders, text, false)
                            return
                        } 

                        // 处理Websocket
                        const contentType = response.headers.get('Content-Type')
                        if (contentType.includes('application/json')) {
                            const data = await response.json()
                            await window.handleStart(response.status, responseHeaders, data, true)
                            return
                        }

                        await window.handleStart(response.status, responseHeaders, null, false)

                        const reader = response.body.getReader()
                        const decoder = new TextDecoder()

                        while (true) {
                            const { done, value } = await reader.read();
                            if (done) break

                            const textChunk = decoder.decode(value, { stream: true })
                            await window.handleData(textChunk)
                        }
                        await window.handleComplete()
                    } catch (error) {
                        await window.handleException(err)
                    }
                })()
            """.replace(
                    "{url}", url
                )
                .replace("{headers}", headers_str)
                .replace("{body}", json_body_str)
            )

            await self.playwright_page.evaluate(javascript_code)

            # error 或者 websocket 直接返回
            if (
                self.conversation_response.status != 200
                or self.conversation_response.is_websocket
            ):
                await route.fulfill(
                    status=self.conversation_response.status,
                    headers=self.conversation_response.headers,
                    body=json.dumps(
                        self.conversation_response.content, ensure_ascii=False
                    ),
                )
                return

            logger.info("[OpenAIClient.__handle_route] Write response to page")
            self.conversation_response.stream.append("data: [DONE]")

            response_body = "".join(self.conversation_response.stream)
            await route.fulfill(
                status=self.conversation_response.status,
                headers=self.conversation_response.headers,
                body=response_body,
            )

            await self.new_conversation()
        except asyncio.TimeoutError:
            logger.error(
                "[OpenAIClient.__handle_route] Timeout while waiting for read completion"
            )
            await route.fulfill(
                status=408,
                headers={"Content-Type": "text/plain"},
                body="Timeout",
            )

    async def setup_route(self):
        # for nologin
        await self.playwright_page.route(
            "**/backend-anon/conversation", self.__handle_route
        )
        # for login user
        await self.playwright_page.route(
            "**/backend-api/conversation", self.__handle_route
        )

    def generate_completion_id(self, prefix="cmpl-"):
        characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        length = 28

        random_chars = [random.choice(characters) for _ in range(length)]
        return prefix + "".join(random_chars)

    async def chunks_to_lines(self, chunks_async):
        previous = ""
        async for chunk in chunks_async:
            # Ensure chunk is a string
            buffer_chunk = chunk.decode() if isinstance(chunk, bytes) else chunk
            previous += buffer_chunk
            eol_index = 0
            while (eol_index := previous.find("\n")) >= 0:
                # Line includes the EOL, trim trailing spaces or newlines
                line = previous[: eol_index + 1].strip()
                if line == "data: [DONE]":
                    break
                if line.startswith("data: "):
                    yield line
                previous = previous[eol_index + 1 :]

    async def lines_to_messages(self, lines_async):
        async for line in lines_async:
            message = line[len("data: ") :]
            yield message

    async def stream_completion(self, data):
        async for message in self.lines_to_messages(self.chunks_to_lines(data)):
            yield message

    async def create_completion(
        self, model: str, messages: list[dict[str, any]], stream: Optional[bool] = False
    ) -> dict[str, any]:
        if not self.openai_login.ready:
            logger.info("[OpenAIClient.create_completion] in login process")
            raise Exception("Please try again later")

        if not self.active:
            error_message = {
                "status": False,
                "error": {
                    "message": "Too many requests. please slow down.",
                    "type": "invalid_request_error",
                },
                "support": "https://github.com/adryfish/llm-web-api",
            }
            logger.error(error_message)

            # TODO
            # 用一个具体的异常类
            raise Exception("Too many requests. please slow down.")

        self.active = False
        logger.info("[OpenAIClient.create_completion] Start chat_completion")

        self.messages = None
        self.ready_to_read.clear()
        self.data_generator = AsyncGenerator()
        self.conversation_response = None

        # 拦截第一个请求，放行重入请求
        self.forward_request = False
        try:
            # 上一个对话结束时就已经开启新对话,但是可能存在不成功的情况，这里重试一下
            # 对于非登录用户，无法判断页面是否已经刷新，索性就跳过，这样会节约响应时间
            if (
                self.openai_login.persona
                and self.openai_login.persona != "chatgpt-noauth"
            ):
                await self.new_conversation()
                await self.change_model(model)

            content = self.message_prepare(messages)
            prompt_textarea = self.playwright_page.locator("#prompt-textarea")

            await prompt_textarea.click()
            if len(content) <= 50:
                await prompt_textarea.type(content, delay=0)
            else:
                # content_to_type = content[:10]
                # await prompt_textarea.type(content_to_type, delay=0)
                await prompt_textarea.fill(content)

            await prompt_textarea.press("Enter", timeout=5000)

            await asyncio.wait_for(self.ready_to_read.wait(), timeout=60)

            if self.conversation_response.status != 200:
                raise Exception(
                    "[OpenAIClient.create_completion] response stream is None"
                )

            async def generator():
                full_content = ""
                error = None
                finish_reason = None
                # 对于非订阅用户，model是动态的，可能是gpt3.5,也可能是gpt4-o
                final_model = model
                created = int(time.time())
                request_id = self.generate_completion_id("chatcmpl-")
                content_chunks = []

                async for message in self.stream_completion(self.data_generator):
                    if re.match(
                        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$", message
                    ):
                        continue  # Skip heartbeat detection

                    parsed = json.loads(message)
                    if parsed.get("error"):
                        error = f"Error message from OpenAI: {parsed['error']}"
                        finish_reason = "stop"
                        break

                    content = (
                        parsed.get("message", {})
                        .get("content", {})
                        .get("parts", [""])[0]
                    )
                    status = parsed.get("message", {}).get("status", "")

                    for msg in messages:
                        if msg["content"] == content:
                            content = ""
                            break

                    if not content:
                        continue

                    completion_chunk = content.replace(full_content, "")
                    full_content = (
                        content if len(content) > len(full_content) else full_content
                    )
                    content_chunks.append(completion_chunk)

                    final_model = (
                        parsed.get("message", {})
                        .get("metadata", {})
                        .get("model_slug", final_model)
                    )

                    # 有时候模型check不一定触发
                    if (
                        self.account_type == "chatgptfreeplan"
                        and model != "gpt-3.5-turbo"
                        and final_model == "text-davinci-002-render-sha"
                    ):
                        self._supported_model = ["gpt-3.5-turbo"]

                    if status == "finished_successfully":
                        finish_details_type = (
                            parsed.get("message", {})
                            .get("metadata", {})
                            .get("finish_details", {})
                            .get("type")
                        )

                        if finish_details_type == "max_tokens":
                            finish_reason = "length"
                        else:
                            finish_reason = "stop"
                        break

                    if stream:
                        response_chunk = {
                            "id": request_id,
                            "created": created,
                            "object": "chat.completion.chunk",
                            "model": final_model,
                            "choices": [
                                {
                                    "delta": {"content": completion_chunk},
                                    "index": 0,
                                    "finish_reason": finish_reason,
                                }
                            ],
                        }
                        yield f"data: {json.dumps(response_chunk)}\n\n"

                logger.info("[OpenAIClient.create_completion] End chat_completion")

                if stream:
                    data = {
                        "id": request_id,
                        "created": created,
                        "object": "chat.completion.chunk",
                        "model": final_model,
                        "choices": [
                            {
                                "delta": {"content": error if error else ""},
                                "index": 0,
                                "finish_reason": finish_reason,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    yield f"data: [DONE]\n\n"
                else:
                    response_data = {
                        "id": request_id,
                        "model": final_model,
                        "object": "chat.completion",
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": error if error else full_content,
                                },
                                "index": 0,
                                "finish_reason": finish_reason,
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 1,
                            "completion_tokens": 1,
                            "total_tokens": 2,
                        },
                        "created": created,
                    }

                    yield response_data

            if stream:
                return generator()

            async for _ in generator():
                return _
        except TimeoutError as e:
            logger.error("[OpenAIClient.chat_completion] wait timeout")
            await self.playwright_page.reload()
        except Exception as e:
            logger.error(
                f"[OpenAIClient.chat_completion] Error happened. message: {str(e)}",
                exc_info=True,
            )
            logger.error(
                f"[OpenAIClient.chat_completion] prams: model={model}, message={json.dumps(messages, ensure_ascii=False)}, stream={stream}"
            )
            await screenshot(self.playwright_page)

            raise e

    def message_prepare(self, messages: list[dict[str, any]]):
        self.messages = messages
        return messages[-1].get("content")

    async def change_model(self, model_name: str):
        if self.account_type == "chatgptfreeplan":
            return

        model_map = {
            "gpt-3.5-turbo": "text-davinci-002-render-sha",
            "gpt-4": "gpt-4",
            "gpt-4o": "gpt-4o",
        }
        if model_map.get(model_name) != self.current_model:
            logger.info(
                f"[OpenAIClient.change_model] Changing model from {self.current_model} to {model_name}"
            )
            # change model
            await self.playwright_page.locator(
                'div[type="button"][aria-haspopup="menu"]', has_text="ChatGPT"
            ).click()

            try:
                await self.playwright_page.wait_for_selector(
                    'div[role="menu"]', state="attached", timeout=10
                )
            except TimeoutError:
                pass

            buttons = self.playwright_page.locator(
                'div[role="menuitem"]', has_text="GPT"
            )

            _count = await buttons.count()
            if _count == 3:
                index = ["gpt-4o", "gpt-4", "gpt-3.5-turbo"].index(model_name)

                button = buttons.nth(index)
                if await button.is_visible():
                    await button.click()
                    logger.info(
                        f"[OpenAIClient.change_model] Success change model to {model_name}"
                    )
                    return
            logger.info("[OpenAIClient.change_model] Fail to change model")

    async def new_conversation(self):
        if self.openai_login.persona == "chatgpt-noauth":
            await self.playwright_page.reload()
            return
        # 先判断是不是已经处于一个新对话
        url = self.playwright_page.url
        if not url.startswith("https://chatgpt.com"):
            await self.playwright_page.goto(self._host)
            return

        logger.info("[OpenAIClient.new_converstion] Start new_converstion")
        button = await get_svg_button(self.playwright_page, "new_conversation")
        await button.click()
        await self.playwright_page.wait_for_load_state()

    # async def remove_conversation(self, conv_id: str):
    #     parent_div = self.playwright_page.locator(f'a[href="/c/{conv_id}"]').locator(
    #         "xpath=.."
    #     )
    #     await parent_div.locator("button").click()

    #     await asyncio.sleep(0.01)
    #     await self.playwright_page.locator(
    #         'div["role=menuitem]', has_text="Delete"
    #     ).click()
