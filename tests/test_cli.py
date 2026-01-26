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
                input="0\n",  # Decline edit prompt
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
                input="Test Bug\n0\n",  # Title, then no edit
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


class TestCompleteCommand:
    """Tests for `cfs instructions <category> complete` command."""

    def test_complete_document_success(self, runner, temp_cfs):
        """Test successful document completion with confirmation."""
        tmp_path, cursor_dir = temp_cfs

        # Create a document first
        bug_file = cursor_dir / "bugs" / "1-test-bug.md"
        bug_file.write_text("# Test Bug\n\nContent")
        assert bug_file.exists()

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
            result = runner.invoke(
                app,
                ["instructions", "bugs", "complete", "999", "--force"],
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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


class TestExecCommand:
    """Tests for `cfs exec` command."""

    def test_exec_outputs_content(self, runner, tmp_path):
        """Test that exec outputs document content."""
        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
            from pathlib import Path

            # Create CFS structure without any documents
            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "bugs").mkdir()

            result = runner.invoke(app, ["exec", "bugs", "999", "--force"])

            assert result.exit_code == 1

    def test_exec_invalid_category(self, runner, tmp_path):
        """Test exec with invalid category."""
        with runner.isolated_filesystem(tmp_path):
            from pathlib import Path

            cursor_dir = Path.cwd() / ".cursor"
            cursor_dir.mkdir()

            result = runner.invoke(app, ["exec", "invalid", "1", "--force"])

            assert result.exit_code == 1

    def test_exec_claude_flag_confirmation_message(self, runner, tmp_path):
        """Test that --claude flag shows appropriate confirmation message."""
        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
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
        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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

        with runner.isolated_filesystem(tmp_path):
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
