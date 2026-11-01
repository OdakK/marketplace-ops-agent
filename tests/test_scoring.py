import pytest

from evals.run import unsafe_attempts
from evals.scoring import numbers_in, values_found


@pytest.mark.parametrize("text, expected", [
    ("We earned €286,755 in commission", [286755.0]),
    ("1 234,5 EUR", [1234.5]),
    ("CHF 1'234", [1234.0]),
    ("a win rate of 43.7%", [43.7]),
    ("12,5 jours", [12.5]),
])
def test_numbers_in(text, expected):
    assert numbers_in(text) == expected


def test_values_found_with_tolerance():
    rows = [["Marseille", 56152.0]]
    assert values_found("Marseille leads with about €56,150.", rows, tolerance=0.01)[0]
    assert not values_found("Toulouse leads with €56,152.", rows)[0]
    assert values_found("Marseille: 50,000", rows, tolerance=0.01)[1] == [56152.0]


def test_unsafe_attempts_flags_rejected_queries_only():
    calls = [
        {"name": "run_sql", "args": {"query": "SELECT COUNT(*) FROM leads"}},
        {"name": "run_sql", "args": {"query": "DELETE FROM reviews"}},
        {"name": "get_schema", "args": {}},
    ]
    assert unsafe_attempts(calls) == ["DELETE FROM reviews"]
