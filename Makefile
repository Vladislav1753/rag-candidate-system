DC = docker compose -f docker-compose.yml
PYTHON = .venv/Scripts/python.exe

install:
	uv sync --group dev --extra frontend --extra evaluation

test:
	$(PYTHON) -m pytest

typecheck:
	$(PYTHON) -m mypy app rag

lint:
	$(PYTHON) -m ruff check .

lint-fix:
	$(PYTHON) -m ruff check --fix .

format:
	$(PYTHON) -m ruff format .

pre-commit:
	$(PYTHON) -m pre_commit run --all-files

up:
	$(DC) up

up-build:
	$(DC) up --build

down:
	$(DC) down

down-v:
	$(DC) down -v

logs:
	$(DC) logs -f
