from contextlib import asynccontextmanager

from fastapi import FastAPI


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


def api():
    from llm.shared_cmd_options import cmd_opts

    app = FastAPI(lifespan=lifespan)
    api = create_api(app)

    api.launch(
        server_name="0.0.0.0" if cmd_opts.listen else "127.0.0.1",
        port=cmd_opts.port if cmd_opts.port else 5000,
    )


if __name__ == "__main__":
    api()
