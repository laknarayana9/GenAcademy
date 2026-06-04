import re
from typing import List, Tuple

import pandas as pd
import streamlit as st

from services.task_service import TaskService, PRIORITIES, CATEGORIES

REQUIRED_COLUMNS = {"title", "priority", "category"}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _validate_rows(df: pd.DataFrame) -> Tuple[List[dict], List[dict]]:
    valid: List[dict] = []
    error_rows: List[dict] = []

    for idx, row in df.iterrows():
        errs = []
        row_num = int(idx) + 2  # 1-indexed + header row offset

        title = str(row.get("title", "") or "").strip()
        priority = str(row.get("priority", "") or "").strip()
        category = str(row.get("category", "") or "").strip()
        status = str(row.get("status", "") or "").strip().lower() or "pending"
        due_time = str(row.get("due_time", "") or "").strip()

        if not title:
            errs.append("title is empty")

        norm_priority = priority.capitalize()
        if norm_priority not in PRIORITIES:
            errs.append(f"priority '{priority}' must be High, Medium, or Low")

        norm_category = category.capitalize()
        if norm_category not in CATEGORIES:
            errs.append(f"category '{category}' must be Work, Personal, or Errands")

        if status not in ("pending", "completed"):
            errs.append(f"status '{status}' must be 'pending' or 'completed'")
            status = "pending"

        if due_time and not _TIME_RE.match(due_time):
            errs.append(f"due_time '{due_time}' must be HH:MM (e.g. 09:30) or blank")
            due_time = ""

        if errs:
            error_rows.append({
                "Row #": row_num,
                "Title": title or "(empty)",
                "Errors": "; ".join(errs),
            })
        else:
            valid.append({
                "title": title,
                "priority": norm_priority,
                "category": norm_category,
                "status": status,
                "due_time": due_time if due_time else None,
            })

    return valid, error_rows


def render_csv_handler(service: TaskService) -> None:
    result = st.session_state.pop("_import_result", None)
    if result:
        if result["imported"]:
            st.success(f"✅ Imported **{result['imported']}** task(s) successfully.")
        if result["duplicates"]:
            st.info(f"ℹ️ **{result['duplicates']}** row(s) skipped — title already exists.")
        if result["errors"]:
            st.warning(f"⚠️ **{result['errors']}** row(s) failed during import. Check logs.")
        if not result["imported"] and not result["errors"]:
            st.info("ℹ️ No new tasks imported — all rows already exist.")

    col_upload, _gap, col_export = st.columns([5, 0.3, 2])

    with col_upload:
        st.markdown('<p class="section-header">Import Tasks from CSV</p>', unsafe_allow_html=True)

        with st.expander("Expected CSV format", expanded=False):
            st.markdown("""
| title | priority | category | status | due_time |
|---|---|---|---|---|
| Fix login bug | High | Work | pending | 09:00 |
| Call dentist | Medium | Personal | completed | |
| Buy groceries | Low | Errands | | 17:30 |

- **title** — required, non-empty string
- **priority** — `High`, `Medium`, or `Low` (case-insensitive)
- **category** — `Work`, `Personal`, or `Errands` (case-insensitive)
- **status** — `pending` or `completed`; defaults to `pending` if blank
- **due_time** — 24-hour `HH:MM` format (e.g. `14:30`) or blank
            """)

        uploaded = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            label_visibility="collapsed",
            key="csv_upload",
        )

        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
            except Exception as exc:
                st.error(f"Could not parse file: {exc}")
                return

            df.columns = [str(c).strip().lower() for c in df.columns]

            missing = REQUIRED_COLUMNS - set(df.columns)
            if missing:
                st.error(
                    f"Missing required column(s): **{', '.join(sorted(missing))}**  \n"
                    f"Your file has: `{', '.join(df.columns.tolist())}`"
                )
                return

            valid_rows, error_rows = _validate_rows(df)

            if error_rows:
                st.warning(f"{len(error_rows)} row(s) have validation errors and will be skipped:")
                st.dataframe(
                    pd.DataFrame(error_rows),
                    use_container_width=True,
                    hide_index=True,
                )

            if valid_rows:
                st.success(f"**{len(valid_rows)} valid row(s)** ready to import.")
                with st.expander("Preview valid rows", expanded=False):
                    st.dataframe(
                        pd.DataFrame(valid_rows),
                        use_container_width=True,
                        hide_index=True,
                    )
                if st.button(
                    f"⬆  Import {len(valid_rows)} Task(s)",
                    type="primary",
                    key="csv_import_btn",
                ):
                    imported, duplicates, errors = service.import_from_rows(valid_rows)
                    st.session_state["_import_result"] = {
                        "imported": imported,
                        "duplicates": duplicates,
                        "errors": errors,
                    }
                    st.rerun()
            else:
                st.error("No valid rows found — fix the errors above and re-upload.")

    with col_export:
        st.markdown('<p class="section-header">Export Tasks</p>', unsafe_allow_html=True)
        all_tasks = service.get_all()
        if all_tasks:
            csv_str = service.to_csv_string()
            st.download_button(
                label=f"⬇  Download CSV  ({len(all_tasks)} tasks)",
                data=csv_str,
                file_name="tasks_export.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.caption("Exports all tasks including completed ones.")
        else:
            st.info("No tasks to export yet.")
