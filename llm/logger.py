import logging

from llm import config

# 创建一个日志记录器
logger = logging.getLogger("AppLogger")
logger.setLevel(logging.DEBUG)  # 设置全局日志级别

# 创建一个处理器，输出到控制台
ch = logging.StreamHandler()
if config.env == "dev":
    ch.setLevel(logging.DEBUG)
else:
    ch.setLevel(logging.INFO)

# 创建一个格式器，并添加到处理器
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(ch)
