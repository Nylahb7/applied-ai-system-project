from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Schedule, Task, TimeSlot

TODAY = date.today().isoformat()

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name=owner_name)

if "pet" not in st.session_state:
    pet = Pet(name=pet_name, animal_type=species)
    st.session_state.owner.add_pet(pet)
    st.session_state.pet = pet

owner = st.session_state.owner
pet = st.session_state.pet
scheduler = Scheduler(owner=owner)

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    task_start = st.time_input("Start time", value=time(8, 0))
with col3:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col4:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    try:
        warning = scheduler.add_task_safe(Task(
            description=task_title,
            pet=pet,
            time=TODAY,
            duration_minutes=int(duration),
            priority=priority,
            start_time=task_start.strftime("%H:%M"),
        ))
        if warning:
            st.warning(warning)
        else:
            st.success(f"Added '{task_title}' for {pet.name}.")
    except ValueError as e:
        st.error(str(e))


def _task_rows(tasks):
    priority_icons = {"high": "🔴 high", "medium": "🟡 medium", "low": "🟢 low"}
    return [
        {
            "description": t.description,
            "start_time": t.start_time,
            "duration_minutes": t.duration_minutes,
            "priority": priority_icons.get(t.priority, t.priority),
            "completed": "✅" if t.completed else "⬜",
        }
        for t in tasks
    ]


pet_tasks = scheduler.get_tasks_for_pet(pet)
st.write("Current tasks (sorted by date/time):")
if pet_tasks:
    st.table(_task_rows(pet_tasks))
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Filter Tasks")
st.caption("Filter this pet's tasks by completion status using `scheduler.filter_tasks`.")

status_choice = st.radio("Status", ["All", "Completed", "Incomplete"], horizontal=True)

if status_choice == "All":
    filtered_tasks = pet_tasks
else:
    filtered_tasks = scheduler.filter_tasks(pet.name, completed=(status_choice == "Completed"))

if filtered_tasks:
    st.success(f"{len(filtered_tasks)} task(s) match '{status_choice}'.")
    st.table(_task_rows(filtered_tasks))
else:
    st.info(f"No tasks match '{status_choice}'.")

st.divider()

st.subheader("Conflict Check")
st.caption(f"Check {TODAY} for overlapping tasks using `scheduler.find_conflicts`.")

conflicts = scheduler.find_conflicts(TODAY)
if conflicts:
    for a, b in conflicts:
        st.warning(
            f"'{a.description}' ({a.pet.name}, {a.start_time}) overlaps with "
            f"'{b.description}' ({b.pet.name}, {b.start_time})."
        )
else:
    st.success("No conflicts detected for today.")

st.divider()

st.subheader("Build Schedule")
st.caption("Set today's available time window, then generate a plan that fits your tasks into it.")

avail_col1, avail_col2 = st.columns(2)
with avail_col1:
    avail_start = st.time_input("Available from", value=time(8, 0))
with avail_col2:
    avail_end = st.time_input("Available until", value=time(10, 0))

if st.button("Generate schedule"):
    schedule = owner.schedules.setdefault(TODAY, Schedule(date=TODAY))
    schedule.time_availabilities = [
        TimeSlot(start=avail_start.strftime("%H:%M"), end=avail_end.strftime("%H:%M"))
    ]

    plan = scheduler.generate_plan_for_date(TODAY)
    if plan:
        st.success(f"Scheduled {len(plan)} of {len(pet_tasks)} task(s) for {TODAY}.")
        st.table(_task_rows(plan))

        scheduled_ids = {id(t) for t in plan}
        skipped = [t for t in pet_tasks if id(t) not in scheduled_ids]
        if skipped:
            st.warning(
                "Didn't fit in the available window: " + ", ".join(t.description for t in skipped)
            )
    else:
        st.info("No tasks fit in the available time window.")
