import asyncio
import json
import random
import re
import time
from typing import Optional
from urllib.parse import urlparse

import httpx
from playwright.async_api import Page, Response

from llm import config
from llm.logger import logger
from llm.provider.openai.login import OpenAILogin


class OpenAIClient:
    def __init__(
        self,
        timeout=180,
        proxy=None,
        *,
        playwright_page: Page,
    ):
        self.proxies = proxy
        self.timeout = timeout
        self._host = "https://chatgpt.com"
        self.playwright_page = playwright_page
        self.http_client = httpx.AsyncClient(
            base_url=self._host, proxy=self.proxies, timeout=self.timeout
        )

        self.lock = asyncio.Lock()

        self.response_stream = None
        self.ready_to_read = asyncio.Event()  # 事件：通知开始读取
        self.read_complete = asyncio.Event()  # 事件：通知读取完成
        self.origin_response = ""

        # 登录账户类型，如果是免费用户，没有切换模型的必要
        self.account_type = None
        # gpt-4o, gpt-4, text-davinci-002-render-sha
        self.current_model = None

    async def post_init(self):
        await self.setup_listener()
        await self.setup_route()
        await self.playwright_page.goto(self._host)
        await self.login()

    async def login(self):
        login_obj = OpenAILogin(
            context_page=self.playwright_page,
            login_type=config.OPENAI_LOGIN_TYPE,
            email=config.OPENAI_LOGIN_EMAIL,
            password=config.OPENAI_LOGIN_PASSWORD,
            proxies=self.proxies,
        )
        await login_obj.begin()

    async def __handle_response(self, response: Response):
        path = urlparse(response.url).path
        if path == "/backend-api/sentinel/chat-requirements":
            # 获取账户类型 freeaccount, paid
            # 不要用 await response.finish()等待response完成，有时会死循环,报错就等下一次
            _body = await response.json()

            # chatgpt-freeaccount or chatgpt-paid
            self.account_type = _body.get("persona")
            logger.info(
                f"[OpenAIClient.__handle_response] Your acount is {self.account_type}"
            )

            if self.account_type == "chatgpt-paid":
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

            self.playwright_page.remove_listener("response", self.__handle_response)

    async def setup_listener(self):
        if config.OPENAI_LOGIN_TYPE == "email":
            self.playwright_page.on("response", self.__handle_response)

    async def __handle_route(self, route):
        request = route.request
        headers = {
            "authority": "chatgpt.com",
            "accept-language": "en-US,en;q=0.9",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            **request.headers,
        }
        # for header, value in headers.items():
        #     print(f"{header}: {value}")

        try:
            url = (
                "/backend-api/conversation"
                if self.account_type
                else "/backend-anon/conversation"
            )
            async with self.http_client.stream(
                "POST",
                url,
                headers=headers,
                json=request.post_data_json,
            ) as response:
                response_headers = response.headers
                if response.status_code != 200:
                    logger.error(
                        "[OpenAIClient.__handle_route] HTTP request failed with status: ",
                        response.status_code,
                    )
                    self.ready_to_read.set()
                    if response.status_code == 403:
                        message = ""
                        async for _ in response.aiter_text():
                            message += _
                        logger.error(
                            f"[OpenAI.Client.__handle_route] response body: {message}"
                        )
                        await self.playwright_page.reload()
                        await self.playwright_page.wait_for_load_state("load")
                        await self.login()
                    raise Exception(
                        "[OpenAIClient.__handle_route] HTTP request failed with status: ",
                        response.status_code,
                    )

                self.response_stream = response.aiter_text()
                self.ready_to_read.set()

                await asyncio.wait_for(self.read_complete.wait(), timeout=self.timeout)

        except asyncio.TimeoutError:
            logger.error(
                "[OpenAIClient.__handle_route] Timeout while waiting for read completion"
            )
        finally:
            await route.fulfill(
                status=response.status_code,
                headers=dict(response_headers),
                body=self.origin_response if self.origin_response else "",
            )

            if config.OPENAI_LOGIN_TYPE == "nologin":
                button = self.playwright_page.locator(
                    'button[aria-label="Stop generating"]'
                )
                if button and await button.is_visible():
                    await button.click()

                await asyncio.sleep(0.1)

                await self.playwright_page.reload()
            else:
                button = self.playwright_page.locator(
                    'button[data-testid="fruitjuice-stop-button"]'
                )
                if button and await button.is_visible():
                    await button.click()

                # await asyncio.sleep(0.1)

                # refresh conversation
                # 效果不好，总有各种各样的问题，改回对话开始创建
                # await self.new_conversation()

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
            self.origin_response += chunk
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
                    # print(line)
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

        try:
            await asyncio.wait_for(self.lock.acquire(), timeout=1)
        except TimeoutError:
            message = {
                "status": False,
                "error": {
                    "message": "Too many requests. please slow down.",
                    "type": "invalid_request_error",
                },
                "support": "https://github.com/adryfish/llm-web-api",
            }
            logger.error(message)

            # TODO
            # 用一个具体的异常类
            raise Exception("Too many requests. please slow down.")

        self.response_stream = None
        self.ready_to_read.clear()
        self.read_complete.clear()
        self.origin_response = ""
        try:
            await self.new_conversation()
            await self.change_model(model)

            prompt_textarea = self.playwright_page.locator("#prompt-textarea")

            content = self.message_prepare(messages)
            await prompt_textarea.click()
            await prompt_textarea.fill(content)

            # 寻找submit button并点击
            form = self.playwright_page.locator("form")

            buttons = form.locator("button")
            button_count = await buttons.count()
            submit_button = buttons.nth(button_count - 1)
            if await submit_button.is_visible():
                await submit_button.click()
            else:
                raise Exception(
                    "[OpenAIClient.create_completion] Cannot submit the content"
                )

            await asyncio.wait_for(self.ready_to_read.wait(), timeout=self.timeout)

            if not self.response_stream:
                # 说明resonse code不是200
                raise Exception(
                    "[OpenAIClient.create_completion] response stream is None"
                )

            full_content = ""
            error = None
            finish_reason = None
            request_id = self.generate_completion_id("chatcmpl-")
            content_chunks = []
            # 对于非订阅用户，model是动态的，可能是gpt3.5,也可能是gpt4-o
            final_model = model

            async def generator():
                nonlocal full_content
                nonlocal error
                nonlocal finish_reason
                nonlocal final_model
                async for message in self.stream_completion(self.response_stream):
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

                    response_chunk = {
                        "id": request_id,
                        "created": int(time.time()),
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

                self.read_complete.set()

            if stream:
                return generator()

            async for _ in generator():
                pass

            response_data = {
                "id": request_id,
                "model": final_model,
                "object": "chat.completion",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": full_content},
                        "index": 0,
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
                "created": int(time.time()),
            }

            if error:
                response_data["choices"][0]["content"] = error

            return response_data
        except Exception as e:
            print(e)
            raise e
        finally:
            self.lock.release()

    # def message_prepare(self, messages: list[dict[str, any]]):
    #     # 合并消息内容
    #     user_message = messages[-1].get("content")
    #     if len(messages) == 1:
    #         return user_message

    #     content = ""
    #     for message in messages[0:-1]:
    #         role = "用户" if message.get("role", "user") == "user" else "系统"
    #         message_content = message.get("content", "")
    #         content += f"{role}:{message_content}\n\n"

    #     content += "以上是对话历史记录，根据下方用户的提问进行回答\n\n"

    #     content += user_message

    #     return content
    def message_prepare(self, messages: list[dict[str, any]]):
        # TODO
        # 对于多轮对话，总是返回空白回答，原因不明
        return messages[-1].get("content")

    async def change_model(self, model_name: str):
        if self.account_type != "chatgpt-paid":
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
        if config.OPENAI_LOGIN_TYPE != "email":
            return
        # 先判断是不是已经处于一个新对话
        url = self.playwright_page.url
        if not url.startswith("https://chatgpt.com"):
            # TODO
            # 如果这里跳到auth页面，需要处理
            await self.playwright_page.goto(self._host)
            return

        _path = urlparse(url).path
        if _path == "/":
            # 已经处于新对话，不用重新创建
            return

        d_value = "M15.673 3.913a3.121 3.121 0 1 1 4.414 4.414l-5.937 5.937a5 5 0 0 1-2.828 1.415l-2.18.31a1 1 0 0 1-1.132-1.13l.311-2.18A5 5 0 0 1 9.736 9.85zm3 1.414a1.12 1.12 0 0 0-1.586 0l-5.937 5.937a3 3 0 0 0-.849 1.697l-.123.86.86-.122a3 3 0 0 0 1.698-.849l5.937-5.937a1.12 1.12 0 0 0 0-1.586M11 4A1 1 0 0 1 10 5c-.998 0-1.702.008-2.253.06-.54.052-.862.141-1.109.267a3 3 0 0 0-1.311 1.311c-.134.263-.226.611-.276 1.216C5.001 8.471 5 9.264 5 10.4v3.2c0 1.137 0 1.929.051 2.546.05.605.142.953.276 1.216a3 3 0 0 0 1.311 1.311c.263.134.611.226 1.216.276.617.05 1.41.051 2.546.051h3.2c1.137 0 1.929 0 2.546-.051.605-.05.953-.142 1.216-.276a3 3 0 0 0 1.311-1.311c.126-.247.215-.569.266-1.108.053-.552.06-1.256.06-2.255a1 1 0 1 1 2 .002c0 .978-.006 1.78-.069 2.442-.064.673-.192 1.27-.475 1.827a5 5 0 0 1-2.185 2.185c-.592.302-1.232.428-1.961.487C15.6 21 14.727 21 13.643 21h-3.286c-1.084 0-1.958 0-2.666-.058-.728-.06-1.369-.185-1.96-.487a5 5 0 0 1-2.186-2.185c-.302-.592-.428-1.233-.487-1.961C3 15.6 3 14.727 3 13.643v-3.286c0-1.084 0-1.958.058-2.666.06-.729.185-1.369.487-1.961A5 5 0 0 1 5.73 3.545c.556-.284 1.154-.411 1.827-.475C8.22 3.007 9.021 3 10 3A1 1 0 0 1 11 4"
        buttons = self.playwright_page.locator(f'button:has(svg > path[d="{d_value}"])')

        _count = await buttons.count()
        for index in range(_count):
            button = buttons.nth(index)
            if await button.is_visible():
                await button.click()
                break
        # else:
        #     self.playwright_page.reload()

    # async def remove_conversation(self, conv_id: str):
    #     parent_div = self.playwright_page.locator(f'a[href="/c/{conv_id}"]').locator(
    #         "xpath=.."
    #     )
    #     await parent_div.locator("button").click()

    #     await asyncio.sleep(0.01)
    #     await self.playwright_page.locator(
    #         'div["role=menuitem]', has_text="Delete"
    #     ).click()
