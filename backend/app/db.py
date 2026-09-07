from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "artifacts" / "evaluation.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenario_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    scenario_id TEXT NOT NULL,
    workflow TEXT NOT NULL,
    passed INTEGER NOT NULL,
    score REAL NOT NULL,
    payload_json TEXT NOT NULL,
    human_override TEXT,
    human_note TEXT,
    FOREIGN KEY(run_id) REFERENCES runs(id)
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_run(output: dict[str, Any]) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO runs(agent_version, summary_json) VALUES (?, ?)",
            (output["summary"]["agent_version"], json.dumps(output["summary"])),
        )
        run_id = int(cur.lastrowid)
        for item in output["results"]:
            conn.execute(
                """INSERT INTO scenario_results
                (run_id, scenario_id, workflow, passed, score, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    item["scenario_id"],
                    item["workflow"],
                    int(item["evaluation"]["passed"]),
                    item["evaluation"]["weighted_score"],
                    json.dumps(item),
                ),
            )
        return run_id


def list_runs() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()
    return [{**dict(r), "summary": json.loads(r["summary_json"])} for r in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            return None
        result_rows = conn.execute("SELECT * FROM scenario_results WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
    results = []
    for row in result_rows:
        payload = json.loads(row["payload_json"])
        payload["result_id"] = row["id"]
        payload["human_override"] = row["human_override"]
        payload["human_note"] = row["human_note"]
        results.append(payload)
    return {"id": run["id"], "agent_version": run["agent_version"], "created_at": run["created_at"], "summary": json.loads(run["summary_json"]), "results": results}


def review_result(result_id: int, label: str | None, note: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE scenario_results SET human_override = ?, human_note = ? WHERE id = ?",
            (label, note, result_id),
        )
