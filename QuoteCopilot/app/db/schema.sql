-- QuoteCopilot business database schema (quotecopilot.db).
-- Owned by the application. LangGraph checkpoints live in a separate DB.

CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    quote_id      TEXT NOT NULL,
    status        TEXT NOT NULL,
    current_node  TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decision_packets (
    run_id             TEXT PRIMARY KEY REFERENCES runs(run_id),
    recommendation     TEXT NOT NULL,
    confidence         REAL,
    reason_codes       TEXT,   -- JSON array
    citations          TEXT,   -- JSON array of {chunk_id, source, text}
    facts_used         TEXT,   -- JSON
    premium_indication REAL,
    next_steps         TEXT,   -- JSON array
    review_status      TEXT,
    created_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL REFERENCES runs(run_id),
    node       TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- started|completed|paused|resumed|failed
    payload    TEXT,            -- JSON snapshot of relevant state slice
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_tasks (
    run_id        TEXT PRIMARY KEY REFERENCES runs(run_id),
    status        TEXT NOT NULL,   -- pending|approved|rejected|info_requested|closed
    priority      TEXT NOT NULL,   -- high|medium|low
    trigger       TEXT NOT NULL,   -- missing_info|refer|decline|verification_failure
    review_packet TEXT,            -- JSON
    reviewer_note TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- Run lifecycle stores follow-up questions while a run is paused.
CREATE TABLE IF NOT EXISTS pending_questions (
    run_id     TEXT PRIMARY KEY REFERENCES runs(run_id),
    questions  TEXT NOT NULL,      -- JSON array of required_questions
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_events(run_id);
CREATE INDEX IF NOT EXISTS idx_review_status ON review_tasks(status);
