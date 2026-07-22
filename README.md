# PawPal+

## Original Project (Modules 1–3): PawPal+

This project builds on **PawPal+**, the Streamlit pet-care scheduler I designed and built in Modules 1–3. The original goal was to help a busy pet owner track care tasks (walks, feeding, meds, grooming) and turn them into a conflict-free daily plan. It let an owner register pets and tasks (with duration and priority), then used a `Scheduler`/`Owner`/`Schedule` domain model to sort tasks by time, detect same-pet vs. cross-pet scheduling conflicts, and generate a priority-ordered plan that best-fits tasks into the owner's available time windows. All of that logic was covered by an automated `pytest` suite before it was ever wired into the UI.

## Title and Summary

**PawPal+** is a Streamlit app for planning pet-care tasks, now extended with an AI chat assistant ("Ask PawPal") that lets an owner restructure their schedule in plain English instead of clicking through forms. It matters because scheduling is inherently fiddly — moving one task can create a conflict with another — and a natural-language interface lets the owner say "move the walk to 9am" or "swap the walk and the feeding" and get the same validated, conflict-checked result they'd get by hand, with the reasoning explained back to them.

## Architecture Overview

The system (see [`diagrams/architecture.mmd`](diagrams/architecture.mmd)) is split into four layers:

- **UI (`app.py`)** — a Streamlit app with two tabs: **Tasks**, for direct manual add/edit/remove/complete actions, and **Ask PawPal**, a chat box for natural-language requests.
- **AI layer (`chatbot.py`)** — sends the user's message plus the current task list to Claude (Sonnet 5) along with a fixed set of tool definitions (`edit_task`, `add_task`, `swap_times`, `remove_task`, `regenerate_plan`). Claude decides which tool(s), if any, to call, and the loop runs for up to 6 tool rounds before returning a plain-language reply.
- **Tool bridge (`chat_tools.py`)** — thin functions that translate each tool call into calls against the core domain objects and return either a confirmation string or a warning string (never a raw exception) so Claude can relay outcomes back to the user.
- **Core domain logic (`pawpal_system.py`)** — the original `Owner`/`Pet`/`Task`/`Schedule`/`Scheduler` classes from Modules 1–3, unchanged in their conflict rules: same-pet time conflicts are a hard rule (blocked outright), cross-pet conflicts are a soft rule (added, with a warning).

Critically, both the Tasks tab and the chat tab mutate the *same* `Owner`/`Scheduler` objects. That means every AI-driven change shows up immediately in the Tasks tab, any conflict warning the domain logic raises gets relayed back through the chat, and the owner can always undo or edit an AI-made change by hand — the human stays in the loop on every write, not just the ones they typed manually.

## Setup Instructions

1. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set your Anthropic API key** (required for the Ask PawPal tab; the Tasks tab works without it)
   ```bash
   export ANTHROPIC_API_KEY=your-key-here   # Windows: set ANTHROPIC_API_KEY=your-key-here
   ```
4. **Run the Streamlit app**
   ```bash
   streamlit run app.py
   ```
5. **Run the CLI demo** (no API key needed — exercises the domain logic directly)
   ```bash
   python main.py
   ```
6. **Run the test suite**
   ```bash
   pytest
   ```

## Sample Interactions

**1. Moving a task by natural language**

> **User:** move the walk to 9am
>
> **PawPal:** Moved 'Morning walk' to 2026-07-21 at 09:00.

Behind the scenes, Claude called `edit_task(task_id=1, attr="start_time", value="09:00")`; `chat_tools.edit_task` pulled the task out, updated it, and re-added it through `add_task_safe`, which found no conflict.

**2. A request that would create a conflict**

> **User:** move the vet checkup to 8am too
>
> **PawPal:** I tried to move 'Vet checkup' to 08:00, but that overlaps with 'Morning walk' for Mochi at that time, so I left it where it was. Want me to pick a different time instead?

Here `add_task_safe` detected a same-pet overlap (a hard constraint) and returned a warning string instead of applying the change; Claude relayed that warning in plain language rather than retrying blindly, per its system prompt.

**3. A compound request**

> **User:** swap the walk and the feeding, and add a 10 minute grooming session for Luna at 5pm, low priority
>
> **PawPal:** Swapped times for 'Morning walk' and 'Feed dinner', and added 'Grooming' for Luna on 2026-07-21 at 17:00.

This took two tool calls in the same turn (`swap_times` then `add_task`) — the loop in `chatbot.py` supports up to 6 tool rounds so multi-step requests like this resolve in one exchange.

## Design Decisions

- **Tool use over free-form generation.** Claude never edits the schedule directly — it can only call a fixed set of tools with a JSON schema. This keeps every change routed through the same validated domain logic (`Scheduler`, `add_task_safe`) that the manual UI uses, so the AI can't produce a state the hand-built forms couldn't also produce.
- **Warnings as strings, not exceptions.** Tool functions in `chat_tools.py` return a warning string on conflict rather than raising, so a blocked or flagged edit becomes something Claude can read and explain, instead of crashing the tool-use loop.
- **Shared mutable state, not a separate AI-only model.** The chat tools operate on the exact same `Owner` object as the Tasks tab. The trade-off is less isolation (a buggy tool call touches real data immediately), but it guarantees the human always sees — and can override — anything the AI did, in the same view they already trust.
- **A capped tool-use loop (6 rounds).** Bounding the loop avoids a runaway back-and-forth if Claude keeps calling tools without converging; the trade-off is that a very long compound request could hit the cap and return a partial-progress message instead of finishing silently.
- **String-typed tool inputs for `edit_task`.** All edit values arrive as strings and get cast internally (e.g. `int()` for `duration_minutes`) rather than using per-attribute schemas. This keeps one generic tool instead of five near-duplicate ones, at the cost of pushing type-coercion into `chatbot.py` instead of the schema itself.
- **No persistence layer.** Both the manual and AI-driven schedule live only in Streamlit's `session_state` for the session. This kept the project scoped to scheduling logic and the AI integration rather than a database layer, at the cost of losing all data on refresh.

## Testing Summary

**What worked:** The 30-test `pytest` suite (`tests/test_pawpal.py`, `tests/test_chat_tools.py`) covers the domain logic and the tool bridge fully offline, with no API calls involved: sorting, filtering, same-pet vs. cross-pet conflict detection, recurring-task rollover, priority-driven plan generation, and every `chat_tools` function's success and warning paths. Because these run without hitting Claude, they verify the exact logic the AI is allowed to trigger, independent of whether the model calls it correctly.

**What didn't (or wasn't tested):** There's no automated coverage of `chatbot.py` itself — the actual Claude tool-selection behavior (does it pick `swap_times` vs. two `edit_task` calls for "swap X and Y"?) was verified manually by running the app and trying different phrasings, not by a repeatable test. Multi-pet plan generation in a single `generate_plan()` call also remains untested, carried over as a known gap from the original Module 2 project.

**What I learned:** Testing the deterministic tool layer separately from the non-deterministic model layer was the right split — it let me be fully confident in what happens *if* a tool gets called correctly, while treating "does the model call the right tool" as a manual, exploratory concern instead of trying to write brittle assertions against LLM output.

## Reflection

Extending PawPal+ with a chat interface reframed the original scheduling problem: instead of "how do I compute a valid plan," the question became "how do I expose a small, safe set of actions that an LLM can compose to reach the same valid plans a human would reach by hand." Keeping the AI confined to the same validated tool calls the UI already used turned out to be the key design choice — it meant trusting the model's *judgment* about what to do, while never trusting it to bypass the rules about *whether* a change is allowed.
