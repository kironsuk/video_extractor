"""Tests for dependency detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from video_extractor.deps import (
    check_handbrake,
    check_libdvdcss,
    get_handbrake_path,
)


class TestCheckHandbrake:
    @patch("video_extractor.deps.shutil.which", return_value="/usr/local/bin/HandBrakeCLI")
    def test_found_on_path(self, mock_which):
        status = check_handbrake()
        assert status.found is True
        assert status.path == "/usr/local/bin/HandBrakeCLI"

    @patch("video_extractor.deps.sys.platform", "darwin")
    @patch("video_extractor.deps.Path.is_file", return_value=False)
    @patch("video_extractor.deps.shutil.which", return_value=None)
    def test_macos_not_found(self, mock_which, mock_is_file):
        status = check_handbrake()
        assert status.found is False
        assert "brew install handbrake" in status.install_hint

    @patch("video_extractor.deps.sys.platform", "win32")
    @patch("video_extractor.deps.Path.is_file", return_value=False)
    @patch("video_extractor.deps.shutil.which", return_value=None)
    def test_windows_not_found(self, mock_which, mock_is_file):
        status = check_handbrake()
        assert status.found is False
        assert "handbrake.fr" in status.install_hint
        assert "choco" in status.install_hint

    @patch("video_extractor.deps.sys.platform", "win32")
    @patch("video_extractor.deps.Path.is_file", return_value=True)
    @patch("video_extractor.deps.shutil.which", return_value=None)
    def test_windows_found_program_files(self, mock_which, mock_is_file):
        status = check_handbrake()
        assert status.found is True
        assert "Program Files" in status.path


class TestCheckLibdvdcss:
    @patch("video_extractor.deps.sys.platform", "darwin")
    @patch("video_extractor.deps.Path.exists", return_value=True)
    @patch("video_extractor.deps.Path.glob")
    def test_macos_found_in_homebrew(self, mock_glob, mock_exists):
        mock_glob.return_value = [Path("/opt/homebrew/lib/libdvdcss.2.dylib")]
        status = check_libdvdcss()
        assert status.found is True

    @patch("video_extractor.deps.sys.platform", "darwin")
    @patch("video_extractor.deps.Path.exists", return_value=False)
    @patch("video_extractor.deps.subprocess.run")
    def test_macos_not_found(self, mock_run, mock_exists):
        mock_run.side_effect = FileNotFoundError  # brew not installed
        status = check_libdvdcss()
        assert status.found is False
        assert "brew install libdvdcss" in status.install_hint

    @patch("video_extractor.deps.sys.platform", "win32")
    @patch("video_extractor.deps.Path.is_file", return_value=True)
    @patch("video_extractor.deps.shutil.which", return_value=r"C:\Program Files\HandBrake\HandBrakeCLI.exe")
    def test_windows_found_alongside_handbrake(self, mock_which, mock_is_file):
        status = check_libdvdcss()
        assert status.found is True

    @patch("video_extractor.deps.os.environ", {"PATH": ""})
    @patch("video_extractor.deps.sys.platform", "win32")
    @patch("video_extractor.deps.Path.is_file", return_value=False)
    @patch("video_extractor.deps.shutil.which", return_value=None)
    def test_windows_not_found(self, mock_which, mock_is_file):
        status = check_libdvdcss()
        assert status.found is False
        assert "videolan.org" in status.install_hint


class TestGetHandbrakePath:
    @patch("video_extractor.deps.check_handbrake")
    def test_found(self, mock_check):
        from video_extractor.deps import DepStatus

        mock_check.return_value = DepStatus(
            "HandBrakeCLI", found=True, path="/usr/bin/HandBrakeCLI"
        )
        assert get_handbrake_path() == "/usr/bin/HandBrakeCLI"

    @patch("video_extractor.deps.check_handbrake")
    def test_not_found_raises(self, mock_check):
        from video_extractor.deps import DepStatus

        mock_check.return_value = DepStatus(
            "HandBrakeCLI", found=False, install_hint="brew install handbrake"
        )
        with pytest.raises(FileNotFoundError, match="brew install handbrake"):
            get_handbrake_path()
