"""Tests for frontmatter support in documents module."""

from cfs.documents import (
    add_frontmatter,
    extract_document_sections,
    parse_frontmatter,
    remove_frontmatter_key,
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


class TestCodeFenceAwareExtraction:
    """Section extraction must not treat heading-like lines inside code fences
    as section breaks, and unknown h2 subsections belong to their parent
    section (originally found via bugs/16)."""

    def test_fenced_headers_are_content_not_section_breaks(self):
        content = """# Title

## Contents

Example of the template:

```markdown
# Repro

## Working directory

`~/some/path`

## Contents

MY BODY LINE ONE

## Acceptance Criteria
```

After the fence.

## Acceptance criteria

- Real criterion
"""
        sections = extract_document_sections(content)

        assert "MY BODY LINE ONE" in sections["contents"]
        assert "## Working directory" in sections["contents"]
        assert "After the fence." in sections["contents"]
        # The fenced `~/some/path` must not leak into working_directory
        assert sections["working_directory"] == ""
        assert sections["acceptance_criteria"] == "- Real criterion"

    def test_tilde_fences_are_respected(self):
        content = """# Title

## Contents

~~~
## Acceptance criteria
~~~

## Acceptance criteria

- Real
"""
        sections = extract_document_sections(content)

        assert "## Acceptance criteria" in sections["contents"]
        assert sections["acceptance_criteria"] == "- Real"

    def test_unknown_h2_headers_are_kept_as_section_content(self):
        content = """# Title

## Contents

## Summary

GitHub-style body with its own subsections.

## Environment

- macOS

## Acceptance criteria

- Done
"""
        sections = extract_document_sections(content)

        assert "## Summary" in sections["contents"]
        assert "## Environment" in sections["contents"]
        assert "- macOS" in sections["contents"]
        assert sections["acceptance_criteria"] == "- Done"

    def test_round_trip_extraction_is_stable(self):
        """Extracting, embedding into a fresh skeleton, and re-extracting must
        produce the same contents, so an edit round-trip never mutates a
        document's body."""
        summary_style_body = """## Summary

Report with a template example:

```markdown
## Contents

MY BODY LINE ONE
```

Closing remarks."""

        doc = "\n".join(
            [
                "# Some Issue",
                "",
                "## Working directory",
                "",
                "`~/repo`",
                "",
                "## Contents",
                "",
                summary_style_body,
                "",
                "## Acceptance criteria",
                "",
            ]
        )

        first = extract_document_sections(doc)["contents"]
        redoc = f"# Some Issue\n\n## Contents\n\n{first}\n"
        second = extract_document_sections(redoc)["contents"]

        assert first == second == summary_style_body
