"""Sync logic between CFS documents and GitHub issues."""

import datetime
import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from cfs.core import (
    BUILTIN_CATEGORIES,
    get_all_categories,
    get_category_path,
    get_hidden_categories,
)
from cfs.documents import (
    CodeFenceTracker,
    build_github_issue_body,
    check_duplicates,
    complete_document,
    create_document,
    edit_document,
    extract_document_sections,
    get_github_issue_number,
    kebab_case,
    list_documents,
    parse_document_id,
    set_github_issue_number,
    uncomplete_document,
    unclose_document,
)
from cfs.github import (
    GitHubIssue,
    add_labels,
    close_issue,
    create_issue,
    ensure_label_exists,
    get_category_from_cfs_label,
    get_cfs_label_for_category,
    update_issue,
)

# Categories to exclude from sync by default.
# Security is excluded because CFS security documents may contain vulnerability
# details that should not be exposed in public GitHub issues.
DEFAULT_EXCLUDED_CATEGORIES = {"tmp", "security"}

# Default categories that should be synced
SYNC_CATEGORIES = BUILTIN_CATEGORIES - DEFAULT_EXCLUDED_CATEGORIES


def compute_sync_categories(
    cfs_root: Optional[Path] = None,
    include_categories: Optional[Set[str]] = None,
    exclude_categories: Optional[Set[str]] = None,
) -> Set[str]:
    """Compute the effective set of categories to sync.

    Args:
        include_categories: Categories to force-include even if in default exclusion list.
        exclude_categories: Additional categories to exclude beyond defaults.

    Returns:
        Set of category names to sync.
    """
    valid_categories = get_all_categories(cfs_root) if cfs_root else set(BUILTIN_CATEGORIES)
    excluded = get_hidden_categories(cfs_root) if cfs_root else set(DEFAULT_EXCLUDED_CATEGORIES)
    if include_categories:
        excluded -= include_categories
    if exclude_categories:
        excluded |= exclude_categories
    return valid_categories - excluded


class SyncAction(Enum):
    """Types of sync actions."""

    CREATE_CFS = "create_cfs"  # Create CFS doc from GitHub issue
    CREATE_GITHUB = "create_github"  # Create GitHub issue from CFS doc
    CLOSE_GITHUB = "close_github"  # Close GitHub issue (CFS is done/closed)
    COMPLETE_CFS = "complete_cfs"  # Mark CFS as done (GitHub is closed)
    REOPEN_CFS = "reopen_cfs"  # Reopen CFS doc (GitHub was reopened)
    CONTENT_CONFLICT = "content_conflict"  # Content differs, needs resolution
    NO_ACTION = "no_action"  # Already in sync


class ConflictStrategy(Enum):
    """Deterministic, non-interactive strategies for resolving content conflicts.

    Used by hooks, CI, and agents so a sync can complete without a human
    at a TTY.  ``INTERACTIVE`` (the default when no strategy is given) prompts
    the user, and falls back to flagging the item for later resolution when no
    usable stdin is available.
    """

    INTERACTIVE = "interactive"  # Prompt the user (default; needs a TTY)
    LOCAL = "local"  # CFS (local) wins — push CFS content to GitHub
    REMOTE = "remote"  # GitHub (remote) wins — pull GitHub content into CFS
    NEWER = "newer"  # Whichever side changed more recently wins
    SKIP = "skip"  # Leave conflicts untouched; report them (advisory)

    @classmethod
    def from_string(cls, value: Optional[str]) -> "ConflictStrategy":
        """Parse a user-supplied strategy name, defaulting to INTERACTIVE for None/empty.

        ``interactive`` is an internal state, not a user-choosable value: passing
        it explicitly (e.g. ``--strategy interactive``) is rejected so it can't
        silently defeat ``--non-interactive`` in a hook/CI wrapper.
        """
        if not value:
            return cls.INTERACTIVE
        normalized = value.strip().lower()
        choosable = [s for s in cls if s != cls.INTERACTIVE]
        for strategy in choosable:
            if strategy.value == normalized:
                return strategy
        valid = ", ".join(s.value for s in choosable)
        raise ValueError(f"Invalid conflict strategy '{value}'. Valid: {valid}.")


# --- Prompt-injection guardrail --------------------------------------------
# When a non-interactive strategy would overwrite a local CFS document (which
# AI agents later read and trust) with content pulled from a GitHub issue, we
# scan that incoming content for common prompt-injection signatures. Anything
# that trips a signature is NOT auto-applied — it is deferred so a human can
# review the diff via an interactive sync. This is a heuristic tripwire meant
# to catch the obvious cases, not a guarantee; interactive resolution (where a
# human sees the full diff) remains the real safeguard.
_INJECTION_SIGNATURES: List[Tuple["re.Pattern[str]", str]] = [
    (
        re.compile(
            r"ignore\s+(?:all\s+|any\s+)?(?:the\s+|your\s+|previous\s+)*"
            r"(?:previous|prior|above|earlier|preceding|foregoing)\s+"
            r"(?:instructions?|prompts?|messages?|context|directions?)",
            re.IGNORECASE,
        ),
        "'ignore previous instructions' phrase",
    ),
    (
        re.compile(
            r"disregard\s+(?:all\s+|any\s+)?(?:the\s+|your\s+)?"
            r"(?:previous|prior|above|earlier|preceding)",
            re.IGNORECASE,
        ),
        "'disregard the above' phrase",
    ),
    (
        re.compile(
            r"forget\s+(?:all\s+|everything\s+)?(?:the\s+|your\s+)?"
            r"(?:previous|prior|above|earlier|instructions?)",
            re.IGNORECASE,
        ),
        "'forget previous instructions' phrase",
    ),
    (
        re.compile(r"you\s+are\s+now\s+(?:a\b|an\b|the\b|no\s+longer\b)", re.IGNORECASE),
        "role-reassignment ('you are now ...')",
    ),
    (
        re.compile(
            r"(?:reveal|print|show|repeat|output|expose|leak|dump)\s+"
            r"(?:me\s+)?(?:your\s+|the\s+)?"
            r"(?:system\s+prompt|system\s+message|instructions|prompt|"
            r"api[\s_-]?key|secret|token|credentials?)",
            re.IGNORECASE,
        ),
        "system-prompt / secret exfiltration attempt",
    ),
    (
        re.compile(r"\bnew\s+instructions?\s*[:\-]", re.IGNORECASE),
        "'new instructions:' directive",
    ),
    (
        re.compile(r"</?\s*(?:system|assistant|user)\s*>", re.IGNORECASE),
        "fake chat/role tag",
    ),
    (
        re.compile(r"\[/?INST\]|<\|im_(?:start|end)\|>|<<SYS>>", re.IGNORECASE),
        "model chat-template control token",
    ),
]

# Invisible / bidirectional control characters commonly used to hide injected
# instructions from a human reviewer while leaving them visible to a model.
_SUSPICIOUS_UNICODE = re.compile(
    "["
    "\u200b-\u200f"  # zero-width space/joiners + LTR/RTL marks
    "\u202a-\u202e"  # bidi embedding / override
    "\u2060-\u2064"  # word joiner / invisible math operators
    "\u2066-\u2069"  # bidi isolates
    "\ufeff"  # BOM / zero-width no-break space
    "]"
)


def detect_prompt_injection(text: str) -> List[str]:
    """Scan untrusted text for common prompt-injection signatures.

    Returns a list of human-readable descriptions of the signatures found
    (empty if the text looks clean). Heuristic only — favors surfacing the
    obvious override phrases and hidden control characters.
    """
    if not text:
        return []
    found: List[str] = []
    for pattern, label in _INJECTION_SIGNATURES:
        if pattern.search(text):
            found.append(label)
    if _SUSPICIOUS_UNICODE.search(text):
        found.append("hidden/bidirectional control characters")
    return found


def _incoming_github_text(item: "SyncItem") -> str:
    """Concatenate the GitHub-side title and body for injection scanning."""
    title = item.github_issue.title if item.github_issue else ""
    return f"{title or ''}\n{item.github_content or ''}"


def _parse_github_timestamp(value: str) -> Optional[float]:
    """Parse a GitHub ISO-8601 timestamp into a POSIX timestamp (UTC).

    Returns None if the value is missing or unparseable.
    """
    if not value:
        return None
    text = value.strip()
    # Python 3.8's fromisoformat does not accept a trailing 'Z'.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


@dataclass
class SyncItem:
    """Represents a single item to be synced."""

    action: SyncAction
    category: str
    cfs_doc_id: Optional[int] = None
    cfs_doc_path: Optional[Path] = None
    github_issue: Optional[GitHubIssue] = None
    cfs_content: Optional[str] = None
    github_content: Optional[str] = None
    title: str = ""
    # For CONTENT_CONFLICT: which fields diverged, so we can tell the user
    # *what* needs a decision rather than just "something differs".
    title_differs: bool = False
    body_differs: bool = False

    def conflict_reason(self) -> str:
        """Human-readable summary of what diverged for a content conflict."""
        parts = []
        if self.title_differs:
            parts.append("title")
        if self.body_differs:
            parts.append("body")
        if not parts:
            return "content"
        return " and ".join(parts)

    def __str__(self) -> str:
        if self.action == SyncAction.CREATE_CFS:
            return f"Create CFS doc in {self.category} from GitHub #{self.github_issue.number}"
        elif self.action == SyncAction.CREATE_GITHUB:
            return f"Create GitHub issue from {self.category}/{self.cfs_doc_id}"
        elif self.action == SyncAction.CLOSE_GITHUB:
            return f"Close GitHub #{self.github_issue.number} (CFS {self.category}/{self.cfs_doc_id} is done)"
        elif self.action == SyncAction.COMPLETE_CFS:
            return f"Mark {self.category}/{self.cfs_doc_id} as done (GitHub #{self.github_issue.number} is closed)"
        elif self.action == SyncAction.REOPEN_CFS:
            return f"Reopen {self.category}/{self.cfs_doc_id} (GitHub #{self.github_issue.number} was reopened)"
        elif self.action == SyncAction.CONTENT_CONFLICT:
            return f"Content conflict: {self.category}/{self.cfs_doc_id} vs GitHub #{self.github_issue.number}"
        return "No action needed"


@dataclass
class SyncPlan:
    """Collection of sync items representing the full sync plan."""

    items: List[SyncItem] = field(default_factory=list)
    linked_count: int = 0
    unlinked_cfs_count: int = 0
    unlinked_github_count: int = 0
    duplicate_categories: Set[str] = field(default_factory=set)

    def add(self, item: SyncItem) -> None:
        """Add a sync item to the plan."""
        self.items.append(item)

    def has_actions(self) -> bool:
        """Check if there are any actions to perform."""
        return any(item.action != SyncAction.NO_ACTION for item in self.items)

    def get_actions(self) -> List[SyncItem]:
        """Get only items that require action."""
        return [item for item in self.items if item.action != SyncAction.NO_ACTION]


def get_all_cfs_documents(
    cfs_root: Path, sync_categories: Optional[Set[str]] = None
) -> Dict[str, List[dict]]:
    """Get all CFS documents organized by category.

    Args:
        cfs_root: Path to the .cursor directory.
        sync_categories: Categories to include. Defaults to SYNC_CATEGORIES.

    Returns:
        Dictionary mapping category to list of document info dicts.
    """
    categories = sync_categories if sync_categories is not None else SYNC_CATEGORIES
    all_docs = {}
    for category in categories:
        docs = list_documents(cfs_root, category)
        if category in docs:
            all_docs[category] = docs[category]
        else:
            all_docs[category] = []
    return all_docs


def get_linked_documents(
    cfs_root: Path, sync_categories: Optional[Set[str]] = None
) -> Dict[int, Tuple[str, int, Path]]:
    """Get all CFS documents that are linked to GitHub issues.

    Args:
        cfs_root: Path to the .cursor directory.
        sync_categories: Categories to include. Defaults to SYNC_CATEGORIES.

    Returns:
        Dictionary mapping GitHub issue number to (category, doc_id, doc_path).
    """
    linked = {}
    all_docs = get_all_cfs_documents(cfs_root, sync_categories)

    for category, docs in all_docs.items():
        for doc in docs:
            doc_path = doc["path"]
            try:
                content = doc_path.read_text(encoding="utf-8")
                issue_num = get_github_issue_number(content)
                if issue_num is not None:
                    linked[issue_num] = (category, doc["id"], doc_path)
            except (OSError, IOError):
                continue

    return linked


_ACCEPTANCE_HEADER_RE = re.compile(r"^#{2,}\s*acceptance\s*criteria\s*$", re.IGNORECASE)


def _normalize_text_for_compare(text: str) -> str:
    """Normalize text for stable comparisons."""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _split_github_issue_body(body: str, normalize: bool = False) -> Tuple[str, str]:
    """Split a GitHub issue body into contents and acceptance criteria sections."""
    if normalize:
        text = _normalize_text_for_compare(body)
    else:
        text = body.replace("\r\n", "\n").replace("\r", "\n") if body else ""

    lines = text.split("\n") if text else []
    contents_lines: List[str] = []
    acceptance_lines: List[str] = []
    in_acceptance = False
    fence = CodeFenceTracker()

    for line in lines:
        # Heading detection is code-fence-aware: a literal "## Acceptance
        # Criteria" inside a code block is content, not a section break.
        if not fence.process(line) and _ACCEPTANCE_HEADER_RE.match(line.strip()):
            in_acceptance = True
            continue
        if in_acceptance:
            acceptance_lines.append(line)
        else:
            contents_lines.append(line)

    contents = "\n".join(contents_lines)
    acceptance = "\n".join(acceptance_lines)

    if normalize:
        return (
            _normalize_text_for_compare(contents),
            _normalize_text_for_compare(acceptance),
        )

    return contents, acceptance


def _build_canonical_issue_body(contents: str, acceptance_criteria: str) -> str:
    """Build a canonical GitHub issue body from section content."""
    parts: List[str] = []
    if contents:
        parts.append(contents)
    if acceptance_criteria:
        if parts:
            parts.append("")
        parts.append("## Acceptance Criteria")
        parts.append("")
        parts.append(acceptance_criteria)
    return "\n".join(parts)


def _build_canonical_cfs_body(cfs_content: str) -> str:
    """Build a canonical comparable body from CFS content."""
    cfs_body = build_github_issue_body(cfs_content) if cfs_content else ""
    return _normalize_text_for_compare(cfs_body)


def _build_canonical_github_body(github_body: str) -> str:
    """Build a canonical comparable body from GitHub content."""
    contents, acceptance = _split_github_issue_body(github_body or "", normalize=True)
    canonical = _build_canonical_issue_body(contents, acceptance)
    return _normalize_text_for_compare(canonical)


def _get_comparable_bodies(cfs_content: str, github_body: str) -> Tuple[str, str]:
    """Return canonical bodies for comparing CFS and GitHub content."""
    return (
        _build_canonical_cfs_body(cfs_content),
        _build_canonical_github_body(github_body),
    )


def is_cfs_document_done(doc_path: Path) -> bool:
    """Check if a CFS document is marked as done or closed.

    Args:
        doc_path: Path to the document.

    Returns:
        True if document is done or closed.
    """
    stem = doc_path.stem
    doc_id = parse_document_id(doc_path.name)
    if doc_id is not None:
        return f"{doc_id}-DONE-" in stem or f"{doc_id}-CLOSED-" in stem
    return "DONE" in stem or "CLOSED" in stem


def get_category_from_github_issue(
    issue: GitHubIssue, sync_categories: Optional[Set[str]] = None
) -> Optional[str]:
    """Extract CFS category from GitHub issue labels.

    Args:
        issue: GitHub issue object.
        sync_categories: Categories to include. Defaults to SYNC_CATEGORIES.

    Returns:
        Category name if found in labels, None otherwise.
    """
    categories = sync_categories if sync_categories is not None else SYNC_CATEGORIES
    for label in issue.labels:
        category = get_category_from_cfs_label(label)
        if category and category in categories:
            return category
    return None


def _find_doc_by_title(docs: List[dict], title: str) -> Optional[dict]:
    """Find a document in a list by matching kebab-case title.

    Args:
        docs: List of document info dicts (from list_documents).
        title: Title to search for (will be kebab-cased for comparison).

    Returns:
        Matching document dict, or None.
    """
    from cfs.documents import _extract_title_from_filename

    target = kebab_case(title)
    if not target:
        return None
    for doc in docs:
        doc_path = doc.get("path")
        if doc_path is None:
            continue
        existing = _extract_title_from_filename(doc_path.name)
        if existing and existing == target:
            return doc
    return None


def build_sync_plan(
    cfs_root: Path,
    github_issues: List[GitHubIssue],
    sync_categories: Optional[Set[str]] = None,
) -> SyncPlan:
    """Build a sync plan comparing CFS documents with GitHub issues.

    Args:
        cfs_root: Path to the .cursor directory.
        github_issues: List of GitHub issues to compare against.
        sync_categories: Categories to include. Defaults to SYNC_CATEGORIES.

    Returns:
        SyncPlan with all necessary sync actions.
    """
    plan = SyncPlan()
    categories = sync_categories if sync_categories is not None else SYNC_CATEGORIES

    # Check for duplicate IDs/titles in each category before building the plan.
    # Duplicate IDs can cause incorrect sync behaviour (wrong document linked,
    # or get_next_id raising an error that aborts creation).
    duplicate_categories: Set[str] = set()
    for category in categories:
        category_path = get_category_path(cfs_root, category)
        if check_duplicates(category_path):
            duplicate_categories.add(category)
    plan.duplicate_categories = duplicate_categories

    # Get all linked documents
    linked_docs = get_linked_documents(cfs_root, categories)
    plan.linked_count = len(linked_docs)

    # Track which GitHub issues are linked
    linked_github_numbers: Set[int] = set(linked_docs.keys())

    # Get all CFS documents
    all_docs = get_all_cfs_documents(cfs_root, categories)

    # Check each linked document for status/content sync
    for issue_num, (category, doc_id, doc_path) in linked_docs.items():
        # Find the corresponding GitHub issue
        github_issue = next(
            (i for i in github_issues if i.number == issue_num),
            None,
        )

        if github_issue is None:
            # GitHub issue was deleted - skip for now
            continue

        cfs_is_done = is_cfs_document_done(doc_path)
        github_is_closed = github_issue.state.lower() == "closed"

        # Check for status mismatch
        if cfs_is_done and not github_is_closed:
            # CFS is done but GitHub is open -> GitHub was reopened, reopen CFS
            plan.add(
                SyncItem(
                    action=SyncAction.REOPEN_CFS,
                    category=category,
                    cfs_doc_id=doc_id,
                    cfs_doc_path=doc_path,
                    github_issue=github_issue,
                    title=github_issue.title,
                )
            )
        elif github_is_closed and not cfs_is_done:
            # GitHub is closed but CFS is open -> mark CFS as done
            plan.add(
                SyncItem(
                    action=SyncAction.COMPLETE_CFS,
                    category=category,
                    cfs_doc_id=doc_id,
                    cfs_doc_path=doc_path,
                    github_issue=github_issue,
                    title=github_issue.title,
                )
            )
        elif not cfs_is_done and not github_is_closed:
            # Both open - check for content differences
            try:
                cfs_content = doc_path.read_text(encoding="utf-8")
                cfs_sections = extract_document_sections(cfs_content)
                cfs_title = cfs_sections["title"]

                # Compare content (normalize whitespace and headings)
                cfs_body_normalized, github_body_normalized = _get_comparable_bodies(
                    cfs_content,
                    github_issue.body or "",
                )

                # Only flag as conflict if bodies differ, or if titles differ AND both have titles
                body_differs = cfs_body_normalized != github_body_normalized
                title_differs = (
                    bool(cfs_title) and cfs_title.strip() != (github_issue.title or "").strip()
                )

                if body_differs or title_differs:
                    plan.add(
                        SyncItem(
                            action=SyncAction.CONTENT_CONFLICT,
                            category=category,
                            cfs_doc_id=doc_id,
                            cfs_doc_path=doc_path,
                            github_issue=github_issue,
                            cfs_content=cfs_content,
                            github_content=github_issue.body,
                            title=cfs_title or github_issue.title,
                            title_differs=title_differs,
                            body_differs=body_differs,
                        )
                    )
            except (OSError, IOError):
                continue

    # Find unlinked CFS documents (need to create GitHub issues)
    for category, docs in all_docs.items():
        for doc in docs:
            doc_path = doc["path"]
            try:
                content = doc_path.read_text(encoding="utf-8")
                issue_num = get_github_issue_number(content)
                if issue_num is None and not is_cfs_document_done(doc_path):
                    # Unlinked and not done -> create GitHub issue
                    sections = extract_document_sections(content)
                    plan.add(
                        SyncItem(
                            action=SyncAction.CREATE_GITHUB,
                            category=category,
                            cfs_doc_id=doc["id"],
                            cfs_doc_path=doc_path,
                            cfs_content=content,
                            title=sections["title"] or doc["title"],
                        )
                    )
                    plan.unlinked_cfs_count += 1
            except (OSError, IOError):
                continue

    # Find unlinked GitHub issues (need to create CFS documents)
    for issue in github_issues:
        if issue.number not in linked_github_numbers and issue.state.lower() == "open":
            # Determine target category from labels
            category = get_category_from_github_issue(issue, categories)

            # Before scheduling CREATE_CFS, check whether a CFS document with
            # the same title already exists in the target category.  This
            # prevents creating a new (duplicate) doc when the existing one
            # simply lacks the github_issue frontmatter link.
            if category is not None:
                existing_doc = _find_doc_by_title(all_docs.get(category, []), issue.title)
                if existing_doc is not None:
                    # A matching document already exists – skip creation.
                    # The user should link them manually or run dedup.
                    continue

                # Also skip if the target category has duplicate IDs; attempting
                # to create there would fail (get_next_id raises on duplicates).
                if category in duplicate_categories:
                    continue

            plan.add(
                SyncItem(
                    action=SyncAction.CREATE_CFS,
                    category=category,  # May be None, will prompt user
                    github_issue=issue,
                    github_content=issue.body,
                    title=issue.title,
                )
            )
            plan.unlinked_github_count += 1

    return plan


def generate_diff(local_content: str, remote_content: str) -> str:
    """Generate a unified diff between local and remote content.

    Args:
        local_content: Local (CFS) content.
        remote_content: Remote (GitHub) content.

    Returns:
        Unified diff string.
    """
    local_lines = local_content.splitlines(keepends=True)
    remote_lines = remote_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        remote_lines,
        local_lines,
        fromfile="GitHub (remote)",
        tofile="CFS (local)",
        lineterm="",
    )

    return "\n".join(diff)


def display_diff(console: Console, local_content: str, remote_content: str) -> None:
    """Display a colored diff between local and remote content.

    Args:
        console: Rich console for output.
        local_content: Local (CFS) content.
        remote_content: Remote (GitHub) content.
    """
    diff = generate_diff(local_content, remote_content)

    if not diff:
        console.print("[green]Contents are identical.[/green]")
        return

    # Color the diff output with a clear legend
    lines = []
    for line in diff.split("\n"):
        if line.startswith("+++"):
            lines.append(f"[bold blue]{line}[/bold blue]")
        elif line.startswith("---"):
            lines.append(f"[bold red]{line}[/bold red]")
        elif line.startswith("@@"):
            lines.append(f"[cyan]{line}[/cyan]")
        elif line.startswith("+"):
            lines.append(f"[blue]{line}[/blue]")
        elif line.startswith("-"):
            lines.append(f"[red]{line}[/red]")
        else:
            lines.append(f"[dim]{line}[/dim]" if line else line)

    diff_panel = Panel("\n".join(lines), title="Diff", border_style="yellow")
    console.print(
        Panel(
            "\n".join(
                [
                    "Legend: [blue]+ CFS (local)[/blue], [red]- GitHub (remote)[/red].",
                    "Normalization: line endings, trailing whitespace, edge blank lines,",
                    "and Acceptance Criteria heading are standardized for comparison.",
                ]
            ),
            title="Comparison Notes",
            border_style="cyan",
        )
    )
    console.print(diff_panel)


def prompt_category_selection(
    console: Console, title: str, sync_categories: Optional[Set[str]] = None
) -> Optional[str]:
    """Prompt user to select a category for a new CFS document.

    Args:
        console: Rich console for output.
        title: Issue title for context.
        sync_categories: Categories to include. Defaults to SYNC_CATEGORIES.

    Returns:
        Selected category name or None if cancelled.
    """
    console.print(f"\n[yellow]Select category for:[/yellow] {title}")

    cats = sync_categories if sync_categories is not None else SYNC_CATEGORIES
    categories = sorted(cats)
    for i, cat in enumerate(categories, 1):
        console.print(f"  {i}. {cat}")

    console.print("  0. Skip this issue")

    while True:
        choice = Prompt.ask("Enter number", default="0")
        try:
            idx = int(choice)
            if idx == 0:
                return None
            if 1 <= idx <= len(categories):
                return categories[idx - 1]
        except ValueError:
            pass
        console.print("[red]Invalid choice. Please try again.[/red]")


def prompt_conflict_resolution(
    console: Console,
    item: SyncItem,
) -> Optional[str]:
    """Prompt user to resolve a content conflict.

    Args:
        console: Rich console for output.
        item: SyncItem with conflict details.

    Returns:
        "local" to use CFS, "remote" to use GitHub, "skip" to skip, or None to abort.
    """
    console.print(f"\n[yellow]Content conflict ({item.conflict_reason()}):[/yellow] {item.title}")
    console.print(f"  CFS: {item.category}/{item.cfs_doc_id}")
    console.print(f"  GitHub: #{item.github_issue.number}")
    console.print(
        "  [dim]The document and the GitHub issue have different content — "
        "pick which one wins.[/dim]"
    )

    # Build comparable content
    cfs_body, github_body = _get_comparable_bodies(
        item.cfs_content or "",
        item.github_content or "",
    )

    cfs_title = extract_document_sections(item.cfs_content or "").get("title", "")
    github_title = item.github_issue.title if item.github_issue else ""
    if cfs_title.strip() != (github_title or "").strip():
        console.print(
            "\n[yellow]Title differs:[/yellow] "
            f"[blue]CFS:[/blue] {cfs_title or '(empty)'} | "
            f"[red]GitHub:[/red] {github_title or '(empty)'}"
        )

    display_diff(console, cfs_body, github_body)

    console.print("\nOptions:")
    console.print("  1. Use [blue]CFS (local)[/blue] version - update GitHub")
    console.print("  2. Use [red]GitHub (remote)[/red] version - update CFS")
    console.print("  3. Skip this conflict")
    console.print("  0. Abort sync")

    while True:
        choice = Prompt.ask("Enter number", default="3")
        if choice == "1":
            return "local"
        elif choice == "2":
            return "remote"
        elif choice == "3":
            return "skip"
        elif choice == "0":
            return None
        console.print("[red]Invalid choice. Please try again.[/red]")


def _resolve_conflict_noninteractive(
    item: SyncItem,
    strategy: ConflictStrategy,
) -> Tuple[Optional[str], str]:
    """Deterministically pick a winner for a content conflict.

    Args:
        item: The CONTENT_CONFLICT sync item.
        strategy: A non-interactive strategy (LOCAL/REMOTE/NEWER/SKIP).

    Returns:
        A tuple of (resolution, explanation) where resolution is "local",
        "remote", or None (meaning skip/defer). The explanation describes why
        that side was chosen, for logging.
    """
    if strategy == ConflictStrategy.LOCAL:
        return "local", "strategy=local (CFS wins)"
    if strategy == ConflictStrategy.REMOTE:
        return "remote", "strategy=remote (GitHub wins)"
    if strategy == ConflictStrategy.SKIP:
        return None, "strategy=skip"

    # NEWER: compare the CFS file mtime with the GitHub issue's updated_at.
    github_ts = _parse_github_timestamp(item.github_issue.updated_at) if item.github_issue else None
    cfs_ts: Optional[float] = None
    if item.cfs_doc_path is not None:
        try:
            cfs_ts = item.cfs_doc_path.stat().st_mtime
        except OSError:
            cfs_ts = None

    if cfs_ts is not None and github_ts is not None:
        if cfs_ts >= github_ts:
            return "local", "strategy=newer (CFS modified more recently)"
        return "remote", "strategy=newer (GitHub updated more recently)"

    # Timestamps unavailable — fall back to CFS (the side the user is most
    # likely actively editing, e.g. during a pre-commit hook). Least surprising
    # for a routine commit, and never silently discards the user's local work.
    return "local", "strategy=newer (timestamps unavailable; defaulting to CFS)"


def _warn_prompt_eof(console: Console, title: str) -> None:
    """Warn that a prompt ran without usable stdin — a human must rerun it."""
    console.print(
        f"[yellow]Needs interactive resolution: '{title}' "
        "(no input available). Run 'cfs gh sync' in a terminal.[/yellow]"
    )


def execute_sync_plan(
    console: Console,
    cfs_root: Path,
    plan: SyncPlan,
    dry_run: bool = False,
    strategy: ConflictStrategy = ConflictStrategy.INTERACTIVE,
) -> Dict[str, int]:
    """Execute a sync plan.

    Args:
        console: Rich console for output.
        cfs_root: Path to the .cursor directory.
        plan: SyncPlan to execute.
        dry_run: If True, only show what would be done.
        strategy: How to resolve content conflicts. ``INTERACTIVE`` (default)
            prompts the user; ``LOCAL``/``REMOTE``/``NEWER``/``SKIP`` resolve
            deterministically without a TTY, for hooks/CI/agents.

    Returns:
        Dictionary with counts of actions taken.
    """
    results = {
        "created_cfs": 0,
        "created_github": 0,
        "closed_github": 0,
        "completed_cfs": 0,
        "reopened_cfs": 0,
        "resolved_conflicts": 0,
        "skipped": 0,
        "deferred": 0,
        "needs_interactive": 0,
        "errors": 0,
    }

    actions = plan.get_actions()
    if not actions:
        console.print("[green]Everything is in sync![/green]")
        return results

    for item in actions:
        try:
            if item.action == SyncAction.CREATE_CFS:
                # Prompt for category if not determined from labels
                category = item.category
                if category is None:
                    if dry_run:
                        # In dry-run mode, skip category selection and just show placeholder
                        console.print(
                            f"[dim]Would create CFS doc (category TBD) "
                            f"from GitHub #{item.github_issue.number}[/dim]"
                        )
                        continue
                    elif strategy != ConflictStrategy.INTERACTIVE:
                        # A category can't be inferred from labels and there is
                        # no deterministic rule to pick one. Defer it (advisory)
                        # rather than blocking a non-interactive sync — the user
                        # can label the issue or run an interactive sync later.
                        console.print(
                            f"[dim]Deferred: GitHub #{item.github_issue.number} "
                            f"('{item.title}') has no CFS category label; skipping "
                            "creation. Add a cfs:<category> label or run "
                            "'cfs gh sync' interactively to file it.[/dim]"
                        )
                        results["deferred"] += 1
                        continue
                    elif not console.is_interactive:
                        # Don't prompt without a TTY — input() would crash with
                        # EOFError. A human needs to pick the category.
                        console.print(
                            f"[yellow]Needs interactive resolution: GitHub "
                            f"#{item.github_issue.number} ('{item.title}') has no "
                            "category. Run 'cfs gh sync' in a terminal to select one.[/yellow]"
                        )
                        results["needs_interactive"] += 1
                        continue
                    else:
                        try:
                            category = prompt_category_selection(console, item.title)
                        except EOFError:
                            _warn_prompt_eof(console, item.title)
                            results["needs_interactive"] += 1
                            continue
                        if category is None:
                            results["skipped"] += 1
                            continue

                if not dry_run:
                    _create_cfs_from_github(console, cfs_root, category, item.github_issue)
                    results["created_cfs"] += 1
                else:
                    console.print(
                        f"[dim]Would create CFS doc in {category} "
                        f"from GitHub #{item.github_issue.number}[/dim]"
                    )

            elif item.action == SyncAction.CREATE_GITHUB:
                if dry_run:
                    console.print(
                        f"[dim]Would create GitHub issue "
                        f"from {item.category}/{item.cfs_doc_id}[/dim]"
                    )
                else:
                    _create_github_from_cfs(console, cfs_root, item)
                    results["created_github"] += 1

            elif item.action == SyncAction.CLOSE_GITHUB:
                if dry_run:
                    console.print(f"[dim]Would close GitHub #{item.github_issue.number}[/dim]")
                else:
                    close_issue(item.github_issue.number)
                    console.print(f"[green]Closed GitHub #{item.github_issue.number}[/green]")
                    results["closed_github"] += 1

            elif item.action == SyncAction.COMPLETE_CFS:
                if dry_run:
                    console.print(
                        f"[dim]Would mark {item.category}/{item.cfs_doc_id} as done[/dim]"
                    )
                else:
                    category_path = get_category_path(cfs_root, item.category)
                    complete_document(category_path, item.cfs_doc_id)
                    console.print(
                        f"[green]Marked {item.category}/{item.cfs_doc_id} as done[/green]"
                    )
                    results["completed_cfs"] += 1

            elif item.action == SyncAction.REOPEN_CFS:
                if dry_run:
                    console.print(f"[dim]Would reopen {item.category}/{item.cfs_doc_id}[/dim]")
                else:
                    category_path = get_category_path(cfs_root, item.category)
                    doc_path = item.cfs_doc_path
                    stem = doc_path.stem
                    if stem.startswith(f"{item.cfs_doc_id}-CLOSED-"):
                        unclose_document(category_path, item.cfs_doc_id)
                    else:
                        uncomplete_document(category_path, item.cfs_doc_id)
                    console.print(f"[green]Reopened {item.category}/{item.cfs_doc_id}[/green]")
                    results["reopened_cfs"] += 1

            elif item.action == SyncAction.CONTENT_CONFLICT:
                reason = item.conflict_reason()

                # Deterministic (non-interactive) resolution path for
                # hooks/CI/agents.
                if strategy != ConflictStrategy.INTERACTIVE:
                    resolution, why = _resolve_conflict_noninteractive(item, strategy)
                    if resolution is None:
                        console.print(
                            f"[dim]Deferred conflict ({reason}) for '{item.title}' "
                            f"({item.category}/{item.cfs_doc_id} vs GitHub "
                            f"#{item.github_issue.number}) — {why}.[/dim]"
                        )
                        results["deferred"] += 1
                        continue

                    # Guardrail: if we're about to pull GitHub content into a
                    # local CFS doc (which agents later read and trust), scan
                    # the incoming content for prompt-injection signatures and
                    # refuse to auto-apply anything suspicious — defer it for a
                    # human to review the diff interactively instead.
                    if resolution == "remote":
                        signatures = detect_prompt_injection(_incoming_github_text(item))
                        if signatures:
                            console.print(
                                f"[yellow]Deferred conflict ({reason}) for "
                                f"'{item.title}': refusing to auto-import GitHub "
                                f"#{item.github_issue.number} content — possible prompt "
                                f"injection ({', '.join(signatures)}). Review it with an "
                                "interactive 'cfs gh sync'.[/yellow]"
                            )
                            results["deferred"] += 1
                            continue

                    if dry_run:
                        console.print(
                            f"[dim]Would resolve conflict ({reason}) for '{item.title}' "
                            f"using {resolution} — {why}.[/dim]"
                        )
                        results["skipped"] += 1
                    else:
                        # Back up any local doc we overwrite so an unwanted
                        # auto-resolution is always recoverable.
                        _resolve_conflict(console, cfs_root, item, resolution, backup=True)
                        console.print(f"[dim]Auto-resolved ({reason}) via {why}.[/dim]")
                        results["resolved_conflicts"] += 1
                    continue

                if not console.is_interactive:
                    console.print(
                        f"[yellow]Needs interactive resolution: {reason} conflict for "
                        f"'{item.title}' ({item.category}/{item.cfs_doc_id} vs GitHub "
                        f"#{item.github_issue.number}). Re-run with a strategy "
                        "(e.g. 'cfs gh sync --non-interactive') or resolve it "
                        "interactively in a terminal.[/yellow]"
                    )
                    results["needs_interactive"] += 1
                    continue

                if dry_run:
                    console.print(
                        "[dim]Dry run: conflict detected. No prompt shown; no changes made.[/dim]"
                    )
                    results["skipped"] += 1
                else:
                    try:
                        resolution = prompt_conflict_resolution(console, item)
                    except EOFError:
                        _warn_prompt_eof(console, item.title)
                        results["needs_interactive"] += 1
                        continue

                    if resolution is None:
                        console.print("[yellow]Sync aborted by user.[/yellow]")
                        return results
                    elif resolution == "skip":
                        results["skipped"] += 1
                        continue

                    _resolve_conflict(console, cfs_root, item, resolution)
                    results["resolved_conflicts"] += 1

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            results["errors"] += 1

    return results


def _create_cfs_from_github(
    console: Console,
    cfs_root: Path,
    category: str,
    issue: GitHubIssue,
) -> Path:
    """Create a CFS document from a GitHub issue.

    Args:
        console: Rich console for output.
        cfs_root: Path to the .cursor directory.
        category: Category for the new document.
        issue: GitHub issue to create from.

    Returns:
        Path to the created document.
    """
    category_path = get_category_path(cfs_root, category)

    # Build document content
    repo_root = cfs_root.parent
    repo_path_str = str(repo_root.resolve())
    try:
        home_dir = Path.home()
        if repo_path_str.startswith(str(home_dir)):
            repo_path_str = "~" + repo_path_str[len(str(home_dir)) :]
    except Exception:
        pass

    # Build the document structure
    content_lines = [
        f"# {issue.title}",
        "",
        "## Working directory",
        "",
        f"`{repo_path_str}`",
        "",
        "## Contents",
        "",
    ]

    # Parse GitHub body for contents and acceptance criteria
    if issue.body:
        contents_text, acceptance_text = _split_github_issue_body(issue.body, normalize=False)
        if contents_text:
            content_lines.extend(contents_text.split("\n"))
        content_lines.append("")
        content_lines.append("## Acceptance criteria")
        content_lines.append("")
        if acceptance_text:
            content_lines.extend(acceptance_text.split("\n"))

    content = "\n".join(content_lines)

    # Add frontmatter with GitHub issue link
    content = set_github_issue_number(content, issue.number)

    # Create the document
    doc_path = create_document(category_path, issue.title, content, repo_root)

    # Ensure the category label exists and add it to the issue
    label = get_cfs_label_for_category(category)
    ensure_label_exists(label)
    if label not in issue.labels:
        add_labels(issue.number, [label])

    console.print(
        f"[green]Created {category}/{parse_document_id(doc_path.name)} "
        f"from GitHub #{issue.number}[/green]"
    )

    return doc_path


def _create_github_from_cfs(
    console: Console,
    cfs_root: Path,
    item: SyncItem,
) -> GitHubIssue:
    """Create a GitHub issue from a CFS document.

    Args:
        console: Rich console for output.
        cfs_root: Path to the .cursor directory.
        item: SyncItem with CFS document details.

    Returns:
        Created GitHub issue.
    """
    # Build GitHub issue content
    body = build_github_issue_body(item.cfs_content)

    # Ensure the category label exists
    label = get_cfs_label_for_category(item.category)
    ensure_label_exists(label)

    # Create the issue
    issue = create_issue(item.title, body, labels=[label])

    # Update CFS document with GitHub issue link
    category_path = get_category_path(cfs_root, item.category)
    updated_content = set_github_issue_number(item.cfs_content, issue.number)
    edit_document(category_path, item.cfs_doc_id, updated_content)

    console.print(
        f"[green]Created GitHub #{issue.number} " f"from {item.category}/{item.cfs_doc_id}[/green]"
    )

    return issue


def _backup_local_document(console: Console, item: SyncItem) -> None:
    """Save the current on-disk CFS content to a sibling ``.orig`` file.

    Called before a non-interactive resolution overwrites a local document, so
    an unwanted auto-resolution is always recoverable. Best-effort: a failed
    backup warns but does not abort the resolution.
    """
    if item.cfs_doc_path is None:
        return
    try:
        backup_path = item.cfs_doc_path.with_name(item.cfs_doc_path.name + ".orig")
        backup_path.write_text(item.cfs_content or "", encoding="utf-8")
        console.print(
            f"[dim]Backed up prior content to {backup_path.name} "
            "(overwrite is recoverable).[/dim]"
        )
    except OSError as e:
        console.print(
            f"[yellow]Warning: could not write backup for {item.cfs_doc_path.name}: {e}[/yellow]"
        )


def _resolve_conflict(
    console: Console,
    cfs_root: Path,
    item: SyncItem,
    resolution: str,
    backup: bool = False,
) -> None:
    """Resolve a content conflict.

    Args:
        console: Rich console for output.
        cfs_root: Path to the .cursor directory.
        item: SyncItem with conflict details.
        resolution: "local" to use CFS, "remote" to use GitHub.
        backup: If True, save the local document to a ``.orig`` sibling before
            overwriting it (only relevant when ``resolution == "remote"``).
    """
    if resolution == "local":
        # Update GitHub with CFS content
        sections = extract_document_sections(item.cfs_content)
        body = build_github_issue_body(item.cfs_content)
        title = sections["title"].strip()
        if not title:
            title = None
        update_issue(item.github_issue.number, title=title, body=body)
        console.print(f"[green]Updated GitHub #{item.github_issue.number} with CFS content[/green]")
    elif resolution == "remote":
        # Update CFS with GitHub content
        # We need to rebuild the CFS document structure
        category_path = get_category_path(cfs_root, item.category)

        # Get the existing frontmatter
        from cfs.documents import parse_frontmatter

        existing_fm, _ = parse_frontmatter(item.cfs_content)

        # Build new content
        repo_root = cfs_root.parent
        repo_path_str = str(repo_root.resolve())
        try:
            home_dir = Path.home()
            if repo_path_str.startswith(str(home_dir)):
                repo_path_str = "~" + repo_path_str[len(str(home_dir)) :]
        except Exception:
            pass

        content_lines = [
            f"# {item.github_issue.title}",
            "",
            "## Working directory",
            "",
            f"`{repo_path_str}`",
            "",
            "## Contents",
            "",
        ]

        # Parse GitHub body
        if item.github_content:
            contents_text, acceptance_text = _split_github_issue_body(
                item.github_content,
                normalize=False,
            )
            if contents_text:
                content_lines.extend(contents_text.split("\n"))
            content_lines.append("")
            content_lines.append("## Acceptance criteria")
            content_lines.append("")
            if acceptance_text:
                content_lines.extend(acceptance_text.split("\n"))

        content = "\n".join(content_lines)

        # Restore frontmatter
        from cfs.documents import add_frontmatter

        if existing_fm:
            content = add_frontmatter(content, existing_fm)
        else:
            content = set_github_issue_number(content, item.github_issue.number)

        if backup:
            _backup_local_document(console, item)

        edit_document(category_path, item.cfs_doc_id, content)
        console.print(
            f"[green]Updated {item.category}/{item.cfs_doc_id} with GitHub content[/green]"
        )


def display_sync_status(console: Console, plan: SyncPlan) -> None:
    """Display sync status summary.

    Args:
        console: Rich console for output.
        plan: SyncPlan to display status for.
    """
    # Warn about categories with duplicate IDs so users can dedup first.
    if plan.duplicate_categories:
        cats = ", ".join(sorted(plan.duplicate_categories))
        console.print(
            f"[red]Warning: Duplicate document IDs detected in: {cats}[/red]\n"
            "[yellow]Run 'cfs gh dedup' to remove duplicates before syncing.[/yellow]"
        )

    table = Table(title="Sync Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Linked documents", str(plan.linked_count))
    table.add_row("Unlinked CFS documents", str(plan.unlinked_cfs_count))
    table.add_row("Unlinked GitHub issues", str(plan.unlinked_github_count))
    if plan.duplicate_categories:
        table.add_row(
            "Categories with duplicates",
            f"[red]{len(plan.duplicate_categories)}[/red]",
        )

    # Count actions by type
    action_counts = {}
    for item in plan.items:
        action_name = item.action.value
        action_counts[action_name] = action_counts.get(action_name, 0) + 1

    if action_counts:
        table.add_section()
        for action, count in sorted(action_counts.items()):
            if action != "no_action":
                table.add_row(f"Action: {action}", str(count))

    console.print(table)


def display_sync_results(console: Console, results: Dict[str, int]) -> None:
    """Display sync execution results.

    Args:
        console: Rich console for output.
        results: Dictionary with action counts.
    """
    table = Table(title="Sync Results")
    table.add_column("Action", style="cyan")
    table.add_column("Count", style="green")

    for action, count in results.items():
        if count > 0:
            if action == "errors":
                style = "red"
            elif action == "needs_interactive":
                style = "yellow"
            elif action == "deferred":
                style = "dim"
            else:
                style = "green"
            table.add_row(action.replace("_", " ").title(), f"[{style}]{count}[/{style}]")

    console.print(table)

    # Closing summary so unresolved items are impossible to miss, especially
    # when the output is captured by a hook or an agent transcript.
    needs_interactive = results.get("needs_interactive", 0)
    deferred = results.get("deferred", 0)
    errors = results.get("errors", 0)
    if needs_interactive > 0:
        console.print(
            f"[yellow]⚠ {needs_interactive} item(s) need interactive resolution — "
            "run 'cfs gh sync' in a terminal, or pass a strategy "
            "(e.g. --non-interactive) to resolve deterministically.[/yellow]"
        )
    if deferred > 0:
        # Advisory only: deferred items were intentionally left for later by a
        # non-interactive strategy. This is NOT a call to action and does not
        # imply anything is wrong — the commit/sync completed cleanly.
        console.print(
            f"[dim]{deferred} item(s) deferred (no deterministic resolution) — "
            "run 'cfs gh sync' when you want to address them.[/dim]"
        )
    if errors > 0:
        console.print(f"[red]❌ {errors} sync error(s) occurred — see messages above.[/red]")
