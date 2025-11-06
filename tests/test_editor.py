"""Unit tests for editor integration."""

import os
import subprocess
from unittest.mock import MagicMock, patch

from cfs.editor import detect_editor, edit_content


class TestDetectEditor:
    """Tests for detect_editor function."""

    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_detect_editor_from_env(self):
        """Test that EDITOR environment variable is respected."""
        editor = detect_editor()
        assert editor == "vim"

    @patch.dict(os.environ, {"VISUAL": "nano"}, clear=True)
    def test_detect_editor_from_visual(self):
        """Test that VISUAL environment variable is used if EDITOR not set."""
        editor = detect_editor()
        assert editor == "nano"

    @patch.dict(os.environ, {}, clear=True)
    @patch("shutil.which")
    def test_detect_editor_fallback(self, mock_which):
        """Test fallback editor detection."""
        # Mock which to return vim
        mock_which.side_effect = lambda x: x if x in ["vim", "nano", "code", "subl"] else None

        editor = detect_editor()
        # Should return first available editor
        assert editor in ["vim", "nano", "code", "subl"]

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    def test_detect_editor_fallback_to_nano(self, mock_run):
        """Test that nano is used as fallback when no editor is found."""
        # Mock which to fail for all editors
        mock_run.side_effect = subprocess.CalledProcessError(1, "which")

        editor = detect_editor()
        # Should fallback to nano
        assert editor == "nano"


class TestEditContent:
    """Tests for edit_content function."""

    @patch("cfs.editor.detect_editor")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    @patch("builtins.open")
    @patch("pathlib.Path.unlink")
    def test_edit_content_success(
        self, mock_unlink, mock_open, mock_tempfile, mock_run, mock_detect
    ):
        """Test successful content editing."""
        # Setup mocks
        mock_detect.return_value = "vim"
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.md"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        mock_run.return_value.returncode = 0

        # Mock file reading
        mock_file_handle = MagicMock()
        mock_file_handle.read.return_value = "Edited content"
        mock_open.return_value.__enter__.return_value = mock_file_handle

        result = edit_content("Initial content")

        assert result == "Edited content"
        mock_run.assert_called_once()
        assert mock_file.write.called

    @patch("cfs.editor.detect_editor")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    def test_edit_content_with_custom_editor(self, mock_tempfile, mock_run, mock_detect):
        """Test editing with custom editor specified."""
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.md"
        mock_tempfile.return_value.__enter__.return_value = mock_file
        mock_run.return_value.returncode = 0

        # Mock file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_file_handle = MagicMock()
            mock_file_handle.read.return_value = "Edited content"
            mock_open.return_value.__enter__.return_value = mock_file_handle

            result = edit_content("Initial content", editor="nano")

            assert result == "Edited content"
            # Should use custom editor, not detect
            mock_detect.assert_not_called()
            mock_run.assert_called_once_with(["nano", "/tmp/test.md"], check=False)
