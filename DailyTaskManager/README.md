# Daily Task Manager
### Mastering Agentic AI — Week 1 Project

> **GitHub:** https://github.com/laknarayana9/GenAcademy/tree/main/DailyTaskManager

---

## Project Overview

I built a custom Daily Task Manager web application using Python, Streamlit, and AI coding agents. The goal of the project was to create a clean, functional productivity app that helps users manage daily tasks while also including data-app features such as CSV import/export, filtering, persistence, and analytics.

The app allows users to add, complete, delete, sort, filter, import, export, and analyze tasks. It was built using a structured AI-assisted coding workflow: first planning the architecture with the agent, then approving edits step by step, then running the app, debugging issues, and finally using a separate agent session for code review and hardening.

---

## Problem Statement

People often need a simple way to manage daily work, personal, and errand-related tasks. Many task apps either feel too complex or do not provide quick insights into productivity. This project solves that by creating a lightweight daily task manager with priority levels, due times, categories, completion tracking, and a built-in insights dashboard.

---

## Key Features Built

| Feature | Description |
|---|---|
| **Add Tasks** | Users can add a task with title, priority, category, and optional due time |
| **Complete Tasks** | Users can mark tasks as completed |
| **Delete Tasks** | Users can remove tasks from the list |
| **Priority Levels** | High, Medium, and Low priorities with visual indicators |
| **Categories** | Work, Personal, and Errands categories |
| **Sorting** | Tasks are sorted by priority, due time, and creation order |
| **Filtering** | Sidebar filters allow users to filter tasks by category |
| **CSV Import/Export** | Users can bulk-import tasks from CSV and export current tasks |
| **Insights Dashboard** | Shows completion rates and task breakdowns by category and priority |
| **Persistence** | Tasks are saved to `data/tasks.json` and survive browser refreshes |

---

## Tech Stack

The project was built with:

- **Python** — core application language
- **Streamlit** — web UI framework
- **JSON file persistence** — lightweight local data storage
- **CSV import/export** — bulk task data handling
- **Modular Python architecture** — separate modules for model, service, persistence, and UI
- **AI coding agent workflow** — Windsurf / Cascade

The project was intentionally structured like a real application rather than a single-file prototype. The architecture includes separate modules for the app entry point, styles, validation, task model, service logic, persistence, UI components, CSV handling, and analytics.

---

## AI-Assisted Coding Workflow

I followed a disciplined AI-assisted coding process:

1. **Planning first** — I asked the AI agent to propose the architecture and file structure before writing any code.
2. **No code without approval** — The agent was instructed not to write code until the plan was reviewed and approved.
3. **Incremental build** — Files were created one at a time sequentially by the agent, including the task model, persistence utility, service layer, Streamlit components, and main app.
4. **Run and debug** — After the first build, I ran the app using Streamlit and fixed launch issues with targeted prompts.
5. **Parallel code review** — A separate AI agent session reviewed the code for blocking and high-severity issues.
6. **Hardening and validation** — The app was improved with atomic writes, corrupt-file recovery, duplicate detection, HTML escaping, and a full validation suite.

This process kept the implementation controlled, reviewable, and reliable.

---

## Important Prompts Used

**Initial planning prompt:**
```
I want to build a daily task manager app. It should have tasks with a title,
priority, category, and optional due time. Tasks should be sorted by priority
first, then due time. Users should be able to complete or delete tasks. Tasks
should persist across browser refreshes. Use Streamlit and Python.
First, give me your proposed file structure and architecture.
Do NOT write any code until I approve the plan.
```

**Build prompt:**
```
Go ahead and build the app following the plan you just described.
Ask me before creating or editing any file.
```

**Parallel code review prompt** *(run in a separate agent session with no prior context)*:
```
Please do a thorough code review. Flag any P0 and P1 issues.
Do not suggest cosmetic changes. Focus on correctness, reliability, and security.
```

**Feature expansion prompt:**
```
Add a CSV import/export tab. Users should be able to upload a CSV to
bulk-import tasks, with duplicate detection by title. They should also be
able to download all current tasks as a CSV.
Add an Insights tab showing total tasks, completion rate, a bar chart of
tasks by category, and a bar chart by priority.
```

---

## Data and CSV Support

Although this was a custom app, CSV support was added to align it with the data application theme of the bootcamp. The app supports importing task data from CSV and exporting all tasks back to CSV. This made the project more than a basic task tracker — it can load a dataset, display structured records, filter the data, and generate productivity insights.

**Example CSV format:**

```csv
title,priority,due_time,category,status
Review project requirements,High,09:00,Work,Pending
Buy groceries,Medium,17:00,Errands,Pending
Clean desk workspace,Low,18:30,Personal,Completed
```

---

## Key Learnings

The biggest learning was that AI-assisted coding works best when the human acts like a product manager and reviewer, not just a prompt typist. The most useful prompts were the ones that clearly defined requirements, acceptance criteria, and constraints.

Asking for a plan before code is extremely important — it prevents the AI agent from creating a messy one-file prototype and leads to a cleaner modular structure.

Using a second AI session for code review was also a key insight. The parallel review caught issues that the building agent had not flagged, including unsafe file writes, corrupt JSON handling, duplicate IDs, and HTML escaping problems.

---

## Final Outcome

The final result is a working Daily Task Manager Streamlit app with a professional UI, persistent task storage, CSV import/export, and productivity analytics. It demonstrates how AI coding agents can be used to rapidly prototype and improve a useful application while still following a thoughtful engineering workflow.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation & Local Setup](#installation--local-setup)
3. [Running the App](#running-the-app)
4. [User Guide](#user-guide)
5. [Validation & Testing](#validation--testing)
6. [Project Structure](#project-structure)

---

## Requirements

- Python 3.9 or higher
- pip

---

## Installation & Local Setup

**1. Clone or navigate to the project folder**

```bash
cd DailyTaskManager
```

**2. (Recommended) Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the App

Start the Streamlit server:

```bash
streamlit run app.py --server.headless true
```

Then open your browser at:

```
http://localhost:8501
```

> **Note:** Always use `--server.headless true` to skip Streamlit's first-run email prompt. Without it the server will block silently and return a 502 error.

**Custom port (optional)**

```bash
streamlit run app.py --server.headless true --server.port 8502
```

**Stop the server**

Press `Ctrl + C` in the terminal.

---

## User Guide

### Layout Overview

```
┌──────────────────────────────────────────────────────┐
│  Monday, June 2, 2026          [ ＋ Add Task ]       │
│  Daily Task Manager                                  │
├──────────────────┬───────────────────────────────────┤
│  SIDEBAR         │  MAIN CONTENT                     │
│                  │                                   │
│  Filter by       │  PENDING TASKS (3)                │
│  Category:       │  ┌────────────────────────────┐   │
│                  │  │ [High] Fix login bug  Work  │   │
│  ○ All           │  │          ⏱ 9:00 AM  [✓][✕] │   │
│  ○ Work          │  └────────────────────────────┘   │
│  ○ Personal      │  ┌────────────────────────────┐   │
│  ○ Errands       │  │ [Med]  Call dentist Personal│   │
│                  │  │          ⏱ 5:00 PM  [✓][✕] │   │
│  Priority Guide  │  └────────────────────────────┘   │
│  [High]          │                                   │
│  [Medium]        │  ✓ Completed (1)  ▼               │
│  [Low]           └───────────────────────────────────┘
```

---

### Adding a Task

1. Click **＋ Add Task** in the top-right corner.
2. A form expands below the header.

| Field | Description |
|---|---|
| **Task title** | Required. What needs to be done. |
| **Priority** | High / Medium / Low. Defaults to Medium. |
| **Category** | Work / Personal / Errands. |
| **Set due time** | Check the box to reveal a time picker. Leave unchecked for no due time. |

3. Click **Add Task** to save, or **Cancel** to dismiss the form.

> Tasks without a due time always appear — they are never filtered out. Within their priority group, timed tasks sort before untimed ones.

---

### Task Sort Order

Pending tasks are always sorted automatically:

1. **Priority** — High → Medium → Low
2. **Due time** — Timed tasks before untimed; earlier times first
3. **Created time** — Tiebreaker (oldest first)

---

### Completing a Task

Click the **✓** button on the right side of any pending task row.

- The task moves to the **Completed** section at the bottom.
- It is shown with strikethrough text and reduced opacity.
- Completed tasks are sorted by most-recently-completed first.

---

### Deleting a Task

Click the **✕** button on any task row (pending or completed).

- The task is permanently removed and cannot be recovered.

---

### Filtering by Category

Use the **sidebar** on the left to filter the task list:

- **All** — Shows every task regardless of category (default).
- **Work / Personal / Errands** — Shows only tasks in that category.

The filter applies to both the pending list and the completed section simultaneously.

---

### Viewing Completed Tasks

Completed tasks are hidden by default in a collapsible section at the bottom of the page labelled **✓ Completed (N)**.

Click the section header to expand or collapse it.

---

### Data Persistence

All tasks are saved immediately to `data/tasks.json` on every action (add, complete, delete). The file is created automatically on first use.

- **Refresh-safe** — Refreshing the browser reloads tasks from disk. Nothing is lost.
- **Crash-safe** — Writes use an atomic temp-file swap (`tasks.json.tmp` → `tasks.json`), so a crash mid-write cannot corrupt your data.
- **Backup on corruption** — If `tasks.json` is ever unreadable, it is automatically renamed to `tasks.corrupt-<timestamp>.json` and the app continues with an empty list. A yellow warning banner is shown at the top of the page.

---

## Validation & Testing

Run the built-in validation suite to verify the app is correctly installed and all logic is working before use:

```bash
# Offline checks only (imports, model, persistence, CRUD, hardening)
python validate.py

# Include live server health check (requires the app to be running)
python validate.py --server

# Custom port
python validate.py --server --port 8502
```

**What is checked:**

| Section | Checks |
|---|---|
| 1 — Module Imports | All 7 modules load without errors |
| 2 — Persistence | JSON round-trip, `None` fields, file creation |
| 3 — TaskService CRUD | add, complete, delete, sort order, category filter |
| 4 — Data Model | UUID validity, ISO timestamps, default fields, serialisation |
| 5 — Hardening | Atomic write, corrupt-file backup, per-record tolerance, duplicate ID dedup, HTML escaping, cross-platform strftime |
| 6 — Live Server | `/healthz`, `/`, `/_stcore/health` endpoints |

Exit code `0` = all checks passed. Non-zero = one or more failures (details printed inline).

---

## Project Structure

```
DailyTaskManager/
├── app.py                   # Entry point — layout orchestration
├── styles.py                # All CSS in one place (edit to change visuals)
├── requirements.txt
├── validate.py              # Pre-flight & regression test suite
├── data/
│   └── tasks.json           # Auto-created on first task; source of truth
├── models/
│   └── task.py              # Task dataclass + to_dict / from_dict
├── services/
│   └── task_service.py      # TaskService: add, complete, delete, sort, filter
├── utils/
│   └── persistence.py       # load_tasks() / save_tasks() — disk I/O only
└── components/
    ├── top_bar.py           # Date header + collapsible add-task form
    ├── task_card.py         # Single task row renderer
    └── sidebar.py           # Category filter + priority legend
```

**Key design rules:**
- `data/tasks.json` is the **only** permanent store. `st.session_state` is used for UI state only (e.g. whether the add form is open).
- All visual changes live in `styles.py` — no CSS is scattered across component files.
- `TaskService` and `persistence.py` have zero Streamlit dependencies and can be tested without a running server.
