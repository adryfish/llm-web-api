import os
from datetime import datetime

import aiofiles
from playwright.async_api import Page

from llm import config
from llm.logger import logger


async def is_clickable(locator):
    return await locator.is_visible() and await locator.is_enabled()


async def screenshot(page: Page):
    error_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    error_file = os.path.join(config.BROWSER_DATA, "error", error_time)

    await page.screenshot(path=f"{error_file}.png")

    content = await page.content()
    async with aiofiles.open(f"{error_file}.html", "w") as f:
        await f.write(content)

    logger.error(
        f"[OpenAIClient.chat_completion] Error screenshot: {error_file}.png. html: {error_file}.html"
    )
