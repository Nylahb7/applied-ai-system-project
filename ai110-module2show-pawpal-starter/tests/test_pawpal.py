from datetime import date, timedelta

from pawpal_system import Owner, Pet, Scheduler, Task, TimeSlot


def test_mark_complete_updates_status():
    pet = Pet(name="Mochi", animal_type="dog")
    task = Task(
        description="Morning walk",
        pet=pet,
        time="2026-07-06",
        duration_minutes=20,
        priority="high",
    )

    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Luna", animal_type="cat")
    task = Task(
        description="Feed dinner",
        pet=pet,
        time="2026-07-07",
        duration_minutes=10,
        priority="medium",
    )

    assert len(pet.tasks) == 0
    pet.add_task(task)
    assert len(pet.tasks) == 1


# --- Recurring tasks ---------------------------------------------------

def test_mark_complete_daily_recurrence_advances_from_today_not_due_date():
    pet = Pet(name="Mochi", animal_type="dog")
    task = Task(
        description="Morning walk",
        pet=pet,
        time="2026-07-01",  # due date is in the past relative to "today"
        duration_minutes=20,
        priority="high",
        recurrence="daily",
    )

    next_task = task.mark_complete()

    assert next_task is not None
    assert next_task.time == (date.today() + timedelta(days=1)).isoformat()
    assert next_task.pet is pet
    assert next_task.recurrence == "daily"
    assert next_task.completed is False


def test_mark_complete_weekly_recurrence_advances_from_original_due_date():
    pet = Pet(name="Luna", animal_type="cat")
    task = Task(
        description="Nail trim",
        pet=pet,
        time="2026-07-06",
        duration_minutes=15,
        priority="low",
        recurrence="weekly",
    )

    next_task = task.mark_complete()

    assert next_task is not None
    assert next_task.time == "2026-07-13"


def test_mark_complete_unsupported_recurrence_returns_none():
    pet = Pet(name="Rex", animal_type="dog")
    task = Task(
        description="Vet checkup",
        pet=pet,
        time="2026-07-06",
        duration_minutes=30,
        priority="medium",
        recurrence="monthly",
    )

    assert task.mark_complete() is None
    assert task.completed is True


def test_complete_task_twice_spawns_two_weekly_occurrences():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    task = Task(
        description="Grooming",
        pet=pet,
        time="2026-07-06",
        duration_minutes=30,
        priority="medium",
        recurrence="weekly",
    )
    scheduler.add_task(task)

    second = scheduler.complete_task(task)
    assert second.time == "2026-07-13"
    assert second in owner.schedules["2026-07-13"].tasks

    third = scheduler.complete_task(second)
    assert third.time == "2026-07-20"
    assert third in owner.schedules["2026-07-20"].tasks


# --- Conflict detection --------------------------------------------------

def test_adjacent_tasks_at_shared_boundary_do_not_conflict():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    first = Task(
        description="Walk", pet=pet, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:00",
    )
    second = Task(
        description="Feed", pet=pet, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:30",
    )
    scheduler.add_task(first)
    scheduler.add_task(second)  # should not raise

    assert scheduler.find_conflicts("2026-07-06") == []


def test_find_conflicts_detects_cross_pet_overlap_that_add_task_allows():
    owner = Owner(name="Sam")
    dog = Pet(name="Milo", animal_type="dog")
    cat = Pet(name="Nala", animal_type="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    scheduler = Scheduler(owner=owner)

    dog_task = Task(
        description="Walk", pet=dog, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:00",
    )
    cat_task = Task(
        description="Litter box", pet=cat, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:15",
    )
    scheduler.add_task(dog_task)
    scheduler.add_task(cat_task)  # different pets: add_task allows the overlap

    conflicts = scheduler.find_conflicts("2026-07-06")
    assert conflicts == [(dog_task, cat_task)]


def test_add_task_safe_blocks_same_pet_conflict():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    existing = Task(
        description="Walk", pet=pet, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:00",
    )
    scheduler.add_task(existing)

    conflicting = Task(
        description="Play", pet=pet, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:15",
    )
    warning = scheduler.add_task_safe(conflicting)

    assert warning is not None
    assert conflicting not in scheduler.get_tasks_for_date("2026-07-06")


def test_add_task_safe_allows_cross_pet_conflict_with_warning():
    owner = Owner(name="Sam")
    dog = Pet(name="Milo", animal_type="dog")
    cat = Pet(name="Nala", animal_type="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    scheduler = Scheduler(owner=owner)

    existing = Task(
        description="Walk", pet=dog, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:00",
    )
    scheduler.add_task(existing)

    conflicting = Task(
        description="Litter box", pet=cat, time="2026-07-06",
        duration_minutes=30, priority="medium", start_time="09:15",
    )
    warning = scheduler.add_task_safe(conflicting)

    assert warning is not None
    assert conflicting in scheduler.get_tasks_for_date("2026-07-06")


# --- Sorting --------------------------------------------------------------

def test_sort_by_time_agrees_with_get_all_tasks_on_same_date_ordering():
    # sort_by_time() re-sorts get_all_tasks()'s output by date alone. Because
    # get_all_tasks() already orders by (date, start_time) and Python's sort
    # is stable, re-sorting by date can't disturb the start_time ordering
    # within a date - so the two methods always agree, regardless of the
    # order tasks were inserted in.
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    later = Task(
        description="Evening walk", pet=pet, time="2026-07-06",
        duration_minutes=20, priority="medium", start_time="18:00",
    )
    earlier = Task(
        description="Morning walk", pet=pet, time="2026-07-06",
        duration_minutes=20, priority="medium", start_time="07:00",
    )
    # Insertion order deliberately puts the later start_time first.
    scheduler.add_task(later)
    scheduler.add_task(earlier)

    by_time = scheduler.sort_by_time()
    all_tasks = scheduler.get_all_tasks()

    expected = ["Morning walk", "Evening walk"]
    assert [t.description for t in all_tasks] == expected
    assert [t.description for t in by_time] == expected


# --- Plan generation -------------------------------------------------------

def test_generate_plan_drops_task_that_fits_no_slot():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    task = Task(
        description="Long hike", pet=pet, time="2026-07-06",
        duration_minutes=60, priority="high",
    )
    scheduler.add_task(task)
    owner.schedules["2026-07-06"].add_time_availability("09:00", "09:30")  # only 30 min

    plan = scheduler.generate_plan_for_date("2026-07-06")
    assert task not in plan


def test_generate_plan_includes_task_at_exact_slot_boundary():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    task = Task(
        description="Walk", pet=pet, time="2026-07-06",
        duration_minutes=30, priority="high",
    )
    scheduler.add_task(task)
    owner.schedules["2026-07-06"].add_time_availability("09:00", "09:30")  # exactly 30 min

    plan = scheduler.generate_plan_for_date("2026-07-06")
    assert task in plan


def test_generate_plan_with_no_time_availabilities_is_empty():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    task = Task(
        description="Walk", pet=pet, time="2026-07-06",
        duration_minutes=15, priority="high",
    )
    scheduler.add_task(task)

    assert scheduler.generate_plan_for_date("2026-07-06") == []


def test_generate_plan_uses_custom_priority_weights():
    owner = Owner(name="Sam")
    pet = Pet(name="Milo", animal_type="dog")
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)

    high = Task(
        description="Vet visit", pet=pet, time="2026-07-06",
        duration_minutes=15, priority="high", start_time="09:00",
    )
    low = Task(
        description="Nail trim", pet=pet, time="2026-07-06",
        duration_minutes=15, priority="low", start_time="09:15",
    )
    scheduler.add_task(high)
    scheduler.add_task(low)

    schedule = owner.schedules["2026-07-06"]
    schedule.add_time_availability("09:00", "09:15")  # room for exactly one task
    schedule.priorities = {"low": 10, "high": 1}  # invert the default ranking

    plan = scheduler.generate_plan_for_date("2026-07-06")
    assert plan == [low]


# --- Filtering --------------------------------------------------------------

def test_filter_tasks_matches_by_pet_name_across_distinct_pet_objects():
    owner = Owner(name="Sam")
    dog = Pet(name="Milo", animal_type="dog")
    other_dog = Pet(name="Milo", animal_type="dog")  # same name, different object
    owner.add_pet(dog)
    owner.add_pet(other_dog)
    scheduler = Scheduler(owner=owner)

    task_a = Task(
        description="Walk", pet=dog, time="2026-07-06",
        duration_minutes=15, priority="medium",
    )
    task_b = Task(
        description="Feed", pet=other_dog, time="2026-07-06",
        duration_minutes=15, priority="medium",
    )
    scheduler.add_task(task_a)
    scheduler.add_task(task_b)

    matches = scheduler.filter_tasks("Milo", completed=False)
    # Compare by identity, not `==`: Task.__eq__ compares `pet`, and Pet.__eq__
    # compares `pet.tasks` right back, so `==` between two *distinct* Task
    # objects recurses forever. `is` sidesteps that entirely.
    assert len(matches) == 2
    assert any(t is task_a for t in matches)
    assert any(t is task_b for t in matches)
