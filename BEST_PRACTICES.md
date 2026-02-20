# Project Best Practices

## File Management

### Ignore Temporary Files
*   **Always ignore `__pycache__` directories.** Do not commit them to version control.
*   Exclude `__pycache__` from backups and file searches unless explicitly debugging import issues.
*   The `.gitignore` file is configured to exclude `__pycache__/`.
*   The `Makefile` is configured to clean `__pycache__` directories.

## Coding Standards

### Type Annotations
*   Use strict type annotations for all new code, especially in core modules like `asimov.io`.
*   Ensure compatibility with strict type checkers (e.g., `mypy`).

### Compatibility
*   Ensure code is compatible with Python 3.10+.
*   Verify imports of standard library modules (e.g., `os`, `sys`) are present before use, even if type checkers don't flag them immediately.
