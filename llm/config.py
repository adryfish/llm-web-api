import os

from dotenv import load_dotenv

load_dotenv()

# enabled LLM provider. select (openai), or comma-delimit multiple like 'openai'
ENABLED_PROVIDER = os.getenv("ENABLED_PROVIDER", "openai").split(",")

PROXY_SERVER = os.getenv("PROXY_SERVER", None)

NO_GUI = os.getenv("NO_GUI", "false").lower() == "true"
SCREEN_WIDTH = int(os.getenv("SCREEN_WIDTH", "1080"))
SCREEN_HEIGHT = int(os.getenv("SCREEN_HEIGHT", "1920"))
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
USER_AGENT = os.getenv("USER_AGENT", None)
SAVE_LOGIN_STATE = os.getenv("SAVE_LOGIN_STATE", True)

BROWSER_PATH = os.getenv("BROWSER_PATH", None)
BROWSER_DATA = os.path.join(os.getenv("BROWSER_DATA", os.getcwd()), "browser_data")
os.makedirs(BROWSER_DATA, exist_ok=True)

env = os.getenv("env", "prod")


OPENAI_LOGIN_TYPE = os.getenv("OPENAI_LOGIN_TYPE", "nologin")
OPENAI_LOGIN_EMAIL = os.getenv("OPENAI_LOGIN_EMAIL", "")
OPENAI_LOGIN_PASSWORD = os.getenv("OPENAI_LOGIN_PASSWORD", "")
