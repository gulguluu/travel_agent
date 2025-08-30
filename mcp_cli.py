#!/usr/bin/env python3
"""
CLI interface for MCP server management.
Provides start, stop, logs, and status commands.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class MCPServerCLI:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.log_file = self.project_root / "logs" / "mcp_server.log"
        self.pid_file = self.project_root / "logs" / "mcp_server.pid"
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def start_server(self):
        """Start the MCP server in background."""
        if self.is_server_running():
            print("MCP server is already running")
            return

        print("Starting MCP server...")

        # Start server process in background
        cmd = [sys.executable, "mcp_server.py", "--daemon"]
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=open(self.log_file, "a"),
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )

        # Save PID
        with open(self.pid_file, "w") as f:
            f.write(str(process.pid))

        # Wait a moment to check if it started successfully
        time.sleep(2)
        if self.is_server_running():
            print(f"MCP server started successfully (PID: {process.pid})")
            print(f"Logs: {self.log_file}")
            print("Use 'python mcp_cli.py logs' to view live logs")
        else:
            print("Failed to start MCP server")

    def stop_server(self):
        """Stop the MCP server."""
        if not self.is_server_running():
            print("MCP server is not running")
            return

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())

            print(f"Stopping MCP server (PID: {pid})...")

            # Send SIGTERM to process group
            os.killpg(os.getpgid(pid), signal.SIGTERM)

            # Wait for graceful shutdown
            for _ in range(10):
                if not self.is_server_running():
                    break
                time.sleep(0.5)

            # Force kill if still running
            if self.is_server_running():
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                time.sleep(1)

            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()

            print("MCP server stopped")

        except (FileNotFoundError, ProcessLookupError, ValueError):
            print("Could not stop server (PID file invalid or process not found)")
            if self.pid_file.exists():
                self.pid_file.unlink()

    def show_logs(self, follow=True):
        """Show server logs."""
        if not self.log_file.exists():
            print("No log file found. Start the server first.")
            return

        if follow:
            print(f"Streaming logs from {self.log_file}")
            print("Press Ctrl+C to stop viewing logs")
            print("-" * 60)

            try:
                # Show last 20 lines first
                with open(self.log_file, "r") as f:
                    lines = f.readlines()
                    for line in lines[-20:]:
                        print(line.rstrip())

                # Follow new lines
                self._tail_file(self.log_file)

            except KeyboardInterrupt:
                print("\nStopped viewing logs")
        else:
            # Just show recent logs
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                for line in lines[-50:]:
                    print(line.rstrip())

    def _tail_file(self, file_path):
        """Tail a file like 'tail -f'."""
        with open(file_path, "r") as f:
            # Go to end of file
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    print(line.rstrip())
                else:
                    time.sleep(0.1)

    def show_status(self):
        """Show server status."""
        if self.is_server_running():
            with open(self.pid_file, "r") as f:
                pid = f.read().strip()
            print(f"MCP server is running (PID: {pid})")
            print(f"Log file: {self.log_file}")
        else:
            print("MCP server is not running")

    def is_server_running(self):
        """Check if server is running."""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)
            return True

        except (FileNotFoundError, ValueError, ProcessLookupError):
            # Clean up stale PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False


def main():
    parser = argparse.ArgumentParser(description="MCP Server CLI")
    parser.add_argument(
        "command",
        choices=["start", "stop", "logs", "status"],
        help="Command to execute",
    )
    parser.add_argument(
        "--no-follow", action="store_true", help="Don't follow logs (for logs command)"
    )

    args = parser.parse_args()
    cli = MCPServerCLI()

    if args.command == "start":
        cli.start_server()
    elif args.command == "stop":
        cli.stop_server()
    elif args.command == "logs":
        cli.show_logs(follow=not args.no_follow)
    elif args.command == "status":
        cli.show_status()


if __name__ == "__main__":
    main()
