import unittest
import os
import tempfile
from src.core.subtitle_exporter import SubtitleExporter, SubtitleSegment

class TestSubtitleExporter(unittest.TestCase):
    def test_format_timestamp_srt(self):
        self.assertEqual(SubtitleExporter._format_timestamp_srt(0), "00:00:00,000")
        self.assertEqual(SubtitleExporter._format_timestamp_srt(3661.123), "01:01:01,123")

    def test_format_timestamp_vtt(self):
        self.assertEqual(SubtitleExporter._format_timestamp_vtt(0), "00:00:00.000")
        self.assertEqual(SubtitleExporter._format_timestamp_vtt(3661.123), "01:01:01.123")

    def test_segments_from_fragments(self):
        fragments = [
            {"text": "Hola mundo", "start_time": 0.0, "end_time": 2.5},
            {"text": "Prueba de subtítulos", "start_time": 2.5, "end_time": 5.0}
        ]
        segments = SubtitleExporter.segments_from_fragments(fragments)
        
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "Hola mundo")
        self.assertEqual(segments[0].index, 1)
        self.assertEqual(segments[1].index, 2)

    def test_save_srt(self):
        segments = [SubtitleSegment(1, 0.0, 2.0, "Prueba")]
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            SubtitleExporter.save_srt(segments, tmp_path)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("00:00:00,000 --> 00:00:02,000", content)
                self.assertIn("Prueba", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
