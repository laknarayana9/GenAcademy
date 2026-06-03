from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class Task:
    title: str
    priority: str            # "High" | "Medium" | "Low"
    category: str            # "Work" | "Personal" | "Errands"
    status: str = "pending"  # "pending" | "completed"
    due_time: Optional[str] = None    # "HH:MM" or None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "category": self.category,
            "status": self.status,
            "due_time": self.due_time,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            title=data["title"],
            priority=data["priority"],
            category=data["category"],
            status=data.get("status", "pending"),
            due_time=data.get("due_time"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            completed_at=data.get("completed_at"),
        )

    @classmethod
    def from_csv_row(cls, row: dict) -> "Task":
        """Create a Task from a validated CSV row dict.
        Generates id and created_at automatically.
        Sets completed_at = now() for rows imported with status='completed'.
        """
        status = (str(row.get("status", "") or "").strip().lower()) or "pending"
        due_time_raw = str(row.get("due_time", "") or "").strip()
        completed_at = datetime.now().isoformat() if status == "completed" else None
        return cls(
            title=str(row["title"]).strip(),
            priority=str(row["priority"]).strip().capitalize(),
            category=str(row["category"]).strip().capitalize(),
            status=status,
            due_time=due_time_raw if due_time_raw else None,
            completed_at=completed_at,
        )
