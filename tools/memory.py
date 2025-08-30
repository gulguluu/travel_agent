#!/usr/bin/env python3
"""
Memory tool for the travel agent MCP server.
Provides persistent memory storage and retrieval for travel preferences and context.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from config import Config


def register_memory_tool(app: FastMCP):
    """Register the memory tool with the FastMCP app."""

    memory_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory")
    os.makedirs(memory_dir, exist_ok=True)

    @app.tool()
    def store_travel_memory(key, data):
        """Store travel information in memory with a key."""
        memory_file = os.path.join(memory_dir, f"{key}.json")
        memory_entry = {"timestamp": datetime.now().isoformat(), "data": data}

        try:
            with open(memory_file, "w") as f:
                json.dump(memory_entry, f, indent=2)

            return {
                "success": True,
                "message": f"Stored memory with key: {key}",
                "timestamp": memory_entry["timestamp"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.tool()
    def retrieve_travel_memory(key):
        """Retrieve travel information from memory."""
        memory_file = os.path.join(memory_dir, f"{key}.json")

        try:
            if not os.path.exists(memory_file):
                return {"success": False, "error": f"No memory found for key: {key}"}

            with open(memory_file, "r") as f:
                memory_entry = json.load(f)

            return {
                "success": True,
                "key": key,
                "data": memory_entry["data"],
                "timestamp": memory_entry["timestamp"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.tool()
    def list_travel_memories():
        """List all available memory keys and their timestamps."""
        try:
            memories = []
            for filename in os.listdir(memory_dir):
                if filename.endswith(".json"):
                    key = filename[:-5]  # Remove .json extension
                    memory_file = os.path.join(memory_dir, filename)

                    try:
                        with open(memory_file, "r") as f:
                            memory_entry = json.load(f)

                        memories.append(
                            {
                                "key": key,
                                "timestamp": memory_entry["timestamp"],
                                "preview": (
                                    str(memory_entry["data"])[:100] + "..."
                                    if len(str(memory_entry["data"])) > 100
                                    else str(memory_entry["data"])
                                ),
                            }
                        )
                    except:
                        continue

            memories.sort(key=lambda x: x["timestamp"], reverse=True)
            return memories

        except Exception as e:
            return [{"error": str(e)}]

    @app.tool()
    def load_travel_context():
        """Load travel context from TRAVEL_CONTEXT.md files."""
        contexts = []
        workspace_path = Path.cwd()

        # Check for context files in hierarchy
        context_files = []

        # Workspace context
        workspace_context = workspace_path / "TRAVEL_CONTEXT.md"
        if workspace_context.exists():
            context_files.append(("workspace", workspace_context))

        # User context
        user_context = Path.home() / ".travel_agent" / "TRAVEL_CONTEXT.md"
        if user_context.exists():
            context_files.append(("user", user_context))

        for level, file_path in context_files:
            try:
                with open(file_path, "r") as f:
                    content = f.read().strip()
                if content:
                    contexts.append(
                        {"level": level, "content": content, "source": str(file_path)}
                    )
            except Exception as e:
                contexts.append(
                    {"level": level, "error": f"Could not load {file_path}: {str(e)}"}
                )

        return {"contexts": contexts, "total_contexts": len(contexts)}

    @app.tool()
    def compress_conversation(messages):
        """Compress conversation when it gets too long."""
        if len(messages) < 10:
            return {"compressed": False, "reason": "Not enough messages to compress"}

        # Simple compression - keep first 2 and last 5 messages, summarize middle
        if len(messages) > 15:
            summary = {
                "conversation_id": f"compressed_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "original_length": len(messages),
                "summary": f"Conversation with {len(messages)} messages about travel planning",
                "key_points": [],
                "compressed_at": datetime.now().isoformat(),
            }

            # Extract key points from middle messages
            middle_messages = messages[2:-5]
            for msg in middle_messages:
                content = str(msg.get("content", ""))
                if any(
                    keyword in content.lower()
                    for keyword in [
                        "destination",
                        "hotel",
                        "flight",
                        "budget",
                        "prefer",
                    ]
                ):
                    summary["key_points"].append(content[:200])

            # Store compressed summary
            store_travel_memory(f"compressed_{summary['conversation_id']}", summary)

            return {
                "compressed": True,
                "summary": summary,
                "new_length": 7,  # 2 + 5 kept messages
                "compression_ratio": f"{len(messages)}:7",
            }

        return {
            "compressed": False,
            "reason": "Conversation not long enough for compression",
        }

    @app.tool()
    def save_user_preferences(preferences):
        """Save user preferences to workspace config."""
        try:
            workspace_config = Config.get_workspace_config()

            # Update preferences
            if "preferred_airlines" in preferences:
                workspace_config["preferred_airlines"] = preferences[
                    "preferred_airlines"
                ]
            if "budget_range" in preferences:
                workspace_config["budget_range"] = preferences["budget_range"]
            if "travel_style" in preferences:
                workspace_config["travel_style"] = preferences["travel_style"]

            # Add timestamp
            workspace_config["preferences_updated"] = datetime.now().isoformat()

            Config.save_workspace_config(workspace_config)

            return {
                "success": True,
                "message": "User preferences saved to workspace config",
                "updated_preferences": preferences,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
