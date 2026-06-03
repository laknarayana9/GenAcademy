"""
validate.py — Pre-flight and post-start validation for DailyTaskManager.

Usage:
    python validate.py              # checks imports, persistence, logic only
    python validate.py --server     # also checks live server health (needs app running)
    python validate.py --port 8501  # custom port (default 8501)

Exit code 0 = all checks passed. Non-zero = one or more failures.
"""

import argparse
import importlib
import json
import os
import pathlib
import sys
import tempfile
import time
import urllib.request
import urllib.error

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

_pass_count = 0
_fail_count = 0


def _ok(label: str) -> None:
    global _pass_count
    _pass_count += 1
    print(f"  {GREEN}✓{RESET}  {label}")


def _fail(label: str, reason: str = "") -> None:
    global _fail_count
    _fail_count += 1
    detail = f"  {YELLOW}→ {reason}{RESET}" if reason else ""
    print(f"  {RED}✕{RESET}  {label}{('  ' + detail) if detail else ''}")


def _section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")
    print("  " + "─" * (len(title) + 2))


# ── 1. Module imports ─────────────────────────────────────────────────────────
def check_imports() -> None:
    _section("1  Module Imports")
    modules = [
        ("models.task",          "Task"),
        ("utils.persistence",    "load_tasks, save_tasks"),
        ("services.task_service","TaskService, PRIORITIES, CATEGORIES"),
        ("styles",               "inject_styles"),
        ("components.top_bar",   "render_top_bar"),
        ("components.task_card", "render_task_card"),
        ("components.sidebar",   "render_sidebar"),
    ]
    for mod_name, symbols in modules:
        try:
            importlib.import_module(mod_name)
            _ok(f"{mod_name}  ({symbols})")
        except Exception as exc:
            _fail(f"{mod_name}", str(exc))


# ── 2. Persistence round-trip ─────────────────────────────────────────────────
def check_persistence() -> None:
    _section("2  Persistence (JSON round-trip)")

    from utils.persistence import load_tasks, save_tasks, TASKS_FILE, DATA_DIR
    from models.task import Task

    # data dir creation
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        _ok(f"data/ directory exists or created  ({DATA_DIR})")
    except Exception as exc:
        _fail("data/ directory creation", str(exc))
        return

    # write to a temp file so we don't corrupt real data
    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", dir=DATA_DIR, delete=False
    )
    tmp.close()
    real_path = TASKS_FILE
    tmp_path  = tmp.name

    try:
        # Temporarily patch the module-level path
        import utils.persistence as pm
        pm.TASKS_FILE = tmp_path

        sample = Task(title="Validate task", priority="High", category="Work", due_time="09:00")

        save_tasks([sample])
        _ok("save_tasks() wrote JSON to disk")

        with open(tmp_path) as f:
            raw = json.load(f)
        assert len(raw) == 1 and raw[0]["title"] == "Validate task"
        _ok("JSON file content is valid")

        loaded = load_tasks()
        assert len(loaded) == 1
        assert loaded[0].id == sample.id
        assert loaded[0].title == sample.title
        assert loaded[0].priority == sample.priority
        assert loaded[0].due_time == "09:00"
        _ok("load_tasks() deserialises Task correctly (id, title, priority, due_time)")

        # None due_time round-trip
        sample2 = Task(title="No time task", priority="Low", category="Errands")
        save_tasks([sample2])
        loaded2 = load_tasks()
        assert loaded2[0].due_time is None
        _ok("due_time=None round-trips as null/None correctly")

    except AssertionError as exc:
        _fail("Persistence round-trip assertion failed", str(exc))
    except Exception as exc:
        _fail("Unexpected persistence error", str(exc))
    finally:
        pm.TASKS_FILE = real_path
        os.unlink(tmp_path)


# ── 3. TaskService CRUD ───────────────────────────────────────────────────────
def check_task_service() -> None:
    _section("3  TaskService CRUD & Sorting")

    import utils.persistence as pm
    from services.task_service import TaskService

    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", dir=pm.DATA_DIR, delete=False
    )
    tmp.close()
    real_path = pm.TASKS_FILE
    pm.TASKS_FILE = tmp.name

    try:
        svc = TaskService()

        # add
        t1 = svc.add("High task",   "High",   "Work",     "08:00")
        t2 = svc.add("Medium task", "Medium", "Personal", "10:00")
        t3 = svc.add("Low task",    "Low",    "Errands")
        t4 = svc.add("High no time","High",   "Work")
        _ok("add() creates 4 tasks")

        # sort order check
        pending, completed = svc.get_sorted_filtered()
        assert len(pending) == 4
        assert pending[0].id == t1.id,  "High+time should be first"
        assert pending[1].id == t4.id,  "High+no-time should be second"
        assert pending[2].id == t2.id,  "Medium should be third"
        assert pending[3].id == t3.id,  "Low should be last"
        _ok("get_sorted_filtered() order: High(timed) → High(no time) → Medium → Low")

        # category filter
        work_p, _ = svc.get_sorted_filtered("Work")
        assert all(t.category == "Work" for t in work_p)
        _ok("category filter 'Work' returns only Work tasks")

        errands_p, _ = svc.get_sorted_filtered("Errands")
        assert len(errands_p) == 1 and errands_p[0].id == t3.id
        _ok("category filter 'Errands' returns correct task")

        # complete
        svc.complete(t1.id)
        pending2, completed2 = svc.get_sorted_filtered()
        assert len(pending2) == 3
        assert len(completed2) == 1
        assert completed2[0].id == t1.id
        assert completed2[0].completed_at is not None
        _ok("complete() moves task to completed with timestamp")

        # delete
        svc.delete(t2.id)
        pending3, _ = svc.get_sorted_filtered()
        assert not any(t.id == t2.id for t in pending3)
        _ok("delete() removes task from list")

        # no-time tasks always appear (all filter = 'All')
        _, _ = svc.get_sorted_filtered("All")
        _ok("get_sorted_filtered('All') runs without error")

    except AssertionError as exc:
        _fail("TaskService assertion failed", str(exc))
    except Exception as exc:
        _fail("Unexpected TaskService error", str(exc))
    finally:
        pm.TASKS_FILE = real_path
        os.unlink(tmp.name)


# ── 4. Data model field completeness ─────────────────────────────────────────
def check_data_model() -> None:
    _section("4  Task Data Model")
    from models.task import Task
    import uuid

    t = Task(title="Test", priority="Medium", category="Personal")

    try:
        uuid.UUID(t.id)
        _ok("id is a valid UUID")
    except ValueError:
        _fail("id is not a valid UUID", t.id)

    try:
        from datetime import datetime
        datetime.fromisoformat(t.created_at)
        _ok("created_at is valid ISO datetime")
    except ValueError:
        _fail("created_at is not valid ISO datetime", t.created_at)

    assert t.status == "pending",     f"default status should be 'pending', got '{t.status}'"
    _ok("default status is 'pending'")

    assert t.due_time is None,        "default due_time should be None"
    _ok("default due_time is None")

    assert t.completed_at is None,    "default completed_at should be None"
    _ok("default completed_at is None")

    d = t.to_dict()
    required_keys = {"id","title","priority","category","status","due_time","created_at","completed_at"}
    missing = required_keys - d.keys()
    assert not missing, f"to_dict() missing keys: {missing}"
    _ok(f"to_dict() contains all required keys")

    t2 = Task.from_dict(d)
    assert t2.id == t.id and t2.title == t.title
    _ok("from_dict(to_dict()) round-trip preserves id and title")


# ── 5. Hardening checks ──────────────────────────────────────────────────────
def check_hardening() -> None:
    _section("5  Hardening Checks")

    import utils.persistence as pm
    from utils.persistence import load_tasks, save_tasks, pop_load_warning, PersistenceError
    from models.task import Task

    project_root = os.path.dirname(os.path.abspath(__file__))
    real_path = pm.TASKS_FILE

    # ── 5a. Atomic write: no orphaned .tmp after successful save ──────────────
    pop_load_warning()  # clear stale state
    tmp_file = tempfile.NamedTemporaryFile(suffix=".json", dir=pm.DATA_DIR, delete=False)
    tmp_file.close()
    pm.TASKS_FILE = tmp_file.name
    try:
        save_tasks([Task(title="atomic", priority="Low", category="Work")])
        tmp_leftover = tmp_file.name + ".tmp"
        if os.path.exists(tmp_leftover):
            _fail("Atomic write: orphaned .tmp file found after save")
            os.unlink(tmp_leftover)
        else:
            _ok("Atomic write: no orphaned .tmp file after successful save")
        with open(tmp_file.name) as f:
            content = json.load(f)
        assert len(content) == 1 and content[0]["title"] == "atomic"
        _ok("Atomic write: content valid after os.replace() write")
    except AssertionError as exc:
        _fail("Atomic write assertion", str(exc))
    except Exception as exc:
        _fail("Atomic write (unexpected)", str(exc))
    finally:
        if os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)
        pm.TASKS_FILE = real_path

    # ── 5b. Corrupt JSON: backup created, warning surfaced ────────────────────
    pop_load_warning()
    corrupt_tmp = tempfile.NamedTemporaryFile(
        suffix=".json", dir=pm.DATA_DIR, delete=False, mode="w"
    )
    corrupt_tmp.write("{ not valid json !!!")
    corrupt_tmp.close()
    pm.TASKS_FILE = corrupt_tmp.name
    try:
        result = load_tasks()
        assert result == [], f"expected [], got {result}"
        _ok("Corrupt JSON: load_tasks() returns empty list")
        assert not os.path.exists(corrupt_tmp.name), "corrupt file should be renamed, not deleted"
        _ok("Corrupt JSON: original corrupt file renamed to backup")
        warn = pop_load_warning()
        assert warn is not None, "expected a warning message"
        _ok(f"Corrupt JSON: warning surfaced ('{warn[:55]}...')")
    except AssertionError as exc:
        _fail("Corrupt JSON check", str(exc))
    except Exception as exc:
        _fail("Corrupt JSON check (unexpected)", str(exc))
    finally:
        if os.path.exists(corrupt_tmp.name):
            os.unlink(corrupt_tmp.name)
        for f in os.listdir(pm.DATA_DIR):
            if ".corrupt-" in f:
                os.unlink(os.path.join(pm.DATA_DIR, f))
        pm.TASKS_FILE = real_path
        pop_load_warning()

    # ── 5c. Per-record tolerance: bad record skipped, good one loads ──────────
    pop_load_warning()
    mixed_tmp = tempfile.NamedTemporaryFile(
        suffix=".json", dir=pm.DATA_DIR, delete=False, mode="w"
    )
    json.dump([
        {"id": "good-1", "title": "Good task", "priority": "High", "category": "Work",
         "status": "pending", "due_time": None, "created_at": "2026-01-01T00:00:00", "completed_at": None},
        {"broken": "record", "missing": "required fields"},
    ], mixed_tmp)
    mixed_tmp.close()
    pm.TASKS_FILE = mixed_tmp.name
    try:
        result = load_tasks()
        assert len(result) == 1, f"expected 1 valid task, got {len(result)}"
        assert result[0].title == "Good task"
        _ok("Per-record tolerance: 1 good + 1 bad record → loads 1 task")
        warn = pop_load_warning()
        assert warn is not None
        _ok("Per-record tolerance: warning surfaced for skipped record")
    except AssertionError as exc:
        _fail("Per-record tolerance", str(exc))
    except Exception as exc:
        _fail("Per-record tolerance (unexpected)", str(exc))
    finally:
        os.unlink(mixed_tmp.name)
        pm.TASKS_FILE = real_path
        pop_load_warning()

    # ── 5d. Dedup: duplicate id keeps first occurrence ────────────────────────
    pop_load_warning()
    dup_tmp = tempfile.NamedTemporaryFile(
        suffix=".json", dir=pm.DATA_DIR, delete=False, mode="w"
    )
    shared_id = "dup-id-abc"
    json.dump([
        {"id": shared_id, "title": "First",  "priority": "High",   "category": "Work",
         "status": "pending", "due_time": None, "created_at": "2026-01-01T00:00:00", "completed_at": None},
        {"id": shared_id, "title": "Second", "priority": "Medium", "category": "Work",
         "status": "pending", "due_time": None, "created_at": "2026-01-01T00:00:00", "completed_at": None},
    ], dup_tmp)
    dup_tmp.close()
    pm.TASKS_FILE = dup_tmp.name
    try:
        result = load_tasks()
        assert len(result) == 1, f"expected 1 task after dedup, got {len(result)}"
        assert result[0].title == "First", "first occurrence should be kept"
        _ok("Dedup: 2 records with same id → 1 task loaded (first kept)")
        warn = pop_load_warning()
        assert warn is not None
        _ok("Dedup: warning surfaced for dropped duplicate")
    except AssertionError as exc:
        _fail("Dedup check", str(exc))
    except Exception as exc:
        _fail("Dedup check (unexpected)", str(exc))
    finally:
        os.unlink(dup_tmp.name)
        pm.TASKS_FILE = real_path
        pop_load_warning()

    # ── 5e. HTML escaping ─────────────────────────────────────────────────────
    try:
        import html as _html
        evil = '<img src=x onerror=alert(1)>'
        escaped = _html.escape(evil)
        assert "<img" not in escaped and "&lt;" in escaped
        _ok("HTML escape: html.escape() converts < > to entities")
        assert "&amp;" in _html.escape("Bread & Butter")
        _ok("HTML escape: html.escape() converts & to &amp;")
        src = pathlib.Path(project_root) / "components" / "task_card.py"
        assert "_html.escape" in src.read_text()
        _ok("HTML escape: task_card.py source contains _html.escape() call")
    except AssertionError as exc:
        _fail("HTML escape check", str(exc))
    except Exception as exc:
        _fail("HTML escape (unexpected)", str(exc))

    # ── 5f. Platform-safe strftime ────────────────────────────────────────────
    try:
        for fname in ["components/task_card.py", "components/top_bar.py"]:
            content = (pathlib.Path(project_root) / fname).read_text()
            assert "%-" not in content, f"platform-specific '%-' found in {fname}"
            _ok(f"Platform strftime: no '%-' format code in {fname}")
        from components.task_card import _fmt_time
        r1 = _fmt_time("09:05")
        assert not r1.startswith("0"), f"_fmt_time('09:05') has leading zero: '{r1}'"
        _ok(f"Platform strftime: _fmt_time('09:05') → '{r1}' (no leading zero)")
        r2 = _fmt_time("14:30")
        assert "2:30" in r2
        _ok(f"Platform strftime: _fmt_time('14:30') → '{r2}'")
    except AssertionError as exc:
        _fail("Platform strftime check", str(exc))
    except Exception as exc:
        _fail("Platform strftime (unexpected)", str(exc))


# ── 6. Live server health ─────────────────────────────────────────────────────
def check_server(port: int) -> None:
    _section(f"6  Live Server  (http://localhost:{port})")

    base = f"http://localhost:{port}"

    # healthz endpoint
    try:
        req = urllib.request.Request(f"{base}/healthz")
        with urllib.request.urlopen(req, timeout=5) as resp:
            code = resp.getcode()
        if code == 200:
            _ok(f"GET /healthz → {code}")
        else:
            _fail(f"GET /healthz", f"expected 200, got {code}")
    except urllib.error.HTTPError as exc:
        _fail("GET /healthz", f"HTTP {exc.code}")
    except Exception as exc:
        _fail("GET /healthz unreachable", str(exc))

    # main page
    try:
        req = urllib.request.Request(base)
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read(512).decode("utf-8", errors="ignore")
            code = resp.getcode()
        if code == 200 and ("streamlit" in body.lower() or "<!doctype" in body.lower()):
            _ok(f"GET /  → {code}  (HTML response)")
        elif code == 200:
            _ok(f"GET /  → {code}")
        else:
            _fail(f"GET /", f"expected 200, got {code}")
    except urllib.error.HTTPError as exc:
        if exc.code == 502:
            _fail(
                "GET /  → 502 Bad Gateway",
                "server process may not have started — try:  "
                f"streamlit run app.py --server.port {port} --server.headless true",
            )
        else:
            _fail("GET /", f"HTTP {exc.code}")
    except Exception as exc:
        _fail(
            "GET /  unreachable",
            f"{exc}  —  is the app running?  "
            f"streamlit run app.py --server.port {port} --server.headless true",
        )

    # websocket endpoint exists
    try:
        req = urllib.request.Request(f"{base}/_stcore/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            status_body = resp.read().decode()
        if "ok" in status_body.lower():
            _ok("GET /_stcore/health → ok")
        else:
            _ok(f"GET /_stcore/health → {status_body.strip()}")
    except Exception as exc:
        _fail("GET /_stcore/health", str(exc))


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="DailyTaskManager validator")
    parser.add_argument("--server", action="store_true", help="Also check live server")
    parser.add_argument("--port",   type=int, default=8501, help="Streamlit port (default 8501)")
    args = parser.parse_args()

    print(f"\n{BOLD}DailyTaskManager — Validation Suite{RESET}")
    print("=" * 40)

    # Change cwd to project root so relative imports resolve
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    check_imports()
    check_data_model()
    check_persistence()
    check_task_service()
    check_hardening()

    if args.server:
        check_server(args.port)

    # ── Summary ──────────────────────────────────────────────────────────────
    total = _pass_count + _fail_count
    print(f"\n{'=' * 40}")
    print(f"{BOLD}Results:{RESET}  "
          f"{GREEN}{_pass_count} passed{RESET}  "
          f"{(RED + str(_fail_count) + ' failed' + RESET) if _fail_count else str(_fail_count) + ' failed'}  "
          f"/ {total} total")
    print()

    if _fail_count:
        print(f"{RED}Some checks failed. Review the errors above before running the app.{RESET}\n")
        sys.exit(1)
    else:
        print(f"{GREEN}All checks passed.{RESET}  "
              f"Run with:  {BOLD}streamlit run app.py --server.headless true{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
