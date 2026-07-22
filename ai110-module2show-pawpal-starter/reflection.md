# PawPal+ Project Reflection

## 1. System Design
- add a pet
- add a task
- see today's tasks

**a. Initial design**

My initial UML design included four classes: `Owner`, `Pet`, `Task`, and `Schedule`.

- **Owner** — represents the person using the app. It stores the owner's name and holds a list of their pets. It connects a person to both their pets and their schedule.
- **Pet** — represents an individual animal. It stores the pet's name and species (`animal_type`).
- **Task** — represents a single care activity (e.g., a walk or feeding). It stores the task type, which pet it belongs to, which day it falls on, how long it takes (`duration_minutes`), and its priority level. It also has an `edit()` method to update individual fields after creation.
- **Schedule** — the core organizing class. It holds a date, the list of tasks to consider, the owner's available time windows (`time_availabilities`), and priority weights. Its methods allow tasks and availability to be added incrementally, and `generate_plan()` produces the final ordered list of tasks that fit within the owner's constraints.


**b. Design changes**

- Did your design change during implementation? yes
- If yes, describe at least one change and why you made it.
    Task.edit field parameter renamed: field shadowed dataclasses.field and could cause a runtime error 
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
    Time (a pet can't have two overlapping tasks), priority (high/medium/low, weighted 3/2/1 by default but overridable per-schedule via `priorities`), and available time windows (`time_availabilities`) that cap how many tasks can actually run on a given day.
- How did you decide which constraints mattered most?
    By splitting them into hard vs. soft constraints. Same-pet double-booking is physically impossible, so it's enforced everywhere — `Schedule.add_task` raises, and `Scheduler.add_task_safe` blocks it with a warning instead of adding. Everything else (a cross-pet overlap, or a lower-priority task not fitting in the available window) is a soft constraint: it produces a warning or gets silently dropped from the plan rather than blocking anything.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
    Schedule.generate_plan() sorts taks by priority weight, then, for each task, places it into the smallest slot it can fit in rather than searching for the "optimal" arrangement
- Why is that tradeoff reasonable for this scenario?
    Priority tasks will always get first pick of slots and best-fir avoids wasting a large open slot on a tiny task.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
    Used AI throughout: talking through the initial UML/class design, converting that UML into Python class skeletons, implementing the sorting/filtering/conflict-detection/scheduling logic, and writing the automated test suite.
- What kinds of prompts or questions were most helpful?
    Asking it to surface edge cases before writing tests (e.g., "what happens at the exact boundary between two time slots?", "what if two pets have the same name?") rather than just asking it to "write tests" — that's what led to the boundary-adjacent and duplicate-pet-name tests.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
    The generated `Task.edit()` method originally named its parameter `field`, which shadowed the `dataclasses.field` import used elsewhere in the same module. I caught this during review and renamed the parameter to `attr` instead of leaving the suggestion as-is, since the shadowing could cause a confusing runtime error later.
- How did you evaluate or verify what the AI suggested?
    Read the generated code closely for naming collisions with existing imports, and ran the test suite after each change to confirm behavior rather than trusting the diff on sight.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
    16 tests covering: recurring-task completion (a daily task rolls to today + 1 day while a weekly task rolls 7 days from its own due date, an unsupported recurrence returns `None`, and completing a recurring task twice chains two future occurrences); conflict detection (tasks that share an exact boundary don't conflict, `find_conflicts` catches cross-pet overlaps that plain `add_task` allows, and `add_task_safe` blocks same-pet conflicts but allows cross-pet ones with a warning); sorting (`sort_by_time` agrees with `get_all_tasks`'s ordering thanks to Python's stable sort); plan generation (a task that fits no slot is dropped, a task that exactly matches a slot's length is included, and custom priority weights change which task wins a single-slot day); and filtering (matching by pet name across two distinct `Pet` objects that happen to share a name).
- Why were these tests important?
    They target exactly the spots where an off-by-one or a wrong assumption would silently produce a wrong schedule — boundary math in the time-overlap check, and object identity vs. equality when two pets can share a name.

**b. Confidence**

- How confident are you that your scheduler works correctly?
    Fairly confident in the core logic — sorting, filtering, conflict detection, and plan generation all have direct tests for their known edge cases. Less confident about scenarios the tests don't touch yet, like multiple pets' tasks being planned together in one `generate_plan()` call.
- What edge cases would you test next if you had more time?
    Multi-pet plans generated in a single call, overlapping `time_availabilities` on the same day, and a day with more tasks than slots where best-fit vs. first-fit would actually pick different tasks to drop.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
    The conflict-detection design — splitting same-pet conflicts (hard, blocked) from cross-pet conflicts (soft, warned) maps cleanly onto how pet care actually works: one pet can't be in two places, but two different pets' care can still legitimately overlap if the owner chooses to allow it.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
    I'd redesign `generate_plan()` to consider all of a day's tasks across every pet at once with a proper bin-packing approach, instead of the current single-pass greedy best-fit, so a lower-priority task that fits a slot perfectly doesn't lose out to a marginally higher-priority task that wastes most of that slot.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
    Small naming or equality decisions — like a parameter named `field` shadowing `dataclasses.field`, or `Task.__eq__` recursing through `Pet.__eq__` — are the kind of bug that only surfaces once you write tests that actually exercise object identity. Reviewing AI-generated code for structure isn't enough; you have to run it and try to break it.
