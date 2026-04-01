"""NEXUS entry point — boots the kernel and starts the API server."""

from __future__ import annotations

import logging

import uvicorn

from nexus.api.server import create_app
from nexus.config import get_config


def main() -> None:
    config = get_config()
    logging.basicConfig(level=config.log_level)

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=config.api_port)


if __name__ == "__main__":
    main()
