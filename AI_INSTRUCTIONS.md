# AI Agent Instructions for DelDuplicator

This document outlines the coding standards, environment preferences, and architectural context for AI agents working on this project.

## 1. Environment & Dependencies (`uv`)
- This project prioritizes the use of [`uv`](https://github.com/astral-sh/uv) for dependency management and scripts.
- Scripts should include [PEP 723](https://peps.python.org/pep-0723/) inline metadata headers.
- Example header:
  ```python
  # /// script
  # dependencies = ["requests", "tqdm"]
  # ///
  ```
- **Execution**: Always prefer `uv run script.py` over direct `python` calls if external dependencies are involved.

## 2. Encoding Standards
- **UTF-8**: All file operations (read/write) MUST force `encoding='utf-8'` explicitly to avoid Windows encoding issues (`cp1252`).
- **Console**: Scripts running on Windows must reconfigure stdout/stderr to UTF-8:
  ```python
  sys.stdout.reconfigure(encoding='utf-8')
  ```

## 3. Project Architecture (SQLite)
The project uses a local SQLite database (`delduplicator.db`) for performance.
- **Key Principle**: Files are Indexed first (path/size/mtime), hashed lazily only on size collision, and deduplicated based on hash.
- **Locking**: Avoid `database locked` errors by separating READ cursors from WRITE cursors. Do not use `UPDATE` inside a loop iterating over a `SELECT` cursor unless you fetch results into memory first.

## 4. Safety First
- **Self-Protection**: Scripts must never delete themselves.
- **Dry Run Default**: Destructive actions (delete) must require an explicit flag.
- **Move > Delete**: Prefer moving files to a quarantine folder over permanent deletion.

## 5. Changelog
- Maintain `CHANGELOG.md` following [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
