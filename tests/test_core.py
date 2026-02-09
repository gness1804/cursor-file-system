"""Unit tests for core CFS operations."""

import pytest

from cfs.core import (
    VALID_CATEGORIES,
    find_cfs_root,
    get_category_path,
    validate_category,
)
from cfs.exceptions import CFSNotFoundError, InvalidCategoryError


class TestFindCFSRoot:
    """Tests for find_cfs_root function."""

    def test_find_cfs_root_in_current_dir(self, tmp_path):
        """Test finding .cursor directory in current directory."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        result = find_cfs_root(tmp_path)
        assert result == cursor_dir
        assert result.exists()
        assert result.is_dir()

    def test_find_cfs_root_in_parent_dir(self, tmp_path):
        """Test finding .cursor directory in parent directory."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)

        result = find_cfs_root(subdir)
        assert result == cursor_dir

    def test_find_cfs_root_not_found(self, tmp_path):
        """Test that CFSNotFoundError is raised when .cursor is not found."""
        with pytest.raises(CFSNotFoundError) as exc_info:
            find_cfs_root(tmp_path)

        assert "CFS structure not found" in str(exc_info.value)
        assert "cfs init" in str(exc_info.value)

    def test_find_cfs_root_with_none_start_path(self, tmp_path, monkeypatch):
        """Test that None start_path defaults to current working directory."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        monkeypatch.chdir(tmp_path)
        result = find_cfs_root(None)
        assert result == cursor_dir


class TestGetCategoryPath:
    """Tests for get_category_path function."""

    def test_get_category_path_valid(self, tmp_path):
        """Test getting path for valid category."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        for category in VALID_CATEGORIES:
            result = get_category_path(cursor_dir, category)
            assert result == cursor_dir / category

    def test_get_category_path_invalid(self, tmp_path):
        """Test that InvalidCategoryError is raised for invalid category."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        with pytest.raises(InvalidCategoryError) as exc_info:
            get_category_path(cursor_dir, "invalid_category")

        assert "invalid_category" in str(exc_info.value)
        assert "Valid categories" in str(exc_info.value)

    def test_get_category_path_case_sensitive(self, tmp_path):
        """Test that category names are case-sensitive."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        with pytest.raises(InvalidCategoryError):
            get_category_path(cursor_dir, "BUGS")  # Should be "bugs"


class TestValidateCategory:
    """Tests for validate_category function."""

    def test_validate_category_valid(self):
        """Test validation of valid categories."""
        for category in VALID_CATEGORIES:
            assert validate_category(category) is True

    def test_validate_category_invalid(self):
        """Test validation of invalid categories."""
        assert validate_category("invalid") is False
        assert validate_category("") is False
        assert validate_category("BUGS") is False  # Case-sensitive

    def test_validate_category_all_valid_categories(self):
        """Test that all expected categories are valid."""
        expected_categories = {
            "rules",
            "research",
            "bugs",
            "features",
            "refactors",
            "docs",
            "progress",
            "qa",
            "security",
            "tmp",
        }
        assert VALID_CATEGORIES == expected_categories
