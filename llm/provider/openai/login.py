import asyncio
from typing import Optional

from playwright.async_api import Page

from llm.logger import logger
from llm.provider.openai.cloudflare_bypass import CloudflareBypass


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

    async def begin(self):
        logger.info("[OpenAILogin.begin] Begin login OpenAI ...")
        await self.bypass_cloudflare()

        # 最后等上几秒，不然不点击登录
        await asyncio.sleep(5)
        if self.login_type == "email":
            await self.login_by_email()

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
        login_button = self.context_page.locator("button", has_text="Log in")
        if not login_button or not await login_button.is_visible():
            # 检查是否真的没有登录
            # TODO
            return

        await login_button.click()
        await self.context_page.wait_for_load_state("load")

        await self.context_page.locator("#email-input").click()
        await self.context_page.locator("#email-input").fill(self.email)

        await self.context_page.locator(".continue-btn").click()
        await self.context_page.wait_for_load_state("load")

        await self.context_page.locator("#password").click()
        await self.context_page.locator("#password").fill(self.password)

        await self.context_page.locator("button._button-login-password").click()

        await self.context_page.wait_for_load_state("load")
