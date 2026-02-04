import os
import sys
import unittest

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.validators import InputValidator

class TestURLPlatforms(unittest.TestCase):
    """
    Pruebas para verificar que InputValidator reconoce correctamente
    URLs de diferentes plataformas.
    """

    def test_youtube_urls(self):
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/abc123def45",
            "youtube.com/watch?v=dQw4w9WgXcQ",
        ]
        for url in urls:
            with self.subTest(url=url):
                is_valid, platform = InputValidator.validate_video_url(url)
                self.assertTrue(is_valid)
                self.assertEqual(platform, "YouTube")

    def test_instagram_urls(self):
        urls = [
            "https://www.instagram.com/reel/C3S4v_4R-tY/",
            "https://instagram.com/p/C3S4v_4R-tY/",
            "https://www.instagram.com/tv/C3S4v_4R-tY/",
            "https://www.instagram.com/reels/C3S4v_4R-tY/",
        ]
        for url in urls:
            with self.subTest(url=url):
                is_valid, platform = InputValidator.validate_video_url(url)
                self.assertTrue(is_valid)
                self.assertEqual(platform, "Instagram")

    def test_facebook_urls(self):
        urls = [
            "https://www.facebook.com/watch/?v=123456789",
            "https://facebook.com/user/videos/123456789",
            "https://fb.watch/abcd1234ef/",
            "https://www.facebook.com/reel/123456789",
            "https://www.facebook.com/share/v/abcd123/",
        ]
        for url in urls:
            with self.subTest(url=url):
                is_valid, platform = InputValidator.validate_video_url(url)
                self.assertTrue(is_valid)
                self.assertEqual(platform, "Facebook")

    def test_tiktok_urls(self):
        urls = [
            "https://www.tiktok.com/@user/video/123456789",
            "https://vm.tiktok.com/ZM6uR8v9L/",
            "https://tiktok.com/t/ZM6uR8v9L/",
        ]
        for url in urls:
            with self.subTest(url=url):
                is_valid, platform = InputValidator.validate_video_url(url)
                self.assertTrue(is_valid)
                self.assertEqual(platform, "TikTok")

    def test_twitter_urls(self):
        urls = [
            "https://twitter.com/user/status/123456789",
            "https://x.com/user/status/123456789",
            "https://t.co/abcd1234",
        ]
        for url in urls:
            with self.subTest(url=url):
                is_valid, platform = InputValidator.validate_video_url(url)
                self.assertTrue(is_valid)
                self.assertEqual(platform, "Twitter/X")

    def test_invalid_urls(self):
        urls = [
            "https://google.com",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "not-a-url",
        ]
        for url in urls:
            with self.subTest(url=url):
                is_valid, _ = InputValidator.validate_video_url(url)
                self.assertFalse(is_valid)

if __name__ == "__main__":
    unittest.main()
