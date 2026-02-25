"""Unit tests for document management operations."""

import pytest

from cfs.documents import (
    _renumber_category,
    check_duplicates,
    close_document,
    complete_document,
    create_document,
    delete_document,
    edit_document,
    find_document_by_id,
    get_document,
    get_next_id,
    get_next_unresolved_document_id,
    kebab_case,
    list_documents,
    move_document,
    parse_document_id,
    parse_document_id_from_string,
    remove_duplicate_documents,
    unclose_document,
    uncomplete_document,
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


class TestMoveDocument:
    """Tests for move_document function."""

    def test_move_document_basic(self, tmp_path):
        """Test basic document move between categories."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "security"
        dest.mkdir()

        (source / "1-add-login.md").write_text("# Add Login\n\nContent here")

        result = move_document(source, dest, 1, renumber=False)

        assert result == dest / "1-add-login.md"
        assert result.exists()
        assert result.read_text() == "# Add Login\n\nContent here"
        assert not (source / "1-add-login.md").exists()

    def test_move_document_gets_next_id_in_destination(self, tmp_path):
        """Test that moved document gets the next available ID in destination."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "security"
        dest.mkdir()

        # Pre-populate destination with existing docs
        (dest / "1-existing-doc.md").write_text("existing")
        (dest / "2-another-doc.md").write_text("existing")

        (source / "1-add-login.md").write_text("content")

        result = move_document(source, dest, 1, renumber=False)

        assert result.name == "3-add-login.md"
        assert result.exists()

    def test_move_document_preserves_done_marker(self, tmp_path):
        """Test that DONE status marker is preserved during move."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "bugs"
        dest.mkdir()

        (source / "1-DONE-add-login.md").write_text("content")

        result = move_document(source, dest, 1, renumber=False)

        assert result.name == "1-DONE-add-login.md"
        assert result.exists()

    def test_move_document_preserves_closed_marker(self, tmp_path):
        """Test that CLOSED status marker is preserved during move."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "bugs"
        dest.mkdir()

        (source / "1-CLOSED-add-login.md").write_text("content")

        result = move_document(source, dest, 1, renumber=False)

        assert result.name == "1-CLOSED-add-login.md"
        assert result.exists()

    def test_move_document_not_found(self, tmp_path):
        """Test that moving a non-existent document raises error."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "bugs"
        dest.mkdir()

        with pytest.raises(DocumentNotFoundError):
            move_document(source, dest, 99, renumber=False)

    def test_move_document_creates_dest_dir(self, tmp_path):
        """Test that destination directory is created if it doesn't exist."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "security"
        # Don't create dest directory

        (source / "1-add-login.md").write_text("content")

        result = move_document(source, dest, 1, renumber=False)

        assert dest.exists()
        assert result.exists()

    def test_move_document_with_renumber(self, tmp_path):
        """Test that source category is renumbered after move."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "security"
        dest.mkdir()

        (source / "1-first.md").write_text("first")
        (source / "2-second.md").write_text("second")
        (source / "3-third.md").write_text("third")

        # Move doc 2
        move_document(source, dest, 2, renumber=True)

        # Source should be renumbered: 1-first.md, 2-third.md
        assert (source / "1-first.md").exists()
        assert (source / "2-third.md").exists()
        assert not (source / "3-third.md").exists()

    def test_move_document_without_renumber(self, tmp_path):
        """Test that source category is NOT renumbered when renumber=False."""
        source = tmp_path / "features"
        source.mkdir()
        dest = tmp_path / "security"
        dest.mkdir()

        (source / "1-first.md").write_text("first")
        (source / "2-second.md").write_text("second")
        (source / "3-third.md").write_text("third")

        # Move doc 2 without renumbering
        move_document(source, dest, 2, renumber=False)

        # Source should have gap: 1-first.md, 3-third.md
        assert (source / "1-first.md").exists()
        assert not (source / "2-second.md").exists()
        assert (source / "3-third.md").exists()


class TestRenumberCategory:
    """Tests for _renumber_category function."""

    def test_renumber_fills_gap(self, tmp_path):
        """Test that renumbering fills gaps in IDs."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-first.md").write_text("first")
        (category / "3-third.md").write_text("third")
        (category / "5-fifth.md").write_text("fifth")

        _renumber_category(category)

        assert (category / "1-first.md").exists()
        assert (category / "2-third.md").exists()
        assert (category / "3-fifth.md").exists()
        assert not (category / "5-fifth.md").exists()

    def test_renumber_already_sequential(self, tmp_path):
        """Test that renumbering is a no-op when IDs are already sequential."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-first.md").write_text("first")
        (category / "2-second.md").write_text("second")

        _renumber_category(category)

        assert (category / "1-first.md").exists()
        assert (category / "2-second.md").exists()

    def test_renumber_empty_category(self, tmp_path):
        """Test renumbering an empty category is a no-op."""
        category = tmp_path / "bugs"
        category.mkdir()

        _renumber_category(category)
        # No error should be raised

    def test_renumber_nonexistent_category(self, tmp_path):
        """Test renumbering a nonexistent category is a no-op."""
        category = tmp_path / "nonexistent"

        _renumber_category(category)
        # No error should be raised

    def test_renumber_preserves_content(self, tmp_path):
        """Test that file contents are preserved during renumbering."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-first.md").write_text("first content")
        (category / "5-fifth.md").write_text("fifth content")

        _renumber_category(category)

        assert (category / "1-first.md").read_text() == "first content"
        assert (category / "2-fifth.md").read_text() == "fifth content"

    def test_renumber_preserves_done_marker(self, tmp_path):
        """Test that DONE markers are preserved during renumbering."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-first.md").write_text("first")
        (category / "5-DONE-fifth.md").write_text("fifth")

        _renumber_category(category)

        assert (category / "1-first.md").exists()
        assert (category / "2-DONE-fifth.md").exists()


class TestUncompleteDocument:
    """Tests for uncomplete_document function."""

    def test_uncomplete_document_success(self, tmp_path):
        """Test successfully uncompleting a DONE document."""
        category = tmp_path / "bugs"
        category.mkdir()

        done_file = category / "1-DONE-test-bug.md"
        done_file.write_text("# Test Bug\n\nContent\n\n<!-- DONE -->\n")

        result = uncomplete_document(category, 1)

        assert result == category / "1-test-bug.md"
        assert result.exists()
        assert not done_file.exists()

    def test_uncomplete_document_removes_done_comment(self, tmp_path):
        """Test that the <!-- DONE --> comment is removed from file content."""
        category = tmp_path / "bugs"
        category.mkdir()

        done_file = category / "1-DONE-test-bug.md"
        done_file.write_text("# Test Bug\n\nContent\n\n<!-- DONE -->\n")

        result = uncomplete_document(category, 1)

        content = result.read_text(encoding="utf-8")
        assert "<!-- DONE -->" not in content
        assert "# Test Bug" in content
        assert "Content" in content

    def test_uncomplete_document_not_done_raises_error(self, tmp_path):
        """Test that uncompleting a non-DONE document raises DocumentOperationError."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-test-bug.md").write_text("# Test Bug\n\nContent")

        with pytest.raises(DocumentOperationError, match="not marked as done"):
            uncomplete_document(category, 1)

    def test_uncomplete_document_not_found_raises_error(self, tmp_path):
        """Test that uncompleting a non-existent document raises DocumentNotFoundError."""
        category = tmp_path / "bugs"
        category.mkdir()

        with pytest.raises(DocumentNotFoundError):
            uncomplete_document(category, 999)

    def test_uncomplete_document_preserves_title(self, tmp_path):
        """Test that the title portion of the filename is preserved after uncomplete."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "3-DONE-my-cool-feature.md"
        done_file.write_text("# My Cool Feature\n\nContent\n\n<!-- DONE -->\n")

        result = uncomplete_document(category, 3)

        assert result.name == "3-my-cool-feature.md"
        assert result.exists()

    def test_uncomplete_document_without_done_comment(self, tmp_path):
        """Test uncompleting a DONE file that lacks the <!-- DONE --> comment."""
        category = tmp_path / "bugs"
        category.mkdir()

        done_file = category / "1-DONE-test-bug.md"
        done_file.write_text("# Test Bug\n\nContent\n")

        result = uncomplete_document(category, 1)

        assert result == category / "1-test-bug.md"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<!-- DONE -->" not in content

    def test_complete_then_uncomplete_roundtrip(self, tmp_path):
        """Test that completing then uncompleting a document restores the original state."""
        category = tmp_path / "bugs"
        category.mkdir()

        original_file = category / "1-test-bug.md"
        original_content = "# Test Bug\n\nContent\n"
        original_file.write_text(original_content)

        complete_document(category, 1)
        uncompleted_path = uncomplete_document(category, 1)

        assert uncompleted_path == original_file
        assert uncompleted_path.exists()
        content = uncompleted_path.read_text(encoding="utf-8")
        assert "<!-- DONE -->" not in content
        assert "# Test Bug" in content


class TestUncloseDocument:
    """Tests for unclose_document function."""

    def test_unclose_document_success(self, tmp_path):
        """Test successfully unclosing a CLOSED document."""
        category = tmp_path / "bugs"
        category.mkdir()

        closed_file = category / "1-CLOSED-test-bug.md"
        closed_file.write_text("# Test Bug\n\nContent\n\n<!-- CLOSED -->\n")

        result = unclose_document(category, 1)

        assert result == category / "1-test-bug.md"
        assert result.exists()
        assert not closed_file.exists()

    def test_unclose_document_removes_closed_comment(self, tmp_path):
        """Test that the <!-- CLOSED --> comment is removed from file content."""
        category = tmp_path / "bugs"
        category.mkdir()

        closed_file = category / "1-CLOSED-test-bug.md"
        closed_file.write_text("# Test Bug\n\nContent\n\n<!-- CLOSED -->\n")

        result = unclose_document(category, 1)

        content = result.read_text(encoding="utf-8")
        assert "<!-- CLOSED -->" not in content
        assert "# Test Bug" in content
        assert "Content" in content

    def test_unclose_document_not_closed_raises_error(self, tmp_path):
        """Test that unclosing a non-CLOSED document raises DocumentOperationError."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-test-bug.md").write_text("# Test Bug\n\nContent")

        with pytest.raises(DocumentOperationError, match="not marked as closed"):
            unclose_document(category, 1)

    def test_unclose_document_not_found_raises_error(self, tmp_path):
        """Test that unclosing a non-existent document raises DocumentNotFoundError."""
        category = tmp_path / "bugs"
        category.mkdir()

        with pytest.raises(DocumentNotFoundError):
            unclose_document(category, 999)

    def test_unclose_document_preserves_title(self, tmp_path):
        """Test that the title portion of the filename is preserved after unclose."""
        category = tmp_path / "features"
        category.mkdir()

        closed_file = category / "3-CLOSED-my-cool-feature.md"
        closed_file.write_text("# My Cool Feature\n\nContent\n\n<!-- CLOSED -->\n")

        result = unclose_document(category, 3)

        assert result.name == "3-my-cool-feature.md"
        assert result.exists()

    def test_unclose_document_without_closed_comment(self, tmp_path):
        """Test unclosing a CLOSED file that lacks the <!-- CLOSED --> comment."""
        category = tmp_path / "bugs"
        category.mkdir()

        closed_file = category / "1-CLOSED-test-bug.md"
        closed_file.write_text("# Test Bug\n\nContent\n")

        result = unclose_document(category, 1)

        assert result == category / "1-test-bug.md"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<!-- CLOSED -->" not in content

    def test_close_then_unclose_roundtrip(self, tmp_path):
        """Test that closing then unclosing a document restores the original state."""
        category = tmp_path / "bugs"
        category.mkdir()

        original_file = category / "1-test-bug.md"
        original_file.write_text("# Test Bug\n\nContent\n")

        close_document(category, 1)
        unclosed_path = unclose_document(category, 1)

        assert unclosed_path == original_file
        assert unclosed_path.exists()
        content = unclosed_path.read_text(encoding="utf-8")
        assert "<!-- CLOSED -->" not in content
        assert "# Test Bug" in content

    def test_unclose_done_document_raises_error(self, tmp_path):
        """Test that unclosing a DONE (not CLOSED) document raises DocumentOperationError."""
        category = tmp_path / "bugs"
        category.mkdir()

        (category / "1-DONE-test-bug.md").write_text("# Test Bug\n\nContent\n\n<!-- DONE -->\n")

        with pytest.raises(DocumentOperationError, match="not marked as closed"):
            unclose_document(category, 1)


class TestAtomicRename:
    """Tests ensuring complete/close/uncomplete/unclose produce no duplicate files."""

    def test_complete_document_no_duplicate_left(self, tmp_path):
        """After completing, only the DONE file should exist (no original)."""
        category = tmp_path / "features"
        category.mkdir()

        original = category / "1-my-feature.md"
        original.write_text("# My Feature\n\nContent\n")

        result = complete_document(category, 1)

        assert result == category / "1-DONE-my-feature.md"
        assert result.exists()
        # The original (non-DONE) file must NOT exist
        assert not original.exists()
        # Only one file in the directory
        md_files = list(category.glob("*.md"))
        assert len(md_files) == 1

    def test_close_document_no_duplicate_left(self, tmp_path):
        """After closing, only the CLOSED file should exist (no original)."""
        category = tmp_path / "features"
        category.mkdir()

        original = category / "1-my-feature.md"
        original.write_text("# My Feature\n\nContent\n")

        result = close_document(category, 1)

        assert result == category / "1-CLOSED-my-feature.md"
        assert result.exists()
        assert not original.exists()
        md_files = list(category.glob("*.md"))
        assert len(md_files) == 1

    def test_uncomplete_document_no_duplicate_left(self, tmp_path):
        """After uncompleting, only the original file should exist (no DONE)."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "1-DONE-my-feature.md"
        done_file.write_text("# My Feature\n\nContent\n\n<!-- DONE -->\n")

        result = uncomplete_document(category, 1)

        assert result == category / "1-my-feature.md"
        assert result.exists()
        assert not done_file.exists()
        md_files = list(category.glob("*.md"))
        assert len(md_files) == 1

    def test_unclose_document_no_duplicate_left(self, tmp_path):
        """After unclosing, only the original file should exist (no CLOSED)."""
        category = tmp_path / "features"
        category.mkdir()

        closed_file = category / "1-CLOSED-my-feature.md"
        closed_file.write_text("# My Feature\n\nContent\n\n<!-- CLOSED -->\n")

        result = unclose_document(category, 1)

        assert result == category / "1-my-feature.md"
        assert result.exists()
        assert not closed_file.exists()
        md_files = list(category.glob("*.md"))
        assert len(md_files) == 1


class TestRemoveDuplicateDocuments:
    """Tests for remove_duplicate_documents function."""

    def test_no_duplicates_returns_empty(self, tmp_path):
        """Returns empty list when no duplicates exist."""
        category = tmp_path / "features"
        category.mkdir()
        (category / "1-alpha.md").write_text("alpha")
        (category / "2-beta.md").write_text("beta")

        result = remove_duplicate_documents(category)
        assert result == []

    def test_removes_duplicate_keeping_done(self, tmp_path):
        """Keeps DONE version when both DONE and incomplete share the same ID."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "15-DONE-my-feature.md"
        plain_file = category / "15-my-feature.md"
        done_file.write_text("done content")
        plain_file.write_text("plain content")

        result = remove_duplicate_documents(category, dry_run=False)

        assert len(result) == 1
        assert result[0]["kept"] == done_file
        assert result[0]["path"] == plain_file
        # plain file removed, done file kept
        assert done_file.exists()
        assert not plain_file.exists()

    def test_dry_run_does_not_delete(self, tmp_path):
        """Dry-run returns actions without deleting files."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "15-DONE-my-feature.md"
        plain_file = category / "15-my-feature.md"
        done_file.write_text("done content")
        plain_file.write_text("plain content")

        result = remove_duplicate_documents(category, dry_run=True)

        assert len(result) == 1
        # Both files still present
        assert done_file.exists()
        assert plain_file.exists()

    def test_nonexistent_category_returns_empty(self, tmp_path):
        """Returns empty list for a nonexistent category path."""
        result = remove_duplicate_documents(tmp_path / "nonexistent")
        assert result == []

    def test_keeps_most_recently_modified_when_same_status(self, tmp_path):
        """When both duplicates have same DONE status, keeps most recently modified."""
        import time

        category = tmp_path / "features"
        category.mkdir()

        older_done = category / "5-DONE-old-feature.md"
        newer_done = category / "5-DONE-new-feature.md"
        older_done.write_text("older")
        time.sleep(0.05)
        newer_done.write_text("newer")

        result = remove_duplicate_documents(category, dry_run=False)

        assert len(result) == 1
        assert result[0]["kept"] == newer_done
        assert newer_done.exists()
        assert not older_done.exists()

    def test_removes_title_based_duplicates_different_ids(self, tmp_path):
        """Removes title-based duplicates when files share title but have different IDs."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "4-DONE-my-feature.md"
        closed_file = category / "20-CLOSED-my-feature.md"
        done_file.write_text("done content")
        closed_file.write_text("closed content")

        result = remove_duplicate_documents(category, dry_run=False)

        assert len(result) == 1
        # One file kept, one removed
        remaining = [f for f in [done_file, closed_file] if f.exists()]
        assert len(remaining) == 1

    def test_title_duplicate_keeps_done_over_plain(self, tmp_path):
        """Keeps DONE version over plain when title duplicates have different IDs."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "4-DONE-my-feature.md"
        plain_file = category / "20-my-feature.md"
        done_file.write_text("done content")
        plain_file.write_text("plain content")

        result = remove_duplicate_documents(category, dry_run=False)

        assert len(result) == 1
        assert result[0]["kept"] == done_file
        assert done_file.exists()
        assert not plain_file.exists()

    def test_title_duplicate_dry_run(self, tmp_path):
        """Dry-run does not delete title-based duplicates."""
        category = tmp_path / "features"
        category.mkdir()

        done_file = category / "4-DONE-my-feature.md"
        plain_file = category / "20-my-feature.md"
        done_file.write_text("done content")
        plain_file.write_text("plain content")

        result = remove_duplicate_documents(category, dry_run=True)

        assert len(result) == 1
        # Both files still present after dry run
        assert done_file.exists()
        assert plain_file.exists()
