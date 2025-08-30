#!/usr/bin/env python3
"""
MCP Travel Tools Server (stdio transport) - Refactored Version.

A clean, modular travel agent MCP server with separated concerns:
- Configuration centralized in config.py
- Utilities in utils/ package
- Individual tools in tools/ package
- Clean server startup with rich UI

ENV:
  OPENAI_API_KEY or OPENROUTER_API_KEY -> OpenAI/OpenRouter API
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from config import Config
from tools.tool_registry import register_all_tools
from utils.openai_client import has_openai_client

logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "mcp_server.log"
daemon_mode = "--daemon" in sys.argv
detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(detailed_formatter)
handlers = [file_handler]
if not daemon_mode:
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(detailed_formatter)
    handlers.append(console_handler)

logging.basicConfig(level=logging.INFO, handlers=handlers)
tool_logger = logging.getLogger("mcp.tools")
tool_logger.setLevel(logging.INFO)

app = FastMCP("travel-tools")
register_all_tools(app)


async def run_server():
    """MCP Server for the travel agent with timeout handling."""
    if not daemon_mode:
        print(
            f"MCP Travel Server starting on http://{Config.SERVER_HOST}:{Config.SERVER_PORT}"
        )
        print(f"Logs: {log_file}")
    logging.info(
        f"MCP Travel Server starting on {Config.SERVER_HOST}:{Config.SERVER_PORT}"
    )
    logging.info(f"Daemon mode: {daemon_mode}")

    def setup_timeout_handlers():
        """Setup graceful timeout handling."""

        def timeout_handler(signum, frame):
            logging.warning("Operation timeout - generating partial results")

        signal.signal(signal.SIGALRM, timeout_handler)
    setup_timeout_handlers()
    start_time = time.time()
    if not daemon_mode:
        print(f"Tools loaded: {len(app._tool_manager._tools)}")
        if Config.OPENROUTER_API_KEY:
            print(f"LLM: OpenRouter ({Config.OPENROUTER_MODEL})")
        elif Config.OPENAI_API_KEY:
            print("LLM: OpenAI")
        else:
            print("LLM: Not configured")

    try:
        logging.info(
            "Server running in daemon mode" if daemon_mode else "Server running"
        )
        await app.run_streamable_http_async()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
        if not daemon_mode:
            print("\nServer shutting down...")
    except Exception as e:
        logging.error(f"Server error: {e}")
        if not daemon_mode:
            print(f"\nServer error: {e}")


def main():
    parser = argparse.ArgumentParser(description="MCP Travel Server")
    parser.add_argument(
        "--daemon", action="store_true", help="Run in daemon mode (no UI)"
    )
    args = parser.parse_args()
    global daemon_mode
    daemon_mode = args.daemon
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
