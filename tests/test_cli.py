"""Integration tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cfs.cli import app


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
        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert (Path.cwd() / ".cursor").exists()
            assert (Path.cwd() / ".cursor" / "bugs").exists()
            assert (Path.cwd() / ".cursor" / "features").exists()

    def test_init_creates_init_md(self, runner, tmp_path):
        """Test that init creates init.md file."""
        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            init_file = Path.cwd() / ".cursor" / "init.md"
            assert init_file.exists()
            assert "CFS Initialization" in init_file.read_text()

    def test_init_with_existing_cfs(self, runner, temp_cfs):
        """Test init behavior when CFS already exists."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
            # First init
            result1 = runner.invoke(app, ["init"])
            assert result1.exit_code == 0

            # Second init (should prompt)
            result2 = runner.invoke(app, ["init"], input="n\n")
            assert result2.exit_code != 0  # Should abort

    def test_init_with_force_flag(self, runner, temp_cfs):
        """Test init with --force flag."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(
                app,
                ["instructions", "bugs", "create", "--title", "Test Bug"],
                input="n\n",  # Decline edit prompt
            )

            assert result.exit_code == 0
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert bug_file.exists()

    def test_create_document_with_prompt(self, runner, tmp_path):
        """Test document creation with title prompt."""
        with runner.isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(
                app,
                ["instructions", "bugs", "create"],
                input="Test Bug\nn\n",  # Title, then no edit
            )

            assert result.exit_code == 0
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            assert bug_file.exists()

    def test_create_document_invalid_category(self, runner, tmp_path):
        """Test that invalid category raises error."""
        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "create", "--title", "Test"],
            )

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout


class TestEditCommand:
    """Tests for `cfs instructions <category> edit` command."""

    def test_edit_document_success(self, runner, tmp_path):
        """Test successful document editing."""
        with runner.isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure and document
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()
            bug_file = cursor_dir / "bugs" / "1-test-bug.md"
            bug_file.write_text("Old content")

            with patch("cfs.editor.edit_content", return_value="New content"):
                result = runner.invoke(app, ["instructions", "bugs", "edit", "1"])

                assert result.exit_code == 0
                assert bug_file.read_text() == "New content"

    def test_edit_document_not_found(self, runner, temp_cfs):
        """Test editing non-existent document."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "bugs", "edit", "999"])

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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "delete", "1"],
                input="n\n",  # Don't confirm
            )

            assert result.exit_code != 0
            assert bug_file.exists()  # File should still exist


class TestViewCommand:
    """Tests for `cfs instructions view` command."""

    def test_view_all_documents(self, runner, temp_cfs):
        """Test viewing all documents."""
        tmp_path, cursor_dir = temp_cfs

        # Create some documents
        (cursor_dir / "bugs" / "1-bug1.md").write_text("content")
        (cursor_dir / "features" / "1-feature1.md").write_text("content")

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "view"])

            assert result.exit_code == 0
            assert "bugs" in result.stdout.lower()
            assert "features" in result.stdout.lower()

    def test_view_empty_cfs(self, runner, temp_cfs):
        """Test viewing empty CFS structure."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "view"])

            assert result.exit_code == 0


class TestRulesCreateCommand:
    """Tests for `cfs rules create` command."""

    def test_rules_create_success(self, runner, temp_cfs):
        """Test successful rules document creation."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["rules", "create", "--name", "test-rules"],
            )

            assert result.exit_code == 0
            rules_file = cursor_dir / "rules" / "test-rules.mdc"
            assert rules_file.exists()

    def test_rules_create_with_prompt(self, runner, tmp_path):
        """Test rules creation with name prompt."""
        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "next", "bugs"])

            assert result.exit_code != 0
            assert "All of the issues have been completed" in result.stdout

    def test_next_document_invalid_category(self, runner, temp_cfs):
        """Test with invalid category."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "next", "invalid"])

            assert result.exit_code != 0

    def test_next_document_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "next", "bugs"])

            assert result.exit_code != 0
            assert "CFS structure not found" in result.stdout


class TestHandoffCommand:
    """Tests for `cfs instructions handoff` command."""

    def test_handoff_create_success(self, runner, temp_cfs):
        """Test successfully generating handoff instructions."""
        tmp_path, cursor_dir = temp_cfs

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff"])

            assert result.exit_code == 0
            assert "Handoff Instructions" in result.stdout
            assert "Create Handoff Document" in result.stdout

    def test_handoff_create_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "pickup"])

            assert result.exit_code != 0
            assert "No incomplete handoff documents found" in result.stdout

    def test_handoff_pickup_no_progress_category(self, runner, temp_cfs):
        """Test when progress category doesn't exist."""
        tmp_path, cursor_dir = temp_cfs

        # Don't create progress category

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["instructions", "handoff", "pickup"])

            # Should either create the category or show an error
            # The behavior depends on get_category_path implementation
            assert result.exit_code != 0

    def test_handoff_pickup_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(app, ["tree"])

            assert result.exit_code == 0
            assert "1-first.md" in result.stdout
            assert "2-second.md" in result.stdout
            assert "init.md" in result.stdout

    def test_tree_no_cfs(self, runner, tmp_path):
        """Test that missing CFS structure raises error."""
        with runner.isolated_filesystem(tmp_path):
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
