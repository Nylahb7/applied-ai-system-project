import pytest

import chat_tools
from pawpal_system import Owner, Pet, Scheduler, Task


def _owner_with_task(start_time="08:00", duration=20, priority="high", pet_name="Milo"):
    owner = Owner(name="Sam")
    pet = Pet(name=pet_name, animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)
    task = Task(
        description="Morning walk", pet=pet, time="2026-07-06",
        duration_minutes=duration, priority=priority, start_time=start_time,
    )
    scheduler.add_task(task)
    return owner, pet, task


def test_list_tasks_serializes_fields():
    owner, pet, task = _owner_with_task()
    [entry] = chat_tools.list_tasks(owner)
    assert entry == {
        "id": task.id,
        "pet": "Milo",
        "description": "Morning walk",
        "date": "2026-07-06",
        "start_time": "08:00",
        "duration_minutes": 20,
        "priority": "high",
        "completed": False,
    }


def test_edit_task_non_schedule_attr_updates_in_place():
    owner, pet, task = _owner_with_task()
    result = chat_tools.edit_task(owner, task.id, "priority", "low")
    assert task.priority == "low"
    assert "Updated" in result


def test_edit_task_reschedule_moves_task():
    owner, pet, task = _owner_with_task()
    result = chat_tools.edit_task(owner, task.id, "start_time", "09:00")
    assert task.start_time == "09:00"
    assert "Moved" in result
    assert task in owner.schedules["2026-07-06"].tasks


def test_edit_task_reschedule_blocks_same_pet_conflict():
    owner, pet, task = _owner_with_task(start_time="08:00")
    scheduler = Scheduler(owner=owner)
    other = Task(
        description="Vet checkup", pet=pet, time="2026-07-06",
        duration_minutes=20, priority="medium", start_time="09:00",
    )
    scheduler.add_task(other)

    result = chat_tools.edit_task(owner, task.id, "start_time", "09:00")
    assert "Warning" in result
    assert task.start_time == "09:00"  # attr is mutated even though the add is blocked
    assert task not in owner.schedules["2026-07-06"].tasks


def test_edit_task_rejects_unknown_attr():
    owner, pet, task = _owner_with_task()
    with pytest.raises(ValueError):
        chat_tools.edit_task(owner, task.id, "completed", True)


def test_edit_task_unknown_id_raises():
    owner, pet, task = _owner_with_task()
    with pytest.raises(ValueError):
        chat_tools.edit_task(owner, 9999, "priority", "low")


def test_swap_times_exchanges_start_times():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    walk = Task(
        description="Walk", pet=pet, time="2026-07-06",
        duration_minutes=20, priority="high", start_time="08:00",
    )
    feed = Task(
        description="Feed", pet=pet, time="2026-07-06",
        duration_minutes=15, priority="medium", start_time="09:00",
    )
    scheduler.add_task(walk)
    scheduler.add_task(feed)

    result = chat_tools.swap_times(owner, walk.id, feed.id)
    assert "Swapped" in result
    assert walk.start_time == "09:00"
    assert feed.start_time == "08:00"


def test_remove_task_deletes_it():
    owner, pet, task = _owner_with_task()
    result = chat_tools.remove_task(owner, task.id)
    assert "Removed" in result
    assert task not in pet.tasks


def test_add_task_creates_new_task_for_named_pet():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)

    result = chat_tools.add_task(
        owner,
        pet_name="Milo",
        description="Nail trim",
        date="2026-07-07",
        start_time="10:00",
        duration_minutes=15,
        priority="low",
    )
    assert "Added" in result
    tasks = Scheduler(owner=owner).get_all_tasks()
    assert len(tasks) == 1
    assert tasks[0].description == "Nail trim"
    assert tasks[0].id is not None


def test_add_task_unknown_pet_raises():
    owner = Owner(name="Sam")
    with pytest.raises(ValueError):
        chat_tools.add_task(
            owner, pet_name="Ghost", description="Walk", date="2026-07-07",
            start_time="10:00", duration_minutes=15, priority="low",
        )


def test_regenerate_plan_returns_scheduled_tasks():
    owner, pet, task = _owner_with_task(duration=20)
    owner.schedules["2026-07-06"].add_time_availability("08:00", "08:30")

    plan = chat_tools.regenerate_plan(owner, "2026-07-06")
    assert plan == [
        {"id": task.id, "description": "Morning walk", "start_time": "08:00", "priority": "high"}
    ]
