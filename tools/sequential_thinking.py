#!/usr/bin/env python3
"""
Sequential thinking tool for the travel agent MCP server.
Provides step-by-step reasoning and planning capabilities.
"""

import json
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Store thought history
thought_history = []
thought_branches = {}


def register_sequential_thinking_tool(app: FastMCP):
    """Register the sequential thinking tool with the FastMCP app."""

    @app.tool()
    def sequential_thinking(
        thought: str,
        thoughtNumber: int,
        totalThoughts: int,
        nextThoughtNeeded: bool,
        isRevision: bool = False,
        revisesThought: int = None,
        branchFromThought: int = None,
        branchId: str = None,
        needsMoreThoughts: bool = False,
    ):
        """
        Facilitates detailed, step-by-step thinking process for problem-solving and analysis.

        Args:
            thought: The current thinking step
            thoughtNumber: Current thought number
            totalThoughts: Estimated total thoughts needed
            nextThoughtNeeded: Whether another thought step is needed
            isRevision: Whether this revises previous thinking
            revisesThought: Which thought is being reconsidered
            branchFromThought: Branching point thought number
            branchId: Branch identifier
            needsMoreThoughts: If more thoughts are needed
        """
        thought_data = {
            "thought": thought,
            "thoughtNumber": thoughtNumber,
            "totalThoughts": totalThoughts,
            "nextThoughtNeeded": nextThoughtNeeded,
            "isRevision": isRevision,
            "revisesThought": revisesThought,
            "branchFromThought": branchFromThought,
            "branchId": branchId,
            "needsMoreThoughts": needsMoreThoughts,
            "timestamp": datetime.now().isoformat(),
        }
        if branchId:
            if branchFromThought:
                if branchId not in thought_branches:
                    branch_from_index = next(
                        (
                            i
                            for i, t in enumerate(thought_history)
                            if t["thoughtNumber"] == branchFromThought
                        ),
                        None,
                    )

                    if branch_from_index is not None:
                        thought_branches[branchId] = thought_history[
                            : branch_from_index + 1
                        ].copy()
                    else:
                        thought_branches[branchId] = []

            if branchId in thought_branches:
                if isRevision and revisesThought:
                    revise_index = next(
                        (
                            i
                            for i, t in enumerate(thought_branches[branchId])
                            if t["thoughtNumber"] == revisesThought
                        ),
                        None,
                    )
                    if revise_index is not None:
                        thought_branches[branchId][revise_index] = thought_data
                else:
                    thought_branches[branchId].append(thought_data)
        else:
            if isRevision and revisesThought:
                revise_index = next(
                    (
                        i
                        for i, t in enumerate(thought_history)
                        if t["thoughtNumber"] == revisesThought
                    ),
                    None,
                )
                if revise_index is not None:
                    thought_history[revise_index] = thought_data
            else:
                thought_history.append(thought_data)

        if isRevision:
            return {
                "success": True,
                "thoughtNumber": thoughtNumber,
                "totalThoughts": totalThoughts,
                "nextThoughtNeeded": nextThoughtNeeded,
                "branches": list(thought_branches.keys()),
                "thoughtHistoryLength": len(thought_history),
                "message": f"Revised thought {revisesThought}.",
            }

        if branchId:
            branch_text = f" (Branch: {branchId})"
        else:
            branch_text = ""

        if nextThoughtNeeded:
            if needsMoreThoughts:
                message = f"Recorded thought {thoughtNumber}/{totalThoughts}{branch_text}. More thoughts will be needed."
            else:
                message = f"Recorded thought {thoughtNumber}/{totalThoughts}{branch_text}. Continue with the next thought."
        else:
            message = f"Recorded final thought {thoughtNumber}/{totalThoughts}{branch_text}. The thinking process is complete."

        return {
            "success": True,
            "thoughtNumber": thoughtNumber,
            "totalThoughts": totalThoughts,
            "nextThoughtNeeded": nextThoughtNeeded,
            "branches": list(thought_branches.keys()),
            "thoughtHistoryLength": len(thought_history),
            "message": message,
        }

    @app.tool()
    def think(thought):
        """
        Legacy simple thinking tool - use sequential_thinking for better reasoning.
        """
        return sequential_thinking(
            thought=thought, thoughtNumber=1, totalThoughts=1, nextThoughtNeeded=False
        )

    @app.tool()
    def create_plan(objective, available_tools=None):
        """
        Create a step-by-step plan for achieving an objective.
        """
        if available_tools is None:
            available_tools = []

        if "travel" in objective.lower() or "trip" in objective.lower():
            plan_steps = [
                {
                    "step": 1,
                    "action": "Assess information completeness",
                    "description": "Check if we have enough details (origin, dates, travelers, preferences) or need to ask clarifying questions",
                    "tools_needed": ["think"],
                    "parallel": False,
                },
                {
                    "step": 2,
                    "action": "Get current date and parse travel dates",
                    "description": "Determine today's date and convert relative dates to specific dates",
                    "tools_needed": ["get_current_date", "parse_travel_dates"],
                    "parallel": False,
                },
                {
                    "step": 3,
                    "action": "Gather core travel information",
                    "description": "Search flights and hotels with available information",
                    "tools_needed": ["search_flights", "search_hotels"],
                    "parallel": True,
                },
                {
                    "step": 4,
                    "action": "Enhance with destination context",
                    "description": "Get weather, cultural info, and practical details",
                    "tools_needed": [
                        "get_weather",
                        "search_wikipedia",
                        "convert_currency",
                    ],
                    "parallel": True,
                },
                {
                    "step": 5,
                    "action": "Create comprehensive itinerary",
                    "description": "Synthesize all information into detailed travel plan",
                    "tools_needed": ["think"],
                    "parallel": False,
                },
            ]
        else:
            plan_steps = [
                {
                    "step": 1,
                    "action": "Analyze objective",
                    "description": f"Break down: {objective}",
                    "tools_needed": ["think"],
                    "parallel": False,
                },
                {
                    "step": 2,
                    "action": "Execute actions",
                    "description": "Use appropriate tools to gather information",
                    "tools_needed": available_tools,
                    "parallel": True,
                },
                {
                    "step": 3,
                    "action": "Synthesize results",
                    "description": "Combine information into final answer",
                    "tools_needed": ["think"],
                    "parallel": False,
                },
            ]

        return {
            "success": True,
            "objective": objective,
            "plan": plan_steps,
            "total_steps": len(plan_steps),
            "estimated_parallel_steps": sum(
                1 for step in plan_steps if step["parallel"]
            ),
            "timestamp": datetime.now().isoformat(),
        }

    @app.tool()
    def verify_plan_progress(plan, completed_steps, current_info=None):
        """
        Verify if we have enough information to continue with the plan.
        """
        if current_info is None:
            current_info = {}

        total_steps = len(plan.get("plan", []))
        completed_count = len(completed_steps)
        progress_percentage = (
            (completed_count / total_steps) * 100 if total_steps > 0 else 0
        )
        next_steps = []
        for step in plan.get("plan", []):
            if step["step"] not in completed_steps:
                next_steps.append(step)
                if not step.get("parallel", False):
                    break

        sufficient_info = True
        missing_info = []
        if "travel" in plan.get("objective", "").lower():
            required_info = ["destination", "dates", "search_results"]
            for req in required_info:
                if req not in current_info:
                    sufficient_info = False
                    missing_info.append(req)

        return {
            "success": True,
            "progress_percentage": progress_percentage,
            "completed_steps": completed_count,
            "total_steps": total_steps,
            "next_steps": next_steps,
            "sufficient_info": sufficient_info,
            "missing_info": missing_info,
            "can_continue": len(next_steps) > 0,
            "plan_complete": completed_count >= total_steps,
            "timestamp": datetime.now().isoformat(),
        }
