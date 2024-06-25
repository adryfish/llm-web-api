import os
import platform

from dotenv import load_dotenv

load_dotenv()

# enabled LLM provider. select (openai), or comma-delimit multiple like 'openai'
ENABLED_PROVIDER = os.getenv("ENABLED_PROVIDER", "openai").split(",")

PROXY_SERVER = os.getenv("PROXY_SERVER", None)

NO_GUI = False if os.getenv("DISPLAY") else True
# if NO_GUI:
#     DEFAULT_SCREEN_WIDTH = "1920"
#     DEFAULT_SCREEN_HEIGHT = "1080"
# else:
#     import tkinter

#     screen_root = tkinter.Tk()
#     screen_root.withdraw()
#     DEFAULT_SCREEN_WIDTH = screen_root.winfo_screenwidth()
#     DEFAULT_SCREEN_HEIGHT = screen_root.winfo_screenheight()
#     screen_root.destroy()

SCREEN_WIDTH = int(os.getenv("SCREEN_WIDTH", "1920"))
SCREEN_HEIGHT = int(os.getenv("SCREEN_HEIGHT", "1080"))
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
USER_AGENT = os.getenv("USER_AGENT", None)
SAVE_LOGIN_STATE = os.getenv("SAVE_LOGIN_STATE", True)


def get_default_browser_path():
    os_name = platform.system().lower()
    if "windows" in os_name:
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    elif "darwin" in os_name:
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:
        return "/usr/bin/google-chrome"


BROWSER_PATH = os.getenv("BROWSER_PATH", get_default_browser_path())

BROWSER_DATA = os.path.join(os.getenv("BROWSER_DATA", os.getcwd()), "browser_data")
os.makedirs(BROWSER_DATA, exist_ok=True)

ENABLE_MULTI_TURN_CONVERSATION = (
    os.getenv("ENABLE_MULTI_TURN_CONVERSATION", "true").lower() == "true"
)

env = os.getenv("env", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if env != "dev" else "DEBUG").upper()


OPENAI_LOGIN_TYPE = os.getenv("OPENAI_LOGIN_TYPE", "nologin")
OPENAI_LOGIN_EMAIL = os.getenv("OPENAI_LOGIN_EMAIL", "")
OPENAI_LOGIN_PASSWORD = os.getenv("OPENAI_LOGIN_PASSWORD", "")
