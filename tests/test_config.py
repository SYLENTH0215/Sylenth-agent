"""
Tests for the configuration module (config.py).

Feature: project-hardening
Covers Requirements 1.1-1.8.

These tests depend only on the standard library and first-party code, so they
run without any third-party packages installed.
"""

import importlib
import sys

import pytest

REQUIRED_VARS = ["BOT_TOKEN", "GEMINI_API_KEY", "ADMIN_ID"]


def _reload_config():
    """Re-import config.py fresh so it re-reads the current environment."""
    sys.modules.pop("config", None)
    return importlib.import_module("config")


def _set_valid_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "valid-token")
    monkeypatch.setenv("GEMINI_API_KEY", "valid-key")
    monkeypatch.setenv("ADMIN_ID", "42")


# --- Example tests ---------------------------------------------------------


def test_reads_all_required_vars(monkeypatch):
    """1.1, 1.2, 1.3: values are read from the environment."""
    monkeypatch.setenv("BOT_TOKEN", "tok123")
    monkeypatch.setenv("GEMINI_API_KEY", "key456")
    monkeypatch.setenv("ADMIN_ID", "789")
    config = _reload_config()
    assert config.BOT_TOKEN == "tok123"
    assert config.GEMINI_API_KEY == "key456"
    assert config.ADMIN_ID == 789


def test_admin_id_is_int(monkeypatch):
    """1.8: ADMIN_ID is exposed as an integer."""
    _set_valid_env(monkeypatch)
    monkeypatch.setenv("ADMIN_ID", "1001")
    config = _reload_config()
    assert isinstance(config.ADMIN_ID, int)
    assert config.ADMIN_ID == 1001


def test_admin_id_non_integer_raises(monkeypatch):
    """1.8: a non-integer ADMIN_ID raises an error naming ADMIN_ID."""
    _set_valid_env(monkeypatch)
    monkeypatch.setenv("ADMIN_ID", "not-a-number")
    with pytest.raises(RuntimeError) as exc_info:
        _reload_config()
    assert "ADMIN_ID" in str(exc_info.value)


def test_process_env_precedence(monkeypatch, tmp_path):
    """
    1.6: process environment wins over a .env file value.

    load_dotenv() does not override already-set process env vars, so the value
    present in the process environment must be used.
    """
    pytest.importorskip("dotenv")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("BOT_TOKEN=from_dotenv\n")
    monkeypatch.setenv("BOT_TOKEN", "from_process_env")
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    monkeypatch.setenv("ADMIN_ID", "5")
    config = _reload_config()
    assert config.BOT_TOKEN == "from_process_env"


def test_dotenv_loaded_when_present(monkeypatch, tmp_path):
    """1.5: values are loaded from a .env file when present in the root."""
    pytest.importorskip("dotenv")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "BOT_TOKEN=dotenv_tok\nGEMINI_API_KEY=dotenv_key\nADMIN_ID=7\n"
    )
    for var in REQUIRED_VARS:
        monkeypatch.delenv(var, raising=False)
    config = _reload_config()
    assert config.BOT_TOKEN == "dotenv_tok"
    assert config.GEMINI_API_KEY == "dotenv_key"
    assert config.ADMIN_ID == 7


# --- Property 1: Missing required variable is reported by name -------------
# Validates: Requirements 1.7


def test_property_missing_variable_reported_by_name(monkeypatch):
    """
    Property 1: For any single required variable that is absent (with the
    others present), loading raises an error whose message names that variable.
    """
    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @settings(max_examples=100)
    @given(missing=st.sampled_from(REQUIRED_VARS))
    def run(missing):
        # Set all required vars to valid values...
        mp = pytest.MonkeyPatch()
        try:
            mp.setenv("BOT_TOKEN", "valid-token")
            mp.setenv("GEMINI_API_KEY", "valid-key")
            mp.setenv("ADMIN_ID", "42")
            # ...then remove exactly one.
            mp.delenv(missing, raising=False)
            with pytest.raises(RuntimeError) as exc_info:
                _reload_config()
            assert missing in str(exc_info.value)
        finally:
            mp.undo()

    run()


def test_missing_each_variable_reported_by_name_examples(monkeypatch):
    """Example-based companion to Property 1 (runs without hypothesis)."""
    for missing in REQUIRED_VARS:
        mp = pytest.MonkeyPatch()
        try:
            mp.setenv("BOT_TOKEN", "valid-token")
            mp.setenv("GEMINI_API_KEY", "valid-key")
            mp.setenv("ADMIN_ID", "42")
            mp.delenv(missing, raising=False)
            with pytest.raises(RuntimeError) as exc_info:
                _reload_config()
            assert missing in str(exc_info.value)
        finally:
            mp.undo()


@pytest.fixture(autouse=True)
def _restore_config(monkeypatch):
    """Leave a valid config importable for other test modules after each test."""
    yield
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("ADMIN_ID", "123456789")
    _reload_config()
