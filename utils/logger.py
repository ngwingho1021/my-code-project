import logging
import os
from datetime import datetime

from config.settings import LOG_DIR


def get_logger(name: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_path = os.path.join(LOG_DIR, f"{datetime.now():%Y-%m-%d}.log")
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    trade_file = os.path.join(LOG_DIR, "trades.log")
    trade_handler = logging.FileHandler(trade_file, encoding="utf-8")
    trade_handler.setFormatter(fmt)
    trade_handler.addFilter(lambda record: record.name == "trade")
    logger.addHandler(trade_handler)

    return logger
