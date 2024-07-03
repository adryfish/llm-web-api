import os
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from llm import config


class CaptchaSolver(ABC):
    @abstractmethod
    async def solve(self, **kwargs):
        """
        Solve the captcha and return the solution.
        """
        pass


class CapsolverCaptcha(CaptchaSolver):

    async def solve(self, **kwargs):
        _api_key = os.getenv("CAPSOLVER_API_KEY")
        if not _api_key:
            raise Exception("CAPSOLVER API key not found")

        images = kwargs["images"]
        question = kwargs["question"]

        url = "https://api.capsolver.com/createTask"
        headers = {"Content-Type": "application/json"}
        data = {
            "clientKey": _api_key,
            "task": {
                "type": "FunCaptchaClassification",
                # "websiteURL": "https://openai.com",
                "images": images,
                "question": question,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            _json = response.json()
            return _json.get("solution", {}).get("objects")[0]


_providers: dict[str, CaptchaSolver] = {"capsolver": CapsolverCaptcha()}


class CaptchaSolverProxy(CaptchaSolver):
    def __init__(self, provider_name: Optional[str] = None):
        if not provider_name:
            provider_name = config.FUNCAPTCHA_PROVIDER

        self.provider = _providers.get(provider_name)

    async def solve(self, **kwargs):
        return await self.provider.solve(**kwargs)
