"""Text editor integration for CFS."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


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


def edit_content(initial_content: str = "", editor: Optional[str] = None) -> str:
    """Edit content using a text editor.
    
    Args:
        initial_content: Initial content to edit.
        editor: Editor command to use. If None, will auto-detect.
        
    Returns:
        Edited content.
        
    Raises:
        RuntimeError: If editor cannot be launched.
    """
    if editor is None:
        editor = detect_editor()
    
    # Create temporary file with initial content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(initial_content)
    
    try:
        # Launch editor
        result = subprocess.run([editor, tmp_path], check=False)
        
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

