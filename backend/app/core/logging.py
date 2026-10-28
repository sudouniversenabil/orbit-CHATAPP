"""Application logging setup."""

import logging


def configure_logging() -> None:
    """Configure concise structured-enough logs for local development."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
