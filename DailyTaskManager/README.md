# Daily Task Manager

A clean, professional task manager built with Python and Streamlit. Tasks are stored locally in JSON and persist across sessions.

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
