"""Validate SQL written by the LLM before it reaches the database.

This is the first layer of defence: the query must be a single read-only SELECT over known tables.
The second layer is the connection itself, opened read-only (see db.py), so a query that slipped
through this check still could not write anything.
"""

from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"contractors", "customers", "leads", "reviews"}
MAX_ROWS = 200

# Statement types that must never run, even nested inside a CTE or a subquery.
FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
             exp.Command, exp.Pragma, exp.Attach, exp.Detach, exp.TruncateTable)


class UnsafeQuery(ValueError):
    """Raised when a query is rejected. The message is safe to show to the LLM."""


@dataclass
class CheckedQuery:
    sql: str          # the query that will actually run (with a LIMIT added if needed)
    tables: set[str]


def check(sql: str) -> CheckedQuery:
    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except sqlglot.errors.ParseError as e:
        raise UnsafeQuery(f"could not parse the query: {e}") from None
    if len(statements) != 1:
        raise UnsafeQuery("exactly one statement is allowed")
    tree = statements[0]

    if not isinstance(tree, exp.Query):
        raise UnsafeQuery(f"only SELECT queries are allowed, got {tree.key.upper()}")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN):
            raise UnsafeQuery(f"{node.key.upper()} is not allowed")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    tables = {t.name.lower() for t in tree.find_all(exp.Table)} - cte_names
    unknown = tables - ALLOWED_TABLES
    if unknown:
        raise UnsafeQuery(f"unknown table(s): {', '.join(sorted(unknown))}. "
                          f"Available: {', '.join(sorted(ALLOWED_TABLES))}")

    # Cap the result size so a careless query cannot flood the context window.
    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        try:
            if int(limit.expression.name) > MAX_ROWS:
                tree = tree.limit(MAX_ROWS)
        except (AttributeError, ValueError):
            tree = tree.limit(MAX_ROWS)

    return CheckedQuery(sql=tree.sql(dialect="sqlite"), tables=tables)
