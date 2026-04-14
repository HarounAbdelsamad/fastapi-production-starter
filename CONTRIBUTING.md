# Contributing

## Getting Started
- Fork and clone the repository.
- Run `make install`.
- Run `make pre-commit-install`.

## Development Workflow
- Use branch prefixes: `feature/`, `fix/`, `docs/`, `chore/`.
- Keep commits focused and descriptive.
- Before push: `make lint && make test`.

## Pull Request Process
- Include a clear summary and test notes.
- Link related issue(s).
- Ensure CI is green.

## Code Style
- Ruff is the source of truth for linting/formatting.
- Add type hints for public functions.
- Avoid `Any` unless truly required.

## Testing
- Place tests under `tests/`.
- Prefer async integration tests for API behavior.
- Maintain at least 70% application coverage.

## Architecture
- Keep separation of concerns: `core`, `db`, `models`, `schemas`, `services`, `routers`.
- Business logic belongs in `services`, not routers.
