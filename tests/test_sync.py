"""Tests for the sync module."""

from unittest.mock import MagicMock, patch

from rich.console import Console

from cfs.github import GitHubIssue
from cfs.sync import (
    SYNC_CATEGORIES,
    SyncAction,
    SyncItem,
    SyncPlan,
    build_sync_plan,
    execute_sync_plan,
    generate_diff,
    get_category_from_github_issue,
    is_cfs_document_done,
)


class TestSyncCategories:
    """Tests for sync category configuration."""

    def test_tmp_excluded(self):
        """Test that tmp category is excluded from sync."""
        assert "tmp" not in SYNC_CATEGORIES

    def test_main_categories_included(self):
        """Test that main categories are included."""
        assert "features" in SYNC_CATEGORIES
        assert "bugs" in SYNC_CATEGORIES
        assert "progress" in SYNC_CATEGORIES


class TestSyncItem:
    """Tests for SyncItem dataclass."""

    def test_str_create_cfs(self):
        """Test string representation for CREATE_CFS action."""
        issue = GitHubIssue(number=42, title="Test", body="", state="open", labels=[], url="")
        item = SyncItem(
            action=SyncAction.CREATE_CFS,
            category="features",
            github_issue=issue,
        )
        assert "Create CFS doc" in str(item)
        assert "#42" in str(item)

    def test_str_create_github(self):
        """Test string representation for CREATE_GITHUB action."""
        item = SyncItem(
            action=SyncAction.CREATE_GITHUB,
            category="bugs",
            cfs_doc_id=5,
        )
        assert "Create GitHub issue" in str(item)
        assert "bugs/5" in str(item)

    def test_str_content_conflict(self):
        """Test string representation for CONTENT_CONFLICT action."""
        issue = GitHubIssue(number=10, title="Test", body="", state="open", labels=[], url="")
        item = SyncItem(
            action=SyncAction.CONTENT_CONFLICT,
            category="features",
            cfs_doc_id=3,
            github_issue=issue,
        )
        assert "Content conflict" in str(item)


class TestSyncPlan:
    """Tests for SyncPlan dataclass."""

    def test_empty_plan_has_no_actions(self):
        """Test that empty plan reports no actions."""
        plan = SyncPlan()
        assert not plan.has_actions()
        assert plan.get_actions() == []

    def test_plan_with_no_action_items(self):
        """Test plan with only NO_ACTION items."""
        plan = SyncPlan()
        plan.add(SyncItem(action=SyncAction.NO_ACTION, category="features"))
        assert not plan.has_actions()

    def test_plan_with_actions(self):
        """Test plan with actionable items."""
        plan = SyncPlan()
        plan.add(SyncItem(action=SyncAction.NO_ACTION, category="features"))
        plan.add(
            SyncItem(
                action=SyncAction.CREATE_GITHUB,
                category="bugs",
                cfs_doc_id=1,
            )
        )
        assert plan.has_actions()
        assert len(plan.get_actions()) == 1


class TestIsCfsDocumentDone:
    """Tests for is_cfs_document_done function."""

    def test_incomplete_document(self, tmp_path):
        """Test detecting incomplete document."""
        doc = tmp_path / "1-test-doc.md"
        doc.touch()
        assert not is_cfs_document_done(doc)

    def test_done_document(self, tmp_path):
        """Test detecting DONE document."""
        doc = tmp_path / "1-DONE-test-doc.md"
        doc.touch()
        assert is_cfs_document_done(doc)

    def test_closed_document(self, tmp_path):
        """Test detecting CLOSED document."""
        doc = tmp_path / "1-CLOSED-test-doc.md"
        doc.touch()
        assert is_cfs_document_done(doc)


class TestGetCategoryFromGithubIssue:
    """Tests for get_category_from_github_issue function."""

    def test_with_cfs_label(self):
        """Test extracting category from CFS label."""
        issue = GitHubIssue(
            number=1,
            title="Test",
            body="",
            state="open",
            labels=["bug", "cfs:features"],
            url="",
        )
        assert get_category_from_github_issue(issue) == "features"

    def test_without_cfs_label(self):
        """Test when no CFS label present."""
        issue = GitHubIssue(
            number=1,
            title="Test",
            body="",
            state="open",
            labels=["bug", "enhancement"],
            url="",
        )
        assert get_category_from_github_issue(issue) is None

    def test_with_invalid_cfs_label(self):
        """Test when CFS label has invalid category."""
        issue = GitHubIssue(
            number=1,
            title="Test",
            body="",
            state="open",
            labels=["cfs:invalid_category"],
            url="",
        )
        assert get_category_from_github_issue(issue) is None

    def test_with_excluded_category(self):
        """Test that excluded categories are not returned."""
        issue = GitHubIssue(
            number=1,
            title="Test",
            body="",
            state="open",
            labels=["cfs:tmp"],
            url="",
        )
        assert get_category_from_github_issue(issue) is None


class TestGenerateDiff:
    """Tests for generate_diff function."""

    def test_identical_content(self):
        """Test diff of identical content."""
        content = "Line 1\nLine 2\n"
        diff = generate_diff(content, content)
        # Identical content should produce minimal diff
        assert "---" not in diff or "+++" not in diff or not diff.strip()

    def test_different_content(self):
        """Test diff of different content."""
        local = "Line 1\nLine 2\n"
        remote = "Line 1\nLine 3\n"
        diff = generate_diff(local, remote)
        assert "-Line 3" in diff or "+Line 2" in diff

    def test_added_content(self):
        """Test diff with added content."""
        local = "Line 1\nLine 2\nLine 3\n"
        remote = "Line 1\n"
        diff = generate_diff(local, remote)
        assert "+Line 2" in diff


class TestBuildSyncPlan:
    """Tests for build_sync_plan function."""

    def test_empty_cfs_and_github(self, tmp_path):
        """Test sync plan with no documents or issues."""
        # Create minimal CFS structure
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        (cfs_root / "features").mkdir()
        (cfs_root / "bugs").mkdir()

        github_issues = []
        plan = build_sync_plan(cfs_root, github_issues)

        assert plan.linked_count == 0
        assert not plan.has_actions()

    def test_unlinked_cfs_document(self, tmp_path):
        """Test sync plan detects unlinked CFS documents."""
        # Create CFS structure with one document
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        doc = features / "1-test-feature.md"
        doc.write_text("# Test Feature\n\n## Contents\n\nSome content.\n")

        github_issues = []
        plan = build_sync_plan(cfs_root, github_issues)

        assert plan.unlinked_cfs_count == 1
        actions = plan.get_actions()
        assert len(actions) == 1
        assert actions[0].action == SyncAction.CREATE_GITHUB

    def test_unlinked_github_issue(self, tmp_path):
        """Test sync plan detects unlinked GitHub issues."""
        # Create empty CFS structure
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        (cfs_root / "features").mkdir()

        github_issues = [
            GitHubIssue(
                number=42,
                title="New Feature",
                body="Feature description",
                state="open",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        assert plan.unlinked_github_count == 1
        actions = plan.get_actions()
        assert len(actions) == 1
        assert actions[0].action == SyncAction.CREATE_CFS

    def test_linked_in_sync(self, tmp_path):
        """Test sync plan detects linked documents that are in sync."""
        # Create CFS structure with linked document
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        doc = features / "1-test-feature.md"
        doc.write_text(
            "---\ngithub_issue: 42\n---\n" "# Test Feature\n\n## Contents\n\nSome content.\n"
        )

        github_issues = [
            GitHubIssue(
                number=42,
                title="Test Feature",
                body="Some content.",
                state="open",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        assert plan.linked_count == 1
        # Should have no actions since content matches
        actions = [a for a in plan.get_actions() if a.action != SyncAction.CONTENT_CONFLICT]
        assert len(actions) == 0
        conflict_actions = [
            a for a in plan.get_actions() if a.action == SyncAction.CONTENT_CONFLICT
        ]
        assert len(conflict_actions) == 0

    def test_linked_in_sync_with_normalization(self, tmp_path):
        """Test sync plan ignores whitespace and heading case differences."""
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        doc = features / "1-test-feature.md"
        doc.write_text(
            "---\ngithub_issue: 42\n---\n"
            "# Test Feature\n\n"
            "## Contents\n\n"
            "Some content.\n\n"
            "## Acceptance criteria\n\n"
            "- Item one\n"
        )

        github_issues = [
            GitHubIssue(
                number=42,
                title="Test Feature",
                body="Some content.\r\n\r\n## Acceptance Criteria\r\n\r\n- Item one\r\n",
                state="open",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        conflict_actions = [
            a for a in plan.get_actions() if a.action == SyncAction.CONTENT_CONFLICT
        ]
        assert len(conflict_actions) == 0

    def test_content_conflict_detected_for_actual_changes(self, tmp_path):
        """Test sync plan flags conflicts when content meaningfully differs."""
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        doc = features / "1-test-feature.md"
        doc.write_text(
            "---\ngithub_issue: 42\n---\n" "# Test Feature\n\n" "## Contents\n\n" "Some content.\n"
        )

        github_issues = [
            GitHubIssue(
                number=42,
                title="Test Feature",
                body="Different content.",
                state="open",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        conflict_actions = [
            a for a in plan.get_actions() if a.action == SyncAction.CONTENT_CONFLICT
        ]
        assert len(conflict_actions) == 1

    def test_status_mismatch_cfs_done(self, tmp_path):
        """Test sync plan detects when CFS is done but GitHub is open."""
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        doc = features / "1-DONE-test-feature.md"
        doc.write_text("---\ngithub_issue: 42\n---\n" "# Test Feature\n\n## Contents\n\nDone.\n")

        github_issues = [
            GitHubIssue(
                number=42,
                title="Test Feature",
                body="Done.",
                state="open",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        actions = plan.get_actions()
        close_actions = [a for a in actions if a.action == SyncAction.CLOSE_GITHUB]
        assert len(close_actions) == 1

    def test_status_mismatch_github_closed(self, tmp_path):
        """Test sync plan detects when GitHub is closed but CFS is open."""
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        doc = features / "1-test-feature.md"
        doc.write_text(
            "---\ngithub_issue: 42\n---\n" "# Test Feature\n\n## Contents\n\nNot done.\n"
        )

        github_issues = [
            GitHubIssue(
                number=42,
                title="Test Feature",
                body="Not done.",
                state="closed",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        actions = plan.get_actions()
        complete_actions = [a for a in actions if a.action == SyncAction.COMPLETE_CFS]
        assert len(complete_actions) == 1

    def test_skips_done_unlinked_documents(self, tmp_path):
        """Test that completed unlinked documents are not synced."""
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        features = cfs_root / "features"
        features.mkdir()

        # Create a completed but unlinked document
        doc = features / "1-DONE-old-feature.md"
        doc.write_text("# Old Feature\n\n## Contents\n\nAlready done.\n")

        plan = build_sync_plan(cfs_root, [])

        # Should not create GitHub issue for done documents
        create_actions = [a for a in plan.get_actions() if a.action == SyncAction.CREATE_GITHUB]
        assert len(create_actions) == 0

    def test_skips_closed_github_issues(self, tmp_path):
        """Test that closed unlinked GitHub issues are not synced."""
        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()
        (cfs_root / "features").mkdir()

        github_issues = [
            GitHubIssue(
                number=99,
                title="Old Issue",
                body="Already closed",
                state="closed",
                labels=["cfs:features"],
                url="",
            )
        ]
        plan = build_sync_plan(cfs_root, github_issues)

        # Should not create CFS doc for closed issues
        create_actions = [a for a in plan.get_actions() if a.action == SyncAction.CREATE_CFS]
        assert len(create_actions) == 0


class TestExecuteSyncPlan:
    """Tests for execute_sync_plan function."""

    @patch("cfs.sync.prompt_conflict_resolution")
    def test_content_conflict_in_non_interactive_mode(
        self,
        mock_prompt_conflict_resolution,
        tmp_path,
    ):
        """Test content conflict in non-interactive mode fails gracefully."""
        # Create a mock console that is not interactive
        mock_console = MagicMock(spec=Console)
        mock_console.is_interactive = False

        cfs_root = tmp_path / ".cursor"
        cfs_root.mkdir()

        # Create a sync plan with a content conflict
        issue = GitHubIssue(number=1, title="Test", body="gh body", state="open", labels=[], url="")
        item = SyncItem(
            action=SyncAction.CONTENT_CONFLICT,
            category="features",
            cfs_doc_id=1,
            cfs_doc_path=cfs_root / "1-test.md",
            github_issue=issue,
            cfs_content="cfs content",
            github_content="gh content",
            title="Test",
        )
        plan = SyncPlan(items=[item])

        # Execute the plan
        results = execute_sync_plan(mock_console, cfs_root, plan)

        # Assert that an error was reported and no conflict was resolved
        assert results["errors"] == 1
        assert results["resolved_conflicts"] == 0
        assert results["skipped"] == 0

        # Assert that the prompt was not called
        mock_prompt_conflict_resolution.assert_not_called()

        # Assert that a relevant error message was printed
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Error: Content conflict" in call_args
        assert "Run in an interactive shell to resolve" in call_args
