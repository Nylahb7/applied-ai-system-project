from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Schedule, Task, TimeSlot

owner = Owner(name="Jordan")

mochi = Pet(name="Mochi", animal_type="dog")
luna = Pet(name="Luna", animal_type="cat")

owner.add_pet(mochi)
owner.add_pet(luna)

vet_checkup = Task(
    description="Vet checkup",
    pet=mochi,
    time="2026-07-08",
    duration_minutes=45,
    priority="high",
    start_time="09:30",
)
feed_dinner = Task(
    description="Feed dinner",
    pet=luna,
    time="2026-07-07",
    duration_minutes=10,
    priority="medium",
    start_time="18:00",
)
morning_walk = Task(
    description="Morning walk",
    pet=mochi,
    time="2026-07-06",
    duration_minutes=20,
    priority="high",
    start_time="08:00",
)

# Added out of chronological order to exercise sort_by_time().
owner.add_task(vet_checkup)
owner.add_task(feed_dinner)
owner.add_task(morning_walk)

# Mark one task complete so filter_tasks() has both statuses to distinguish.
morning_walk.mark_complete()

TODAY = date.today().isoformat()
scheduler = Scheduler(owner=owner)

print(f"Today's Schedule ({TODAY}):")
for task in scheduler.get_tasks_for_date(TODAY):
    print(f"  - [{task.pet.name}] {task.description} ({task.duration_minutes} min, {task.priority})")

print("\nAll tasks sorted by time:")
for task in scheduler.sort_by_time():
    print(f"  - {task.time} [{task.pet.name}] {task.description}")

print("\nMochi's completed tasks:")
for task in scheduler.filter_tasks(pet_name="Mochi", completed=True):
    print(f"  - {task.time} {task.description}")

print("\nMochi's incomplete tasks:")
for task in scheduler.filter_tasks(pet_name="Mochi", completed=False):
    print(f"  - {task.time} {task.description}")

# Two tasks scheduled at the same time on 2026-07-08 (different pets) to test conflict detection.
groom_luna = Task(
    description="Groom Luna",
    pet=luna,
    time="2026-07-08",
    duration_minutes=15,
    priority="low",
    start_time="09:30",
)
warning = scheduler.add_task_safe(groom_luna)

print("\nAttempting to add a conflicting task:")
if warning:
    print(f"  {warning}")
else:
    print(f"  Added '{groom_luna.description}' with no conflicts.")

print("\nConflicts detected on 2026-07-08:")
for a, b in scheduler.find_conflicts("2026-07-08"):
    print(f"  - '{a.description}' overlaps with '{b.description}'")
