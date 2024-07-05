import os
import random
import time
from datetime import datetime
from typing import Optional

import pyautogui
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
            # 最大化窗口保证坐标的准确性
            arguments.append("--start-maximized")
            arguments.append("--no-sandbox")
        else:
            # 图形界面中，如果使用--start-maximized，获取的page_x和page_y有时候并不准确(原因未知)，所以全屏使page_x, page_y为0
            arguments.append("--start-fullscreen")

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
                error_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-DrissionPage")
                error_path = os.path.join(config.BROWSER_DATA, "error")
                self.driver.get_screenshot(
                    path=error_path, name=f"{error_time}.png", full_page=True
                )
                raise Exception("Meet challenge restart")

            logger.info(f"Meet challenge and check it. Count: {check_count}")
            self.try_to_click_challenge()

            check_count += 1

        return self.driver.cookies(all_info=True)

    def try_to_click_challenge(self):
        try:
            if self.driver.wait.ele_displayed("xpath://div/iframe", timeout=15):
                if config.env == "dev":
                    iframe = self.driver("xpath://div/iframe")
                    iframe = self.driver.get_frame(iframe)
                    iframe.run_js(
                        script="""
                        document.addEventListener('click', function(event) {
                            console.log("click event trigger")
                            console.table(event);
                        });
                    """
                    )
                verify_element = self.driver("xpath://div/iframe").ele(
                    "Verify you are human", timeout=25
                )
                time.sleep(random.uniform(2, 5))

                # 2024-07-05
                # 直接在element上执行click(通过CDP协议)无法通过cloudflare challenge
                # 原因:
                # CDP命令执行的event中client_x, client_y与screen_x, screen_y是一样的，而手动点击触发的事件两者是不一样的,所以无法使用CDP模拟出鼠标点击通过验证
                # 解决方法:
                # 先获取点击的坐标，使用pyautogui模拟鼠标点击
                # CDP参考 https://chromedevtools.github.io/devtools-protocol/tot/Input/
                # verify_element.click()
                def generate_biased_random(n):
                    weights = [min(i, n - i + 1) for i in range(1, n + 1)]
                    return random.choices(range(1, n + 1), weights=weights)[0]

                if config.env == "dev":
                    property_list = {
                        attr: getattr(verify_element.rect, attr)
                        for attr in dir(verify_element.rect)
                        if not attr.startswith("__")
                        and not callable(getattr(verify_element.rect, attr))
                    }

                    # 手动遍历字典并格式化输出
                    for key, value in property_list.items():
                        print(f"{key}: {value}")

                    print("\n")
                    property_list = {
                        attr: getattr(self.driver.rect, attr)
                        for attr in dir(self.driver.rect)
                        if not attr.startswith("__")
                        and not callable(getattr(self.driver.rect, attr))
                    }

                    # 手动遍历字典并格式化输出
                    for key, value in property_list.items():
                        print(f"{key}: {value}")

                screen_x, screen_y = verify_element.rect.screen_location
                page_x, page_y = self.driver.rect.page_location
                width, height = verify_element.rect.size
                offset_x, offset_y = generate_biased_random(
                    int(width - 1)
                ), generate_biased_random(int(height - 1))

                click_x, click_y = (
                    screen_x + page_x + offset_x,
                    screen_y + page_y + offset_y,
                )

                logger.info(
                    f"[CloudflareBypass.try_to_click_challenge] Screen point [{screen_x}, {screen_y}]"
                )
                logger.info(
                    f"[CloudflareBypass.try_to_click_challenge] Page point[{page_x}, {page_y}]"
                )
                logger.info(
                    f"[CloudflareBypass.try_to_click_challenge] Click point [{click_x}, {click_y}]"
                )
                pyautogui.moveTo(
                    click_x, click_y, duration=0.5, tween=pyautogui.easeInElastic
                )
                pyautogui.click()
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
