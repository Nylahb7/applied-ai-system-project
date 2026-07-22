from __future__ import annotations

from pawpal_system import Owner, Scheduler, Task

EDITABLE_ATTRS = {"description", "time", "start_time", "duration_minutes", "priority"}
RESCHEDULE_ATTRS = {"time", "start_time", "duration_minutes"}


def _find_task(owner: Owner, task_id: int) -> Task:
    task = Scheduler(owner=owner).get_task_by_id(task_id)
    if task is None:
        raise ValueError(f"No task with id {task_id}")
    return task


def list_tasks(owner: Owner) -> list[dict]:
    """Serialize every task for the model's context."""
    return [
        {
            "id": t.id,
            "pet": t.pet.name,
            "description": t.description,
            "date": t.time,
            "start_time": t.start_time,
            "duration_minutes": t.duration_minutes,
            "priority": t.priority,
            "completed": t.completed,
        }
        for t in owner.get_all_tasks()
    ]


def edit_task(owner: Owner, task_id: int, attr: str, value) -> str:
    if attr not in EDITABLE_ATTRS:
        raise ValueError(f"Cannot edit '{attr}'; editable fields are {sorted(EDITABLE_ATTRS)}")
    task = _find_task(owner, task_id)
    scheduler = Scheduler(owner=owner)

    if attr not in RESCHEDULE_ATTRS:
        task.edit(attr, value)
        return f"Updated '{task.description}' {attr} to {value}."

    # Changing date/start_time/duration affects conflict checking, so pull the
    # task out and re-add it through add_task_safe rather than editing in place.
    scheduler.remove_task(task)
    task.edit(attr, value)
    warning = scheduler.add_task_safe(task)
    if warning:
        return warning
    return f"Moved '{task.description}' to {task.time} at {task.start_time}."


def swap_times(owner: Owner, task_id_a: int, task_id_b: int) -> str:
    task_a = _find_task(owner, task_id_a)
    task_b = _find_task(owner, task_id_b)
    a_time, a_start = task_a.time, task_a.start_time
    b_time, b_start = task_b.time, task_b.start_time

    scheduler = Scheduler(owner=owner)
    scheduler.remove_task(task_a)
    scheduler.remove_task(task_b)

    task_a.edit("time", b_time)
    task_a.edit("start_time", b_start)
    task_b.edit("time", a_time)
    task_b.edit("start_time", a_start)

    warnings = [w for w in (scheduler.add_task_safe(task_a), scheduler.add_task_safe(task_b)) if w]
    if warnings:
        return " ".join(warnings)
    return f"Swapped times for '{task_a.description}' and '{task_b.description}'."


def remove_task(owner: Owner, task_id: int) -> str:
    task = _find_task(owner, task_id)
    Scheduler(owner=owner).remove_task(task)
    return f"Removed '{task.description}'."


def add_task(
    owner: Owner,
    pet_name: str,
    description: str,
    date: str,
    start_time: str,
    duration_minutes: int,
    priority: str,
) -> str:
    pet = next((p for p in owner.pets if p.name == pet_name), None)
    if pet is None:
        raise ValueError(f"No pet named '{pet_name}'")
    task = Task(
        description=description,
        pet=pet,
        time=date,
        duration_minutes=duration_minutes,
        priority=priority,
        start_time=start_time,
    )
    warning = Scheduler(owner=owner).add_task_safe(task)
    if warning:
        return warning
    return f"Added '{description}' for {pet_name} on {date} at {start_time}."


def regenerate_plan(owner: Owner, date: str) -> list[dict]:
    plan = Scheduler(owner=owner).generate_plan_for_date(date)
    return [
        {"id": t.id, "description": t.description, "start_time": t.start_time, "priority": t.priority}
        for t in plan
    ]
