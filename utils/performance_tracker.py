#!/usr/bin/env python3
"""
Performance tracking utilities for the travel agent.
Tracks timing, token usage, and API call metrics with context manager support.
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    start_time: float
    end_time: float = 0.0
    duration_seconds: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_calls: int = 0
    tool_calls: int = 0
    errors: int = 0
    query: str = ""

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            **asdict(self),
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time_iso": (
                datetime.fromtimestamp(self.end_time).isoformat()
                if self.end_time
                else None
            ),
            "duration_formatted": f"{self.duration_seconds:.2f}s",
        }


class PerformanceTracker:
    """Context manager for tracking travel agent performance metrics."""

    def __init__(self, query=""):
        self.metrics = PerformanceMetrics(start_time=time.time(), query=query)
        self._log_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "performance_logs.jsonl"
        )

    def add_tokens(self, prompt_tokens=0, completion_tokens=0):
        """Add token usage to metrics."""
        self.metrics.prompt_tokens += prompt_tokens
        self.metrics.completion_tokens += completion_tokens
        self.metrics.total_tokens = (
            self.metrics.prompt_tokens + self.metrics.completion_tokens
        )

    def add_api_call(self):
        """Increment API call counter."""
        self.metrics.api_calls += 1

    def add_tool_call(self):
        """Increment tool call counter."""
        self.metrics.tool_calls += 1

    def add_error(self):
        """Increment error counter."""
        self.metrics.errors += 1

    def finish(self):
        """Finalize metrics and calculate duration."""
        self.metrics.end_time = time.time()
        self.metrics.duration_seconds = self.metrics.end_time - self.metrics.start_time

    def save_to_file(self):
        """Save metrics to JSONL log file."""
        try:
            os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
            with open(self._log_file, "a") as f:
                f.write(json.dumps(self.metrics.to_dict()) + "\n")
        except Exception as e:
            print(f"Warning: Could not save performance metrics: {e}")

    def print_summary(self):
        """Print a formatted summary of performance metrics."""
        from rich.console import Console
        from rich.table import Table

        console = Console()

        table = Table(
            title="Performance Summary", show_header=True, header_style="bold magenta"
        )
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        table.add_row("Duration", f"{self.metrics.duration_seconds:.2f}s")
        table.add_row("Total Tokens", f"{self.metrics.total_tokens:,}")
        table.add_row("Prompt Tokens", f"{self.metrics.prompt_tokens:,}")
        table.add_row("Completion Tokens", f"{self.metrics.completion_tokens:,}")
        table.add_row("API Calls", str(self.metrics.api_calls))
        table.add_row("Tool Calls", str(self.metrics.tool_calls))

        if self.metrics.errors > 0:
            table.add_row("Errors", str(self.metrics.errors), style="red")
        if self.metrics.duration_seconds > 0:
            tokens_per_sec = self.metrics.total_tokens / self.metrics.duration_seconds
            table.add_row("Tokens/sec", f"{tokens_per_sec:.1f}")
        console.print(table)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        self.save_to_file()
        if exc_type:
            self.add_error()


@asynccontextmanager
async def track_performance(query=""):
    """Async context manager for performance tracking."""
    tracker = PerformanceTracker(query)
    try:
        yield tracker
    finally:
        tracker.finish()
        tracker.save_to_file()


def get_performance_stats(days=7):
    """Get performance statistics from recent logs."""
    log_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "performance_logs.jsonl"
    )

    if not os.path.exists(log_file):
        return {"error": "No performance logs found"}

    cutoff_time = time.time() - (days * 24 * 60 * 60)
    stats = {
        "total_queries": 0,
        "avg_duration": 0.0,
        "avg_tokens": 0,
        "total_api_calls": 0,
        "total_tool_calls": 0,
        "total_errors": 0,
    }

    durations = []
    token_counts = []

    try:
        with open(log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get("start_time", 0) >= cutoff_time:
                        stats["total_queries"] += 1
                        durations.append(data.get("duration_seconds", 0))
                        token_counts.append(data.get("total_tokens", 0))
                        stats["total_api_calls"] += data.get("api_calls", 0)
                        stats["total_tool_calls"] += data.get("tool_calls", 0)
                        stats["total_errors"] += data.get("errors", 0)
                except json.JSONDecodeError:
                    continue

        if durations:
            stats["avg_duration"] = sum(durations) / len(durations)
        if token_counts:
            stats["avg_tokens"] = sum(token_counts) / len(token_counts)

    except Exception as e:
        return {"error": f"Could not read performance logs: {e}"}

    return stats
