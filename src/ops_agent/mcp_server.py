"""MCP server that exposes the marketplace database to any MCP client (this agent, Claude Desktop, ...).

Run it over stdio: python -m ops_agent.mcp_server
"""

from __future__ import annotations

import json
from contextlib import closing

from mcp.server.fastmcp import FastMCP

from . import db
from .sql_guard import UnsafeQuery

mcp = FastMCP("marketplace-db")


def _wrap(payload: dict | str) -> str:
    # Mark tool output explicitly as untrusted data, so the model never mistakes it for instructions.
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
    return f"<untrusted_data>\n{body}\n</untrusted_data>"


@mcp.tool()
def get_schema() -> str:
    """Return the CREATE TABLE statements of every table, with column comments."""
    with closing(db.connect()) as con:
        return db.schema(con)


@mcp.tool()
def run_sql(query: str) -> str:
    """Run one read-only SQLite SELECT query and return columns and rows as JSON.

    Only SELECT is allowed, results are capped at 200 rows. Dates are ISO strings (YYYY-MM-DD).
    """
    try:
        with closing(db.connect()) as con:
            return _wrap(db.run_query(con, query))
    except UnsafeQuery as e:
        return f"Query rejected: {e}"
    except Exception as e:  # SQL errors go back to the model so it can fix its query
        return f"SQL error: {e}"


@mcp.tool()
def contractor_scorecard(contractor_id: int) -> str:
    """Key metrics for one contractor: leads, win rate, median response time, average rating, revenue."""
    sql = """
        SELECT c.id, c.name, c.trade, c.city, c.active,
               COUNT(l.id) AS leads,
               ROUND(1.0 * SUM(l.status = 'won') / NULLIF(SUM(l.status IN ('won', 'lost')), 0), 3)
                   AS win_rate,
               ROUND(AVG(julianday(l.responded_on) - julianday(l.created_on)), 1) AS avg_response_days,
               (SELECT ROUND(AVG(rating), 2) FROM reviews r WHERE r.contractor_id = c.id) AS avg_rating,
               ROUND(SUM(CASE WHEN l.status = 'won' THEN l.quote_amount * l.commission_rate END), 2)
                   AS commission_eur
        FROM contractors c LEFT JOIN leads l ON l.contractor_id = c.id
        WHERE c.id = ?
        GROUP BY c.id
    """
    with closing(db.connect()) as con:
        row = con.execute(sql, (contractor_id,)).fetchone()
    return _wrap(dict(row)) if row else f"No contractor with id {contractor_id}"


if __name__ == "__main__":
    mcp.run()
