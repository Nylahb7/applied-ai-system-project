from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

_DEFAULT_PRIORITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}
_RECURRENCE_INTERVALS = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}


def _to_minutes(time_str: str) -> int:
    hours, minutes = time_str.split(":")
    return int(hours) * 60 + int(minutes)


def _advance_date(date_str: str, recurrence: str) -> str:
    """Compute the next due date for a recurring task. "daily" resolves to
    today + 1 day (the completion date), so a late completion doesn't leave
    the next occurrence stuck in the past; "weekly" advances 7 days from the
    task's own due date instead."""
    if recurrence == "daily":
        return (date.today() + timedelta(days=1)).isoformat()
    interval = _RECURRENCE_INTERVALS[recurrence]
    return (date.fromisoformat(date_str) + interval).isoformat()


def _times_overlap(a: Task, b: Task) -> bool:
    a_start = _to_minutes(a.start_time)
    a_end = a_start + a.duration_minutes
    b_start = _to_minutes(b.start_time)
    b_end = b_start + b.duration_minutes
    return a_start < b_end and b_start < a_end


@dataclass
class Pet:
    name: str
    animal_type: str
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Record a task as belonging to this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task previously added to this pet, if present."""
        self.tasks = [t for t in self.tasks if t is not task]


@dataclass
class Task:
    description: str
    pet: Pet
    time: str
    duration_minutes: int
    priority: str
    start_time: str = "00:00"  # "HH:MM" format
    completed: bool = False
    recurrence: str | None = None  # None, "daily", or "weekly"

    def edit(self, attr: str, value) -> None:
        """Update a single field on this task by name."""
        if not hasattr(self, attr):
            raise AttributeError(f"Task has no attribute '{attr}'")
        setattr(self, attr, value)

    def mark_complete(self) -> Task | None:
        """Flag this task as completed and, for recurring tasks, spin off the
        next occurrence. Returns a new unattached Task (same fields, advanced
        `time`) when `recurrence` is "daily" or "weekly", so the caller can
        schedule it; returns None for one-off tasks."""
        self.completed = True
        if self.recurrence not in _RECURRENCE_INTERVALS:
            return None
        return Task(
            description=self.description,
            pet=self.pet,
            time=_advance_date(self.time, self.recurrence),
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            start_time=self.start_time,
            recurrence=self.recurrence,
        )


@dataclass
class TimeSlot:
    start: str  # "HH:MM" format
    end: str    # "HH:MM" format


@dataclass
class Schedule:
    date: str
    tasks: list = field(default_factory=list)
    time_availabilities: list[TimeSlot] = field(default_factory=list)
    priorities: dict = field(default_factory=dict)

    def add_task(self, task: Task) -> None:
        """Add a task to this schedule, enforcing it falls on this schedule's date
        and doesn't overlap another task already scheduled for the same pet."""
        if task.time != self.date:
            raise ValueError(f"Task time '{task.time}' does not match schedule date '{self.date}'")
        for existing in self.tasks:
            if existing.pet is task.pet and _times_overlap(existing, task):
                raise ValueError(
                    f"Task '{task.description}' overlaps with '{existing.description}' "
                    f"for {task.pet.name} on {self.date}"
                )
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this schedule, if present."""
        self.tasks = [t for t in self.tasks if t is not task]

    def add_time_availability(self, start: str, end: str) -> None:
        """Register a window of free time on this schedule's date."""
        self.time_availabilities.append(TimeSlot(start=start, end=end))

    def generate_plan(self) -> list:
        """Order tasks by priority and fit as many as possible into individual
        available time slots (a task must fit within one slot, not pooled minutes)."""

        def priority_weight(task: Task) -> int:
            return self.priorities.get(
                task.priority, _DEFAULT_PRIORITY_WEIGHTS.get(task.priority, 0)
            )

        ordered_tasks = sorted(self.tasks, key=priority_weight, reverse=True)
        remaining_per_slot = [
            _to_minutes(slot.end) - _to_minutes(slot.start)
            for slot in self.time_availabilities
        ]

        plan = []
        for task in ordered_tasks:
            # Best-fit: place the task in the tightest slot it still fits in,
            # to leave larger slots open for later, bigger tasks.
            best_slot_index = None
            for i, remaining in enumerate(remaining_per_slot):
                if task.duration_minutes <= remaining:
                    if best_slot_index is None or remaining < remaining_per_slot[best_slot_index]:
                        best_slot_index = i
            if best_slot_index is not None:
                plan.append(task)
                remaining_per_slot[best_slot_index] -= task.duration_minutes

        return plan


@dataclass
class Owner:
    name: str
    pets: list = field(default_factory=list)
    schedules: dict[str, Schedule] = field(default_factory=dict)  # keyed by date "YYYY-MM-DD"

    def add_pet(self, pet: Pet) -> None:
        """Register a pet as belonging to this owner."""
        self.pets.append(pet)

    def add_task(self, task: Task) -> None:
        """Add a task for one of this owner's pets, creating a schedule for its date if needed."""
        if task.pet not in self.pets:
            raise ValueError(f"Pet '{task.pet.name}' is not one of this owner's pets")
        if task.time not in self.schedules:
            self.schedules[task.time] = Schedule(date=task.time)
        self.schedules[task.time].add_task(task)
        task.pet.add_task(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from its pet and from the schedule for its date."""
        schedule = self.schedules.get(task.time)
        if schedule is not None:
            schedule.remove_task(task)
        task.pet.remove_task(task)

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets, ordered by date and time."""
        all_tasks = [task for pet in self.pets for task in pet.tasks]
        return sorted(all_tasks, key=lambda t: (t.time, t.start_time))


@dataclass
class Scheduler:
    owner: Owner

    def add_task(self, task: Task) -> None:
        """Add a task via the owner it manages."""
        self.owner.add_task(task)

    def edit_task(self, task: Task, attr: str, value) -> None:
        """Update a single field on an existing task."""
        task.edit(attr, value)

    def complete_task(self, task: Task) -> Task | None:
        """Mark a task complete and, if `task.mark_complete()` produced a next
        occurrence (recurring task), add it to the owner's schedule so it
        shows up in future lookups. Returns that next Task, or None."""
        next_task = task.mark_complete()
        if next_task is not None:
            self.add_task(next_task)
        return next_task

    def remove_task(self, task: Task) -> None:
        """Remove a task via the owner it manages."""
        self.owner.remove_task(task)

    def get_tasks_for_pet(self, pet: Pet) -> list[Task]:
        """Return all tasks belonging to a single pet, ordered by date and time."""
        return sorted(pet.tasks, key=lambda t: (t.time, t.start_time))

    def get_tasks_for_date(self, date: str) -> list[Task]:
        """Return all tasks scheduled for a given date."""
        schedule = self.owner.schedules.get(date)
        return list(schedule.tasks) if schedule else []

    def find_conflicts(self, date: str) -> list[tuple[Task, Task]]:
        """Detect scheduling conflicts on a given date via pairwise comparison:
        check every task against every task after it (O(n^2) over that day's
        tasks) and flag pairs whose start/end times overlap, regardless of
        whether they belong to the same pet or different pets."""
        tasks = self.get_tasks_for_date(date)
        conflicts = []
        for i, a in enumerate(tasks):
            for b in tasks[i + 1:]:
                if _times_overlap(a, b):
                    conflicts.append((a, b))
        return conflicts

    def add_task_safe(self, task: Task) -> str | None:
        """Add a task using a lenient conflict-detection strategy: scan that
        date's existing tasks for a time overlap before adding, so a conflict
        surfaces as a returned warning string instead of a raised exception.
        A same-pet conflict is treated as a hard constraint (a pet can't do
        two things at once) and blocks the add; a different-pet conflict is
        only a soft constraint, so the task is still added alongside the
        warning. Returns None when there's no conflict."""
        conflicts = [t for t in self.get_tasks_for_date(task.time) if _times_overlap(t, task)]
        if not conflicts:
            self.add_task(task)
            return None

        same_pet = next((t for t in conflicts if t.pet is task.pet), None)
        if same_pet is not None:
            return (
                f"Warning: could not add '{task.description}' - it overlaps with "
                f"'{same_pet.description}' for {task.pet.name} on {task.time}."
            )

        self.add_task(task)
        other = conflicts[0]
        return (
            f"Warning: '{task.description}' for {task.pet.name} overlaps with "
            f"'{other.description}' for {other.pet.name} on {task.time}."
        )

    def get_all_tasks(self) -> list[Task]:
        """Return every task across all of the owner's pets."""
        return self.owner.get_all_tasks()

    def sort_by_time(self) -> list[Task]:
        """Return every task across all of the owner's pets, sorted ascending
        by their `time` (date) attribute via a standard key-based sort."""
        return sorted(self.owner.get_all_tasks(), key=lambda t: t.time)

    def filter_tasks(self, pet_name: str, completed: bool) -> list[Task]:
        """Return tasks matching both a pet name and a completion status,
        via a single linear scan over every task with an AND predicate."""
        return [
            task for task in self.owner.get_all_tasks()
            if task.pet.name == pet_name and task.completed == completed
        ]

    def generate_plan_for_date(self, date: str) -> list[Task]:
        """Build the prioritized, time-fitted plan for a given date."""
        schedule = self.owner.schedules.get(date)
        return schedule.generate_plan() if schedule else []