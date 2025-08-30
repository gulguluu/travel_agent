#!/usr/bin/env python3
"""
Configuration module for the Travel Agent MCP server.
Centralizes API keys, settings, and environment variables.
"""

import json
import os
from pathlib import Path


class Config:
    """Configuration class for travel agent settings."""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

    # OpenAI/OpenRouter Settings
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
    DEFAULT_MODEL = "gpt-4o-mini"  # Use mini for all tasks - 60x cheaper than gpt-4o

    # HTTP Settings
    HTTP_TIMEOUT = 20.0
    HTTP_CONNECT_TIMEOUT = 10.0
    USER_AGENT = "MCPTravelAgent/1.0"

    # Server Settings
    SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://{SERVER_HOST}:{SERVER_PORT}")

    # Tool Settings
    DEFAULT_MAX_RESULTS = 20
    DEFAULT_WEATHER_DAYS = 7
    DEFAULT_CURRENCY = "USD"

    # File Paths
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "screenshots")
    PERFORMANCE_LOG_FILE = os.getenv("PERFORMANCE_LOG_FILE", "performance_logs.jsonl")

    # Workspace Settings
    _workspace_config = None

    @classmethod
    def get_openai_api_key(cls):
        """Get OpenAI API key, preferring OpenRouter if available."""
        return cls.OPENROUTER_API_KEY or cls.OPENAI_API_KEY

    @classmethod
    def has_openai_client(cls):
        """Check if OpenAI client can be configured."""
        return bool(cls.get_openai_api_key())

    @classmethod
    def get_workspace_config(cls, workspace_path=None):
        """Get workspace-specific configuration."""
        if cls._workspace_config is None:
            cls._load_workspace_config(workspace_path)
        return cls._workspace_config

    @classmethod
    def _load_workspace_config(cls, workspace_path=None):
        """Load workspace configuration from .travel_agent/config.json"""
        if workspace_path is None:
            workspace_path = Path.cwd()
        else:
            workspace_path = Path(workspace_path)

        config_file = workspace_path / ".travel_agent" / "config.json"

        # Default workspace config
        defaults = {
            "preferred_airlines": [],
            "preferred_hotel_chains": [],
            "budget_range": {"min": 100, "max": 1000},
            "travel_style": "moderate",
            "mcp_servers": {},
            "memory_retention_days": 30,
            "enabled_tools": [],
            "disabled_tools": [],
        }

        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    user_config = json.load(f)
                    defaults.update(user_config)
            except (json.JSONDecodeError, IOError):
                pass

        cls._workspace_config = defaults

    @classmethod
    def save_workspace_config(cls, config_data, workspace_path=None):
        """Save workspace configuration."""
        if workspace_path is None:
            workspace_path = Path.cwd()
        else:
            workspace_path = Path(workspace_path)

        config_dir = workspace_path / ".travel_agent"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f, indent=2)

        cls._workspace_config = config_data

    @classmethod
    def get_mcp_servers(cls):
        """Get configured MCP servers."""
        workspace_config = cls.get_workspace_config()
        return workspace_config.get("mcp_servers", {})

    @classmethod
    def validate_tool_params(cls, tool_name, params):
        """Basic parameter validation for tools."""
        validation_errors = []

        # Common validations
        if not isinstance(params, dict):
            validation_errors.append("Parameters must be a dictionary")
            return validation_errors

        # Tool-specific validations
        if tool_name in ["search_flights", "flight_search"]:
            required = ["origin", "destination", "departure_date"]
            for field in required:
                if not params.get(field):
                    validation_errors.append(f"Missing required field: {field}")

        elif tool_name in ["search_hotels", "hotel_search"]:
            required = ["location", "checkin_date", "checkout_date"]
            for field in required:
                if not params.get(field):
                    validation_errors.append(f"Missing required field: {field}")

        elif tool_name in ["get_weather", "weather_forecast"]:
            if not params.get("location"):
                validation_errors.append("Missing required field: location")

        elif tool_name == "web_search":
            if not params.get("query"):
                validation_errors.append("Missing required field: query")

        elif tool_name == "geocode_location":
            if not params.get("location"):
                validation_errors.append("Missing required field: location")

        return validation_errors
