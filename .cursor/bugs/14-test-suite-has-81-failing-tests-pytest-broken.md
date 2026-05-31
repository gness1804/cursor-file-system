# Test Suite Has 81 Failing Tests Pytest Broken

## Working directory

`/home/user/cursor-file-system`

## Contents

The test suite has 81 failing tests (223 passing) on the current branch. These failures pre-date the `infrastructure-and-deployment` category work and break `pytest` for everyone. They fall into four clusters:

### 1. `tests/test_cli.py` — 78 failures (the big one)

Every failing test errors with:

```
AttributeError: 'CliRunner' object has no attribute 'isolated_filesystem'
```

These tests call `runner.isolated_filesystem(tmp_path)` (78 occurrences). The installed Typer (`0.26.4`) / Click (`8.4.1`) combination no longer exposes `isolated_filesystem` on `typer.testing.CliRunner`. This is a test-harness/dependency-drift issue, not a product bug.

**Likely fix:** replace `runner.isolated_filesystem(...)` with a `tmp_path`/`monkeypatch.chdir(...)` pattern, or pin/adjust the Typer/Click versions in `pyproject.toml` to a combination where the helper exists. Worth confirming what API the project intends to support.

### 2. `tests/test_documents.py::TestCreateDocument::test_create_document_empty_content`

Test asserts `result.read_text() == ""`, but `create_document()` now always writes the structured skeleton (`# Title`, `## Working directory`, `## Contents`, ...). The test is stale relative to current behavior. Either the test should assert the skeleton, or `create_document` should honor truly-empty content — needs a product decision.

### 3. `tests/test_documents.py::TestListDocuments::test_list_documents_ignores_non_md_files`

Test creates `1-test.md`, `other.txt`, and `README.md` (no ID prefix), then asserts `len(result["bugs"]) == 1`. Actual is `2` — `README.md` (a `.md` file without an ID prefix) is now included with `conforms_to_naming: False`. The listing behavior changed to include non-conforming `.md` files; the test (and possibly the intended behavior) need to be reconciled.

### 4. `tests/test_editor.py::TestDetectEditor::test_detect_editor_from_visual`

Test asserts `detect_editor() == "nano"`, but does not isolate the `EDITOR`/`VISUAL` environment or the installed-editor fallback, so it returns `"vim"` in this environment. The test should `monkeypatch` the relevant env vars / detection path so it is hermetic.

## Acceptance criteria

- `pytest` passes (0 failures) in a clean dev environment (`pip install -e ".[dev]"`).
- The `test_cli.py` `isolated_filesystem` breakage is resolved (harness fix or dependency pin) and documented.
- Stale `test_documents.py` and `test_editor.py` tests are reconciled with intended behavior (fix the test or the product code, whichever is correct).
- A note on the supported Typer/Click version range is added if the fix involves pinning.
