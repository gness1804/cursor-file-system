"""Text editor integration for CFS."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Union


# Known editors with display names and commands
KNOWN_EDITORS = [
    ("VS Code", "code", ["--wait"]),
    ("Cursor", "cursor", ["--wait"]),
    ("Vim", "vim", []),
    ("Neovim", "nvim", []),
    ("Nano", "nano", []),
    ("Sublime Text", "subl", ["--wait"]),
    ("Emacs", "emacs", []),
    ("Zed", "zed", []),
]


def get_available_editors() -> List[Tuple[str, str, List[str]]]:
    """Get list of available editors on the system.

    Returns:
        List of tuples: (display_name, command, extra_args)
    """
    available = []
    for display_name, cmd, extra_args in KNOWN_EDITORS:
        if is_editor_available(cmd):
            available.append((display_name, cmd, extra_args))
    return available


def is_editor_available(editor_cmd: str) -> bool:
    """Check if an editor command is available on the system."""
    try:
        result = subprocess.run(
            ["which", editor_cmd],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def detect_editor() -> str:
    """Detect available text editor.

    Priority:
    1. $EDITOR environment variable
    2. Common editors: vim, nano, code (VS Code), subl (Sublime)
    3. Fallback to nano

    Returns:
        Editor command name.
    """
    # Check $EDITOR first
    editor = os.environ.get("EDITOR")
    if editor:
        return editor

    # Check common editors
    common_editors = ["vim", "nano", "code", "subl"]
    for editor_name in common_editors:
        try:
            result = subprocess.run(
                ["which", editor_name],
                capture_output=True,
                check=True,
            )
            if result.returncode == 0:
                return editor_name
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    # Fallback to nano
    return "nano"


def edit_content(
    initial_content: str = "",
    editor: Optional[str] = None,
    editor_args: Optional[List[str]] = None,
) -> str:
    """Edit content using a text editor.

    Args:
        initial_content: Initial content to edit.
        editor: Editor command to use. If None, will auto-detect.
        editor_args: Additional arguments to pass to the editor.

    Returns:
        Edited content.

    Raises:
        RuntimeError: If editor cannot be launched.
    """
    if editor is None:
        editor = detect_editor()

    if editor_args is None:
        editor_args = []

    # Create temporary file with initial content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(initial_content)

    try:
        # Launch editor with any extra args
        cmd = [editor] + editor_args + [tmp_path]
        subprocess.run(cmd, check=False)

        # Read edited content
        with open(tmp_path, "r") as f:
            content = f.read()

        return content
    finally:
        # Clean up temporary file
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


def open_file_in_editor(
    file_path: Union[str, Path],
    editor: Optional[str] = None,
    editor_args: Optional[List[str]] = None,
) -> None:
    """Open a file directly in the chosen editor."""
    if editor is None:
        editor = detect_editor()

    if editor_args is None:
        editor_args = []

    cmd = [editor] + editor_args + [str(file_path)]
    subprocess.run(cmd, check=False)
