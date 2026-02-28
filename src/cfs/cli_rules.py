"""Rules commands for the CFS CLI."""

from pathlib import Path
from typing import Optional

import typer

from cfs.cli_helpers import console, handle_cfs_error
from cfs.exceptions import CFSNotFoundError

rules_app = typer.Typer(
    name="rules",
    help="Manage Cursor rules documents",
)


@rules_app.command("create")
def create_rule(
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Rule document name (if not provided, will prompt)",
    ),
    edit: bool = typer.Option(
        False,
        "--edit",
        "-e",
        help="Open editor immediately after creating",
    ),
    comprehensive: bool = typer.Option(
        False,
        "--comprehensive",
        "-c",
        help="Create comprehensive base rules document",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompts (overwrite existing files)",
    ),
) -> None:
    """Create a new Cursor rules document."""
    from cfs import core, documents

    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Get rules directory path
    rules_path = cfs_root / "rules"

    # Check if rules directory is empty (no existing .mdc files)
    existing_rules = list(rules_path.glob("*.mdc")) if rules_path.exists() else []
    is_first_rule = len(existing_rules) == 0

    # If no rules exist and user didn't specify comprehensive, offer it
    if is_first_rule and not comprehensive and name is None and not force:
        console.print(
            "[yellow]No rules files found. This will be your base rules document.[/yellow]",
        )
        comprehensive = typer.confirm(
            "Would you like to create a comprehensive base rules document?",
            default=True,
        )

    # Get name if not provided
    if name is None:
        if comprehensive:
            # Suggest a name based on project
            repo_root = cfs_root.parent
            suggested_name = repo_root.name
            name = typer.prompt(
                "Rule document name (will be converted to kebab-case)",
                default=suggested_name,
            )
        else:
            name = typer.prompt("Rule document name (will be converted to kebab-case)")

        if not name.strip():
            console.print("[red]Error: Name cannot be empty[/red]")
            raise typer.Abort()

    # Convert to kebab-case
    kebab_name = documents.kebab_case(name)

    # Ensure filename ends with .mdc
    if not kebab_name.endswith(".mdc"):
        kebab_name = f"{kebab_name}.mdc"

    file_path = rules_path / kebab_name

    # Check if file already exists
    if file_path.exists():
        console.print(
            f"[yellow]Warning: Rule file '{file_path}' already exists[/yellow]",
        )
        if not force:
            if not typer.confirm("Overwrite existing file?", default=False):
                console.print("[green]Cancelled[/green]")
                raise typer.Abort()

    # Detect repository type for boilerplate
    repo_type = _detect_repo_type(cfs_root)

    # Generate boilerplate content based on repo type and comprehensive flag
    if comprehensive:
        content = _generate_comprehensive_rule_boilerplate(name, repo_type, cfs_root)
    else:
        content = _generate_rule_boilerplate(name, repo_type)

    # If edit flag is set, launch editor with boilerplate
    if edit:
        from cfs import editor

        console.print(f"[yellow]Opening editor for '{kebab_name}'...[/yellow]")
        content = editor.edit_content(content)

    # Create the file
    try:
        rules_path.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        console.print(
            f"[green]✓ Created rule: {file_path}[/green]",
        )
    except Exception as e:
        console.print(f"[red]Error creating rule: {e}[/red]")
        raise typer.Abort()


def _detect_repo_type(cfs_root: Path) -> dict:
    """Detect repository type and technologies.

    Args:
        cfs_root: Path to .cursor directory.

    Returns:
        Dictionary with detected information about repo type.
    """
    repo_root = cfs_root.parent
    detected = {
        "language": None,
        "framework": None,
        "package_manager": None,
        "has_python": False,
        "has_javascript": False,
    }

    # Check for Python
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        detected["language"] = "python"
        detected["has_python"] = True
        detected["package_manager"] = "pip"
        if (repo_root / "poetry.lock").exists():
            detected["package_manager"] = "poetry"
        elif (repo_root / "Pipfile").exists():
            detected["package_manager"] = "pipenv"

    # Check for JavaScript/TypeScript
    if (repo_root / "package.json").exists():
        detected["has_javascript"] = True
        if not detected["language"]:
            detected["language"] = "javascript"
        try:
            import json

            with open(repo_root / "package.json") as f:
                package_data = json.load(f)
                deps = package_data.get("dependencies", {})
                dev_deps = package_data.get("devDependencies", {})

                # Detect frameworks
                if "react" in deps or "react" in dev_deps:
                    detected["framework"] = "react"
                elif "vue" in deps or "vue" in dev_deps:
                    detected["framework"] = "vue"
                elif "next" in deps:
                    detected["framework"] = "nextjs"
                elif "@angular/core" in deps or "@angular/core" in dev_deps:
                    detected["framework"] = "angular"

                if "typescript" in dev_deps or "typescript" in deps:
                    detected["language"] = "typescript"
        except Exception:
            pass

        if (repo_root / "yarn.lock").exists():
            detected["package_manager"] = "yarn"
        elif (repo_root / "pnpm-lock.yaml").exists():
            detected["package_manager"] = "pnpm"
        else:
            detected["package_manager"] = "npm"

    # Check for Ruby/Rails
    if (repo_root / "Gemfile").exists():
        if not detected["language"]:
            detected["language"] = "ruby"
        if (repo_root / "config" / "application.rb").exists():
            detected["framework"] = "rails"

    # Check for Java
    if (repo_root / "pom.xml").exists() or (repo_root / "build.gradle").exists():
        detected["language"] = "java"

    # Check for Go
    if (repo_root / "go.mod").exists():
        detected["language"] = "go"

    return detected


def _generate_rule_boilerplate(name: str, repo_type: dict) -> str:
    """Generate boilerplate content for a rules file.

    Args:
        name: Rule document name.
        repo_type: Dictionary with detected repository information.

    Returns:
        Boilerplate content as string.
    """
    # Determine globs pattern based on language
    globs = "*"
    if repo_type.get("language") == "python":
        globs = "*.py"
    elif repo_type.get("language") == "javascript":
        globs = "*.js"
    elif repo_type.get("language") == "typescript":
        globs = "*.{ts,tsx}"
    elif repo_type.get("language") == "ruby":
        globs = "*.rb"
    elif repo_type.get("language") == "java":
        globs = "*.java"
    elif repo_type.get("language") == "go":
        globs = "*.go"

    # Build description
    desc_parts = [name]
    if repo_type.get("framework"):
        desc_parts.append(f"{repo_type['framework']} framework")
    if repo_type.get("language"):
        desc_parts.append(f"{repo_type['language']} coding standards")
    description = " - ".join(desc_parts)

    # Build content sections
    sections = []

    # Title
    title = name.replace("-", " ").title()
    sections.append(f"# {title}")

    if repo_type.get("language"):
        sections.append(
            "\nThis document provides Cursor AI with coding standards and best practices for this project."
        )
        sections.append("\n## Project Overview")
        sections.append(
            f"\n{name.replace('-', ' ').title()} project using {repo_type['language']}."
        )
        if repo_type.get("framework"):
            sections.append(f"\n**Framework**: {repo_type['framework']}")
        if repo_type.get("package_manager"):
            sections.append(f"\n**Package Manager**: {repo_type['package_manager']}")
    else:
        sections.append(
            f"\nThis document provides Cursor AI with coding standards and best practices for {name.replace('-', ' ')}."
        )

    sections.append("\n## Code Standards")
    sections.append("\n<!-- Add your coding standards here -->")

    sections.append("\n## Best Practices")
    sections.append("\n<!-- Add best practices here -->")

    # Combine into frontmatter + content
    frontmatter = f"""---
globs: {globs}
description: {description}
---
"""

    content = "\n".join(sections)

    return frontmatter + content


def _generate_comprehensive_rule_boilerplate(name: str, repo_type: dict, cfs_root: Path) -> str:
    """Generate comprehensive boilerplate content for a base rules file.

    Args:
        name: Rule document name.
        repo_type: Dictionary with detected repository information.
        cfs_root: Path to .cursor directory.

    Returns:
        Comprehensive boilerplate content as string.
    """
    repo_root = cfs_root.parent

    # Determine globs pattern based on language
    globs = "*"
    if repo_type.get("language") == "python":
        globs = "*.py"
    elif repo_type.get("language") == "javascript":
        globs = "*.js"
    elif repo_type.get("language") == "typescript":
        globs = "*.{ts,tsx}"
    elif repo_type.get("language") == "ruby":
        globs = "*.rb"
    elif repo_type.get("language") == "java":
        globs = "*.java"
    elif repo_type.get("language") == "go":
        globs = "*.go"

    # Build description
    desc_parts = [name.replace("-", " ").title()]
    if repo_type.get("framework"):
        desc_parts.append(f"{repo_type['framework']} framework")
    if repo_type.get("language"):
        desc_parts.append(f"{repo_type['language']} coding standards")
    description = " - ".join(desc_parts)

    # Build comprehensive content sections
    title = name.replace("-", " ").title()

    sections = [f"# {title}"]

    # Project Overview
    if repo_type.get("language"):
        sections.append(
            f"\nThis document provides Cursor AI with specific guidance for working with the {title} codebase"
        )
        if repo_type.get("framework"):
            sections.append(
                f"- a {repo_type['language']} project using {repo_type['framework']} framework."
            )
        else:
            sections.append(f"- a {repo_type['language']} project.")
    else:
        sections.append(
            f"\nThis document provides Cursor AI with coding standards and best practices for {title}."
        )

    sections.append("\n## Technology Stack\n")

    if repo_type.get("language"):
        sections.append(f"- **Language**: {repo_type['language']}")
    if repo_type.get("framework"):
        sections.append(f"- **Framework**: {repo_type['framework']}")
    if repo_type.get("package_manager"):
        sections.append(f"- **Package Manager**: {repo_type['package_manager']}")

    # Detect common tools based on language
    if repo_type.get("language") == "python":
        sections.append("- **Testing**: pytest")
        sections.append("- **Code Quality**: Black (formatting), Ruff (linting)")
        if (repo_root / "pyproject.toml").exists():
            sections.append("- **Packaging**: setuptools with pyproject.toml (PEP 518/621)")

    elif repo_type.get("language") == "javascript":
        sections.append("- **Testing**: Jest or Vitest")
        sections.append("- **Code Quality**: ESLint, Prettier")

    elif repo_type.get("language") == "typescript":
        sections.append("- **Language**: TypeScript")
        sections.append("- **Testing**: Jest or Vitest")
        sections.append("- **Code Quality**: ESLint, Prettier")

    elif repo_type.get("framework") == "rails":
        sections.append("- **Testing**: RSpec")
        sections.append("- **Code Quality**: RuboCop")

    # Code Style & Formatting
    sections.append("\n## Code Style & Formatting\n")

    if repo_type.get("language") == "python":
        sections.append("### Line Length & Formatting")
        # Check pyproject.toml for line length
        line_length = 100
        try:
            # Try tomllib (Python 3.11+)
            try:
                import tomllib

                with open(repo_root / "pyproject.toml", "rb") as f:
                    config = tomllib.load(f)
                    if "tool" in config and "black" in config["tool"]:
                        line_length = config["tool"]["black"].get("line-length", 100)
            except ImportError:
                # Fallback to tomli for Python < 3.11
                try:
                    import tomli as tomllib

                    with open(repo_root / "pyproject.toml", "rb") as f:
                        config = tomllib.load(f)
                        if "tool" in config and "black" in config["tool"]:
                            line_length = config["tool"]["black"].get("line-length", 100)
                except ImportError:
                    pass
        except Exception:
            pass

        sections.append(f"- **Line length**: {line_length} characters")
        sections.append("- **Formatter**: Black")
        sections.append("- **Linter**: Ruff")
        sections.append("- Always run `black src/` and `ruff check src/` before committing")
        sections.append("\n### PEP 8 Compliance")
        sections.append("- Follow PEP 8 standards")
        sections.append("- Use 4 spaces for indentation (no tabs)")
        sections.append(
            "- Use consistent naming: `snake_case` for functions/variables, `PascalCase` for classes"
        )

    elif repo_type.get("language") in ["javascript", "typescript"]:
        sections.append("### Code Style")
        sections.append("- Follow project ESLint configuration")
        sections.append("- Use Prettier for formatting")
        sections.append("- Use consistent naming conventions")

    # Type Hints / TypeScript
    if repo_type.get("language") == "python":
        sections.append("\n## Type Hints\n")
        sections.append(
            "**CRITICAL**: Always use type hints for function signatures and return types.\n"
        )
        sections.append("```python")
        sections.append("from pathlib import Path")
        sections.append("from typing import Optional")
        sections.append("")
        sections.append("def example(start_path: Optional[Path] = None) -> Optional[Path]:")
        sections.append('    """Example function with type hints."""')
        sections.append("    ...")
        sections.append("```")
        sections.append("\n- Use `Optional[T]` for nullable types")
        sections.append("- Use `Path` from pathlib instead of `str` for file paths")
        sections.append("- Import types from `typing` module explicitly")

    elif repo_type.get("language") == "typescript":
        sections.append("\n## Type Safety\n")
        sections.append("**CRITICAL**: Always use TypeScript types and interfaces.\n")
        sections.append("- Use explicit types for function parameters and return values")
        sections.append("- Prefer interfaces over type aliases for object shapes")
        sections.append("- Avoid `any` - use `unknown` when type is truly unknown")

    # Documentation Standards
    sections.append("\n## Documentation Standards\n")

    if repo_type.get("language") == "python":
        sections.append("### Docstrings")
        sections.append("All functions must have docstrings following Google/NumPy style:\n")
        sections.append("```python")
        sections.append("def function_name(param: str) -> int:")
        sections.append('    """Short description.')
        sections.append("    ")
        sections.append("    Args:")
        sections.append("        param: Parameter description.")
        sections.append("        ")
        sections.append("    Returns:")
        sections.append("        Return value description.")
        sections.append('    """')
        sections.append("```")

    # Error Handling
    sections.append("\n## Error Handling\n")
    sections.append("### Exception Types")
    if repo_type.get("language") == "python":
        sections.append(
            "- Use specific exception types: `ValueError`, `FileNotFoundError`, `PermissionError`"
        )
        sections.append("- Raise exceptions with descriptive messages")
    sections.append("- Validate inputs early")
    sections.append("- Include context in error messages")

    # Testing Standards
    sections.append("\n## Testing Standards\n")
    if repo_type.get("language") == "python":
        sections.append("### Test Structure")
        sections.append("- Use pytest for testing")
        sections.append("- Use descriptive test function names")
        sections.append("- Include docstrings explaining what the test verifies")
        sections.append("- Mock external dependencies when appropriate")

    # Project Structure
    sections.append("\n## Project Structure\n")
    sections.append("<!-- Describe your project structure here -->")
    sections.append("\n- Keep code organized in logical modules")
    sections.append("- Each module should have a clear, single responsibility")

    # Module Organization
    sections.append("\n## Module Organization\n")
    sections.append("### Imports Order")
    sections.append("1. Standard library imports")
    sections.append("2. Third-party imports")
    sections.append("3. Local application imports")

    # Code Quality Checklist
    sections.append("\n## Code Quality Checklist\n")
    sections.append("Before committing code, ensure:")
    if repo_type.get("language") == "python":
        sections.append("- [ ] All functions have type hints")
        sections.append("- [ ] All functions have docstrings")
        sections.append("- [ ] Code passes `black` formatting check")
        sections.append("- [ ] Code passes `ruff` linting check")
    sections.append("- [ ] Tests are written for new functionality")
    sections.append("- [ ] Error handling is in place")

    # Development Workflow
    sections.append("\n## Development Workflow\n")
    sections.append("1. **Make changes** in source code")
    if repo_type.get("language") == "python":
        sections.append("2. **Run formatters**: `black src/` and `ruff check src/`")
    sections.append("3. **Write tests**")
    sections.append("4. **Run tests**")
    sections.append("5. **Commit** using conventional commits format")

    # Combine into frontmatter + content
    frontmatter = f"""---
globs: {globs}
description: {description}
---
"""

    content = "\n".join(sections)

    return frontmatter + content
