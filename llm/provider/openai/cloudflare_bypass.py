import platform
import time
from typing import Optional

from DrissionPage import ChromiumOptions, ChromiumPage

from llm import config
from llm.logger import logger


class CloudflareBypass:
    def __init__(
        self, proxy_server: Optional[str] = None, user_agent: Optional[str] = None
    ):
        browser_path = config.BROWSER_PATH
        if not browser_path:
            os_name = platform.system().lower()
            if "windows" in os_name:
                browser_path = "C:\Program Files\Google\Chrome\Application\chrome.exe"
            elif "darwin" in os_name:
                browser_path = (
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                )
            else:
                # linux like
                browser_path = "/usr/bin/google-chrome"

        options = ChromiumOptions()
        options.set_paths(browser_path=browser_path)

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

        self.driver = ChromiumPage(addr_driver_opts=options)
        print(self.driver.user_agent)

    def bypass(self, url: str):
        self.driver.get(url)

        check_count = 1
        while not self.is_passed():
            self.try_to_click_challenge()

            if check_count >= 6:
                if not self.is_passed():
                    raise Exception("Meet challenge restart")

            logger.info(
                f"Handle category - meet challenge. Wait 20s to check it again. Count: {check_count}"
            )
            check_count += 1

            time.sleep(20)

        return self.driver.cookies(all_info=True)

    def try_to_click_challenge(self):
        try:
            if self.driver.wait.ele_displayed("xpath://div/iframe", timeout=1.5):
                time.sleep(1.5)
                self.driver("xpath://div/iframe").ele(
                    "Verify you are human", timeout=2.5
                ).click()
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
        print(self.driver.cookies())
        for cookie in self.driver.cookies():
            if cookie.get("name") == "cf_clearance":
                return True
        return False

    def close(self):
        try:
            self.driver.close()
        except Exception as e:
            print(e)
