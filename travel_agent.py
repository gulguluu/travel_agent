#!/usr/bin/env python3
import warnings

warnings.filterwarnings("ignore")
import asyncio
import json
import os
import sys
from datetime import datetime

from dateutil.parser import parse as dateparse
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.workflow import StartEvent, StopEvent, Workflow, step
from llama_index.llms.openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from config import Config
from utils.date_utils import infer_future_date
from utils.performance_tracker import track_performance
from utils.prompt_loader import SYSTEM_PROMPT, load_prompt

console = Console()


def _build_llm():
    api_key = Config.get_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY or OPENROUTER_API_KEY environment variable not set."
        )
    if Config.OPENROUTER_API_KEY:
        return OpenAI(
            model=Config.OPENROUTER_MODEL,
            api_key=Config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.1,
        )
    else:
        return OpenAI(
            model="gpt-4o-mini", api_key=Config.OPENAI_API_KEY, temperature=0.1
        )


async def _list_tools_for_openai(base_url):
    transport = StreamableHttpTransport(url=f"{base_url}/mcp")
    async with Client(transport) as client:
        tools = await client.list_tools()
        openai_tools = []
        for t in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema
                        or {"type": "object", "properties": {}},
                    },
                }
            )
        return openai_tools


async def _call_tool(base_url, tool_name, args):
    transport = StreamableHttpTransport(url=f"{base_url}/mcp")
    async with Client(transport) as client:
        result_obj = await client.call_tool(tool_name, args)
        if (
            hasattr(result_obj, "structured_content")
            and result_obj.structured_content
            and "result" in result_obj.structured_content
        ):
            result = result_obj.structured_content["result"]
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return result
            return result
        if hasattr(result_obj, "content") and result_obj.content:
            if isinstance(result_obj.content, list) and len(result_obj.content) > 0:
                first_content = result_obj.content[0]
                if hasattr(first_content, "text"):
                    content = first_content.text
                    if isinstance(content, str) and content.strip().startswith("{"):
                        try:
                            return json.loads(content)
                        except json.JSONDecodeError:
                            return content
                    return content
                return str(first_content)
            return result_obj.content
        if (
            hasattr(result_obj, "content")
            and isinstance(result_obj.content, list)
            and len(result_obj.content) == 0
        ):
            return []
        if not hasattr(result_obj, "is_error") or result_obj.is_error:
            console.print(
                f"[bold red]Warning: Unexpected tool result structure for {tool_name}: {result_obj}[/bold red]"
            )
        return {
            "error": "Failed to parse tool result from MCP server",
            "data": str(result_obj),
        }


async def store_conversation_memory(base_url, user_query, agent_response):
    """Store conversation context in memory."""
    memory_data = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query,
        "agent_response": agent_response,
        "conversation_type": "travel_planning",
    }

    try:
        await _call_tool(
            base_url,
            "store_travel_memory",
            {
                "key": f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "data": memory_data,
            },
        )
    except Exception as e:
        console.print(f"[yellow]Warning: Could not store memory: {e}[/yellow]")


async def get_conversation_history(base_url):
    """Retrieve recent conversation history from memory."""
    try:
        memories = await _call_tool(base_url, "list_travel_memories", {})
        if isinstance(memories, list):
            return memories[-5:]  # Get last 5 conversations
        return []
    except Exception:
        return []


async def _execute_tool_call(tool_call, base_url: str, perf_tracker, workflow):
    """Helper function to execute a single tool call."""
    tool_name = tool_call.function.name
    try:
        tool_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        tool_args = {}

    console.print(
        f"[bold cyan]Action:[/bold cyan] Calling [bold]{tool_name}[/bold] with {tool_args}"
    )

    try:
        with console.status(f"[bold green]Executing {tool_name}..."):
            perf_tracker.add_tool_call()
            tool_result = await _call_tool(base_url, tool_name, tool_args)
        console.print(f"[green]{tool_name} completed.[/green]")

        display_result = workflow._filter_tool_result(tool_result, display_only=True)
        console.print(
            Panel(
                json.dumps(display_result, indent=2),
                title=f"[green]Result from {tool_name}[/green]",
                border_style="green",
                expand=False,
            )
        )

        filtered_result = workflow._filter_tool_result(tool_result)
        return ChatMessage(
            role=MessageRole.TOOL,
            content=json.dumps(filtered_result),
            additional_kwargs={"tool_call_id": tool_call.id},
        )
    except Exception as e:
        perf_tracker.add_error()
        console.print(f"[red]{tool_name} failed: {e}[/red]")
        error_message = f"Error executing tool {tool_name}: {e}"
        return ChatMessage(
            role=MessageRole.TOOL,
            content=json.dumps({"error": error_message}),
            additional_kwargs={"tool_call_id": tool_call.id},
        )


class InteractiveTravelWorkflow(Workflow):
    def __init__(self, base_url, llm, conversation_history: list, max_calls=15):
        super().__init__(timeout=600, verbose=True)
        self.base_url = base_url
        self.llm = llm
        self.conversation_history = conversation_history
        self.max_calls = max_calls

    def _filter_tool_result(self, tool_result, display_only=False):
        """Filter tool results to prevent context poisoning or for clean display."""
        if not isinstance(tool_result, dict):
            return (
                str(tool_result)[:500]
                if len(str(tool_result)) > 500
                else str(tool_result)
            )

        filtered = {}
        for key, value in tool_result.items():
            is_base64 = "base64" in key.lower()
            is_long_str = isinstance(value, str) and len(value) > 2000

            if is_base64:
                if display_only:
                    continue  # Skip for display
                else:
                    filtered[key] = "[image data removed]"
            elif is_long_str:
                if display_only:
                    filtered[key] = f"[truncated string, {len(value)} chars]"
                else:
                    filtered[key] = value[:2000] + "...[truncated]"
            else:
                filtered[key] = value
        return filtered

    @step
    async def process_interactive_query(self, _: StartEvent) -> StopEvent:
        """Orchestrates the agent's Plan-and-Execute workflow."""
        async with track_performance(
            self.conversation_history[-1].content
        ) as perf_tracker:
            openai_tools = await _list_tools_for_openai(self.base_url)
            console.print(f"[dim]Available tools: {len(openai_tools)}[/dim]")
            is_follow_up = len(self.conversation_history) > 1
            if is_follow_up:
                console.print(
                    "\n[bold yellow]--- Agent Turn: Continuing Conversation ---[/bold yellow]"
                )
                messages = [
                    ChatMessage(
                        role=MessageRole.SYSTEM, content=load_prompt(SYSTEM_PROMPT)
                    ),
                    *self.conversation_history,
                    ChatMessage(
                        role=MessageRole.USER,
                        content="Continue helping with this travel request based on the conversation history.",
                    ),
                ]

                with console.status("[bold yellow]Processing your request..."):
                    perf_tracker.add_api_call()
                    response = self.llm.chat(messages, tools=openai_tools)

                response_message = response.message
                tool_calls = response_message.additional_kwargs.get("tool_calls", [])

                if tool_calls:
                    messages.append(response_message)
                    tool_results = await asyncio.gather(
                        *(
                            _execute_tool_call(tc, self.base_url, perf_tracker, self)
                            for tc in tool_calls
                        )
                    )
                    messages.extend(tool_results)
                    final_response = self.llm.chat(messages)
                    response_message = final_response.message
                perf_tracker.print_summary()
                await store_conversation_memory(
                    self.base_url,
                    self.conversation_history[-1].content,
                    response_message.content,
                )
                return StopEvent(result=response_message.content)
            console.print(
                "\n[bold yellow]--- Agent Turn: Query Evaluation ---[/bold yellow]"
            )
            evaluation_messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM, content=load_prompt(SYSTEM_PROMPT)
                ),
                *self.conversation_history,
                ChatMessage(
                    role=MessageRole.USER,
                    content="Evaluate this travel request. Make reasonable assumptions where information is missing (e.g., assume Portland PDX for origin if not specified, assume 2 weeks duration, assume 2 travelers). Only ask questions if the request is completely ambiguous. Follow the 'Be Proactive and Make Assumptions' principle from your instructions.",
                ),
            ]

            with console.status("[bold yellow]Evaluating request completeness..."):
                perf_tracker.add_api_call()
                evaluation_response = self.llm.chat(
                    evaluation_messages, tools=openai_tools
                )

            evaluation_message = evaluation_response.message
            evaluation_tool_calls = evaluation_message.additional_kwargs.get(
                "tool_calls", []
            )
            if evaluation_tool_calls:
                evaluation_messages.append(evaluation_message)
                tool_results = await asyncio.gather(
                    *(
                        _execute_tool_call(tc, self.base_url, perf_tracker, self)
                        for tc in evaluation_tool_calls
                    )
                )
                evaluation_messages.extend(tool_results)
                evaluation_response = self.llm.chat(
                    evaluation_messages, tools=openai_tools
                )
                evaluation_message = evaluation_response.message
            if evaluation_message.content and any(
                word in evaluation_message.content.lower()
                for word in [
                    "need to know",
                    "clarify",
                    "question",
                    "missing",
                    "where",
                    "when",
                    "how many",
                ]
            ):
                perf_tracker.print_summary()
                await store_conversation_memory(
                    self.base_url,
                    self.conversation_history[-1].content,
                    evaluation_message.content,
                )
                return StopEvent(result=evaluation_message.content)
            console.print(
                "\n[bold yellow]--- Agent Turn: Travel Planning Clarification ---[/bold yellow]"
            )
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM, content=load_prompt(SYSTEM_PROMPT)
                ),
                *self.conversation_history,
                ChatMessage(
                    role=MessageRole.USER,
                    content="Based on the travel request, please ask any clarifying questions about preferences (budget, accommodation type, activities, etc.) and confirm your assumptions about dates, travelers, and destinations. Be concise and helpful.",
                ),
            ]

            with console.status("[bold yellow]Preparing clarifying questions..."):
                perf_tracker.add_api_call()
                clarification_response = self.llm.chat(messages)

            clarification_message = clarification_response.message
            perf_tracker.print_summary()
            await store_conversation_memory(
                self.base_url,
                self.conversation_history[-1].content,
                clarification_message.content,
            )
            return StopEvent(result=clarification_message.content)


async def _amain():
    console.print(
        Panel.fit(
            "[bold green]Interactive Travel Agent with Memory[/bold green]",
            border_style="green",
        )
    )

    base_url = Config.MCP_SERVER_URL
    try:
        with console.status("[bold blue]Checking MCP server..."):
            if not await _list_tools_for_openai(base_url):
                console.print(f"[red]MCP server not found at {base_url}[/red]")
                console.print(
                    f"[dim]Please start the server: 'python mcp_server.py'[/dim]"
                )
                return
        console.print(f"[green]MCP server running at {base_url}[/green]")

        llm = _build_llm()
        conversation_history = []

        while True:
            if not conversation_history:
                # Initial query
                if len(sys.argv) > 1:
                    query = " ".join(sys.argv[1:])
                    console.print(f"[bold blue]Initial Query:[/bold blue] {query}")
                    conversation_history.append(
                        ChatMessage(role=MessageRole.USER, content=query)
                    )
                    wf = InteractiveTravelWorkflow(base_url, llm, conversation_history)
                    result_event = await wf.run()
                    final_answer = (
                        result_event.result
                        if isinstance(result_event, StopEvent)
                        else str(result_event)
                    )
                    conversation_history.append(
                        ChatMessage(role=MessageRole.ASSISTANT, content=final_answer)
                    )
                    console.print(
                        Panel(
                            final_answer,
                            title="[bold green]Travel Agent Response[/bold green]",
                            border_style="green",
                        )
                    )
                    if any(
                        word in final_answer.lower()
                        for word in [
                            "need",
                            "clarify",
                            "question",
                            "provide",
                            "could you",
                            "what are",
                        ]
                    ):
                        console.print(
                            "\n[dim]Continue the conversation by providing the requested information...[/dim]"
                        )
                    else:
                        break
                else:
                    query = Prompt.ask("[bold cyan]>[/bold cyan]")
            else:
                query = Prompt.ask("[bold cyan]>[/bold cyan]")
            if query.strip().lower() in ["quit", "exit", "bye"]:
                break
            if not query.strip():
                continue

            conversation_history.append(
                ChatMessage(role=MessageRole.USER, content=query)
            )
            wf = InteractiveTravelWorkflow(base_url, llm, conversation_history)
            result_event = await wf.run()
            final_answer = (
                result_event.result
                if isinstance(result_event, StopEvent)
                else str(result_event)
            )
            conversation_history.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=final_answer)
            )
            console.print(
                Panel(
                    final_answer,
                    title="[bold green]Travel Plan[/bold green]",
                    border_style="green",
                )
            )

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Exiting agent.[/bold yellow]")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred: {e}[/red]")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(_amain())
