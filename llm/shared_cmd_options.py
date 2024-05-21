import os

from llm import cmd_args

parser = cmd_args.parser

if os.getenv("IGNORE_CMD_ARGS_ERRORS", None) is None:
    cmd_opts = parser.parse_args()
else:
    cmd_opts, _ = parser.parse_known_args()
