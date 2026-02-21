"""Shared test fixtures."""

from __future__ import annotations

import pytest

from video_extractor.models import DiscInfo


@pytest.fixture
def disc_info() -> DiscInfo:
    """A macOS-style DiscInfo."""
    return DiscInfo(
        device_path="/dev/disk4",
        mount_point="/Volumes/MY_DVD",
        volume_label="MY_DVD",
    )


@pytest.fixture
def windows_disc_info() -> DiscInfo:
    """A Windows-style DiscInfo."""
    return DiscInfo(
        device_path="D:",
        mount_point="D:\\",
        volume_label="MY_DVD",
    )
