import os
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse
from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Cookie,
    ElementHandle,
    Page,
    Playwright,
    async_playwright,
)

from llm import config
from llm.api.chat import Message
from llm.base.chat import AbstractChat
from llm.base.crawler import AbstractCrawler
from llm.logger import logger
from llm.provider.openai.client import OpenAIClient


class OpenAICrawler(AbstractCrawler, AbstractChat):
    playwright: Playwright
    context_page: Page
    browser_context: BrowserContext
    openai_client: OpenAIClient

    def __init__(self) -> None:
        self.index_url = "https://chatgpt.com"
        self.https_proxy = config.PROXY_SERVER

        if config.OPENAI_LOGIN_TYPE == "nologin":
            self.supported_model = ["gpt-3.5-turbo"]
        else:
            self.supported_model = ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        # Launch a browser context.
        chromium = self.playwright.chromium
        self.browser_context = await self.launch_browser(
            chromium,
            {"server": self.https_proxy},
            config.USER_AGENT,
            headless=config.HEADLESS,
        )
        self.browser_context.set_default_timeout(180_000)
        # stealth.min.js is a js script to prevent the website from detecting the crawler.
        await self.browser_context.add_init_script(
            path=os.path.join(os.getcwd(), "libs/stealth.min.js")
        )

        self.context_page = await self.browser_context.new_page()
        self.context_page.set_default_timeout(180_000)
        await self.context_page.goto(self.index_url)

        self.openai_client = OpenAIClient(
            proxy=self.https_proxy, playwright_page=self.context_page
        )
        await self.openai_client.post_init()

    # async def cloudflare_bypass(self, page: Page):
    #     stage = await page.query_selector("div#challenge-stage")
    #     check_count = 1
    #     while stage:
    #         await self.try_to_click_challenge(page, stage)
    #         if check_count >= 6:
    #             if await page.query_selector("div#challenge-stage"):
    #                 raise Exception("Meet challenge restart")
    #         logger.info(f"Handle category - meet challenge. Wait 20s to check it again. Count: {check_count}")
    #         check_count += 1
    #         await page.wait_for_timeout(20000)  # 20 seconds
    #         stage = await page.query_selector("div#challenge-stage")

    # async def try_to_click_challenge(self, page: Page, stage: ElementHandle):
    #     # 获取元素的边界框
    #     box = await stage.bounding_box()
    #     if box:
    #         # 计算点击的位置
    #         x_position = box['x'] + 100
    #         y_position = box['y'] + box['height'] / 2

    #         # 移动鼠标到计算的位置
    #         await page.mouse.move(x_position, y_position)

    #         # 随机等待时间，模拟更自然的行为
    #         await page.wait_for_timeout(1000 + random.randint(100, 1000))

    #         # 在相同的位置进行点击
    #         await page.mouse.click(x_position, y_position)

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[dict],
        user_agent: Optional[str] = None,
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(config.BROWSER_DATA, "openai")
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                # viewport={"width": config.SCREEN_WIDTH, "height": config.SCREEN_HEIGHT},
                user_agent=user_agent,
                channel="chrome",
                # https://peter.sh/experiments/chromium-command-line-switches/
                # 网上的答案都不对!!!
                # 隐藏“Chrome is being controlled by automated test software”提示
                ignore_default_args=["--enable-automation"],
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(
                headless=headless,
                proxy=playwright_proxy,
            )  # type: ignore
            browser_context = await browser.new_context(
                viewport={"width": config.SCREEN_WIDTH, "height": config.SCREEN_HEIGHT},
                user_agent=user_agent,
            )
            return browser_context

    async def stop(self) -> None:
        """Close browser context"""
        await self.browser_context.close()
        await self.playwright.stop()
        logger.info("[OpenAICrawler.close] Browser context closed ...")

    async def chat_completion(
        self, model: str, messages=list[Message], stream: Optional[bool] = False
    ):
        messages = [_.dict() for _ in messages]

        try:
            if stream:
                return StreamingResponse(
                    await self.openai_client.create_completion(
                        model, messages, stream=True
                    ),
                    media_type="text/event-stream",
                )
            else:
                return await self.openai_client.create_completion(model, messages)
        except Exception:
            return {
                "status": False,
                "error": {
                    "message": "An error occurred. please try again. Additionally, ensure that your request complies with OpenAI's policy.",
                    "type": "invalid_request_error",
                },
                "support": "https://github.com/adryfish/llm-web-api",
            }
