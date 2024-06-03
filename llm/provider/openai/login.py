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

            # 最后等上几秒，不然不点击登录
            await asyncio.sleep(5)

    async def login_by_email(self):
        # 2024-05-28
        # 某些客户端打开首页后会弹出一个登录的dialog
        dialog = self.context_page.locator('div[role="dialog"]')
        if dialog and await dialog.is_visible():
            login_button = dialog.locator("button", has_text="Log in")
        else:
            login_button = self.context_page.locator("button", has_text="Log in")

        if await login_button.is_visible():
            await login_button.click()
            await self.context_page.wait_for_load_state("load")
        else:
            # 2024-05-25
            # 打开首页后直接跳到登录页面，这里要判断一下，如果已经在登录页，就不用点击按钮
            if self.context_page.url.lower().startswith(
                "https://auth.openai.com/authorize"
            ):
                ...
            else:
                # 其他没有登录的情况
                # TODO
                return
        logger.info("[OpenAILogin.login_by_email] start login")

        # TODO
        # 可能会再次遇到cloudflare 5s盾

        await self.context_page.locator("#email-input").click()
        await self.context_page.locator("#email-input").fill(self.email)

        await self.context_page.locator(".continue-btn").click()
        await self.context_page.wait_for_load_state("load")

        await self.context_page.locator("#password").click()
        await self.context_page.locator("#password").fill(self.password)

        await self.context_page.locator("button._button-login-password").click()

        await self.context_page.wait_for_load_state("load")
        logger.info("[OpenAILogin.login_by_email] finish login")
