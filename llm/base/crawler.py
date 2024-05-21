from abc import ABC, abstractmethod
from typing import Optional

from playwright.async_api import BrowserContext, BrowserType


class AbstractCrawler(ABC):
    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        pass


class AbstractLogin(ABC):
    @abstractmethod
    async def begin(self):
        pass

    @abstractmethod
    async def login_by_email(self):
        pass
