from pathlib import Path

import pytest

from ops_agent import db, seed


@pytest.fixture(scope="session", autouse=True)
def database(tmp_path_factory) -> Path:
    path = seed.build(tmp_path_factory.mktemp("data") / "marketplace.db")
    db.DB_PATH = path
    return path
