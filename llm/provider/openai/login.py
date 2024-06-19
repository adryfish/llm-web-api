import asyncio
import random
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Page, Response

from llm.logger import logger
from llm.provider.openai.cloudflare_bypass import CloudflareBypass
from llm.provider.openai.playwright_utils import is_clickable, screenshot


class OpenAILogin:
    def __init__(
        self,
        context_page: Page,
        login_type: str,
        email: Optional[str] = None,
        password: Optional[str] = None,
        proxies: Optional[str] = None,
    ):
        self.login_type = login_type
        self.context_page = context_page
        self.email = email
        self.password = password
        self.proxies = proxies

        # chatgpt-noauth: no login user
        # chatgpt-freeaccount: free account
        # chatgpt-paid": plus user
        self.persona = None
        self.persona_ready = asyncio.Event()

    async def post_init(self):
        logger.info("[OpenAILogin.post_init] Start...")
        await self.setup_listener()
        logger.info("[OpenAILogin.post_init] End...")

    async def setup_listener(self):
        self.context_page.on("response", self.__handle_response)

    async def __handle_response(self, response: Response):
        path = urlparse(response.url).path
        if path in [
            "/backend-anon/sentinel/chat-requirements",
            "/backend-api/sentinel/chat-requirements",
        ]:
            json_body = await response.json()
            self.persona = json_body.get("persona")
            self.persona_ready.set()

            # if self.persona == "chatgpt-noauth" and self.login_type == "email":
            #     await self.begin()

    async def begin(self):
        logger.info("[OpenAILogin.begin] OpenAILogin start...")
        await self.bypass_cloudflare()

        if self.login_type == "email":
            await self.login_by_email()
        else:
            # 2024-05-28
            # 某些客户端打开首页后会弹出一个登录的dialog
            dialog = self.context_page.locator('div[role="dialog"]')
            if dialog and await dialog.is_visible():
                stay_logged_out = dialog.locator("a", has_text="Stay logged out")
                if stay_logged_out and await stay_logged_out.is_visible():
                    await stay_logged_out.click()
                    await self.context_page.wait_for_load_state("load")

        logger.info("[OpenAILogin.begin] OpenAILogin finished...")

    async def bypass_cloudflare(self):
        challenge_form = await self.context_page.query_selector("#challenge-form")
        if challenge_form:
            logger.info("[OpenAILogin.bypass_cloudflare] Meet cloudflare challenge")
            # bypass cloudflare
            user_agent = await self.context_page.evaluate("navigator.userAgent")
            cloudflare_bypass = CloudflareBypass(
                proxy_server=self.proxies, user_agent=user_agent
            )
            cookies = cloudflare_bypass.bypass(self.context_page.url)

            await self.context_page.context.clear_cookies()
            await self.context_page.context.add_cookies(cookies)

            cloudflare_bypass.close()
            logger.info("[OpenAILogin.bypass_cloudflare] Finish cloudflare challenge")

            await self.context_page.reload()
            await self.context_page.wait_for_load_state("load")

    async def login_by_email(self):
        if self.login_type != "email":
            return

        # 确保访问chat-requirements
        await asyncio.wait_for(self.persona_ready.wait(), timeout=10)

        if self.persona != "chatgpt-noauth":
            return
        logger.info("[OpenAILogin.login_by_email] start login")
        if not self.context_page.url.lower().startswith(
            "https://auth.openai.com/authorize"
        ):
            await self.goto_auth_page()

        try:
            await asyncio.sleep(random.uniform(0.5, 2.0))

            email_input = self.context_page.locator("#email-input")
            await email_input.focus()
            await asyncio.sleep(0.1)
            await email_input.fill(self.email)

            continue_button = self.context_page.locator(".continue-btn")
            await continue_button.click()
            await self.context_page.wait_for_load_state()

            await asyncio.sleep(random.uniform(0.5, 2.0))

            password_input = self.context_page.locator("#password")
            await password_input.focus()
            await asyncio.sleep(0.1)
            await password_input.fill(self.password)

            await asyncio.sleep(random.uniform(0.5, 2.0))

            login_password_button = self.context_page.locator("button:text('Continue')")
            self.persona_ready.clear()
            await login_password_button.click()

            await self.context_page.wait_for_load_state()

            # 再次等待chat-requirements加载
            await asyncio.wait_for(self.persona_ready.wait(), timeout=10)
            if self.persona == "chatgpt-noauth":
                logger.error(
                    "[OpenAILogin.login_by_email] login failed. Still chatgpt-noauth user"
                )
            else:
                logger.info("[OpenAILogin.login_by_email] finish login")
        except Exception as e:
            logger.error(
                f"[OpenAILogin.login_by_email] Error during login process: {e}"
            )
            await screenshot(self.context_page)

    async def goto_auth_page(self):
        # 2024-05-28
        # 某些客户端打开首页后会弹出一个登录的dialog
        dialog = self.context_page.locator('div[role="dialog"]')
        if await dialog.is_visible():
            login_button = dialog.locator("button", has_text="Log in")
        else:
            login_button = self.context_page.locator("button", has_text="Log in")

        if await is_clickable(login_button):
            await login_button.click()
        else:
            logger.error("[OpenAILogin.goto_auth_page] Login button not found")

        await self.context_page.wait_for_load_state()
        # TODO
        # 可能会再次遇到cloudflare 5s盾
