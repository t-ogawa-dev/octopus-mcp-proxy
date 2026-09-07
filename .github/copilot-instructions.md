# Octopus MCP Proxy 開発ルール

This file contains project instructions for VS Code / GitHub Copilot.
See [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md) for detailed structure, ownership, coding conventions, and validation guidance.

## Before Changes

- Start from the target file, symbol, failing test, or reproduction steps.
- Read nearby implementations, callers, and related tests to identify the controlling layer.
- Form a falsifiable hypothesis and choose the cheapest check that can disprove it.
- Check uncommitted changes and never overwrite or discard user changes.

## Implementation

- Preserve the existing Flask Blueprint, SQLAlchemy ORM, and application-factory patterns.
- Keep complex business logic out of controllers and place reusable logic in `app/services/`.
- For schema changes, update the model, Alembic migration, and related tests.
- Update tests and documentation when changing a public API, route, or model contract.
- Do not mix unrelated refactoring, dependency updates, or formatting changes into a task.
- Never put secrets, tokens, or real data in source code, logs, or screenshots.
- Do not edit generated assets manually; regenerate them with existing scripts.

## Editing and Validation

- Use `apply_patch` for manual edits and keep the change focused.
- Run the nearest relevant test, lint, or type check immediately after editing.
- Use `./run_check.sh` for Python quality checks and `./run_tests.sh` for the full suite.
- For template, CSS, or image changes, run related E2E tests or `python scripts/capture_screenshots.py`.
- Report skipped validation, existing warnings, and unresolved risks at completion.
- Do not create commits or branches unless explicitly requested.
