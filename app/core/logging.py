import logging
import sys


def configure_logging() -> None:
    """Initializes and manages the logging settings

    Args:
        None
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    # Clear existing handlers to avoid duplicates in reload
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
