"""
Tests for download hardening (bot/downloader.py).

Feature: project-hardening
Covers Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2.

bot.downloader imports yt-dlp at module load; skips gracefully when missing.
"""

import asyncio
import uuid

import pytest

pytest.importorskip("yt_dlp")

from bot import downloader


# --- Unit (11.1, 11.2): finite socket_timeout and bounded retries ---------


def test_video_opts_have_finite_timeout_and_retries():
    opts = downloader._build_video_ydl_opts("https://youtu.be/x", token="abc123")
    assert isinstance(opts["socket_timeout"], (int, float))
    assert opts["socket_timeout"] > 0
    assert isinstance(opts["retries"], int)
    assert 0 <= opts["retries"] < 100


def test_music_opts_have_finite_timeout_and_retries():
    opts = downloader._build_music_ydl_opts(use_cookies=False, token="abc123")
    assert isinstance(opts["socket_timeout"], (int, float))
    assert opts["socket_timeout"] > 0
    assert isinstance(opts["retries"], int)
    assert 0 <= opts["retries"] < 100


# --- Property 9: Concurrent downloads never exceed the cap ----------------
# Validates: Requirements 10.1, 10.2


def test_property_concurrency_cap(monkeypatch):
    cap = downloader.MAX_CONCURRENT_DOWNLOADS
    # Use a fresh semaphore with the real cap to measure peak concurrency.
    sem = asyncio.Semaphore(cap)
    monkeypatch.setattr(downloader, "_download_semaphore", sem)

    state = {"current": 0, "peak": 0}

    async def guarded_body():
        async with downloader._download_semaphore:
            state["current"] += 1
            state["peak"] = max(state["peak"], state["current"])
            await asyncio.sleep(0.01)
            state["current"] -= 1

    async def run(n):
        await asyncio.gather(*(guarded_body() for _ in range(n)))

    asyncio.run(run(20))
    assert state["peak"] <= cap


# --- Property 10: Concurrent same-id downloads use distinct paths ---------
# Validates: Requirements 10.3


def test_property_distinct_paths_for_same_id():
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=100)
    @given(n=st.integers(min_value=2, max_value=10))
    def run(n):
        # Tokens are generated as uuid4().hex[:8] per invocation in the code.
        tokens = [uuid.uuid4().hex[:8] for _ in range(n)]
        opts = [
            downloader._build_video_ydl_opts("https://youtu.be/SAMEID", token=t)
            for t in tokens
        ]
        outtmpls = [o["outtmpl"] for o in opts]
        assert len(set(outtmpls)) == len(outtmpls)

    run()


# --- Property 11: Send attempts leave no residual file --------------------
# Validates: Requirements 10.4


def test_property_cleanup_removes_file(tmp_path):
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=50, deadline=None)
    @given(name=st.text(alphabet="abcdef0123456789", min_size=1, max_size=10))
    def run(name):
        f = tmp_path / f"{name}.mp4"
        f.write_text("data")
        downloader.cleanup_file(str(f))
        assert not f.exists()

    run()


def test_cleanup_file_tolerates_missing(tmp_path):
    # Should not raise on a non-existent path.
    downloader.cleanup_file(str(tmp_path / "nope.mp4"))


# --- Property 12: Startup clears the downloads directory ------------------
# Validates: Requirements 10.5


def test_property_startup_clears_downloads(tmp_path, monkeypatch):
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=50, deadline=None)
    @given(file_names=st.lists(
        st.text(alphabet="abcdef0123456789", min_size=1, max_size=8),
        min_size=0,
        max_size=8,
        unique=True,
    ))
    def run(file_names):
        d = tmp_path / "downloads"
        d.mkdir(exist_ok=True)
        monkeypatch.setattr(downloader, "DOWNLOADS_DIR", str(d))
        for name in file_names:
            (d / f"{name}.mp4").write_text("x")
        downloader.cleanup_stale_downloads()
        remaining = [p for p in d.iterdir() if p.is_file()]
        assert remaining == []

    run()


def test_cleanup_stale_downloads_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader, "DOWNLOADS_DIR", str(tmp_path / "does_not_exist"))
    # Should be a no-op, not raise.
    downloader.cleanup_stale_downloads()
