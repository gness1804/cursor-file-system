"""Unit tests for document management operations."""

import pytest

from cfs.documents import (
    check_duplicates,
    create_document,
    delete_document,
    edit_document,
    find_document_by_id,
    get_document,
    get_next_id,
    get_next_unresolved_document_id,
    kebab_case,
    list_documents,
    parse_document_id,
    parse_document_id_from_string,
)
from cfs.exceptions import (
    DocumentNotFoundError,
    DocumentOperationError,
    InvalidDocumentIDError,
)


class TestKebabCase:
    """Tests for kebab_case function."""

    def test_kebab_case_simple(self):
        """Test basic kebab-case conversion."""
        assert kebab_case("Hello World") == "hello-world"
        assert kebab_case("fix login bug") == "fix-login-bug"

    def test_kebab_case_with_underscores(self):
        """Test conversion of underscores to hyphens."""
        assert kebab_case("fix_login_bug") == "fix-login-bug"
        assert kebab_case("test_underscore_and space") == "test-underscore-and-space"

    def test_kebab_case_removes_special_chars(self):
        """Test that special characters are removed."""
        assert kebab_case("Fix Login Bug!") == "fix-login-bug"
        assert kebab_case("Test@#$%") == "test"

    def test_kebab_case_multiple_hyphens(self):
        """Test that multiple consecutive hyphens are collapsed."""
        assert kebab_case("test---multiple") == "test-multiple"

    def test_kebab_case_leading_trailing_hyphens(self):
        """Test that leading/trailing hyphens are removed."""
        assert kebab_case("-test-") == "test"
        assert kebab_case("  test  ") == "test"


class TestParseDocumentID:
    """Tests for parse_document_id function."""

    def test_parse_document_id_with_title(self):
        """Test parsing ID from filename with title."""
        assert parse_document_id("1-fix-login-bug.md") == 1
        assert parse_document_id("42-test-document.md") == 42

    def test_parse_document_id_without_extension(self):
        """Test parsing ID from filename without extension."""
        assert parse_document_id("1-fix-login-bug") == 1
        assert parse_document_id("42") == 42

    def test_parse_document_id_numeric_only(self):
        """Test parsing ID from numeric-only filename."""
        assert parse_document_id("1.md") == 1
        assert parse_document_id("42") == 42

    def test_parse_document_id_invalid(self):
        """Test parsing invalid filenames."""
        assert parse_document_id("invalid.md") is None
        assert parse_document_id("no-id-here.md") is None
        assert parse_document_id("") is None


class TestParseDocumentIDFromString:
    """Tests for parse_document_id_from_string function."""

    def test_parse_from_filename(self):
        """Test parsing ID from filename string."""
        assert parse_document_id_from_string("1-fix-login-bug.md") == 1
        assert parse_document_id_from_string("42-test.md") == 42

    def test_parse_from_numeric_string(self):
        """Test parsing ID from numeric string."""
        assert parse_document_id_from_string("1") == 1
        assert parse_document_id_from_string("42") == 42

    def test_parse_invalid_string(self):
        """Test that InvalidDocumentIDError is raised for invalid strings."""
        with pytest.raises(InvalidDocumentIDError):
            parse_document_id_from_string("invalid")

        with pytest.raises(InvalidDocumentIDError):
            parse_document_id_from_string("abc-def")


class TestGetNextID:
    """Tests for get_next_id function."""

    def test_get_next_id_empty_category(self, tmp_path):
        """Test getting next ID when category is empty."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        assert get_next_id(category_path) == 1

    def test_get_next_id_nonexistent_category(self, tmp_path):
        """Test getting next ID when category doesn't exist."""
        category_path = tmp_path / "bugs"

        assert get_next_id(category_path) == 1

    def test_get_next_id_with_existing_documents(self, tmp_path):
        """Test getting next ID with existing documents."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Create some documents
        (category_path / "1-first.md").write_text("content")
        (category_path / "2-second.md").write_text("content")
        (category_path / "5-fifth.md").write_text("content")

        assert get_next_id(category_path) == 6

    def test_get_next_id_ignores_non_md_files(self, tmp_path):
        """Test that non-.md files are ignored."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        (category_path / "1-first.md").write_text("content")
        (category_path / "other.txt").write_text("content")
        (category_path / "README.md").write_text("content")  # No ID prefix

        assert get_next_id(category_path) == 2


class TestFindDocumentByID:
    """Tests for find_document_by_id function."""

    def test_find_document_by_id_exists(self, tmp_path):
        """Test finding an existing document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        doc_file = category_path / "1-fix-login-bug.md"
        doc_file.write_text("content")

        result = find_document_by_id(category_path, 1)
        assert result == doc_file

    def test_find_document_by_id_not_found(self, tmp_path):
        """Test finding a non-existent document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        result = find_document_by_id(category_path, 999)
        assert result is None

    def test_find_document_by_id_nonexistent_category(self, tmp_path):
        """Test finding document in non-existent category."""
        category_path = tmp_path / "bugs"

        result = find_document_by_id(category_path, 1)
        assert result is None


class TestCreateDocument:
    """Tests for create_document function."""

    def test_create_document_success(self, tmp_path):
        """Test successful document creation."""
        category_path = tmp_path / "bugs"
        content = "# Fix Login Bug\n\nThis is a test."

        result = create_document(category_path, "Fix Login Bug", content)
        assert result.exists()
        assert result.read_text() == content
        assert result.name == "1-fix-login-bug.md"

    def test_create_document_empty_content(self, tmp_path):
        """Test creating document with empty content."""
        category_path = tmp_path / "bugs"

        result = create_document(category_path, "Test Document", "")
        assert result.exists()
        assert result.read_text() == ""

    def test_create_document_increments_id(self, tmp_path):
        """Test that IDs increment correctly."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Create first document
        doc1 = create_document(category_path, "First Document")
        assert doc1.name.startswith("1-")

        # Create second document
        doc2 = create_document(category_path, "Second Document")
        assert doc2.name.startswith("2-")

    def test_create_document_empty_title(self, tmp_path):
        """Test that ValueError is raised for empty title."""
        category_path = tmp_path / "bugs"

        with pytest.raises(ValueError, match="title cannot be empty"):
            create_document(category_path, "")

        with pytest.raises(ValueError, match="title cannot be empty"):
            create_document(category_path, "   ")


class TestGetDocument:
    """Tests for get_document function."""

    def test_get_document_success(self, tmp_path):
        """Test successfully reading a document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        doc_file = category_path / "1-test.md"
        content = "# Test Document\n\nContent here."
        doc_file.write_text(content)

        result = get_document(category_path, 1)
        assert result == content

    def test_get_document_not_found(self, tmp_path):
        """Test that DocumentNotFoundError is raised for missing document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        with pytest.raises(DocumentNotFoundError) as exc_info:
            get_document(category_path, 999)

        assert exc_info.value.doc_id == 999
        assert exc_info.value.category == "bugs"


class TestEditDocument:
    """Tests for edit_document function."""

    def test_edit_document_success(self, tmp_path):
        """Test successfully editing a document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        doc_file = category_path / "1-test.md"
        doc_file.write_text("Old content")

        new_content = "New content"
        result = edit_document(category_path, 1, new_content)

        assert result == doc_file
        assert result.read_text() == new_content

    def test_edit_document_not_found(self, tmp_path):
        """Test that DocumentNotFoundError is raised for missing document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        with pytest.raises(DocumentNotFoundError):
            edit_document(category_path, 999, "content")


class TestDeleteDocument:
    """Tests for delete_document function."""

    def test_delete_document_success(self, tmp_path):
        """Test successfully deleting a document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        doc_file = category_path / "1-test.md"
        doc_file.write_text("content")
        assert doc_file.exists()

        delete_document(category_path, 1)
        assert not doc_file.exists()

    def test_delete_document_not_found(self, tmp_path):
        """Test that DocumentNotFoundError is raised for missing document."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        with pytest.raises(DocumentNotFoundError):
            delete_document(category_path, 999)


class TestListDocuments:
    """Tests for list_documents function."""

    def test_list_documents_single_category(self, tmp_path):
        """Test listing documents in a single category."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        bugs_dir = cursor_dir / "bugs"
        bugs_dir.mkdir()

        (bugs_dir / "1-first.md").write_text("content")
        (bugs_dir / "2-second.md").write_text("content")

        result = list_documents(cursor_dir, category="bugs")
        assert "bugs" in result
        assert len(result["bugs"]) == 2
        assert result["bugs"][0]["id"] == 1
        assert result["bugs"][1]["id"] == 2

    def test_list_documents_all_categories(self, tmp_path):
        """Test listing documents across all categories."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        bugs_dir = cursor_dir / "bugs"
        bugs_dir.mkdir()
        (bugs_dir / "1-bug.md").write_text("content")

        features_dir = cursor_dir / "features"
        features_dir.mkdir()
        (features_dir / "1-feature.md").write_text("content")

        result = list_documents(cursor_dir)
        assert "bugs" in result
        assert "features" in result
        assert len(result["bugs"]) == 1
        assert len(result["features"]) == 1

    def test_list_documents_empty_category(self, tmp_path):
        """Test listing empty category."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        bugs_dir = cursor_dir / "bugs"
        bugs_dir.mkdir()

        result = list_documents(cursor_dir, category="bugs")
        assert result["bugs"] == []

    def test_list_documents_ignores_non_md_files(self, tmp_path):
        """Test that non-.md files are ignored."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        bugs_dir = cursor_dir / "bugs"
        bugs_dir.mkdir()

        (bugs_dir / "1-test.md").write_text("content")
        (bugs_dir / "other.txt").write_text("content")
        (bugs_dir / "README.md").write_text("content")  # No ID prefix

        result = list_documents(cursor_dir, category="bugs")
        assert len(result["bugs"]) == 1
        assert result["bugs"][0]["id"] == 1


class TestGetNextUnresolvedDocumentID:
    """Tests for get_next_unresolved_document_id function."""

    def test_get_next_unresolved_empty_category(self, tmp_path):
        """Test getting next unresolved when category is empty."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        result = get_next_unresolved_document_id(category_path)
        assert result is None

    def test_get_next_unresolved_nonexistent_category(self, tmp_path):
        """Test getting next unresolved when category doesn't exist."""
        category_path = tmp_path / "bugs"

        result = get_next_unresolved_document_id(category_path)
        assert result is None

    def test_get_next_unresolved_with_unresolved_documents(self, tmp_path):
        """Test getting next unresolved with unresolved documents."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Create some unresolved documents
        (category_path / "1-first.md").write_text("content")
        (category_path / "3-third.md").write_text("content")
        (category_path / "5-fifth.md").write_text("content")

        result = get_next_unresolved_document_id(category_path)
        assert result == 1  # Should return the lowest ID

    def test_get_next_unresolved_ignores_completed_documents(self, tmp_path):
        """Test that completed documents (with DONE in filename) are ignored."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Create completed documents
        (category_path / "1-DONE-first.md").write_text("content")
        (category_path / "2-DONE-second.md").write_text("content")

        # Create unresolved documents
        (category_path / "3-third.md").write_text("content")
        (category_path / "5-fifth.md").write_text("content")

        result = get_next_unresolved_document_id(category_path)
        assert result == 3  # Should return the lowest unresolved ID

    def test_get_next_unresolved_all_completed(self, tmp_path):
        """Test that None is returned when all documents are completed."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Create only completed documents
        (category_path / "1-DONE-first.md").write_text("content")
        (category_path / "2-DONE-second.md").write_text("content")

        result = get_next_unresolved_document_id(category_path)
        assert result is None

    def test_get_next_unresolved_mixed_completed_and_unresolved(self, tmp_path):
        """Test with mix of completed and unresolved documents."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Create completed documents
        (category_path / "1-DONE-first.md").write_text("content")
        (category_path / "3-DONE-third.md").write_text("content")

        # Create unresolved documents
        (category_path / "2-second.md").write_text("content")
        (category_path / "4-fourth.md").write_text("content")

        result = get_next_unresolved_document_id(category_path)
        assert result == 2  # Should return the lowest unresolved ID

    def test_get_next_unresolved_ignores_non_md_files(self, tmp_path):
        """Test that non-.md files are ignored."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        (category_path / "1-first.md").write_text("content")
        (category_path / "other.txt").write_text("content")
        (category_path / "README.md").write_text("content")  # No ID prefix

        result = get_next_unresolved_document_id(category_path)
        assert result == 1


class TestDuplicatePrevention:
    """Tests for duplicate ID and title prevention."""

    def test_create_document_auto_increments_on_id_collision(self, tmp_path):
        """Test that create_document skips an ID already used by another file."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Pre-create a document with ID 1
        (category_path / "1-existing-bug.md").write_text("content")

        # Create a new document — get_next_id returns 2, no collision
        doc = create_document(category_path, "New Bug", "content")
        assert doc.name == "2-new-bug.md"

        # Simulate race: manually create file with ID 3 after get_next_id would return 3
        (category_path / "3-race-condition.md").write_text("content")

        # Now create_document should skip 3 and use 4
        doc2 = create_document(category_path, "Another Bug", "content")
        assert doc2.name == "4-another-bug.md"

    def test_create_document_rejects_duplicate_title(self, tmp_path):
        """Test that creating a document with a duplicate title raises an error."""
        category_path = tmp_path / "features"
        category_path.mkdir()

        # Create first document
        create_document(category_path, "Add Login", "content")

        # Try to create another with same title
        with pytest.raises(DocumentOperationError, match="already exists"):
            create_document(category_path, "Add Login", "content")

    def test_create_document_rejects_duplicate_title_with_done_marker(self, tmp_path):
        """Test that a DONE-marked doc still blocks creation of same title."""
        category_path = tmp_path / "features"
        category_path.mkdir()

        # Pre-create a DONE document
        (category_path / "1-DONE-add-login.md").write_text("content")

        with pytest.raises(DocumentOperationError, match="already exists"):
            create_document(category_path, "Add Login", "content")

    def test_create_document_rejects_duplicate_title_with_closed_marker(self, tmp_path):
        """Test that a CLOSED-marked doc still blocks creation of same title."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        (category_path / "1-CLOSED-fix-crash.md").write_text("content")

        with pytest.raises(DocumentOperationError, match="already exists"):
            create_document(category_path, "Fix Crash", "content")

    def test_get_next_id_raises_on_existing_duplicates(self, tmp_path):
        """Test that get_next_id raises an error when duplicate IDs exist."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        # Manually create two files with the same ID
        (category_path / "1-first.md").write_text("content")
        (category_path / "1-second.md").write_text("content")

        with pytest.raises(DocumentOperationError, match="Duplicate IDs detected"):
            get_next_id(category_path)


class TestCheckDuplicates:
    """Tests for check_duplicates function."""

    def test_no_issues_on_clean_category(self, tmp_path):
        """Test that a clean category returns no issues."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        (category_path / "1-first-bug.md").write_text("content")
        (category_path / "2-second-bug.md").write_text("content")

        issues = check_duplicates(category_path)
        assert issues == []

    def test_detects_duplicate_ids(self, tmp_path):
        """Test that duplicate IDs are detected."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        (category_path / "1-first.md").write_text("content")
        (category_path / "1-also-first.md").write_text("content")

        issues = check_duplicates(category_path)
        assert len(issues) >= 1
        assert any("Duplicate ID 1" in issue for issue in issues)

    def test_detects_duplicate_titles(self, tmp_path):
        """Test that duplicate titles are detected."""
        category_path = tmp_path / "features"
        category_path.mkdir()

        (category_path / "1-add-login.md").write_text("content")
        (category_path / "2-add-login.md").write_text("content")

        issues = check_duplicates(category_path)
        assert len(issues) >= 1
        assert any("Duplicate title 'add-login'" in issue for issue in issues)

    def test_detects_duplicate_titles_across_status_markers(self, tmp_path):
        """Test that DONE/CLOSED markers are ignored for title comparison."""
        category_path = tmp_path / "bugs"
        category_path.mkdir()

        (category_path / "1-DONE-fix-crash.md").write_text("content")
        (category_path / "2-fix-crash.md").write_text("content")

        issues = check_duplicates(category_path)
        assert any("Duplicate title 'fix-crash'" in issue for issue in issues)

    def test_nonexistent_category_returns_empty(self, tmp_path):
        """Test that a nonexistent category returns no issues."""
        category_path = tmp_path / "nonexistent"
        issues = check_duplicates(category_path)
        assert issues == []
