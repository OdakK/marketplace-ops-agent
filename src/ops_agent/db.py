"""Read-only access to the marketplace database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from . import sql_guard

DB_PATH = Path(os.environ.get("OPS_AGENT_DB", "data/marketplace.db"))


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run `python -m ops_agent.seed` first")
    # mode=ro + query_only: the second layer of defence, independent from the SQL validator.
    con = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    con.row_factory = sqlite3.Row
    return con


def schema(con: sqlite3.Connection) -> str:
    rows = con.execute("SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
    return "\n\n".join(r["sql"] for r in rows)


def run_query(con: sqlite3.Connection, sql: str) -> dict:
    checked = sql_guard.check(sql)
    cur = con.execute(checked.sql)
    columns = [d[0] for d in cur.description]
    rows = [list(r) for r in cur.fetchall()]
    return {"sql": checked.sql, "columns": columns, "rows": rows,
            "truncated": len(rows) == sql_guard.MAX_ROWS}
