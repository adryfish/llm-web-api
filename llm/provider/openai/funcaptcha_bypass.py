import asyncio
import base64
import random
from urllib.parse import urlparse

from playwright.async_api import Page, Request, Response

from llm.logger import logger
from llm.provider.openai.captcha import CaptchaSolverProxy


class FunCaptchaBypass:
    def __init__(self, context_page: Page):
        self.context_page = context_page
        self.trigger = False
        self.ready_flag = asyncio.Event()

        self.captcha_solver = CaptchaSolverProxy()

        self.landing_start = "Begin puzzle"
        self.instruction_string = None
        self.challenge_images = []

    async def post_init(self):
        self.context_page.on("request", self.setup_request_listener)
        self.context_page.on("response", self.setup_response_listener)

    async def setup_request_listener(self, request: Request):
        path = urlparse(request.url).path
        if path == "/fc/gfct/":
            logger.info("[FunCaptchaBypass] FunCaptcha triggered")
            self.trigger = True
            self.ready_flag.clear()

    async def setup_response_listener(self, response: Response):
        path = urlparse(response.url).path
        if path == "/fc/gfct/":
            try:
                _body = await response.json()
                print(_body)
                self.instruction_string = _body.get("game_data", {}).get(
                    "instruction_string", None
                )
                self.challenge_images = (
                    _body.get("game_data", {})
                    .get("customGUI", {})
                    .get("_challenge_imgs")
                )

                self.landing_start = _body.get("string_table", {}).get(
                    "openai_custom_instructions-game_meta.landing_start", "Begin puzzle"
                )

                await self.bypass()
            except Exception as e:
                logger.error(f"[FunCaptchaBypass] Error: {str(e)}", exc_info=True)
            finally:
                self.trigger = False
                self.ready_flag.set()

    async def bypass(self):
        # click Verify
        def filter(url: str):
            return url.startswith("https://tcr9i.openai.com")

        challenge_frame = self.context_page.frame(filter)
        iframe = challenge_frame.child_frames[0]

        verify_button = iframe.locator("button:text('Begin puzzle')")
        await verify_button.click(timeout=5000)
        await challenge_frame.wait_for_load_state()

        for challenge_image in self.challenge_images:
            response = await self.context_page.request.get(challenge_image)
            _image_data = await response.body()
            _base64_data = base64.b64encode(_image_data).decode("utf-8")

            # captcha solve
            result = await self.captcha_solver.solve(
                **{"question": self.instruction_string, "images": [_base64_data]}
            )

            # result = random.randint(0, 5)
            await self.nav_to_result(iframe, result)

            submit_button = iframe.locator("button:text('Submit')")
            await submit_button.click(timeout=5000)

    async def nav_to_result(self, iframe, result):
        answer_frame = iframe.locator("div.answer-frame")
        pip = answer_frame.locator(".pip-container").locator(".pip")
        result_pip = pip.nth(result)

        option_count = await pip.count()

        for _ in range(option_count):
            has_active_class = await result_pip.evaluate(
                "el => el.classList.contains('active')"
            )

            if not has_active_class:
                d_value = "M23.97 15 28 18.5m0 0L23.97 22M28 18.5H9"
                button = answer_frame.locator(f'a:has(svg > path[d="{d_value}"])')
                await button.click(timeout=5000)

                await asyncio.sleep(random.uniform(0.5, 3))
            else:
                break
