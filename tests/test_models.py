"""Tests for data models."""

from video_extractor.models import OutputFormat, Title, VideoCodec


class TestTitleDurationDisplay:
    def test_short_duration(self):
        t = Title(number=1, duration_seconds=65)
        assert t.duration_display == "0:01:05"

    def test_hours(self):
        t = Title(number=1, duration_seconds=7261)
        assert t.duration_display == "2:01:01"

    def test_zero(self):
        t = Title(number=1, duration_seconds=0)
        assert t.duration_display == "0:00:00"

    def test_exact_hour(self):
        t = Title(number=1, duration_seconds=3600)
        assert t.duration_display == "1:00:00"


class TestOutputFormat:
    def test_mkv_handbrake_format(self):
        assert OutputFormat.MKV.handbrake_format == "av_mkv"

    def test_mp4_handbrake_format(self):
        assert OutputFormat.MP4.handbrake_format == "av_mp4"


class TestVideoCodec:
    def test_h265_encoder(self):
        assert VideoCodec.H265.handbrake_encoder == "x265"

    def test_h264_encoder(self):
        assert VideoCodec.H264.handbrake_encoder == "x264"
