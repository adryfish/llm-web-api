import asyncio
import random
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Page, Request, Response

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
        self._host = "https://chatgpt.com"
        self.login_type = login_type
        self.context_page = context_page
        self.email = email
        self.password = password
        self.proxies = proxies

        # chatgpt-noauth: no login user
        # chatgpt-freeaccount: free account
        # chatgpt-paid": plus user
        self.persona = None
        self.is_lock = False

    async def setup_listener(self):
        self.context_page.on("request", self.cloudflare_challenge_listener)
        self.context_page.on("response", self.login_listener)

    async def login_listener(self, response: Response):
        path = urlparse(response.url).path
        if path in [
            "/backend-anon/sentinel/chat-requirements",
            "/backend-api/sentinel/chat-requirements",
        ]:
            if not response.ok:
                text = await response.text()
                logger.info(
                    f"[OpenAILogin.login_listener] status: {response.status}. text: {text}"
                )
                if not self.is_lock:
                    await self.begin()
                return

            json_body = await response.json()
            self.persona = json_body.get("persona")
            if self.persona == "chatgpt-noauth" and self.login_type != "nologin":
                if not self.is_lock:
                    await self.begin()

    async def cloudflare_challenge_listener(self, request: Request):
        url = request.url
        if url.startswith("https://challenges.cloudflare.com"):
            logger.info("[OpenAIClient.login_listener] trigger...")
            if not self.is_lock:
                await self.begin()

    async def begin(self):
        logger.info("[OpenAILogin.begin] OpenAILogin start...")
        if self.is_lock:
            logger.info("[OpenAILogin.begin] processing...")
            return
        self.is_lock = True
        try:
            await self.context_page.goto(self._host)
            await self.context_page.wait_for_load_state("load")

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
        finally:
            self.is_lock = False

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
        logger.info("[OpenAILogin.login_by_email] start login")
        try:
            if not self.context_page.url.lower().startswith(
                "https://auth.openai.com/authorize"
            ):
                await self.goto_auth_page()

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
            await login_password_button.click(timeout=5000)

            await self.context_page.wait_for_url(lambda url: url.startswith(self._host))

            logger.info("[OpenAILogin.login_by_email] finish login")
        except Exception as e:
            logger.error(
                f"[OpenAILogin.login_by_email] Error during login process: {e}"
            )
            await screenshot(self.context_page)
            if not self.context_page.url.startswith(self._host):
                await self.context_page.goto(self._host)

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
            raise Exception("Login button not found")

        await self.context_page.wait_for_url(
            lambda url: url.startswith("https://auth.openai.com/authorize")
        )
