import csv
import io
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from models.task import Task
from utils.persistence import load_tasks, save_tasks

logger = logging.getLogger(__name__)

PRIORITIES: List[str] = ["High", "Medium", "Low"]
CATEGORIES: List[str] = ["Work", "Personal", "Errands"]
PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}


class TaskService:

    def add(
        self,
        title: str,
        priority: str,
        category: str,
        due_time: Optional[str] = None,
    ) -> Task:
        tasks = load_tasks()
        task = Task(
            title=title.strip(),
            priority=priority,
            category=category,
            due_time=due_time or None,
        )
        tasks.append(task)
        save_tasks(tasks)
        return task

    def complete(self, task_id: str) -> None:
        tasks = load_tasks()
        for task in tasks:
            if task.id == task_id and task.status == "pending":
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                break
        save_tasks(tasks)

    def delete(self, task_id: str) -> None:
        tasks = load_tasks()
        tasks = [t for t in tasks if t.id != task_id]
        save_tasks(tasks)

    def get_sorted_filtered(
        self,
        category_filter: Optional[str] = None,
        sort_mode: str = "Priority",
    ) -> Tuple[List[Task], List[Task]]:
        tasks = load_tasks()

        if category_filter and category_filter != "All":
            tasks = [t for t in tasks if t.category == category_filter]

        sort_key = (
            self._due_time_sort_key if sort_mode == "Due Time"
            else self._pending_sort_key
        )
        pending = sorted(
            [t for t in tasks if t.status == "pending"],
            key=sort_key,
        )
        completed = sorted(
            [t for t in tasks if t.status == "completed"],
            key=lambda t: t.completed_at or "",
            reverse=True,
        )
        return pending, completed

    def get_all(self) -> List[Task]:
        """Return all tasks unfiltered — used by insights and export."""
        return load_tasks()

    def import_from_rows(self, rows: List[dict]) -> Tuple[int, int, int]:
        """Bulk-import validated CSV row dicts.
        Returns (imported_count, duplicate_count, error_count).
        Rows whose title already exists (case-insensitive) are silently skipped.
        """
        existing = load_tasks()
        existing_titles = {t.title.strip().lower() for t in existing}
        imported = 0
        duplicates = 0
        errors = 0
        for row in rows:
            try:
                task = Task.from_csv_row(row)
                if task.title.strip().lower() in existing_titles:
                    duplicates += 1
                    logger.info("Skipping duplicate task title: '%s'", task.title)
                    continue
                existing.append(task)
                existing_titles.add(task.title.strip().lower())
                imported += 1
            except (KeyError, ValueError) as exc:
                errors += 1
                logger.warning("Skipping CSV row during import (%s): %s", exc, row)
        if imported:
            save_tasks(existing)
        return imported, duplicates, errors

    def to_csv_string(self) -> str:
        """Serialise all tasks to a CSV string for download."""
        fields = [
            "id", "title", "priority", "category",
            "status", "due_time", "created_at", "completed_at",
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for task in load_tasks():
            writer.writerow(task.to_dict())
        return buf.getvalue()

    @staticmethod
    def _pending_sort_key(task: Task) -> tuple:
        rank = PRIORITY_RANK.get(task.priority, 99)
        # Tasks WITH a due time sort before tasks without (0 < 1)
        has_time = 0 if task.due_time else 1
        time_val = task.due_time if task.due_time else "99:99"
        return (rank, has_time, time_val, task.created_at)

    @staticmethod
    def _due_time_sort_key(task: Task) -> tuple:
        # Timed tasks first, sorted by earliest time; untimed tasks last by priority
        has_time = 0 if task.due_time else 1
        time_val = task.due_time if task.due_time else "99:99"
        rank = PRIORITY_RANK.get(task.priority, 99)
        return (has_time, time_val, rank, task.created_at)
