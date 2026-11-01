.PHONY: install data test lint eval ask

ENV := $(if $(wildcard .env),--env-file .env)

install:
	uv sync --all-extras

data:
	uv run python -m ops_agent.seed

test:
	uv run pytest -v

lint:
	uv run ruff check .

eval: data
	uv run $(ENV) python -m evals.run --judge

ask: data
	uv run $(ENV) ops-agent -v
