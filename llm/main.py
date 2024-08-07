import os
import platform
from contextlib import asynccontextmanager

from fastapi import FastAPI

from llm import config
from llm.logger import logger


def create_api(app):
    from llm.api.api import Api

    api = Api(app)

    return api


@asynccontextmanager
async def lifespan(app: FastAPI):
    from llm.provider_manager import provider_manager

    await provider_manager.start_all()
    try:
        yield
    finally:
        # Teardown logic here (after yield)
        # If you have any teardown process, place it here. For example:
        # await close_db_connection()
        pass


xvfb_display = None


def start_xvfb_display():
    from pyvirtualdisplay import Display

    xvfb_display = Display(
        backend="xvfb",
        visible=True,
        size=(config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
        use_xauth=True,
    )
    xvfb_display.start()
    print(f"DISPLAY={os.getenv('DISPLAY')}")


def api():
    from llm.shared_cmd_options import cmd_opts

    if config.NO_GUI and platform.system() == "Linux":
        logger.info(f"Start xvfb service")
        start_xvfb_display()

    app = FastAPI(lifespan=lifespan)
    api = create_api(app)

    api.launch(
        server_name="0.0.0.0" if cmd_opts.listen else "127.0.0.1",
        port=cmd_opts.port if cmd_opts.port else 5000,
    )


if __name__ == "__main__":
    api()
