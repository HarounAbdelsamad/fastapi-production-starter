.PHONY: install run test test-cov lint format format-check migrate migrate-new docker-up docker-down clean seed create-admin pre-commit-install

install:
	uv sync --extra dev

run:
	uv run uvicorn app.main:app --reload --port 8000

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=app --cov-report=term-missing -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(msg)"

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	-uv run python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.db')]"
	-uv run python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	-rm -rf .pytest_cache .ruff_cache

seed:
	uv run cli seed

create-admin:
	uv run cli create-admin

pre-commit-install:
	uv run pre-commit install
