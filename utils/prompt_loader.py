#!/usr/bin/env python3
"""
Prompt loading utilities for the travel agent.
Loads prompts from text files in the prompts directory.
"""

import os


def load_prompt(prompt_name):
    """Load a prompt from the prompts directory."""
    prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
    prompt_file = os.path.join(prompts_dir, f"{prompt_name}.txt")

    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return f"Prompt file not found: {prompt_name}.txt"
    except Exception as e:
        return f"Error loading prompt {prompt_name}: {e}"


def format_prompt(prompt_name, **kwargs):
    """Load and format a prompt with variables."""
    prompt_text = load_prompt(prompt_name)
    try:
        return prompt_text.format(**kwargs)
    except KeyError as e:
        return f"Missing variable in prompt {prompt_name}: {e}"
    except Exception as e:
        return f"Error formatting prompt {prompt_name}: {e}"


SYSTEM_PROMPT = "system_prompt"
FINAL_PLAN_PROMPT = "final_plan_prompt"
