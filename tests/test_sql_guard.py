import sqlite3
from contextlib import closing

import pytest

from ops_agent import db
from ops_agent.sql_guard import MAX_ROWS, UnsafeQuery, check


@pytest.mark.parametrize("sql", [
    "SELECT * FROM leads",
    "SELECT trade, COUNT(*) FROM leads GROUP BY trade",
    "WITH won AS (SELECT * FROM leads WHERE status = 'won') SELECT COUNT(*) FROM won",
    "SELECT c.name FROM contractors c JOIN reviews r ON r.contractor_id = c.id WHERE r.rating < 3",
    "SELECT id FROM leads UNION SELECT id FROM reviews",
])
def test_accepts_read_only_queries(sql):
    check(sql)


@pytest.mark.parametrize("sql, reason", [
    ("DELETE FROM reviews", "only SELECT"),
    ("DROP TABLE leads", "only SELECT"),
    ("UPDATE leads SET status = 'won'", "only SELECT"),
    ("INSERT INTO reviews VALUES (1, 1, 1, 5, 'x', '2026-01-01')", "only SELECT"),
    ("SELECT 1; DROP TABLE leads", "exactly one statement"),
    ("PRAGMA writable_schema = 1", "only SELECT"),
    ("ATTACH DATABASE '/tmp/x.db' AS x", "only SELECT"),
    ("SELECT * FROM sqlite_master", "unknown table"),
    ("SELECT * FROM users", "unknown table"),
])
def test_rejects_unsafe_queries(sql, reason):
    with pytest.raises(UnsafeQuery, match=reason):
        check(sql)


def test_cte_names_are_not_treated_as_tables():
    assert check("WITH x AS (SELECT id FROM leads) SELECT * FROM x").tables == {"leads"}


def test_adds_a_limit_when_missing_or_too_high():
    assert f"LIMIT {MAX_ROWS}" in check("SELECT * FROM leads").sql
    assert f"LIMIT {MAX_ROWS}" in check("SELECT * FROM leads LIMIT 100000").sql
    assert "LIMIT 5" in check("SELECT * FROM leads LIMIT 5").sql


def test_connection_is_read_only_even_without_the_validator():
    # Second layer of defence: bypass the validator and write directly.
    with closing(db.connect()) as con, pytest.raises(sqlite3.OperationalError):
        con.execute("DELETE FROM reviews")


def test_run_query_returns_columns_and_rows():
    with closing(db.connect()) as con:
        result = db.run_query(con, "SELECT status, COUNT(*) AS n FROM leads GROUP BY status ORDER BY status")
    assert result["columns"] == ["status", "n"]
    assert sum(n for _, n in result["rows"]) == 1200
