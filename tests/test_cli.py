"""Integration tests for CLI commands."""

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cfs.cli import app


@contextmanager
def isolated_filesystem(temp_dir):
    """Run a block inside a fresh, empty directory created under ``temp_dir``.

    Drop-in replacement for ``CliRunner.isolated_filesystem(temp_dir)``, which
    was removed in newer Typer/Click releases. It mirrors Click's behavior: a
    new empty temp directory is created *inside* ``temp_dir`` (a pytest
    ``tmp_path``), the cwd is switched to it, and the previous cwd is restored
    on exit. Creating a fresh subdirectory — rather than chdir-ing into
    ``temp_dir`` itself — keeps each test isolated from anything the fixture
    placed in ``temp_dir``, and makes the suite independent of the installed
    Typer/Click version.
    """
    previous_cwd = os.getcwd()
    new_dir = tempfile.mkdtemp(dir=temp_dir)
    os.chdir(new_dir)
    try:
        yield Path(new_dir)
    finally:
        os.chdir(previous_cwd)
        shutil.rmtree(new_dir, ignore_errors=True)


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_cfs(tmp_path):
    """Create a temporary CFS structure for testing."""
    cursor_dir = tmp_path / ".cursor"
    cursor_dir.mkdir()

    # Create category directories
    for category in ["bugs", "features", "research", "rules"]:
        (cursor_dir / category).mkdir()

    return tmp_path, cursor_dir


class TestInitCommand:
    """Tests for `cfs init` command."""

    def test_init_creates_structure(self, runner, tmp_path):
        """Test that init creates the CFS structure."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert (Path.cwd() / ".cursor").exists()
            assert (Path.cwd() / ".cursor" / "bugs").exists()
            assert (Path.cwd() / ".cursor" / "features").exists()

    def test_init_creates_init_md(self, runner, tmp_path):
        """Test that init creates init.md file."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            init_file = Path.cwd() / ".cursor" / "init.md"
            assert init_file.exists()
            assert "CFS Initialization" in init_file.read_text()

    def test_init_with_existing_cfs(self, runner, temp_cfs):
        """Test init behavior when CFS already exists."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            # First init
            result1 = runner.invoke(app, ["init"])
            assert result1.exit_code == 0

            # Second init (should prompt)
            result2 = runner.invoke(app, ["init"], input="n\n")
            assert result2.exit_code != 0  # Should abort

    def test_init_with_force_flag(self, runner, temp_cfs):
        """Test init with --force flag."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            # First init
            runner.invoke(app, ["init"])

            # Second init with force
            result = runner.invoke(app, ["init", "--force"])
            assert result.exit_code == 0


class TestCreateCommand:
    """Tests for `cfs instructions <category> create` command."""

    def test_create_document_success(self, runner, tmp_path):
        """Test successful document creation."""
        # Create CFS structure inside isolated filesystem
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(
                app,
                ["instructions", "bugs", "create", "--title", "Test Bug"],
                input="0\n",  # Decline edit prompt
            )

            assert result.exit_code == 0
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert bug_file.exists()

    def test_create_document_with_prompt(self, runner, tmp_path):
        """Test document creation with title prompt."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(
                app,
                ["instructions", "bugs", "create"],
                input="Test Bug\n0\n",  # Title, then no edit
            )

            assert result.exit_code == 0
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert bug_file.exists()

    def test_create_document_invalid_category(self, runner, tmp_path):
        """Test that invalid category raises error."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()

            result = runner.invoke(
                app,
                ["instructions", "invalid", "create", "--title", "Test"],
            )

            assert result.exit_code != 0
            # Typer catches invalid commands before our validation
            # So we check for Typer's error message
            assert (
                "No such command" in result.stderr
                or "Invalid category" in result.stdout
                or "Invalid category" in result.stderr
            )

    def test_create_document_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "create", "--title", "Test"],
            )

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout

    def test_create_document_with_content_flag(self, runner, tmp_path):
        """Test non-interactive document creation with --content flag."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(
                app,
                [
                    "instructions",
                    "bugs",
                    "create",
                    "--title",
                    "Non Interactive Bug",
                    "--content",
                    "This bug happens in non-interactive mode",
                ],
            )

            assert result.exit_code == 0
            bug_file = cursor_dir / "bugs" / "1-non-interactive-bug.md"
            assert bug_file.exists()
            content = bug_file.read_text()
            assert "# Non Interactive Bug" in content
            assert "## Contents" in content
            assert "This bug happens in non-interactive mode" in content
            assert "## Acceptance criteria" in content

    def test_create_document_with_content_flag_no_editor_prompt(self, runner, tmp_path):
        """Test that --content flag skips the editor prompt entirely."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "features").mkdir()

            result = runner.invoke(
                app,
                [
                    "instructions",
                    "features",
                    "create",
                    "--title",
                    "Test Feature",
                    "--content",
                    "Feature description",
                ],
            )

            assert result.exit_code == 0
            # Should not contain editor selection text
            assert "Select an editor" not in result.stdout


class TestCategoryCommand:
    """Tests for `cfs instructions category` commands."""

    def test_create_custom_category(self, runner, tmp_path):
        """Create a custom category directory."""
        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()

            result = runner.invoke(app, ["instructions", "category", "create", "work"])

            assert result.exit_code == 0
            assert (cursor_dir / "work").exists()

    def test_create_custom_category_hidden(self, runner, tmp_path):
        """Creating with --hidden persists hidden category config."""
        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()

            result = runner.invoke(
                app,
                ["instructions", "category", "create", "work", "--hidden"],
            )

            assert result.exit_code == 0
            config_path = cursor_dir / ".cfs-categories.json"
            assert config_path.exists()
            config = json.loads(config_path.read_text(encoding="utf-8"))
            assert "work" in config["hidden_categories"]

    def test_use_custom_category_after_create(self, runner, tmp_path):
        """Custom category can be used with standard category commands."""
        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()

            create_result = runner.invoke(app, ["instructions", "category", "create", "work"])
            assert create_result.exit_code == 0

            doc_result = runner.invoke(
                app,
                [
                    "instructions",
                    "work",
                    "create",
                    "--title",
                    "Weekly Plan",
                    "--content",
                    "Plan sprint work",
                ],
            )
            assert doc_result.exit_code == 0
            assert (cursor_dir / "work" / "1-weekly-plan.md").exists()


class TestEditCommand:
    """Tests for `cfs instructions <category> edit` command."""

    def test_edit_document_success(self, runner, tmp_path):
        """Test successful document editing."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure and document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            bug_file.write_text("Old content")

            with patch("cfs.editor.edit_content", return_value="New content"):
                result = runner.invoke(
                    app,
                    ["instructions", "bugs", "edit", "1"],
                    input="1\n",  # Select default editor
                )

                assert result.exit_code == 0
                assert bug_file.read_text() == "New content"

    def test_edit_document_not_found(self, runner, temp_cfs):
        """Test editing non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "bugs", "edit", "999"])

            assert result.exit_code != 0
            assert "not found" in result.stdout

    def test_edit_document_with_content_flag(self, runner, tmp_path):
        """`edit -c` replaces the Contents body while preserving structure."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            bug_file.write_text(
                "# Test Bug\n\n"
                "## Working directory\n\n`~/proj`\n\n"
                "## Contents\n\nOld body\n\n"
                "## Acceptance criteria\n\nDone when fixed\n"
            )

            result = runner.invoke(
                app,
                [
                    "instructions",
                    "bugs",
                    "edit",
                    "1",
                    "--content",
                    "New content via non-interactive mode",
                ],
            )

            assert result.exit_code == 0
            content = bug_file.read_text()
            # New body landed in the Contents section.
            assert "New content via non-interactive mode" in content
            assert "Old body" not in content
            # Title and other sections are preserved.
            assert "# Test Bug" in content
            assert "## Working directory" in content
            assert "`~/proj`" in content
            assert "## Acceptance criteria" in content
            assert "Done when fixed" in content
            # Should not contain editor selection text
            assert "Select an editor" not in result.stdout

    def test_edit_document_with_content_flag_preserves_frontmatter(self, runner, tmp_path):
        """`edit -c` must not drop YAML frontmatter (e.g. github_issue:)."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            bug_file.write_text(
                "---\ngithub_issue: 42\n---\n"
                "# Test Bug\n\n"
                "## Working directory\n\n`~/proj`\n\n"
                "## Contents\n\nOld body\n\n"
                "## Acceptance criteria\n\n"
            )

            result = runner.invoke(
                app,
                ["instructions", "bugs", "edit", "1", "--content", "Fresh body"],
            )

            assert result.exit_code == 0
            content = bug_file.read_text()
            assert "github_issue: 42" in content
            assert content.startswith("---\n")
            assert "Fresh body" in content
            assert "Old body" not in content
            assert "# Test Bug" in content

    def test_create_then_edit_content_round_trip(self, runner, tmp_path):
        """create -c then edit -c yields a single consistent structure."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            create_result = runner.invoke(
                app,
                ["instructions", "bugs", "create", "-t", "Round Trip", "-c", "First body"],
            )
            assert create_result.exit_code == 0
            bug_file = cursor_dir / "bugs" / "1-round-trip.md"
            assert bug_file.exists()

            edit_result = runner.invoke(
                app,
                ["instructions", "bugs", "edit", "1", "-c", "Second body"],
            )
            assert edit_result.exit_code == 0
            content = bug_file.read_text()
            # No duplicated section headers.
            assert content.count("## Working directory") == 1
            assert content.count("## Contents") == 1
            assert content.count("## Acceptance criteria") == 1
            assert "Second body" in content
            assert "First body" not in content

    def test_edit_document_with_content_flag_no_contents_heading(self, runner, tmp_path):
        """Freeform doc without a Contents heading still keeps frontmatter."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            bug_file.write_text("---\ngithub_issue: 7\n---\nJust some freeform notes\n")

            result = runner.invoke(
                app,
                ["instructions", "bugs", "edit", "1", "--content", "Replaced body"],
            )

            assert result.exit_code == 0
            content = bug_file.read_text()
            assert "github_issue: 7" in content
            assert "Replaced body" in content
            assert "Just some freeform notes" not in content

    def test_edit_document_with_content_flag_not_found(self, runner, temp_cfs):
        """Test non-interactive edit of non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "edit", "999", "--content", "New content"],
            )

            assert result.exit_code != 0
            assert "not found" in result.stdout


class TestDeleteCommand:
    """Tests for `cfs instructions <category> delete` command."""

    def test_delete_document_success(self, runner, temp_cfs):
        """Test successful document deletion."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("Content")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "delete", "1"],
                input="y\n",  # Confirm deletion
            )

            assert result.exit_code == 0
            assert not bug_file.exists()

    def test_delete_document_without_confirmation(self, runner, temp_cfs):
        """Test that deletion requires confirmation."""
        tmp_path, cursor_dir = temp_cfs

        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("Content")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "delete", "1"],
                input="n\n",  # Don't confirm
            )

            assert result.exit_code != 0
            assert bug_file.exists()  # File should still exist


class TestCompleteCommand:
    """Tests for `cfs instructions <category> complete` command."""

    def test_complete_document_success(self, runner, temp_cfs):
        """Test successful document completion with confirmation."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "complete", "1"],
                input="y\n",  # Confirm completion
            )

            assert result.exit_code == 0
            # File should be renamed with DONE prefix
            completed_file = cursor_dir / "bugs" / "1-DONE-test-bug.md"
            assert completed_file.exists()
            assert not bug_file.exists()

    def test_complete_document_with_force_flag(self, runner, temp_cfs):
        """Test completing document with --force flag skips confirmation."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "complete", "1", "--force"],
            )

            assert result.exit_code == 0
            # File should be renamed with DONE prefix
            completed_file = cursor_dir / "bugs" / "1-DONE-test-bug.md"
            assert completed_file.exists()
            assert not bug_file.exists()

    def test_complete_document_with_y_flag(self, runner, temp_cfs):
        """Test completing document with -y flag skips confirmation."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "complete", "1", "-y"],
            )

            assert result.exit_code == 0
            # File should be renamed with DONE prefix
            completed_file = cursor_dir / "bugs" / "1-DONE-test-bug.md"
            assert completed_file.exists()
            assert not bug_file.exists()

    def test_complete_document_without_confirmation(self, runner, temp_cfs):
        """Test that completion requires confirmation."""
        tmp_path, cursor_dir = temp_cfs

        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "complete", "1"],
                input="n\n",  # Don't confirm
            )

            assert result.exit_code != 0
            assert bug_file.exists()  # File should still exist
            assert "Operation cancelled" in result.stdout

    def test_complete_document_not_found(self, runner, temp_cfs):
        """Test completing non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "complete", "999", "--force"],
            )

            assert result.exit_code != 0
            assert "not found" in result.stdout


class TestUncompleteCommand:
    """Tests for `cfs instructions <category> uncomplete` command."""

    def test_uncomplete_document_success(self, runner, temp_cfs):
        """Test successfully uncompleting a DONE document with confirmation."""
        tmp_path, cursor_dir = temp_cfs

        done_file = cursor_dir / "bugs" / "1-DONE-test-bug.md"
        done_file.parent.mkdir(parents=True, exist_ok=True)
        done_file.write_text("# Test Bug\n\nContent\n\n<!-- DONE -->\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "uncomplete", "1"],
                input="y\n",
            )

            assert result.exit_code == 0
            uncompleted_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert uncompleted_file.exists()
            assert not done_file.exists()

    def test_uncomplete_document_with_force_flag(self, runner, temp_cfs):
        """Test uncompleting a document with --force flag skips confirmation."""
        tmp_path, cursor_dir = temp_cfs

        done_file = cursor_dir / "bugs" / "1-DONE-test-bug.md"
        done_file.parent.mkdir(parents=True, exist_ok=True)
        done_file.write_text("# Test Bug\n\nContent\n\n<!-- DONE -->\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "uncomplete", "1", "--force"],
            )

            assert result.exit_code == 0
            uncompleted_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert uncompleted_file.exists()
            assert not done_file.exists()

    def test_uncomplete_document_cancellation(self, runner, temp_cfs):
        """Test that uncomplete requires confirmation and can be cancelled."""
        tmp_path, cursor_dir = temp_cfs

        done_file = cursor_dir / "bugs" / "1-DONE-test-bug.md"
        done_file.parent.mkdir(parents=True, exist_ok=True)
        done_file.write_text("# Test Bug\n\nContent\n\n<!-- DONE -->\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "uncomplete", "1"],
                input="n\n",
            )

            assert result.exit_code != 0
            assert done_file.exists()
            assert "Operation cancelled" in result.stdout

    def test_uncomplete_document_not_done(self, runner, temp_cfs):
        """Test uncompleting a document that is not marked as done."""
        tmp_path, cursor_dir = temp_cfs

        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.parent.mkdir(parents=True, exist_ok=True)
        bug_file.write_text("# Test Bug\n\nContent")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "uncomplete", "1", "--force"],
            )

            assert result.exit_code != 0

    def test_uncomplete_document_not_found(self, runner, temp_cfs):
        """Test uncompleting a non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "uncomplete", "999", "--force"],
            )

            assert result.exit_code != 0
            assert "not found" in result.stdout


class TestUncloseCommand:
    """Tests for `cfs instructions <category> unclose` command."""

    def test_unclose_document_success(self, runner, temp_cfs):
        """Test successfully unclosing a CLOSED document with confirmation."""
        tmp_path, cursor_dir = temp_cfs

        closed_file = cursor_dir / "bugs" / "1-CLOSED-test-bug.md"
        closed_file.parent.mkdir(parents=True, exist_ok=True)
        closed_file.write_text("# Test Bug\n\nContent\n\n<!-- CLOSED -->\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "unclose", "1"],
                input="y\n",
            )

            assert result.exit_code == 0
            unclosed_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert unclosed_file.exists()
            assert not closed_file.exists()

    def test_unclose_document_with_force_flag(self, runner, temp_cfs):
        """Test unclosing a document with --force flag skips confirmation."""
        tmp_path, cursor_dir = temp_cfs

        closed_file = cursor_dir / "bugs" / "1-CLOSED-test-bug.md"
        closed_file.parent.mkdir(parents=True, exist_ok=True)
        closed_file.write_text("# Test Bug\n\nContent\n\n<!-- CLOSED -->\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "unclose", "1", "--force"],
            )

            assert result.exit_code == 0
            unclosed_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert unclosed_file.exists()
            assert not closed_file.exists()

    def test_unclose_document_cancellation(self, runner, temp_cfs):
        """Test that unclose requires confirmation and can be cancelled."""
        tmp_path, cursor_dir = temp_cfs

        closed_file = cursor_dir / "bugs" / "1-CLOSED-test-bug.md"
        closed_file.parent.mkdir(parents=True, exist_ok=True)
        closed_file.write_text("# Test Bug\n\nContent\n\n<!-- CLOSED -->\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "unclose", "1"],
                input="n\n",
            )

            assert result.exit_code != 0
            assert closed_file.exists()
            assert "Operation cancelled" in result.stdout

    def test_unclose_document_not_closed(self, runner, temp_cfs):
        """Test unclosing a document that is not marked as closed."""
        tmp_path, cursor_dir = temp_cfs

        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.parent.mkdir(parents=True, exist_ok=True)
        bug_file.write_text("# Test Bug\n\nContent")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "unclose", "1", "--force"],
            )

            assert result.exit_code != 0

    def test_unclose_document_not_found(self, runner, temp_cfs):
        """Test unclosing a non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "unclose", "999", "--force"],
            )

            assert result.exit_code != 0
            assert "not found" in result.stdout


class TestCloseCommand:
    """Tests for `cfs instructions <category> close` command."""

    def test_close_document_success(self, runner, temp_cfs):
        """Test successful document closing with confirmation."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "close", "1"],
                input="y\n",  # Confirm closing
            )

            assert result.exit_code == 0
            # File should be renamed with CLOSED prefix
            closed_file = cursor_dir / "bugs" / "1-CLOSED-test-bug.md"
            assert closed_file.exists()
            assert not bug_file.exists()

    def test_close_document_with_force_flag(self, runner, temp_cfs):
        """Test closing document with --force flag skips confirmation."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "close", "1", "--force"],
            )

            assert result.exit_code == 0
            # File should be renamed with CLOSED prefix
            closed_file = cursor_dir / "bugs" / "1-CLOSED-test-bug.md"
            assert closed_file.exists()
            assert not bug_file.exists()

    def test_close_document_not_found(self, runner, temp_cfs):
        """Test closing non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "close", "999", "--force"],
            )

            assert result.exit_code != 0
            assert "not found" in result.stdout


class TestViewCommand:
    """Tests for `cfs instructions view` command."""

    def test_view_all_documents(self, runner, temp_cfs):
        """Test viewing all documents."""
        tmp_path, cursor_dir = temp_cfs

        # Create some documents
        (cursor_dir / "bugs" / "1-bug1.md").write_text("content")
        (cursor_dir / "features" / "1-feature1.md").write_text("content")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "view"])

            assert result.exit_code == 0
            assert "bugs" in result.stdout.lower()
            assert "features" in result.stdout.lower()

    def test_view_empty_cfs(self, runner, temp_cfs):
        """Test viewing empty CFS structure."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "view"])

            assert result.exit_code == 0

    def test_view_shortcut_shows_incomplete_only(self, runner, temp_cfs):
        """Test that `cfs view` shows only incomplete documents (shortcut for `cfs i view -i`)."""
        tmp_path, cursor_dir = temp_cfs

        # Create incomplete and complete documents
        (cursor_dir / "bugs" / "1-incomplete-bug.md").write_text("content")
        (cursor_dir / "bugs" / "2-DONE-completed-bug.md").write_text("content")
        (cursor_dir / "features" / "1-incomplete-feature.md").write_text("content")
        (cursor_dir / "features" / "2-CLOSED-closed-feature.md").write_text("content")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["view"])

            assert result.exit_code == 0
            # Should show incomplete documents
            assert "incomplete-bug" in result.stdout.lower()
            assert "incomplete-feature" in result.stdout.lower()
            # Should NOT show completed/closed documents
            assert "completed-bug" not in result.stdout.lower()
            assert "closed-feature" not in result.stdout.lower()
            # Should indicate "Incomplete Only" in the title
            assert "incomplete only" in result.stdout.lower()


class TestRulesCreateCommand:
    """Tests for `cfs rules create` command."""

    def test_rules_create_success(self, runner, temp_cfs):
        """Test successful rules document creation."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["rules", "create", "--name", "test-rules"],
            )

            assert result.exit_code == 0
            rules_file = cursor_dir / "rules" / "test-rules.mdc"
            assert rules_file.exists()

    def test_rules_create_with_prompt(self, runner, tmp_path):
        """Test rules creation with name prompt."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "rules").mkdir()

            result = runner.invoke(
                app,
                ["rules", "create"],
                input="n\ntest-rules\n",  # Decline comprehensive, then provide name
            )

            assert result.exit_code == 0
            rules_file = cursor_dir / "rules" / "test-rules.mdc"
            assert rules_file.exists()


class TestNextCommand:
    """Tests for `cfs instructions next <category>` command."""

    def test_next_document_success(self, runner, temp_cfs):
        """Test successfully finding next unresolved document."""
        tmp_path, cursor_dir = temp_cfs

        # Create unresolved documents
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent here.")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "next", "bugs"],
                input="n\n",  # Decline to work on it
            )

            assert result.exit_code != 0  # Should abort after declining
            assert "Next issue in bugs" in result.stdout
            assert "Test Bug" in result.stdout

    def test_next_document_all_completed(self, runner, temp_cfs):
        """Test when all documents are completed."""
        tmp_path, cursor_dir = temp_cfs

        # Create only completed documents
        (cursor_dir / "bugs" / "1-DONE-completed.md").write_text("content")
        (cursor_dir / "bugs" / "2-DONE-another.md").write_text("content")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "next", "bugs"])

            assert result.exit_code != 0
            assert "All of the issues have been completed" in result.stdout

    def test_next_document_invalid_category(self, runner, temp_cfs):
        """Test with invalid category."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "next", "invalid"])

            assert result.exit_code != 0

    def test_next_document_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "next", "bugs"])

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout


class TestHandoffCommand:
    """Tests for `cfs instructions handoff` command."""

    def test_handoff_create_success(self, runner, temp_cfs):
        """Test successfully generating handoff instructions."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff"])

            assert result.exit_code == 0
            assert "Handoff Instructions" in result.stdout
            assert "Create Handoff Document" in result.stdout

    def test_handoff_create_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff"])

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout


class TestHandoffPickupCommand:
    """Tests for `cfs instructions handoff pickup` command."""

    def test_handoff_pickup_success(self, runner, temp_cfs):
        """Test successfully picking up handoff document."""
        tmp_path, cursor_dir = temp_cfs

        # Create progress category if not exists
        progress_dir = cursor_dir / "progress"
        if not progress_dir.exists():
            progress_dir.mkdir()

        # Create unresolved handoff document
        handoff_file = progress_dir / "1-handoff-test.md"
        handoff_file.write_text("# Handoff Test\n\nContent here.")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "handoff", "pickup"],
                input="n\n",  # Decline to pick up
            )

            assert result.exit_code != 0  # Should abort after declining
            assert "Next handoff document" in result.stdout
            assert "Handoff Test" in result.stdout

    def test_handoff_pickup_all_completed(self, runner, temp_cfs):
        """Test when all handoff documents are completed."""
        tmp_path, cursor_dir = temp_cfs

        # Create progress category
        progress_dir = cursor_dir / "progress"
        progress_dir.mkdir()

        # Create only completed handoff documents
        (progress_dir / "1-DONE-handoff-completed.md").write_text("content")
        (progress_dir / "2-DONE-another-handoff.md").write_text("content")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "pickup"])

            assert result.exit_code != 0
            assert "No incomplete handoff documents found" in result.stdout

    def test_handoff_pickup_no_progress_category(self, runner, temp_cfs):
        """Test when progress category doesn't exist."""
        tmp_path, cursor_dir = temp_cfs

        # Don't create progress category

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "pickup"])

            # Should either create the category or show an error
            # The behavior depends on get_category_path implementation
            assert result.exit_code != 0

    def test_handoff_pickup_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "pickup"])

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout


class TestTreeCommand:
    """Tests for `cfs tree` command."""

    def test_tree_success(self, runner, temp_cfs):
        """Test successfully displaying tree structure."""
        tmp_path, cursor_dir = temp_cfs

        # Create some files and directories
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("content")
        (cursor_dir / "features" / "1-test-feature.md").write_text("content")
        (cursor_dir / "rules" / "test-rules.mdc").write_text("content")
        # Leave some directories empty to test empty folder display

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["tree"])

            assert result.exit_code == 0
            assert ".cursor" in result.stdout
            assert "bugs" in result.stdout
            assert "features" in result.stdout
            assert "rules" in result.stdout
            # Check that empty folders are shown
            assert "research" in result.stdout or "qa" in result.stdout

    def test_tree_shows_empty_folders(self, runner, temp_cfs):
        """Test that empty folders are displayed in the tree."""
        tmp_path, cursor_dir = temp_cfs

        # Ensure some directories exist but are empty
        (cursor_dir / "research").mkdir(exist_ok=True)
        (cursor_dir / "qa").mkdir(exist_ok=True)

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["tree"])

            assert result.exit_code == 0
            # Empty folders should still appear in the tree
            assert "research" in result.stdout
            assert "qa" in result.stdout

    def test_tree_shows_all_files(self, runner, temp_cfs):
        """Test that all files are displayed in the tree."""
        tmp_path, cursor_dir = temp_cfs

        # Create multiple files
        (cursor_dir / "bugs" / "1-first.md").write_text("content")
        (cursor_dir / "bugs" / "2-second.md").write_text("content")
        (cursor_dir / "init.md").write_text("content")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["tree"])

            assert result.exit_code == 0
            assert "1-first.md" in result.stdout
            assert "2-second.md" in result.stdout
            assert "init.md" in result.stdout

    def test_tree_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["tree"])

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout


class TestTreeFormatting:
    """Tests for tree formatting helper functions."""

    def test_format_tree_highlights_incomplete(self, tmp_path):
        """Ensure incomplete documents are highlighted."""
        from cfs.cli import _format_tree_entry

        file_path = tmp_path / "1-incomplete.md"
        file_path.write_text("content")

        formatted = _format_tree_entry(file_path, file_path.name)
        assert "[bold orange3]1-incomplete.md[/]" == formatted

    def test_format_tree_skips_completed(self, tmp_path):
        """Ensure completed documents are not highlighted."""
        from cfs.cli import _format_tree_entry

        file_path = tmp_path / "1-DONE-complete.md"
        file_path.write_text("content")

        formatted = _format_tree_entry(file_path, file_path.name)
        assert formatted == file_path.name


class TestExecCommand:
    """Tests for `cfs exec` command."""

    def test_exec_outputs_content(self, runner, tmp_path):
        """Test that exec outputs document content."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure with a document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            doc_content = "# Test Bug\n\nThis is a test bug document."
            (bugs_dir / "1-test-bug.md").write_text(doc_content)

            result = runner.invoke(app, ["exec", "bugs", "1", "--force"])

            assert result.exit_code == 0
            assert "Test Bug" in result.output
            assert "Custom Instructions" in result.output

    def test_exec_with_confirmation_declined(self, runner, tmp_path):
        """Test that exec aborts when confirmation is declined."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure with a document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1"], input="n\n")

            assert result.exit_code == 1
            assert "cancelled" in result.output.lower()

    def test_exec_document_not_found(self, runner, tmp_path):
        """Test exec with non-existent document ID."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure without any documents
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(app, ["exec", "bugs", "999", "--force"])

            assert result.exit_code == 1

    def test_exec_invalid_category(self, runner, tmp_path):
        """Test exec with invalid category."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()

            result = runner.invoke(app, ["exec", "invalid", "1", "--force"])

            assert result.exit_code == 1

    def test_exec_claude_flag_confirmation_message(self, runner, tmp_path):
        """Test that --claude flag shows appropriate confirmation message."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure with a document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--claude"], input="n\n")

            assert "Claude Code session" in result.output

    @patch("shutil.which")
    def test_exec_claude_not_installed(self, mock_which, runner, tmp_path):
        """Test exec --claude when Claude Code is not installed."""
        mock_which.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure with a document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--claude", "--force"])

            assert result.exit_code == 1
            assert "Claude Code CLI not found" in result.output

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_exec_claude_launches_session(self, mock_which, mock_run, runner, tmp_path):
        """Test that exec --claude launches Claude Code with correct prompt."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure with a document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            doc_content = "# Test Bug\n\nThis is a test bug."
            (bugs_dir / "1-test-bug.md").write_text(doc_content)

            result = runner.invoke(app, ["exec", "bugs", "1", "--claude", "--force"])

            assert result.exit_code == 0
            assert "Starting Claude Code session" in result.output

            # Verify subprocess.run was called with correct arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "/usr/local/bin/claude"
            assert "Test Bug" in call_args[1]
            assert "cfs i bugs complete 1" in call_args[1]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_exec_claude_includes_completion_instruction(
        self, mock_which, mock_run, runner, tmp_path
    ):
        """Test that the Claude prompt includes the completion instruction."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            features_dir = cursor_dir / "features"
            features_dir.mkdir()

            (features_dir / "5-new-feature.md").write_text("# New Feature\n\nDetails")

            result = runner.invoke(app, ["exec", "features", "5", "--claude", "--force"])

            assert result.exit_code == 0

            call_args = mock_run.call_args[0][0]
            prompt = call_args[1]

            # Check prompt contains the completion instruction
            assert "cfs i features complete 5" in prompt
            assert "offer to close the corresponding CFS document" in prompt

    def test_exec_mutual_exclusivity_error(self, runner, tmp_path):
        """Test that using multiple AI flags raises an error."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure with a document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--claude", "--gemini", "--force"])

            assert result.exit_code == 1
            assert "Only one AI service flag can be used at a time" in result.output
            assert "--claude" in result.output
            assert "--gemini" in result.output

    def test_exec_gemini_flag_confirmation_message(self, runner, tmp_path):
        """Test that --gemini flag shows appropriate confirmation message."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--gemini"], input="n\n")

            assert "Gemini CLI session" in result.output

    def test_exec_cursor_flag_confirmation_message(self, runner, tmp_path):
        """Test that --cursor flag shows appropriate confirmation message."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--cursor"], input="n\n")

            assert "Cursor Agent CLI session" in result.output

    def test_exec_codex_flag_confirmation_message(self, runner, tmp_path):
        """Test that --codex flag shows appropriate confirmation message."""
        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--codex"], input="n\n")

            assert "OpenAI Codex CLI session" in result.output

    @patch("shutil.which")
    def test_exec_gemini_not_installed(self, mock_which, runner, tmp_path):
        """Test exec --gemini when Gemini CLI is not installed."""
        mock_which.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--gemini", "--force"])

            assert result.exit_code == 1
            assert "Gemini CLI not found" in result.output

    @patch("shutil.which")
    def test_exec_cursor_not_installed(self, mock_which, runner, tmp_path):
        """Test exec --cursor when Cursor Agent CLI is not installed."""
        mock_which.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--cursor", "--force"])

            assert result.exit_code == 1
            assert "Cursor Agent CLI not found" in result.output

    @patch("shutil.which")
    def test_exec_codex_not_installed(self, mock_which, runner, tmp_path):
        """Test exec --codex when OpenAI Codex CLI is not installed."""
        mock_which.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            (bugs_dir / "1-test-bug.md").write_text("# Test Bug\n\nContent")

            result = runner.invoke(app, ["exec", "bugs", "1", "--codex", "--force"])

            assert result.exit_code == 1
            assert "OpenAI Codex CLI not found" in result.output

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_exec_gemini_launches_session(self, mock_which, mock_run, runner, tmp_path):
        """Test that exec --gemini launches Gemini CLI with correct prompt."""
        mock_which.return_value = "/usr/local/bin/gemini"
        mock_run.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            doc_content = "# Test Bug\n\nThis is a test bug."
            (bugs_dir / "1-test-bug.md").write_text(doc_content)

            result = runner.invoke(app, ["exec", "bugs", "1", "--gemini", "--force"])

            assert result.exit_code == 0
            assert "Starting Gemini CLI session" in result.output

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "/usr/local/bin/gemini"
            assert "Test Bug" in call_args[1]
            assert "cfs i bugs complete 1" in call_args[1]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_exec_cursor_launches_session(self, mock_which, mock_run, runner, tmp_path):
        """Test that exec --cursor launches Cursor Agent CLI with correct prompt."""
        mock_which.return_value = "/usr/local/bin/agent"
        mock_run.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            doc_content = "# Test Bug\n\nThis is a test bug."
            (bugs_dir / "1-test-bug.md").write_text(doc_content)

            result = runner.invoke(app, ["exec", "bugs", "1", "--cursor", "--force"])

            assert result.exit_code == 0
            assert "Starting Cursor Agent CLI session" in result.output

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "/usr/local/bin/agent"
            assert call_args[1] == "chat"
            assert "Test Bug" in call_args[2]
            assert "cfs i bugs complete 1" in call_args[2]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_exec_codex_launches_session(self, mock_which, mock_run, runner, tmp_path):
        """Test that exec --codex launches OpenAI Codex CLI with correct prompt."""
        mock_which.return_value = "/usr/local/bin/codex"
        mock_run.return_value = None

        with isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            doc_content = "# Test Bug\n\nThis is a test bug."
            (bugs_dir / "1-test-bug.md").write_text(doc_content)

            result = runner.invoke(app, ["exec", "bugs", "1", "--codex", "--force"])

            assert result.exit_code == 0
            assert "Starting OpenAI Codex CLI session" in result.output

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "/usr/local/bin/codex"
            assert "Test Bug" in call_args[1]
            assert "cfs i bugs complete 1" in call_args[1]


# =============================================================================
# Tests for GitHub auto-sync hooks
# =============================================================================


class TestTryAutoCreateGithubIssue:
    """Tests for _try_auto_create_github_issue helper."""

    def test_skips_when_gh_not_installed(self, tmp_path):
        """Should silently skip when gh CLI is not installed."""
        from cfs.cli import _try_auto_create_github_issue

        doc_path = tmp_path / "1-test.md"
        doc_path.write_text("# Test\n\n## Contents\n\nHello\n")

        with patch("cfs.github.check_gh_installed", return_value=False):
            # Should not raise and should not attempt to create issue
            with patch("cfs.github.create_issue") as mock_create:
                _try_auto_create_github_issue("bugs", doc_path, "Test")
                mock_create.assert_not_called()

    def test_skips_when_not_authenticated(self, tmp_path):
        """Should silently skip when gh CLI is not authenticated."""
        from cfs.cli import _try_auto_create_github_issue

        doc_path = tmp_path / "1-test.md"
        doc_path.write_text("# Test\n\n## Contents\n\nHello\n")

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=False):
                with patch("cfs.github.create_issue") as mock_create:
                    _try_auto_create_github_issue("bugs", doc_path, "Test")
                    mock_create.assert_not_called()

    def test_skips_for_excluded_category_tmp(self, tmp_path):
        """Should skip for 'tmp' category (excluded from sync)."""
        from cfs.cli import _try_auto_create_github_issue

        doc_path = tmp_path / "1-test.md"
        doc_path.write_text("# Test\n\n## Contents\n\nHello\n")

        with patch("cfs.github.create_issue") as mock_create:
            _try_auto_create_github_issue("tmp", doc_path, "Test")
            mock_create.assert_not_called()

    def test_skips_for_excluded_category_security(self, tmp_path):
        """Should skip for 'security' category (excluded from sync)."""
        from cfs.cli import _try_auto_create_github_issue

        doc_path = tmp_path / "1-test.md"
        doc_path.write_text("# Test\n\n## Contents\n\nHello\n")

        with patch("cfs.github.create_issue") as mock_create:
            _try_auto_create_github_issue("security", doc_path, "Test")
            mock_create.assert_not_called()

    def test_skips_when_document_already_linked(self, tmp_path):
        """Should skip when document already has a github_issue link."""
        from cfs.cli import _try_auto_create_github_issue

        doc_path = tmp_path / "1-test.md"
        doc_path.write_text("---\ngithub_issue: 42\n---\n# Test\n\n## Contents\n\nHello\n")

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=True):
                with patch("cfs.github.create_issue") as mock_create:
                    _try_auto_create_github_issue("bugs", doc_path, "Test")
                    mock_create.assert_not_called()

    def test_creates_issue_and_links_document(self, tmp_path):
        """Should create GitHub issue and update document with frontmatter link."""

        from cfs.cli import _try_auto_create_github_issue
        from cfs.github import GitHubIssue

        doc_path = tmp_path / "1-test-bug.md"
        doc_path.write_text(
            "# Test Bug\n\n## Contents\n\nSome content\n\n## Acceptance criteria\n\nDone\n"
        )

        mock_issue = GitHubIssue(
            number=99,
            title="Test Bug",
            body="Some content",
            state="open",
            labels=["cfs:bugs"],
            url="https://github.com/owner/repo/issues/99",
        )

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=True):
                with patch("cfs.github.ensure_label_exists", return_value=True):
                    with patch("cfs.github.create_issue", return_value=mock_issue) as mock_create:
                        _try_auto_create_github_issue("bugs", doc_path, "Test Bug")

                        mock_create.assert_called_once()
                        # Verify document was updated with frontmatter
                        content = doc_path.read_text()
                        assert "github_issue: 99" in content

    def test_handles_github_error_gracefully(self, tmp_path):
        """Should display a warning and not raise when a GitHub error occurs."""
        from cfs.cli import _try_auto_create_github_issue
        from cfs.github import GitHubAPIError

        doc_path = tmp_path / "1-test.md"
        doc_path.write_text("# Test\n\n## Contents\n\nHello\n")

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=True):
                with patch("cfs.github.ensure_label_exists", return_value=True):
                    with patch("cfs.github.create_issue", side_effect=GitHubAPIError("API error")):
                        # Should not raise
                        _try_auto_create_github_issue("bugs", doc_path, "Test")


class TestTryAutoCloseGithubIssue:
    """Tests for _try_auto_close_github_issue helper."""

    def test_skips_when_no_github_issue_link(self, tmp_path):
        """Should silently skip when document has no github_issue frontmatter."""
        from cfs.cli import _try_auto_close_github_issue

        doc_path = tmp_path / "1-DONE-test.md"
        doc_path.write_text("# Test\n\n## Contents\n\nHello\n<!-- DONE -->\n")

        with patch("cfs.github.close_issue") as mock_close:
            _try_auto_close_github_issue(doc_path)
            mock_close.assert_not_called()

    def test_skips_when_gh_not_installed(self, tmp_path):
        """Should silently skip when gh CLI is not installed."""
        from cfs.cli import _try_auto_close_github_issue

        doc_path = tmp_path / "1-DONE-test.md"
        doc_path.write_text(
            "---\ngithub_issue: 42\n---\n# Test\n\n## Contents\n\nHello\n<!-- DONE -->\n"
        )

        with patch("cfs.github.check_gh_installed", return_value=False):
            with patch("cfs.github.close_issue") as mock_close:
                _try_auto_close_github_issue(doc_path)
                mock_close.assert_not_called()

    def test_skips_when_not_authenticated(self, tmp_path):
        """Should silently skip when gh CLI is not authenticated."""
        from cfs.cli import _try_auto_close_github_issue

        doc_path = tmp_path / "1-DONE-test.md"
        doc_path.write_text(
            "---\ngithub_issue: 42\n---\n# Test\n\n## Contents\n\nHello\n<!-- DONE -->\n"
        )

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=False):
                with patch("cfs.github.close_issue") as mock_close:
                    _try_auto_close_github_issue(doc_path)
                    mock_close.assert_not_called()

    def test_skips_when_issue_already_closed(self, tmp_path):
        """Should silently skip when the linked GitHub issue is already closed."""

        from cfs.cli import _try_auto_close_github_issue
        from cfs.github import GitHubIssue

        doc_path = tmp_path / "1-DONE-test.md"
        doc_path.write_text(
            "---\ngithub_issue: 42\n---\n# Test\n\n## Contents\n\nHello\n<!-- DONE -->\n"
        )

        already_closed_issue = GitHubIssue(
            number=42,
            title="Test",
            body="",
            state="closed",
            labels=[],
            url="https://github.com/owner/repo/issues/42",
        )

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=True):
                with patch("cfs.github.get_issue", return_value=already_closed_issue):
                    with patch("cfs.github.close_issue") as mock_close:
                        _try_auto_close_github_issue(doc_path)
                        mock_close.assert_not_called()

    def test_closes_open_linked_issue(self, tmp_path):
        """Should close a linked GitHub issue that is currently open."""
        from cfs.cli import _try_auto_close_github_issue
        from cfs.github import GitHubIssue

        doc_path = tmp_path / "1-DONE-test.md"
        doc_path.write_text(
            "---\ngithub_issue: 42\n---\n# Test\n\n## Contents\n\nHello\n<!-- DONE -->\n"
        )

        open_issue = GitHubIssue(
            number=42,
            title="Test",
            body="",
            state="open",
            labels=[],
            url="https://github.com/owner/repo/issues/42",
        )

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=True):
                with patch("cfs.github.get_issue", return_value=open_issue):
                    with patch("cfs.github.close_issue") as mock_close:
                        _try_auto_close_github_issue(doc_path)
                        mock_close.assert_called_once_with(42)

    def test_handles_github_error_gracefully(self, tmp_path):
        """Should display a warning and not raise when a GitHub error occurs."""
        from cfs.cli import _try_auto_close_github_issue
        from cfs.github import GitHubAPIError

        doc_path = tmp_path / "1-DONE-test.md"
        doc_path.write_text(
            "---\ngithub_issue: 42\n---\n# Test\n\n## Contents\n\nHello\n<!-- DONE -->\n"
        )

        with patch("cfs.github.check_gh_installed", return_value=True):
            with patch("cfs.github.check_gh_authenticated", return_value=True):
                with patch("cfs.github.get_issue", side_effect=GitHubAPIError("API error")):
                    # Should not raise
                    _try_auto_close_github_issue(doc_path)


class TestCreateCommandWithGithubAutoSync:
    """Integration tests for create command triggering GitHub auto-sync."""

    def test_create_skips_github_when_gh_not_installed(self, runner, tmp_path):
        """Create command should succeed even when gh is not installed."""
        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            with patch("cfs.github.check_gh_installed", return_value=False):
                result = runner.invoke(
                    app,
                    [
                        "instructions",
                        "bugs",
                        "create",
                        "--title",
                        "Auto Sync Bug",
                        "--content",
                        "Some content",
                    ],
                )

            assert result.exit_code == 0
            assert (cursor_dir / "bugs" / "1-auto-sync-bug.md").exists()
            # No GitHub issue should be mentioned in output
            assert "Created GitHub issue" not in result.output

    def test_create_auto_creates_github_issue_when_authenticated(self, runner, tmp_path):
        """Create command should auto-create a GitHub issue when gh is authenticated."""
        from cfs.github import GitHubIssue

        mock_issue = GitHubIssue(
            number=55,
            title="Auto Sync Bug",
            body="Some content",
            state="open",
            labels=["cfs:bugs"],
            url="https://github.com/owner/repo/issues/55",
        )

        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            with patch("cfs.github.check_gh_installed", return_value=True):
                with patch("cfs.github.check_gh_authenticated", return_value=True):
                    with patch("cfs.github.ensure_label_exists", return_value=True):
                        with patch("cfs.github.create_issue", return_value=mock_issue):
                            result = runner.invoke(
                                app,
                                [
                                    "instructions",
                                    "bugs",
                                    "create",
                                    "--title",
                                    "Auto Sync Bug",
                                    "--content",
                                    "Some content",
                                ],
                            )

            assert result.exit_code == 0
            assert "Created GitHub issue #55" in result.output
            doc_path = cursor_dir / "bugs" / "1-auto-sync-bug.md"
            assert doc_path.exists()
            assert "github_issue: 55" in doc_path.read_text()

    def test_complete_auto_closes_github_issue(self, runner, tmp_path):
        """Complete command should auto-close a linked GitHub issue."""
        from cfs.github import GitHubIssue

        open_issue = GitHubIssue(
            number=42,
            title="Test Bug",
            body="",
            state="open",
            labels=[],
            url="https://github.com/owner/repo/issues/42",
        )

        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            bugs_dir = cursor_dir / "bugs"
            bugs_dir.mkdir()

            # Create document already linked to GitHub issue
            (bugs_dir / "1-test-bug.md").write_text(
                "---\ngithub_issue: 42\n---\n# Test Bug\n\n## Contents\n\nHello\n"
            )

            with patch("cfs.github.check_gh_installed", return_value=True):
                with patch("cfs.github.check_gh_authenticated", return_value=True):
                    with patch("cfs.github.get_issue", return_value=open_issue):
                        with patch("cfs.github.close_issue") as mock_close:
                            result = runner.invoke(
                                app,
                                ["instructions", "bugs", "complete", "1", "--force"],
                            )

            assert result.exit_code == 0
            assert "Completed document" in result.output
            assert "Closed GitHub issue #42" in result.output
            mock_close.assert_called_once_with(42)

    def test_close_auto_closes_github_issue(self, runner, tmp_path):
        """Close command should auto-close a linked GitHub issue."""
        from cfs.github import GitHubIssue

        open_issue = GitHubIssue(
            number=77,
            title="Test Feature",
            body="",
            state="open",
            labels=[],
            url="https://github.com/owner/repo/issues/77",
        )

        with isolated_filesystem(tmp_path):
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            features_dir = cursor_dir / "features"
            features_dir.mkdir()

            # Create document already linked to GitHub issue
            (features_dir / "1-test-feature.md").write_text(
                "---\ngithub_issue: 77\n---\n# Test Feature\n\n## Contents\n\nHello\n"
            )

            with patch("cfs.github.check_gh_installed", return_value=True):
                with patch("cfs.github.check_gh_authenticated", return_value=True):
                    with patch("cfs.github.get_issue", return_value=open_issue):
                        with patch("cfs.github.close_issue") as mock_close:
                            result = runner.invoke(
                                app,
                                ["instructions", "features", "close", "1", "--force"],
                            )

            assert result.exit_code == 0
            assert "Closed document" in result.output
            assert "Closed GitHub issue #77" in result.output
            mock_close.assert_called_once_with(77)


class TestConsistentCommandGrammar:
    """Tests for the noun-first command grammar (issue #16).

    Canonical forms are `cfs i <category> <verb> [id]`; the old verb-first
    forms still work but emit a deprecation warning.
    """

    # --- New canonical forms ---

    def test_category_next(self, runner, temp_cfs):
        """`cfs i bugs next` finds the next unresolved document."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n\nContent here.")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "next"],
                input="n\n",  # Decline to work on it
            )

            assert "Next issue in bugs" in result.stdout
            assert "Test Bug" in result.stdout
            assert "deprecated" not in result.stdout

    def test_category_order(self, runner, temp_cfs):
        """`cfs i bugs order` reports when files already follow the convention."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "bugs", "order"])

            assert result.exit_code == 0
            assert "already follow the naming convention" in result.stdout
            assert "deprecated" not in result.stdout

    def test_category_order_renames(self, runner, temp_cfs):
        """`cfs i bugs order --force` renames non-conforming files."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "5-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "bugs", "order", "--force"])

            assert result.exit_code == 0
            assert (cursor_dir / "bugs" / "1-test-bug.md").exists()

    def test_category_move(self, runner, temp_cfs):
        """`cfs i bugs move 1 features --force` moves a document."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "move", "1", "features", "--force"],
            )

            assert result.exit_code == 0
            assert "Moved document" in result.stdout
            assert (cursor_dir / "features" / "1-test-bug.md").exists()
            assert not (cursor_dir / "bugs" / "1-test-bug.md").exists()
            assert "deprecated" not in result.stdout

    def test_category_exec(self, runner, temp_cfs):
        """`cfs i bugs exec 1 --force` outputs the document content."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n\nUnique exec body.")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "exec", "1", "--force"],
            )

            assert result.exit_code == 0
            assert "Unique exec body." in result.stdout
            assert "deprecated" not in result.stdout

    def test_handoff_create(self, runner, temp_cfs):
        """`cfs i handoff create` generates handoff instructions."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "create"])

            assert result.exit_code == 0
            assert "Handoff Instructions" in result.stdout
            assert "deprecated" not in result.stdout

    # --- Deprecated verb-first forms still work but warn ---

    def test_deprecated_next_warns(self, runner, temp_cfs):
        """`cfs i next bugs` still works and emits a deprecation warning."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n\nContent here.")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "next", "bugs"],
                input="n\n",
            )

            assert "deprecated" in result.stdout
            assert "Next issue in bugs" in result.stdout

    def test_deprecated_order_warns(self, runner, temp_cfs):
        """`cfs i order bugs` still works and emits a deprecation warning."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "order", "bugs"])

            assert result.exit_code == 0
            assert "deprecated" in result.stdout
            assert "already follow the naming convention" in result.stdout

    def test_deprecated_move_warns(self, runner, temp_cfs):
        """`cfs i move bugs 1 features` still works and emits a deprecation warning."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "move", "bugs", "1", "features", "--force"],
            )

            assert result.exit_code == 0
            assert "deprecated" in result.stdout
            assert (cursor_dir / "features" / "1-test-bug.md").exists()

    def test_deprecated_view_with_category_warns(self, runner, temp_cfs):
        """`cfs i view bugs` still works and emits a deprecation warning."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "view", "bugs"])

            assert result.exit_code == 0
            assert "deprecated" in result.stdout

    def test_view_all_does_not_warn(self, runner, temp_cfs):
        """Bare `cfs i view` (all categories) emits no deprecation warning."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "view"])

            assert result.exit_code == 0
            assert "deprecated" not in result.stdout

    def test_deprecated_handoff_create_warns(self, runner, temp_cfs):
        """`cfs i handoff create-handoff` still works and emits a deprecation warning."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "create-handoff"])

            assert result.exit_code == 0
            assert "deprecated" in result.stdout
            assert "Handoff Instructions" in result.stdout

    def test_category_exec_rejects_multiple_ai_flags(self, runner, temp_cfs):
        """`cfs i bugs exec` rejects more than one AI service flag."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "exec", "1", "--force", "--claude", "--gemini"],
            )

            assert result.exit_code != 0
            assert "Only one AI service flag" in result.stdout

    def test_category_move_same_category_rejected(self, runner, temp_cfs):
        """`cfs i bugs move <id> bugs` is rejected."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "move", "1", "bugs", "--force"],
            )

            assert result.exit_code != 0
            assert "same" in result.stdout

    def test_custom_category_cannot_shadow_command_verbs(self, runner, temp_cfs):
        """Custom categories cannot be named after reserved command verbs."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            for reserved in ["next", "order", "move", "view", "exec", "handoff", "category"]:
                result = runner.invoke(
                    app,
                    ["instructions", "category", "create", reserved],
                )

                assert result.exit_code != 0, f"'{reserved}' should be rejected"
                assert "reserved" in result.stdout


class TestTopLevelCategoryCommands:
    """Tests for top-level category grammar (issue #59): `cfs <category> <verb> [id]`.

    The `instructions`/`instr`/`i` forms remain permanent, equivalent aliases.
    """

    def test_top_level_create_and_view(self, runner, temp_cfs):
        """`cfs bugs create` and `cfs bugs view` work without the `i` prefix."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["bugs", "create", "--title", "Top level bug", "--content", "Body."],
            )

            assert result.exit_code == 0
            assert (cursor_dir / "bugs" / "1-top-level-bug.md").exists()

            result = runner.invoke(app, ["bugs", "view"])
            assert result.exit_code == 0
            assert "top-level-bug" in result.stdout

    def test_top_level_equivalent_to_i_form(self, runner, temp_cfs):
        """Top-level and `i`-prefixed forms run the same command."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n\nContent.")

        with isolated_filesystem(tmp_path):
            top = runner.invoke(app, ["bugs", "next"], input="n\n")
            aliased = runner.invoke(app, ["i", "bugs", "next"], input="n\n")

            assert "Next issue in bugs" in top.stdout
            assert "Next issue in bugs" in aliased.stdout
            assert "deprecated" not in top.stdout
            assert "deprecated" not in aliased.stdout

    def test_top_level_complete(self, runner, temp_cfs):
        """`cfs bugs complete <id>` works at the top level."""
        tmp_path, cursor_dir = temp_cfs
        (cursor_dir / "bugs" / "1-test-bug.md").write_text("# Test Bug\n")

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["bugs", "complete", "1", "--force"])

            assert result.exit_code == 0
            assert (cursor_dir / "bugs" / "1-DONE-test-bug.md").exists()

    def test_top_level_handoff_and_category_groups(self, runner, temp_cfs):
        """`cfs handoff` and `cfs category list` work at the top level."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["handoff", "create"])
            assert result.exit_code == 0
            assert "Handoff Instructions" in result.stdout

            result = runner.invoke(app, ["category", "list"])
            assert result.exit_code == 0
            assert "bugs" in result.stdout

    def test_runtime_custom_category_works_at_top_level(self, runner, temp_cfs):
        """A custom category created at runtime is immediately usable at the top level."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["category", "create", "toplevel-notes"])
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                ["toplevel-notes", "create", "--title", "A note", "--content", "Body."],
            )
            assert result.exit_code == 0
            assert (cursor_dir / "toplevel-notes" / "1-a-note.md").exists()

            # The same runtime-created category must also work via the `i` alias
            # (proves the multi-target backfill registers on both apps).
            result = runner.invoke(app, ["i", "toplevel-notes", "view"])
            assert result.exit_code == 0
            assert "a-note" in result.stdout

    def test_top_level_names_are_reserved(self, runner, temp_cfs):
        """Custom categories cannot shadow top-level commands or groups."""
        tmp_path, cursor_dir = temp_cfs

        with isolated_filesystem(tmp_path):
            for reserved in ["init", "version", "tree", "gh", "instructions", "instr", "i"]:
                result = runner.invoke(app, ["category", "create", reserved])

                assert result.exit_code != 0, f"'{reserved}' should be rejected"
                assert "reserved" in result.stdout


class TestUnifiedViewSemantics:
    """`cfs view` and `cfs i view` both default to incomplete-only; --all shows everything."""

    def _make_docs(self, cursor_dir):
        (cursor_dir / "bugs" / "1-DONE-finished-bug.md").write_text("# Finished\n")
        (cursor_dir / "bugs" / "2-open-bug.md").write_text("# Open\n")

    def test_top_level_view_defaults_to_incomplete(self, runner, temp_cfs):
        tmp_path, cursor_dir = temp_cfs
        self._make_docs(cursor_dir)

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["view"])

            assert result.exit_code == 0
            assert "open-bug" in result.stdout
            assert "finished-bug" not in result.stdout

    def test_top_level_view_all_includes_completed(self, runner, temp_cfs):
        tmp_path, cursor_dir = temp_cfs
        self._make_docs(cursor_dir)

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["view", "--all"])

            assert result.exit_code == 0
            assert "open-bug" in result.stdout
            assert "finished-bug" in result.stdout

    def test_i_view_matches_top_level_default(self, runner, temp_cfs):
        tmp_path, cursor_dir = temp_cfs
        self._make_docs(cursor_dir)

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["i", "view"])

            assert result.exit_code == 0
            assert "open-bug" in result.stdout
            assert "finished-bug" not in result.stdout

    def test_i_view_all_includes_completed(self, runner, temp_cfs):
        tmp_path, cursor_dir = temp_cfs
        self._make_docs(cursor_dir)

        with isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["i", "view", "--all"])

            assert result.exit_code == 0
            assert "finished-bug" in result.stdout


class TestGhSyncStrict:
    """Tests for the gh sync --strict exit-code behavior."""

    def _invoke_sync(self, runner, tmp_path, results, args):
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir(exist_ok=True)

        mock_plan = MagicMock()
        mock_plan.has_actions.return_value = True

        patches = [
            patch("cfs.github.check_gh_installed", return_value=True),
            patch("cfs.github.check_gh_authenticated", return_value=True),
            patch("cfs.github.list_issues", return_value=[]),
            patch("cfs.cli_github_commands.core.find_cfs_root", return_value=cfs_root),
            patch("cfs.cli_github_commands.core.get_all_categories", return_value={"bugs"}),
            patch("cfs.sync.compute_sync_categories", return_value={"bugs"}),
            patch("cfs.sync.build_sync_plan", return_value=mock_plan),
            patch("cfs.sync.display_sync_status"),
            patch("cfs.sync.display_sync_results"),
            patch("cfs.sync.execute_sync_plan", return_value=results),
        ]
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            return runner.invoke(app, ["gh", "sync", *args])

    def test_strict_fails_on_real_errors(self, runner, tmp_path):
        results = {"errors": 2, "needs_interactive": 0}
        result = self._invoke_sync(runner, tmp_path, results, ["--strict"])
        assert result.exit_code == 1

    def test_strict_passes_when_only_interactive_items_remain(self, runner, tmp_path):
        results = {"errors": 0, "needs_interactive": 3}
        result = self._invoke_sync(runner, tmp_path, results, ["--strict"])
        assert result.exit_code == 0

    def test_default_mode_never_fails_on_errors(self, runner, tmp_path):
        results = {"errors": 2, "needs_interactive": 1}
        result = self._invoke_sync(runner, tmp_path, results, [])
        assert result.exit_code == 0
