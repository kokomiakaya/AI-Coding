"""日志配置：loguru 控制台 + 按天滚动文件（UTF-8，规避 Windows 控制台 GBK 乱码）。"""
import sys

from loguru import logger

from app.core.config import get_settings

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan> - <level>{message}</level>",
    )
    logger.add(
        settings.logs_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="20 MB",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )
