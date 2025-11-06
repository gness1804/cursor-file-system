"""Unit tests for custom exception classes."""

from cfs.exceptions import (
    CFSError,
    CFSNotFoundError,
    DocumentNotFoundError,
    DocumentOperationError,
    InvalidCategoryError,
    InvalidDocumentIDError,
)


class TestCFSError:
    """Tests for base CFSError exception."""

    def test_cfs_error_message(self):
        """Test that CFSError stores and displays message correctly."""
        error = CFSError("Test error message")
        assert str(error) == "Test error message"
        # CFSError doesn't store message attribute, only subclasses do


class TestCFSNotFoundError:
    """Tests for CFSNotFoundError exception."""

    def test_cfs_not_found_error(self):
        """Test CFSNotFoundError creation and message."""
        error = CFSNotFoundError("CFS not found")
        assert str(error) == "CFS not found"
        assert isinstance(error, CFSError)


class TestInvalidCategoryError:
    """Tests for InvalidCategoryError exception."""

    def test_invalid_category_error(self):
        """Test InvalidCategoryError with category and valid categories."""
        valid_categories = {"bugs", "features", "research"}
        error = InvalidCategoryError("invalid", valid_categories)

        assert error.category == "invalid"
        assert error.valid_categories == valid_categories
        assert "invalid" in str(error)
        assert "Valid categories" in str(error)


class TestDocumentNotFoundError:
    """Tests for DocumentNotFoundError exception."""

    def test_document_not_found_error(self):
        """Test DocumentNotFoundError with doc_id and category."""
        error = DocumentNotFoundError(42, "bugs")

        assert error.doc_id == 42
        assert error.category == "bugs"
        assert "42" in str(error)
        assert "bugs" in str(error)
        assert isinstance(error, CFSError)


class TestInvalidDocumentIDError:
    """Tests for InvalidDocumentIDError exception."""

    def test_invalid_document_id_error(self):
        """Test InvalidDocumentIDError with invalid ID string."""
        error = InvalidDocumentIDError("invalid-id")

        assert error.doc_id == "invalid-id"
        assert "invalid-id" in str(error)
        assert "Invalid document ID" in str(error)
        assert isinstance(error, CFSError)


class TestDocumentOperationError:
    """Tests for DocumentOperationError exception."""

    def test_document_operation_error(self):
        """Test DocumentOperationError with operation and message."""
        error = DocumentOperationError("create document", "Permission denied")

        assert error.operation == "create document"
        assert "create document" in str(error)
        assert "Permission denied" in str(error)
        assert isinstance(error, CFSError)
