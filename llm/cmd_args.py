import argparse

parser = argparse.ArgumentParser()

parser.add_argument(
    "--listen",
    action="store_true",
    help="server name, allowing to respond to network request",
)
parser.add_argument(
    "--port",
    type=int,
    help="server port, you need root/admin rights for ports < 1024, defaults to 5000 if available",
    default=None,
)
# parser.add_argument("--api-auth", type=str, help='Set authentication for API like "username:password"; or comma-delimit multiple like "u1:p1,u2:p2,u3:p3"', default=None)
parser.add_argument(
    "--api-log",
    action="store_true",
    help="use api-log=True to enable logging of all API requests",
)
parser.add_argument(
    "--timeout-keep-alive",
    type=int,
    default=30,
    help="set timeout_keep_alive for uvicorn",
)

# parser.add_argument(
#     "--enabled-provider",
#     type=str,
#     help="enabled LLM provider. select (openai | step | kimi | glm), or comma-delimit multiple like 'openai,step'",
#     default="openai"
# )
