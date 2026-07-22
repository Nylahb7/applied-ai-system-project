from __future__ import annotations

import json

import anthropic

import chat_tools
from pawpal_system import Owner

MODEL = "claude-sonnet-5"
MAX_TOOL_ROUNDS = 6

TOOLS = [
    {
        "name": "edit_task",
        "description": (
            "Change a single field on an existing task: its date, start time, duration, "
            "priority, or description. Use this for 'move X to 9am', 'make X low priority', "
            "'X is actually 45 minutes', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "The id of the task to edit."},
                "attr": {
                    "type": "string",
                    "enum": sorted(chat_tools.EDITABLE_ATTRS),
                    "description": "Which field to change.",
                },
                "value": {
                    "type": "string",
                    "description": (
                        "The new value as a string (e.g. '2026-07-22' for time, '09:00' for "
                        "start_time, '45' for duration_minutes, 'high' for priority)."
                    ),
                },
            },
            "required": ["task_id", "attr", "value"],
        },
    },
    {
        "name": "swap_times",
        "description": "Swap the date/start_time between two existing tasks. Use for 'swap the walk and the feeding'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id_a": {"type": "integer"},
                "task_id_b": {"type": "integer"},
            },
            "required": ["task_id_a", "task_id_b"],
        },
    },
    {
        "name": "remove_task",
        "description": "Delete an existing task.",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "add_task",
        "description": "Create a new task for one of the owner's pets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {"type": "string"},
                "description": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "start_time": {"type": "string", "description": "HH:MM"},
                "duration_minutes": {"type": "integer"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["pet_name", "description", "date", "start_time", "duration_minutes", "priority"],
        },
    },
    {
        "name": "regenerate_plan",
        "description": "Recompute the prioritized, time-fitted plan for a given date after edits.",
        "input_schema": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["date"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are PawPal+'s scheduling assistant. You can move, edit, add, remove, and swap the "
    "pet-care tasks already in the owner's schedule using the tools provided. Always act on "
    "the task list given below rather than assuming tasks exist. When an edit would create a "
    "same-pet conflict, the tool will return a warning explaining why - relay that back to the "
    "user instead of retrying blindly. After making changes, briefly confirm what changed in "
    "plain language."
)


def _run_tool(owner: Owner, name: str, tool_input: dict) -> str:
    if name == "edit_task":
        attr = tool_input["attr"]
        value = tool_input["value"]
        if attr == "duration_minutes":
            value = int(value)
        return chat_tools.edit_task(owner, int(tool_input["task_id"]), attr, value)
    if name == "swap_times":
        return chat_tools.swap_times(owner, int(tool_input["task_id_a"]), int(tool_input["task_id_b"]))
    if name == "remove_task":
        return chat_tools.remove_task(owner, int(tool_input["task_id"]))
    if name == "add_task":
        return chat_tools.add_task(
            owner,
            pet_name=tool_input["pet_name"],
            description=tool_input["description"],
            date=tool_input["date"],
            start_time=tool_input["start_time"],
            duration_minutes=int(tool_input["duration_minutes"]),
            priority=tool_input["priority"],
        )
    if name == "regenerate_plan":
        return json.dumps(chat_tools.regenerate_plan(owner, tool_input["date"]))
    raise ValueError(f"Unknown tool: {name}")


def run_chat(owner: Owner, user_message: str, history: list[dict]) -> tuple[str, list[dict]]:
    """Send `user_message` to Claude with tool access to `owner`'s tasks.

    `history` is a list of {"role": "user"|"assistant", "content": str} text-only turns
    from earlier in the conversation. Returns (reply_text, updated_history).
    """
    client = anthropic.Anthropic()

    tasks_context = json.dumps(chat_tools.list_tasks(owner), indent=2)
    opening = f"Current tasks:\n{tasks_context}\n\nUser request: {user_message}"

    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({"role": "user", "content": opening})

    final_text = ""
    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = next((b.text for b in response.content if b.type == "text"), "")
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                result = _run_tool(owner, block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            except Exception as exc:
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True}
                )
        messages.append({"role": "user", "content": tool_results})
    else:
        final_text = "I made several changes but ran out of turns confirming them - check the task list above."

    updated_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_text},
    ]
    return final_text, updated_history
