from typing import Optional

from llm import config
from llm.base.crawler import AbstractCrawler
from llm.provider.openai.core import OpenAICrawler


class CrawlerFactory:
    CRAWLERS = {
        "openai": OpenAICrawler,
    }

    @staticmethod
    def create_crawler(provider: str) -> AbstractCrawler:
        crawler_class = CrawlerFactory.CRAWLERS.get(provider)
        if not crawler_class:
            raise ValueError("Invalid provider. Currently only supported openai")
        return crawler_class()


class ProviderManager:
    def __init__(self, enabled_providers: list[str]):
        self.provider_dict: dict[str, AbstractCrawler] = {}

        for provider in enabled_providers:
            crawler = CrawlerFactory.create_crawler(provider)
            self.provider_dict[provider] = crawler

    async def start_all(self):
        for crawler in self.provider_dict.values():
            await crawler.start()

    def get_provider(self, model: str) -> Optional[AbstractCrawler]:
        for provider in self.provider_dict.values():
            if model in provider.supported_model:
                return provider
        return None

    def get_all_providers(self) -> dict[str, AbstractCrawler]:
        return self.provider_dict


provider_manager = ProviderManager(config.ENABLED_PROVIDER)
