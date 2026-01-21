"""Tests for frontmatter support in documents module."""

from cfs.documents import (
    add_frontmatter,
    build_github_issue_body,
    extract_document_sections,
    get_github_issue_number,
    parse_frontmatter,
    remove_frontmatter_key,
    remove_github_issue_link,
    set_github_issue_number,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_parse_valid_frontmatter(self):
        """Test parsing valid YAML frontmatter."""
        content = """---
github_issue: 42
title: Test
---
# Document Title

Content here.
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {"github_issue": 42, "title": "Test"}
        assert body.startswith("# Document Title")

    def test_parse_no_frontmatter(self):
        """Test parsing document without frontmatter."""
        content = """# Document Title

Content here.
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {}
        assert body == content

    def test_parse_empty_frontmatter(self):
        """Test parsing frontmatter with only whitespace."""
        content = """---

---
# Document Title
"""
        frontmatter, body = parse_frontmatter(content)

        assert frontmatter == {}
        assert body.startswith("# Document Title")

    def test_parse_invalid_yaml(self):
        """Test that invalid YAML is treated as no frontmatter."""
        content = """---
invalid: yaml: content:
---
# Document Title
"""
        frontmatter, body = parse_frontmatter(content)

        # Invalid YAML should return empty frontmatter and original content
        assert frontmatter == {}
        assert body == content

    def test_parse_frontmatter_preserves_body(self):
        """Test that body content is preserved exactly."""
        content = """---
key: value
---
Line 1
Line 2

Line 4
"""
        _, body = parse_frontmatter(content)

        assert body == "Line 1\nLine 2\n\nLine 4\n"


class TestAddFrontmatter:
    """Tests for add_frontmatter function."""

    def test_add_to_document_without_frontmatter(self):
        """Test adding frontmatter to document that has none."""
        content = "# Title\n\nContent"
        result = add_frontmatter(content, {"github_issue": 42})

        assert result.startswith("---\n")
        assert "github_issue: 42" in result
        assert "# Title" in result

    def test_add_to_document_with_frontmatter(self):
        """Test adding to document with existing frontmatter."""
        content = """---
existing: value
---
# Title
"""
        result = add_frontmatter(content, {"github_issue": 42})

        frontmatter, _ = parse_frontmatter(result)
        assert frontmatter["existing"] == "value"
        assert frontmatter["github_issue"] == 42

    def test_update_existing_key(self):
        """Test updating an existing frontmatter key."""
        content = """---
github_issue: 1
---
# Title
"""
        result = add_frontmatter(content, {"github_issue": 42})

        frontmatter, _ = parse_frontmatter(result)
        assert frontmatter["github_issue"] == 42

    def test_add_empty_frontmatter(self):
        """Test adding empty frontmatter does nothing."""
        content = "# Title\n\nContent"
        result = add_frontmatter(content, {})

        assert result == content


class TestRemoveFrontmatterKey:
    """Tests for remove_frontmatter_key function."""

    def test_remove_existing_key(self):
        """Test removing an existing key."""
        content = """---
github_issue: 42
other: value
---
# Title
"""
        result = remove_frontmatter_key(content, "github_issue")

        frontmatter, _ = parse_frontmatter(result)
        assert "github_issue" not in frontmatter
        assert frontmatter["other"] == "value"

    def test_remove_only_key(self):
        """Test removing the only key removes frontmatter entirely."""
        content = """---
github_issue: 42
---
# Title
"""
        result = remove_frontmatter_key(content, "github_issue")

        assert not result.startswith("---")
        assert result.startswith("# Title")

    def test_remove_nonexistent_key(self):
        """Test removing a key that doesn't exist."""
        content = """---
other: value
---
# Title
"""
        result = remove_frontmatter_key(content, "github_issue")

        frontmatter, _ = parse_frontmatter(result)
        assert frontmatter == {"other": "value"}


class TestGetGithubIssueNumber:
    """Tests for get_github_issue_number function."""

    def test_get_existing_issue_number(self):
        """Test getting issue number from frontmatter."""
        content = """---
github_issue: 42
---
# Title
"""
        assert get_github_issue_number(content) == 42

    def test_get_missing_issue_number(self):
        """Test getting issue number when not present."""
        content = "# Title\n\nContent"
        assert get_github_issue_number(content) is None

    def test_get_invalid_issue_number(self):
        """Test handling invalid issue number format."""
        content = """---
github_issue: not_a_number
---
# Title
"""
        assert get_github_issue_number(content) is None

    def test_get_issue_number_as_string(self):
        """Test that string numbers are converted."""
        content = """---
github_issue: "42"
---
# Title
"""
        assert get_github_issue_number(content) == 42


class TestSetGithubIssueNumber:
    """Tests for set_github_issue_number function."""

    def test_set_new_issue_number(self):
        """Test setting issue number on document without one."""
        content = "# Title\n\nContent"
        result = set_github_issue_number(content, 42)

        assert get_github_issue_number(result) == 42

    def test_update_issue_number(self):
        """Test updating existing issue number."""
        content = """---
github_issue: 1
---
# Title
"""
        result = set_github_issue_number(content, 42)

        assert get_github_issue_number(result) == 42


class TestRemoveGithubIssueLink:
    """Tests for remove_github_issue_link function."""

    def test_remove_link(self):
        """Test removing GitHub issue link."""
        content = """---
github_issue: 42
---
# Title
"""
        result = remove_github_issue_link(content)

        assert get_github_issue_number(result) is None


class TestExtractDocumentSections:
    """Tests for extract_document_sections function."""

    def test_extract_all_sections(self):
        """Test extracting all standard sections."""
        content = """# My Document

## Working directory

`~/projects/test`

## Contents

This is the main content.
It has multiple lines.

## Acceptance criteria

- Criterion 1
- Criterion 2
"""
        sections = extract_document_sections(content)

        assert sections["title"] == "My Document"
        assert sections["working_directory"] == "`~/projects/test`"
        assert "main content" in sections["contents"]
        assert "Criterion 1" in sections["acceptance_criteria"]

    def test_extract_with_frontmatter(self):
        """Test that frontmatter is ignored when extracting sections."""
        content = """---
github_issue: 42
---
# My Document

## Contents

Content here.
"""
        sections = extract_document_sections(content)

        assert sections["title"] == "My Document"
        assert "Content here" in sections["contents"]

    def test_extract_missing_sections(self):
        """Test handling of missing sections."""
        content = """# Title Only
"""
        sections = extract_document_sections(content)

        assert sections["title"] == "Title Only"
        assert sections["contents"] == ""
        assert sections["acceptance_criteria"] == ""

    def test_extract_case_insensitive_headers(self):
        """Test that section headers are matched case-insensitively."""
        content = """# Title

## WORKING DIRECTORY

`~/test`

## Acceptance Criteria

- Done
"""
        sections = extract_document_sections(content)

        assert sections["working_directory"] == "`~/test`"
        assert "Done" in sections["acceptance_criteria"]


class TestBuildGithubIssueBody:
    """Tests for build_github_issue_body function."""

    def test_build_with_contents_and_criteria(self):
        """Test building body with both sections."""
        content = """# Issue Title

## Working directory

`~/test`

## Contents

This is what needs to be done.

## Acceptance criteria

- Must work
- Must be tested
"""
        body = build_github_issue_body(content)

        assert "This is what needs to be done." in body
        assert "## Acceptance Criteria" in body
        assert "Must work" in body

    def test_build_contents_only(self):
        """Test building body with only contents section."""
        content = """# Issue Title

## Contents

Just the content.
"""
        body = build_github_issue_body(content)

        assert "Just the content" in body
        assert "Acceptance Criteria" not in body

    def test_build_empty_document(self):
        """Test building body from empty document."""
        content = "# Title"
        body = build_github_issue_body(content)

        assert body == ""

    def test_build_preserves_markdown(self):
        """Test that markdown formatting is preserved."""
        content = """# Title

## Contents

Here's some **bold** and `code`.

- List item 1
- List item 2

## Acceptance criteria

1. First
2. Second
"""
        body = build_github_issue_body(content)

        assert "**bold**" in body
        assert "`code`" in body
        assert "- List item 1" in body
