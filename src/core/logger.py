import logging
import sys
from contextvars import ContextVar
from typing import Optional

# Context variables for logging context
_worker_id: ContextVar[Optional[str]] = ContextVar("worker_id", default=None)


class _ContextFilter(logging.Filter):
    """Add context variables to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.worker_id = _worker_id.get() or ""
        record.worker_prefix = ""
        return True


class _ColoredFormatter(logging.Formatter):
    """Formatter with ANSI color support for different log levels."""

    COLORS = {
        "RESET": "\033[0m",
        "BOLD": "\033[1m",
        "RED": "\033[91m",
        "GREEN": "\033[92m",
        "YELLOW": "\033[93m",
        "BLUE": "\033[94m",
    }

    LEVEL_COLORS = {
        logging.DEBUG: COLORS["BLUE"],
        logging.INFO: COLORS["GREEN"],
        logging.WARNING: COLORS["YELLOW"],
        logging.ERROR: COLORS["RED"],
        logging.CRITICAL: COLORS["RED"] + COLORS["BOLD"],
    }

    def format(self, record: logging.LogRecord) -> str:
        level_color = self.LEVEL_COLORS.get(record.levelno, self.COLORS["RESET"])
        record.levelname = f"{level_color}{record.levelname}{self.COLORS['RESET']}"

        # Add worker context only if available
        if record.worker_id:
            record.worker_prefix = (
                f"Worker #{self.COLORS['BOLD']}{record.worker_id}{self.COLORS['RESET']} | "
            )
        else:
            record.worker_prefix = ""

        return super().format(record)


def set_worker_id(worker_id: str) -> None:
    """Set the current worker ID in logging context."""
    _worker_id.set(worker_id)


def clear_worker_id() -> None:
    """Clear the worker ID from logging context."""
    _worker_id.set(None)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance with color support.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Configured logger instance with color and context support
    """
    logger = logging.getLogger(name)

    # Configure only once to avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = _ColoredFormatter(
            fmt=(
                "%(asctime)s | %(levelname)s | %(worker_prefix)s"
                "%(filename)s:%(lineno)d | %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.addFilter(_ContextFilter())
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
