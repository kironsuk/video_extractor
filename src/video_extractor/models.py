"""Data models for DVD video extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class OutputFormat(Enum):
    MKV = "mkv"
    MP4 = "mp4"

    @property
    def handbrake_format(self) -> str:
        return {"mkv": "av_mkv", "mp4": "av_mp4"}[self.value]


class VideoCodec(Enum):
    H265 = "h265"
    H264 = "h264"

    @property
    def handbrake_encoder(self) -> str:
        return {"h265": "x265", "h264": "x264"}[self.value]


@dataclass
class AudioTrack:
    index: int
    codec: str
    language: str
    channels: int
    description: str


@dataclass
class SubtitleTrack:
    index: int
    language: str
    format: str
    description: str


@dataclass
class Chapter:
    number: int
    duration_ms: int


@dataclass
class Title:
    number: int
    duration_seconds: float
    chapters: list[Chapter] = field(default_factory=list)
    audio_tracks: list[AudioTrack] = field(default_factory=list)
    subtitle_tracks: list[SubtitleTrack] = field(default_factory=list)
    is_main_feature: bool = False
    resolution: str = ""

    @property
    def duration_display(self) -> str:
        h = int(self.duration_seconds) // 3600
        m = (int(self.duration_seconds) % 3600) // 60
        s = int(self.duration_seconds) % 60
        return f"{h}:{m:02d}:{s:02d}"


@dataclass
class DiscInfo:
    device_path: str
    mount_point: str
    volume_label: str


@dataclass
class DVDInfo:
    disc: DiscInfo
    titles: list[Title] = field(default_factory=list)


@dataclass
class RipJob:
    title: Title
    source_device: str
    output_path: Path
    output_format: OutputFormat = OutputFormat.MKV
    video_codec: VideoCodec = VideoCodec.H265
    quality: int = 20
    audio_tracks: list[int] | None = None
    subtitle_tracks: list[int] | None = None
