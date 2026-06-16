"""
Tests for URL / music-request detection (bot/downloader.py).

Feature: project-hardening
Covers Requirements 13.2.

bot.downloader imports yt-dlp at module load, so these tests skip gracefully
when yt-dlp is not installed.
"""

import pytest

pytest.importorskip("yt_dlp")

from bot.downloader import is_video_url, is_music_request, MUSIC_KEYWORDS

SUPPORTED_VIDEO_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/abc123",
    "https://www.instagram.com/reel/xyz/",
    "https://www.tiktok.com/@user/video/123",
    "https://fb.watch/abc/",
]

NON_VIDEO_TEXTS = [
    "salom dunyo",
    "https://example.com/page",
    "qanday qilib kod yozaman",
]


@pytest.mark.parametrize("url", SUPPORTED_VIDEO_URLS)
def test_video_url_detected(url):
    assert is_video_url(url) is True


@pytest.mark.parametrize("text", NON_VIDEO_TEXTS)
def test_non_video_text_not_detected(text):
    assert is_video_url(text) is False


@pytest.mark.parametrize("keyword", MUSIC_KEYWORDS)
def test_music_keyword_detected(keyword):
    assert is_music_request(f"menga {keyword} kerak") is True


def test_non_music_text_not_detected():
    assert is_music_request("bugun havo issiq") is False
    assert is_video_url("") is False
    assert is_music_request("") is False


# --- Property 14: Detection over supported URLs and music keywords ---------
# Validates: Requirements 13.2


def test_property_detection():
    """
    Property 14: any URL from a supported platform is detected as a video URL,
    and any text containing a music keyword is detected as a music request.
    """
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=100)
    @given(url=st.sampled_from(SUPPORTED_VIDEO_URLS))
    def run_urls(url):
        assert is_video_url(url) is True

    run_urls()

    @settings(max_examples=100)
    @given(
        keyword=st.sampled_from(MUSIC_KEYWORDS),
        prefix=st.text(alphabet="abcdefg ", max_size=10),
        suffix=st.text(alphabet="abcdefg ", max_size=10),
    )
    def run_music(keyword, prefix, suffix):
        assert is_music_request(f"{prefix}{keyword}{suffix}") is True

    run_music()
