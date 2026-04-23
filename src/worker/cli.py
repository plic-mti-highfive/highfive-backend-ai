"""CLI entry point for starting worker service."""

import asyncio

from src.worker.main import main

if __name__ == "__main__":
    asyncio.run(main())
