# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```
Today's Schedule (2026-07-06):
  - [Mochi] Morning walk (20 min, high)

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
=============================== test session starts ================================
platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Nylah\OneDrive\AI110\ai110-module2show-pawpal-starter
plugins: anyio-4.14.0
collected 16 items                                                                  

tests\test_pawpal.py ................                                         [100%]

================================ 16 passed in 0.04s ================================

The suite's 16 tests exercise recurring-task completion, conflict detection, sort/filter consistency, and priority-driven plan generation — targeting edge cases like boundary-adjacent time slots, cross-pet vs. same-pet conflicts, and duplicate pet names that the original two tests didn't cover.

**Confidence Level**
5 stars
```

## 📐 Smarter Scheduling

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()` | Sorts every task across all pets ascending by its `time` (date) attribute |
| Filtering | `Scheduler.filter_tasks()` | Filters tasks by pet name and completion status (`completed` True/False) |
| Conflict handling | `Scheduler.find_conflicts()`, `Scheduler.add_task_safe()` | `find_conflicts()` detects any overlapping tasks on a date (same or different pet); `add_task_safe()` blocks same-pet overlaps and warns (instead of raising) on different-pet overlaps |
| Recurring tasks | `Task.mark_complete()`, `Scheduler.complete_task()` | Completing a `"daily"`/`"weekly"` task spins off and schedules its next occurrence automatically |

## 📸 Demo Walkthrough

### UI features

The Streamlit app (`app.py`) lets a user:

- Enter an owner name, pet name, and species to create the owner/pet in session state
- Add a task with a title, start time, duration, and priority (low/medium/high)
- View that pet's tasks in a table, always sorted by date/time
- Filter the task list to All / Completed / Incomplete
- Check today's tasks for scheduling conflicts (overlapping times, same or different pet)
- Set an available time window and generate a prioritized daily plan, seeing which tasks were scheduled and which didn't fit

### Example workflow

1. Enter owner "Jordan" and pet "Mochi" (a dog).
2. Add a task — "Morning walk", 08:00, 20 minutes, high priority. It's added and shown in the task table.
3. Add a second task for the same time slot, e.g. "Vet checkup" at 08:00 — `add_task_safe` detects the overlap and returns a warning instead of silently double-booking Mochi.
4. Switch the filter to "Incomplete" to confirm both tasks show up, then mark one complete to see it move under "Completed".
5. Set an available window (e.g. 08:00–10:00) and click "Generate schedule" — the scheduler sorts tasks by priority and fits as many as possible into the window, reporting any that didn't fit.

### Key Scheduler behaviors shown

- **Sorting** — `get_tasks_for_pet` / `sort_by_time` always return tasks ordered by date and start time, regardless of the order they were entered.
- **Conflict warnings** — `find_conflicts` flags any overlapping tasks on a given date; `add_task_safe` blocks a same-pet overlap outright and warns (but still adds) a different-pet overlap.
- **Priority-driven planning** — `generate_plan_for_date` orders tasks by priority weight and best-fits them into the day's available time slots.

### Sample CLI output (`main.py`)

```
Today's Schedule (2026-07-06):
  - [Mochi] Morning walk (20 min, high)

All tasks sorted by time:
  - 2026-07-06 [Mochi] Morning walk
  - 2026-07-07 [Luna] Feed dinner
  - 2026-07-08 [Mochi] Vet checkup

Mochi's completed tasks:
  - 2026-07-06 Morning walk

Mochi's incomplete tasks:
  - 2026-07-08 Vet checkup

Attempting to add a conflicting task:
  Warning: 'Groom Luna' for Luna overlaps with 'Vet checkup' for Mochi on 2026-07-08.

Conflicts detected on 2026-07-08:
  - 'Vet checkup' overlaps with 'Groom Luna'
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
