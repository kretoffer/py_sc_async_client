# Code Style Guide

This project uses Ruff as the primary linter and formatter to enforce consistent code style and quality. Below are the key style rules and configuration settings.

## Target Python Version
- Code must be compatible with Python 3.8

- Avoid syntax and standard library features introduced in later versions:

  - No match statements (Python 3.10+)

  - No str.removeprefix() or str.removesuffix() (Python 3.9+)

  - Use TypedDict from typing instead of typing_extensions only if available in 3.8

## Auto-Fix Enabled
- Ruff is configured to automatically fix style violations
- Run Ruff with --fix to apply corrections:

``` bash
ruff check . --fix
```
- Common fixes include:
  - Removing unused imports
  - Reordering imports
  - Simplifying expressions
  - Enforcing consistent whitespace and formatting

## Ruff configuration
```
[tool.ruff]
line-length = 100
target-version = "py38"
fix = true
```
