import random
import time
from typing import Optional

from DrissionPage import ChromiumOptions, ChromiumPage

from llm import config
from llm.logger import logger


class CloudflareBypass:
    def __init__(
        self, proxy_server: Optional[str] = None, user_agent: Optional[str] = None
    ):
        options = ChromiumOptions()
        options.set_paths(browser_path=config.BROWSER_PATH)

        # https://stackoverflow.com/questions/68289474/selenium-headless-how-to-bypass-cloudflare-detection-using-selenium
        if config.HEADLESS:
            options.headless(True)

        if user_agent:
            options.set_user_agent(user_agent)

        arguments = []
        if proxy_server:
            arguments.append(f"--proxy-server={proxy_server}")

        # Some arguments to make the browser better for automation and less detectable.
        if config.NO_GUI:
            logger.info("[CloudflareBypass.__init__] set --no-sandbox")
            arguments.append("--no-sandbox")

        for argument in arguments:
            options.set_argument(argument)

        self.driver = ChromiumPage(addr_or_opts=options)
        print(self.driver.user_agent)

    def bypass(self, url: str):
        self.driver.get(url)

        check_count = 0
        while True:
            print(self.driver.cookies())
            if self.is_passed():
                break

            if check_count >= 5:
                raise Exception("Meet challenge restart")

            logger.info(f"Meet challenge and check it. Count: {check_count}")
            self.try_to_click_challenge()

            check_count += 1

        return self.driver.cookies(all_info=True)

    def try_to_click_challenge(self):
        try:
            if self.driver.wait.ele_displayed("xpath://div/iframe", timeout=15):
                verify_element = self.driver("xpath://div/iframe").ele(
                    "Verify you are human", timeout=25
                )
                time.sleep(random.uniform(2, 5))
                verify_element.click()
                self.driver.wait.load_start(timeout=20)
        except Exception as e:
            # 2025-05-26
            # 有时会出现错误，重试能解决一部分问题
            # 1. DrissionPage.errors.ContextLostError: 页面被刷新，请操作前尝试等待页面刷新或加载完成。
            # 2. DrissionPage.errors.ElementNotFoundError:
            #    没有找到元素。
            #    method: ele()
            #    args: {'locator': 'Verify you are human', 'index': 1}
            logger.info(
                f"[CloudflareBypass.try_to_click_challenge] fail to click the challenge. message: {str(e)}"
            )
            self.driver.refresh()

    def is_passed(self):
        return any(
            cookie.get("name") == "cf_clearance" for cookie in self.driver.cookies()
        )

    def close(self):
        try:
            self.driver.close()
        except Exception as e:
            print(e)
