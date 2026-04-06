.PHONY: test lint fmt install-dev

install-dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src/ tests/

fmt:
	ruff format src/ tests/
	ruff check --fix src/ tests/
