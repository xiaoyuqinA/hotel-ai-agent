"""统一日志入口。在 api/main.py 中配置 basicConfig 后，所有模块共用同一格式。"""

import logging


def get_logger(name: str = "hotel_ai") -> logging.Logger:
    return logging.getLogger(name)
