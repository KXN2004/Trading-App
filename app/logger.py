from datetime import datetime, timedelta
from sys import stdout

from config import get_settings
from loguru import logger


def now() -> str:
    return


settings = get_settings()
logger.remove()
logger.add(
    stdout,
    colorize=True,
    format="<green>{level}</green>:<cyan>{time:HH:mm:ss}</cyan>:<magenta>{file.name}</magenta>:<yellow>{function}</yellow>:<red>{line}</red> - <blue>{message}</blue> {extra}",
)
logger.add(
    f"logs/{datetime.today().strftime('%d-%m-%Y')}/{datetime.now().strftime('%I:%M:%S %p')}.log",
    format="{level}:{time:HH:mm:ss}:{file.name}:{function}:{line} - {message} {extra}",
    retention=timedelta(days=7),
)
