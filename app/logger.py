from datetime import datetime, timedelta
from sys import stdout

from config import get_settings
from logtail import LogtailHandler
from loguru import logger

settings = get_settings()
betterstack_handler = LogtailHandler(source_token=settings.betterstack_source_token)
logger.remove()
logger.add(
    stdout,
    colorize=True,
    level="DEBUG",
    # format="<green>{time:HH:mm:ss:SSSS}</green>:<red>{line}</red> - <blue>{message}</blue> <yellow>{extra}</yellow>",
    format="<green>{time:HH:mm:ss:SSSS}</green>:<magenta>{file.name}</magenta>:<cyan>{function}</cyan>:<red>{line}</red> - <blue>{message}</blue> <yellow>{extra}</yellow>",
)
logger.add(
    f"logs/{datetime.today().strftime('%d-%m-%Y')}/{datetime.now().strftime('%I:%M:%S %p')}.log",
    level="DEBUG",
    format="{level}:{time:HH:mm:ss:SSS}:{file.name}:{function}:{line} - {message} {extra}",
    retention=timedelta(days=7),
)
logger.add(
    betterstack_handler,
    format="{level}:{time:HH:mm:ss:SSS}:{file.name}:{function}:{line} - {message} {extra}",
)
logger.info(settings.betterstack_source_token)
