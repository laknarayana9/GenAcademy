# Vibe Coding — Master Class Submission
### Daily Task Manager · Built with AI Coding Agents

---

## Project Description — What This Project Is

**Daily Task Manager** is a full-featured, production-quality task management web application built entirely through AI-assisted (vibe) coding using Windsurf / Cascade as the primary coding agent.

The app is built with **Python + Streamlit** and runs locally in the browser. It lets users:

- **Add tasks** with a title, priority (High / Medium / Low), category (Work / Personal / Errands), and an optional due time
- **Sort tasks automatically** by priority → due time → creation order
- **Complete or delete tasks** with immediate UI feedback
- **Filter tasks by category** via a persistent sidebar
- **Import and export tasks via CSV** with duplicate detection and validation messages
- **View Insights** — a built-in analytics tab showing task completion rates and breakdowns by category and priority
- **Persist data reliably** — tasks are saved to `data/tasks.json` on every action, survive browser refreshes, and are protected by atomic writes and automatic corruption recovery

The project ended up with a **clean, modular architecture** across 7 Python modules — a real-world structure, not a single-file prototype:

```
DailyTaskManager/
├── app.py                  ← Entry point, layout orchestration only
├── styles.py               ← All CSS centralized
├── validate.py             ← 30+ automated pre-flight checks
├── models/task.py          ← Task dataclass + serialization
├── services/task_service.py← Business logic: CRUD, sort, filter, CSV
├── utils/persistence.py    ← Disk I/O, atomic writes, corruption recovery
└── components/
    ├── top_bar.py          ← Header + add-task form
    ├── task_card.py        ← Single task row renderer
    ├── sidebar.py          ← Category filter + priority legend
    ├── csv_handler.py      ← Import / export UI
    └── insights.py         ← Analytics tab
```

---

## How I Built It — Prompts and Iterations

The build followed a disciplined vibe coding workflow: **plan first, review before every edit, fix only the root cause, then harden**. Below is the exact sequence of prompts and what each iteration produced.

---

### Phase 1 — Planning Before Any Code

The very first prompt asked the agent to **think and plan, not build**:

```
I want to build a daily task manager app.

It should have tasks with a title, priority (High/Medium/Low),
category (Work/Personal/Errands), and an optional due time.

Tasks should be sorted by priority first, then due time.
Users should be able to complete or delete tasks.
Tasks should persist across browser refreshes.

Use Streamlit and Python.

First, give me your proposed file structure and architecture.
Do NOT write any code until I approve the plan.
```

**What happened:** The agent proposed the modular structure (models / services / utils / components). I reviewed it, asked a clarifying question about persistence (`JSON file vs. database?`), and approved only after the plan looked right.

> **Best practice applied:** Requiring a plan before code forces the agent to think through architecture. Starting with "Do NOT write code" is the single most effective control lever in vibe coding.

---

### Phase 2 — Incremental Build with Edit Approval

After approving the architecture, I issued the build prompt:

```
Go ahead and build the app following the plan you just described.
Ask me before creating or editing any file.
```

The agent created files one at a time — `models/task.py` → `utils/persistence.py` → `services/task_service.py` → components → `app.py`. Each file was reviewed before being written.

**What happened in this iteration:**
- The `Task` dataclass with UUID, ISO timestamps, and `to_dict` / `from_dict` was created cleanly
- `TaskService.add()`, `complete()`, `delete()`, and `get_sorted_filtered()` were implemented correctly on first pass
- The sorting logic (`priority rank → has_time flag → time_val → created_at`) required one clarification prompt:

```
For tasks without a due time — should they appear before or after
timed tasks of the same priority?
```

I answered: *after timed tasks*. The agent updated the sort key accordingly.

> **Best practice applied:** Asking about tie-breaking rules **during** the build (not after) avoids a silent incorrect default that is hard to spot in the UI later.

---

### Phase 3 — Running and Testing

After the initial build I ran the app:

```
streamlit run app.py
```

The server started but the browser showed a **502 Bad Gateway** on the first launch. I pasted the symptom back to the agent:

```
The app returns a 502 error when I open it in the browser.
Diagnose the root cause. Propose the smallest safe fix.
Do not edit any files until I approve.
```

**Root cause identified:** Streamlit's first-run email prompt was blocking the server in interactive mode. The agent proposed a one-flag fix:

```bash
streamlit run app.py --server.headless true
```

This became the canonical launch command documented in the README.

> **Best practice applied:** Always ask the agent to diagnose and propose *before* editing. A one-line flag fix is better than a code rewrite. This is the **minimal upstream fix** principle.

---

### Phase 4 — Parallel Agent Session: Code Review

Once the app was working, I opened a **second, independent agent session** (a parallel Cascade thread) and asked it to perform a code review with no prior context about the build:

```
Here is a Streamlit + Python task manager app. Please do a thorough
code review. Flag any P0 (blocking / data loss) and P1 (high severity)
issues. Do not suggest cosmetic changes. Focus on correctness,
reliability, and security.
```

The parallel reviewer — with fresh eyes and no attachment to the existing code — identified issues the building agent had not flagged. This is the most powerful quality gate in a vibe coding workflow.

**P0 Issues found by the code review agent:**

| # | Issue | File | Risk |
|---|-------|------|------|
| P0-1 | `save_tasks()` writes directly to `tasks.json` — a crash mid-write corrupts the only data file | `utils/persistence.py` | **Data loss** |
| P0-2 | A `JSONDecodeError` on `load_tasks()` raises an unhandled exception, crashing the whole app | `utils/persistence.py` | **App crash** |
| P0-3 | No `--server.headless true` in documented launch command → 502 on first run | `README.md` | **Silent server block** |

**P1 Issues found by the code review agent:**

| # | Issue | File | Risk |
|---|-------|------|------|
| P1-1 | Malformed records in `tasks.json` (missing keys) stop all tasks from loading | `utils/persistence.py` | Data unavailability |
| P1-2 | Duplicate task IDs in `tasks.json` cause silent double-rendering | `utils/persistence.py` | UI corruption |
| P1-3 | Task title rendered as raw HTML in `st.markdown()` — XSS vector | `components/task_card.py` | Security |
| P1-4 | `strftime("%Z")` returns empty string on some platforms → broken date header | `components/top_bar.py` | Cross-platform crash |

---

### Phase 5 — Fixing P0 and P1 Issues

Each issue was fed back to the **original building agent** as a targeted fix prompt:

**For P0-1 (data loss on crash):**
```
The reviewer flagged that save_tasks() writes directly to tasks.json.
A crash mid-write can corrupt the file.
Fix this with an atomic temp-file write using os.replace().
Propose the change before editing.
```

**Fix applied:** `save_tasks()` now writes to `tasks.json.tmp` first, then calls `os.replace()` to atomically swap it in. A crash before `os.replace()` leaves the original file intact.

**For P0-2 (corrupt file crash):**
```
If tasks.json contains invalid JSON, load_tasks() raises an exception
and crashes the app. Fix this by catching JSONDecodeError, backing up
the corrupt file with a timestamp, and returning an empty list.
Also surface a yellow warning banner to the user.
```

**Fix applied:** `load_tasks()` now catches `JSONDecodeError`, renames the corrupt file to `tasks.corrupt-<timestamp>.json`, and sets a module-level `_load_warning` string that the UI picks up on the next render.

**For P1-1 + P1-2 (malformed records, duplicate IDs):**
```
load_tasks() currently stops entirely if any single record is malformed.
Add per-record tolerance: skip bad records and log a warning.
Also de-duplicate by ID, keeping the first occurrence.
```

**Fix applied:** `load_tasks()` now wraps each `Task.from_dict()` call in a `try/except`, counts skipped records, and removes duplicates with a `seen` set.

**For P1-3 (XSS in task title):**
```
Task titles are rendered via st.markdown(unsafe_allow_html=True).
This means a title like <script>alert(1)</script> executes.
Escape the title before injecting it into the HTML template.
```

**Fix applied:** Task titles are passed through `html.escape()` before being embedded in any `st.markdown()` HTML string.

> **Best practice applied:** Each P0/P1 fix was a **separate, scoped prompt** — not a batch rewrite. This keeps the diff small and reviewable, and avoids the agent accidentally breaking working code while fixing one thing.

---

### Phase 6 — Validation Suite

After fixes were applied, I asked the agent to build a standalone test runner:

```
Write a validate.py script that runs offline checks for:
1. All module imports
2. Persistence JSON round-trip
3. TaskService CRUD and sort order
4. Task data model field completeness
5. All the hardening fixes (atomic write, corrupt-file backup,
   per-record tolerance, duplicate dedup, HTML escaping)

Also add a --server flag that checks live HTTP health endpoints.
Exit with code 0 on all pass, non-zero on any failure.
```

**Result:** A 514-line regression suite with 30+ assertions covering every scenario the code review surfaced. This runs in under two seconds with no browser required.

---

### Phase 7 — Extra Features via Upgrade Prompts

Once the core app was hardened, additional features were added one at a time, each as an isolated prompt:

```
Add a CSV import/export tab. Users should be able to upload a CSV
to bulk-import tasks, with duplicate detection by title.
They should also be able to download all current tasks as a CSV.
```

```
Add an Insights tab showing: total tasks, completion rate,
a bar chart of tasks by category, and a bar chart by priority.
No new dependencies.
```

Each feature was accepted only after reviewing the proposed changes.

---

## Key Learnings for the Human Developer

These are the lessons that would not be obvious without going through a real vibe coding project:

---

**1. The plan prompt is the most valuable prompt you write.**

The time you spend asking the agent to brainstorm architecture *before* any code is written saves hours of untangling wrong structure later. An agent that plans first produces modular, testable code. An agent that jumps straight to coding produces a single sprawling file.

---

**2. "Ask Before Edits" mode is not optional for a first build.**

In auto-edit mode, the agent can overwrite a working file while trying to fix something unrelated. Reviewing each file before it is written keeps you in control and forces you to understand the code as it is produced — which matters when you need to debug it later.

---

**3. The parallel review session finds things the building agent will not.**

A coding agent that built something has an implicit bias toward its own decisions. A fresh agent reviewing the same code with no context applies different heuristics. The P0 data-loss bug (non-atomic write) and the XSS issue were both found only by the parallel reviewer, not by the agent that wrote the code.

---

**4. Scope your fix prompts tightly.**

When reporting a bug to the agent, include: the symptom, the root cause if you know it, and an explicit instruction like *"Propose the smallest safe fix. Do not edit other files."* Wide-open fix prompts like *"fix all the bugs"* result in large diffs that are hard to review and often introduce new bugs.

---

**5. P0 vs P1 classification forces you to prioritize.**

Not every code review finding needs to be fixed immediately. Classifying issues as P0 (blocking, data loss) vs P1 (high severity but not immediate) vs cosmetic gave a clear sequence for what to address first. The parallel agent was explicitly asked to use this classification in its output.

---

**6. A validation script is a force multiplier.**

Building `validate.py` after the hardening fixes meant every subsequent change could be verified in two seconds. Without it, regression testing would require manual UI interaction every time. Asking the agent to write the test suite (not writing it yourself) is itself a vibe coding best practice — the agent knows the exact internal interfaces and edge cases to cover.

---

**7. You are the product manager, not the typist.**

The human's job in vibe coding is to decide *what* to build, review *what was built*, and know *what questions to ask*. The agent's job is the implementation. The most effective prompts in this project were the ones that clearly stated requirements and acceptance criteria — not the ones that described how to implement something.

---

*Submitted for GenAcademy Master Class: Vibe Coding How-To · June 2026*
