"""Tests for DVD scanner parsing logic."""

from video_extractor.scanner import _channel_count, _extract_json, _parse_titles


class TestExtractJson:
    def test_valid_output(self):
        output = (
            'Some log line\n'
            'JSON Title Set: {"TitleList": []}\n'
        )
        result = _extract_json(output)
        assert result == {"TitleList": []}

    def test_no_marker(self):
        output = "No JSON here, just log lines\n"
        assert _extract_json(output) is None

    def test_invalid_json_after_marker(self):
        output = "JSON Title Set: {not valid json"
        assert _extract_json(output) is None

    def test_complex_payload(self):
        output = (
            'Scanning...\n'
            'JSON Title Set: {"TitleList": [{"Index": 1}]}\n'
        )
        result = _extract_json(output)
        assert result["TitleList"][0]["Index"] == 1


class TestParseTitles:
    def test_typical_title(self):
        data = {
            "TitleList": [
                {
                    "Index": 1,
                    "Duration": {"Hours": 1, "Minutes": 30, "Seconds": 45},
                    "ChapterList": [
                        {"Duration": {"Hours": 0, "Minutes": 5, "Seconds": 0}},
                        {"Duration": {"Hours": 0, "Minutes": 10, "Seconds": 30}},
                    ],
                    "AudioList": [
                        {
                            "CodecName": "ac3",
                            "LanguageCode": "eng",
                            "ChannelLayout": 0x3F,  # 6 bits = 5.1
                            "Description": "English (AC3) (5.1 ch)",
                        }
                    ],
                    "SubtitleList": [
                        {
                            "LanguageCode": "eng",
                            "SourceName": "VobSub",
                            "Description": "English",
                        }
                    ],
                    "Geometry": {"Width": 720, "Height": 480},
                    "MainFeature": True,
                }
            ]
        }

        titles = _parse_titles(data)
        assert len(titles) == 1

        t = titles[0]
        assert t.number == 1
        assert t.duration_seconds == 5445  # 1*3600 + 30*60 + 45
        assert t.is_main_feature is True
        assert t.resolution == "720x480"
        assert len(t.chapters) == 2
        assert t.chapters[0].number == 1
        assert t.chapters[0].duration_ms == 300000  # 5 min
        assert len(t.audio_tracks) == 1
        assert t.audio_tracks[0].codec == "ac3"
        assert t.audio_tracks[0].language == "eng"
        assert t.audio_tracks[0].channels == 6
        assert len(t.subtitle_tracks) == 1
        assert t.subtitle_tracks[0].language == "eng"
        assert t.subtitle_tracks[0].format == "VobSub"

    def test_empty_title_list(self):
        assert _parse_titles({"TitleList": []}) == []

    def test_missing_title_list(self):
        assert _parse_titles({}) == []

    def test_minimal_title(self):
        data = {"TitleList": [{"Index": 2, "Duration": {}}]}
        titles = _parse_titles(data)
        assert len(titles) == 1
        assert titles[0].number == 2
        assert titles[0].duration_seconds == 0


class TestChannelCount:
    def test_stereo_bitmask(self):
        # 0x3 = 0b11 → 2 channels (stereo)
        assert _channel_count(0x3) == 2

    def test_51_surround(self):
        # 0x3F = 0b111111 → 6 channels (5.1)
        assert _channel_count(0x3F) == 6

    def test_71_surround(self):
        # 0xFF = 0b11111111 → 8 channels (7.1)
        assert _channel_count(0xFF) == 8

    def test_zero_defaults_stereo(self):
        assert _channel_count(0) == 2

    def test_negative_defaults_stereo(self):
        assert _channel_count(-1) == 2
