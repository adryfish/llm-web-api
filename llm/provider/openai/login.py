import asyncio
import random
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Page, Request, Response

from llm.logger import logger
from llm.provider.openai.cloudflare_bypass import CloudflareBypass
from llm.provider.openai.playwright_utils import screenshot


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
        self.persona_ready = asyncio.Event()
        self.ready = True

        self.error_count = 0

    async def post_init(self):
        self.context_page.on("response", self.setup_response_listener)

    async def setup_listener(self):
        self.context_page.on("request", self.setup_request_listener)

    async def setup_response_listener(self, response: Response):
        path = urlparse(response.url).path
        if path in [
            "/backend-anon/sentinel/chat-requirements",
            "/backend-api/sentinel/chat-requirements",
        ]:
            if not response.ok:
                text = await response.text()
                logger.info(
                    f"[OpenAILogin.response_listener] status: {response.status}. text: {text}"
                )
                if self.ready:
                    await self.begin()
                return

            json_body = await response.json()
            self.persona = json_body.get("persona")
            self.persona_ready.set()

    async def setup_request_listener(self, request: Request):
        url = request.url
        if url.startswith("https://challenges.cloudflare.com"):
            logger.info(
                "[OpenAIClient.request_listener] cloudflare challenge trigger..."
            )
            if self.ready:
                await self.begin()
        elif (
            url == "/backend-anon/sentinel/chat-requirements"
            and self.login_type == "email"
        ):
            logger.info("[OpenAIClient.request_listener] login trigger...")
            if self.ready:
                await self.begin()

    async def begin(self):
        logger.info("[OpenAILogin.begin] OpenAILogin start...")
        if not self.ready:
            logger.info("[OpenAILogin.begin] processing...")
            return
        self.ready = False

        is_error = False
        try:
            if self.context_page.url != self._host:
                await self.context_page.goto(self._host)
            else:
                await self.context_page.reload()
            await asyncio.sleep(5)

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
            self.error_count = 0
        except Exception as e:
            is_error = True
            logger.error(
                f"[OpenAILogin.begin] Error during process: {e}",
                exc_info=True,
            )
            await screenshot(self.context_page)
            self.error_count += 1
            logger.info(
                f"[OpenAILogin.login_by_email] failed. sleep {30 * self.error_count}s"
            )
            await asyncio.sleep(30 * self.error_count)
        finally:
            self.ready = True

        if is_error:
            await self.begin()

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

    async def login_by_email(self):
        if self.persona is None:
            await asyncio.wait_for(self.persona_ready.wait(), timeout=10)

        if self.persona != "chatgpt-noauth":
            return

        logger.info("[OpenAILogin.login_by_email] start login")
        if not self.context_page.url.lower().startswith(
            "https://auth.openai.com/authorize"
        ):
            await self.goto_auth_page()

        await self.context_page.wait_for_load_state()
        await self.context_page.wait_for_selector("#email-input", timeout=30000)
        await asyncio.sleep(random.uniform(0.5, 2.0))

        email_input = self.context_page.locator("#email-input")
        await email_input.focus()
        await asyncio.sleep(0.1)
        await email_input.fill(self.email)

        continue_button = self.context_page.locator(".continue-btn")
        await continue_button.click()

        await self.context_page.wait_for_load_state()
        await self.context_page.wait_for_selector("#password", timeout=30000)
        await asyncio.sleep(random.uniform(0.5, 2.0))

        password_input = self.context_page.locator("#password")
        await password_input.focus()
        await asyncio.sleep(0.1)
        await password_input.fill(self.password)

        await asyncio.sleep(random.uniform(0.5, 2.0))

        login_password_button = self.context_page.locator("button:text('Continue')")
        self.persona_ready.clear()
        await login_password_button.click(timeout=5000)

        await self.context_page.wait_for_url(lambda url: url.startswith(self._host))
        await asyncio.wait_for(self.persona_ready.wait(), timeout=10)

        if self.persona == "chatgpt-noauth":
            logger.error(
                "[OpenAILogin.login_by_email] login failed. Still chatgpt-noauth user"
            )
        else:
            logger.info("[OpenAILogin.login_by_email] finish login")

    async def goto_auth_page(self):
        # 2024-05-28
        # 某些客户端打开首页后会弹出一个登录的dialog
        await self.context_page.wait_for_selector(
            "button >> text='Log in'", timeout=30000
        )
        dialog = self.context_page.locator('div[role="dialog"]')
        if await dialog.is_visible():
            login_button = dialog.locator("button", has_text="Log in")
        else:
            login_button = self.context_page.locator("button", has_text="Log in")

        await asyncio.sleep(random.uniform(2, 5))
        await login_button.click(timeout=5000)

        await self.context_page.wait_for_url(
            lambda url: url.startswith("https://auth.openai.com/authorize")
        )
