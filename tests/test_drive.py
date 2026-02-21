"""Tests for DVD drive detection."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from video_extractor.drive import DriveError, _detect_disc_windows, detect_disc


class TestDetectDiscWindows:
    """Tests for Windows drive detection via wmic."""

    WMIC_HEADER = "Node,DeviceID,VolumeName\n"

    def _mock_wmic(self, stdout: str, returncode: int = 0):
        """Create a mock subprocess result for wmic."""
        mock = MagicMock()
        mock.stdout = stdout
        mock.returncode = returncode
        return mock

    @patch("video_extractor.drive.Path.is_dir")
    @patch("video_extractor.drive.subprocess.run")
    def test_happy_path(self, mock_run, mock_is_dir):
        mock_run.return_value = self._mock_wmic(
            self.WMIC_HEADER + "PC1,D:,MY_MOVIE\n"
        )
        mock_is_dir.return_value = True

        info = _detect_disc_windows()
        assert info.device_path == "D:"
        assert info.volume_label == "MY_MOVIE"
        assert info.mount_point == "D:\\"

    @patch("video_extractor.drive.subprocess.run")
    def test_no_dvd_drive(self, mock_run):
        mock_run.return_value = self._mock_wmic(self.WMIC_HEADER)

        with pytest.raises(DriveError, match="No DVD drive found"):
            _detect_disc_windows()

    @patch("video_extractor.drive.Path.is_dir")
    @patch("video_extractor.drive.subprocess.run")
    def test_no_video_ts(self, mock_run, mock_is_dir):
        mock_run.return_value = self._mock_wmic(
            self.WMIC_HEADER + "PC1,D:,SOME_DISC\n"
        )
        mock_is_dir.return_value = False

        with pytest.raises(DriveError, match="not a DVD-Video"):
            _detect_disc_windows()

    @patch("video_extractor.drive.subprocess.run")
    def test_wmic_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError

        with pytest.raises(DriveError, match="wmic not found"):
            _detect_disc_windows()

    @patch("video_extractor.drive.Path.is_dir")
    @patch("video_extractor.drive.subprocess.run")
    def test_empty_volume_name_defaults(self, mock_run, mock_is_dir):
        mock_run.return_value = self._mock_wmic(
            self.WMIC_HEADER + "PC1,D:,\n"
        )
        mock_is_dir.return_value = True

        info = _detect_disc_windows()
        assert info.volume_label == "DVD"


class TestDetectDiscMacos:
    """Tests for macOS drive detection error cases."""

    @patch("video_extractor.drive.subprocess.run")
    def test_diskutil_not_found(self, mock_run):
        """_find_optical_device raises DriveError when diskutil is missing."""
        mock_run.side_effect = FileNotFoundError

        from video_extractor.drive import _detect_disc_macos

        with pytest.raises(DriveError, match="diskutil not found"):
            _detect_disc_macos()


class TestDetectDiscDispatcher:
    """Tests for the platform dispatcher."""

    @patch("video_extractor.drive.sys.platform", "linux")
    def test_unsupported_platform(self):
        with pytest.raises(DriveError, match="Unsupported platform"):
            detect_disc()

    @patch("video_extractor.drive.sys.platform", "win32")
    @patch("video_extractor.drive._detect_disc_windows")
    def test_dispatches_to_windows(self, mock_win):
        from video_extractor.models import DiscInfo

        mock_win.return_value = DiscInfo("D:", "D:\\", "DVD")
        result = detect_disc()
        mock_win.assert_called_once()
        assert result.device_path == "D:"

    @patch("video_extractor.drive.sys.platform", "darwin")
    @patch("video_extractor.drive._detect_disc_macos")
    def test_dispatches_to_macos(self, mock_mac):
        from video_extractor.models import DiscInfo

        mock_mac.return_value = DiscInfo("/dev/disk4", "/Volumes/DVD", "DVD")
        result = detect_disc()
        mock_mac.assert_called_once()
        assert result.device_path == "/dev/disk4"
