# Implementation Plan: Project Hardening

## Overview

This plan hardens the SYLENTH Agent Telegram bot (Python 3.11, aiogram 3.x) through a
sequence of incremental, dependency-ordered coding steps. Each step builds on the previous
one and ends with wiring the change into the running bot so no code is left orphaned.

The work proceeds bottom-up: configuration and secrets first (everything imports
`config.py`), then the concurrency-correctness changes to the AI engine and the async
offloading/dependency migration, then middleware and defect fixes, then download hardening,
then the test suite, and finally a clean import/boot verification.

Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster path;
core implementation sub-tasks are never marked optional. Property-test sub-tasks each
reference a specific correctness property from the design document.

## Tasks

- [ ] 1. Configuration, secrets, and dependency manifest
  - [ ] 1.1 Rewrite `config.py` for env-based secret loading with fail-fast validation
    - Optionally `load_dotenv()` when a `.env` file exists in the project root (process env wins over `.env`)
    - Read `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_ID` via `os.getenv`; add `_require(name)` raising `RuntimeError` naming the missing/empty variable
    - Parse `ADMIN_ID` with `int(...)`, raising a `RuntimeError` naming `ADMIN_ID` on a non-integer value
    - Remove all hardcoded secret literals; keep non-secret tuning constants as plain literals
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 12.1_

  - [ ] 1.2 Update `requirements.txt` and `.env.example`
    - Add `python-dotenv>=1.0.0`; swap `duckduckgo-search` for `ddgs`
    - Add dev dependencies `pytest` and `hypothesis`
    - Verify `.env.example` lists `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_ID` with placeholders and no real credentials
    - _Requirements: 1.9, 5.3, 13.5_

  - [ ] 1.3 Inject CI secrets in `.github/workflows/main.yml`
    - Add an `env:` block on the bot run step mapping `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_ID` from GitHub Secrets
    - Confirm no secret literals appear anywhere in the workflow file
    - _Requirements: 2.1, 2.2_

- [ ] 2. Non-blocking AI engine (`bot/ai_engine.py`)
  - [ ] 2.1 Add off-loop Gemini call helper with timeout and bounded retry
    - Implement `_gemini_call` using `asyncio.wait_for(asyncio.to_thread(send_fn, *args), timeout=GEMINI_TIMEOUT_SECONDS)` with `GEMINI_MAX_RETRIES` bounded retries on transient errors
    - Route the initial turn and every tool-loop turn through `_gemini_call` so no Gemini call blocks the event loop
    - Ensure timeout/exhausted-retry cases propagate into the existing outer handler returning the Uzbek error dict
    - Log only `type(exc).__name__` and an attempt counter — never the API key, prompt, or token
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 12.2_

  - [ ]* 2.2 Write property test for AI failure collapse
    - **Property 2: AI failures collapse to the error response**
    - **Validates: Requirements 3.3, 3.4**
    - Mock the Gemini SDK to simulate timeout and transient-error-past-retry-bound; assert the exact `{"type": "error", "content": <Uzbek msg>, "music_results": None}` dict

  - [ ]* 2.3 Write unit tests for timeout and retry-bound behavior
    - Assert a finite timeout is applied and the retry count is bounded using a mocked SDK
    - _Requirements: 3.2, 3.4_

- [ ] 3. Modernize asyncio offloading and migrate web search to `ddgs`
  - [ ] 3.1 Migrate `bot/search.py` to `ddgs` with off-loop execution and finite timeout
    - Replace `from duckduckgo_search import DDGS` with `from ddgs import DDGS`; keep the existing formatter and `title`/`body`/`href` keys
    - Replace `asyncio.get_event_loop().run_in_executor(...)` with `await asyncio.wait_for(asyncio.to_thread(_search), timeout=SEARCH_TIMEOUT_SECONDS)`
    - Confirm the existing `except` path returns the Uzbek error string (timeout included)
    - _Requirements: 4.1, 5.1, 5.2, 5.4, 5.5, 11.3_

  - [ ]* 3.2 Write property test for search result formatting
    - **Property 3: Search result formatting is structure-preserving**
    - **Validates: Requirements 5.4**

  - [ ]* 3.3 Write property test for search error handling
    - **Property 4: Search errors yield the fixed Uzbek message**
    - **Validates: Requirements 5.5**

  - [ ] 3.4 Modernize offloading in `bot/file_analyzer.py` and fix the except clause
    - Replace `asyncio.get_event_loop().run_in_executor(...)` with `asyncio.to_thread(...)` in `analyze_pdf`, `analyze_docx`, `analyze_xlsx`, `analyze_code_file`, `analyze_zip`
    - Replace the redundant `except (UnicodeDecodeError, Exception)` fallback with a valid non-redundant `except (UnicodeDecodeError, OSError)`, returning the existing unsupported-file-type message on failure
    - _Requirements: 4.3, 8.1, 8.2_

  - [ ]* 3.5 Write property test for undecodable-file handling
    - **Property 7: Unknown undecodable files return the unsupported message**
    - **Validates: Requirements 8.2**

  - [ ] 3.6 Modernize offloading in `bot/downloader.py`
    - Replace all `asyncio.get_event_loop().run_in_executor(...)` download/search calls with `await asyncio.to_thread(...)`
    - _Requirements: 4.2_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Throttle middleware dual-type support and registration
  - [ ] 5.1 Broaden `middlewares/throttle.py` to accept messages and callback queries
    - Change the event type to `TelegramObject`; read `from_user` defensively and pass through unthrottled when it is `None`
    - On throttle, branch: `CallbackQuery.answer(THROTTLE_WARNING)` for callbacks, `Message.answer(THROTTLE_WARNING)` for messages, preserving once-per-burst warning behavior
    - _Requirements: 6.3, 6.4, 6.5, 6.6_

  - [ ] 5.2 Register the throttle middleware in `main.py`
    - Register a single `ThrottleMiddleware` instance on both `dp.message` and `dp.callback_query`
    - _Requirements: 6.1, 6.2_

  - [ ]* 5.3 Write property test for throttle event-type and missing-user handling
    - **Property 5: Throttle handles both event types and missing users**
    - **Validates: Requirements 6.3, 6.6**

  - [ ]* 5.4 Write unit tests for warn-once and callback acknowledgement branches
    - Verify single-warning-per-burst and the callback `answer` branch versus the message reply branch
    - _Requirements: 6.4, 6.5_

- [ ] 6. Defect fixes: group mention detection and database foreign keys
  - [ ] 6.1 Fix case-insensitive mention detection in `handlers/group.py`
    - Normalize both sides to lowercase in `_is_bot_mentioned` for the text-substring check and the `mention` entity check
    - _Requirements: 7.1, 7.2_

  - [ ]* 6.2 Write property test for case-insensitive mention detection
    - **Property 6: Mention detection is case-insensitive**
    - **Validates: Requirements 7.1, 7.2**

  - [ ] 6.3 Correct and enforce foreign keys in `database.py`
    - Change `conversations.user_id` and `user_memory.user_id` foreign keys to reference `users(id)` (the primary key)
    - Add an async `_connect()` context manager that opens a connection and runs `PRAGMA foreign_keys = ON`; route every FK-constrained write site through it
    - Preserve all existing public function signatures and return shapes
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ]* 6.4 Write property test for foreign-key enforcement
    - **Property 8: Foreign-key enforcement rejects orphan writes**
    - **Validates: Requirements 9.2**

  - [ ]* 6.5 Write unit test for FK schema shape
    - Assert FK targets via `PRAGMA foreign_key_list` and confirm public signatures unchanged
    - _Requirements: 9.1, 9.3_

- [ ] 7. Download hardening (`bot/downloader.py` + `main.py`)
  - [ ] 7.1 Add concurrency cap and collision-safe output paths
    - Add module-level `asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)` guarding the blocking body in `download_video`, `download_music`, `download_music_by_url`
    - Build a per-invocation unique `outtmpl` (e.g. `%(id)s.{uuid-token}.%(ext)s`); keep `prepare_filename`-based discovery working
    - _Requirements: 10.1, 10.2, 10.3_

  - [ ] 7.2 Add finite timeouts, bounded retries, and stale-file cleanup
    - Keep finite `socket_timeout` and bounded `retries` in yt-dlp opts for download and music-search operations
    - Add `cleanup_stale_downloads()` that removes leftover files; confirm post-send `cleanup_file` removal in callers' `finally`
    - Call `cleanup_stale_downloads()` from `main.on_startup` after creating the downloads directory
    - _Requirements: 10.4, 10.5, 11.1, 11.2_

  - [ ]* 7.3 Write property test for concurrency cap
    - **Property 9: Concurrent downloads never exceed the cap**
    - **Validates: Requirements 10.1, 10.2**
    - Replace the blocking body with an instrumented async stub guarded by the real semaphore to measure peak concurrency

  - [ ]* 7.4 Write property test for distinct concurrent output paths
    - **Property 10: Concurrent same-id downloads use distinct paths**
    - **Validates: Requirements 10.3**

  - [ ]* 7.5 Write property test for residual-file cleanup after send
    - **Property 11: Send attempts leave no residual file**
    - **Validates: Requirements 10.4**

  - [ ]* 7.6 Write property test for startup cleanup
    - **Property 12: Startup clears the downloads directory**
    - **Validates: Requirements 10.5**

  - [ ]* 7.7 Write unit test for finite timeouts/retries in built opts
    - Assert finite `socket_timeout` and bounded `retries` are present in the yt-dlp opts
    - _Requirements: 11.1, 11.2, 11.3_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Test suite scaffolding and remaining coverage
  - [ ] 9.1 Create `tests/conftest.py` with env and temp-DB fixtures
    - Set `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_ID` dummy values before any first-party import
    - Provide a temp-DB fixture that points `DB_PATH` at a `tmp_path` file and calls `init_db()`; create parent `users` rows before FK-constrained writes
    - _Requirements: 13.4, 13.5, 14.1_

  - [ ]* 9.2 Write property test and config unit tests in `test_config.py`
    - **Property 1: Missing required variable is reported by name**
    - **Validates: Requirements 1.7**
    - Add example tests for env reads, `.env` loading, process-env precedence, and `ADMIN_ID` int coercion (1.1-1.6, 1.8)

  - [ ]* 9.3 Write property test for safety classification in `test_safety.py`
    - **Property 13: Safety classification is correct over generated inputs**
    - **Validates: Requirements 13.1**

  - [ ]* 9.4 Write property test for detection in `test_detection.py`
    - **Property 14: Detection over supported URLs and music keywords**
    - **Validates: Requirements 13.2**

  - [ ]* 9.5 Write property test for message splitting in `test_splitting.py`
    - **Property 15: Message splitting bounds chunks and preserves content**
    - **Validates: Requirements 13.3**

  - [ ]* 9.6 Write property test for database round-trips in `test_database.py`
    - **Property 16: Database reads reflect writes**
    - **Validates: Requirements 13.4**

- [ ] 10. Clean import and boot verification
  - [ ] 10.1 Verify clean import and boot via tests and a manual import/boot check
    - Run a clean import of every first-party module with env vars present and confirm no error
    - Exercise the startup logic (`init_db()` + downloads-dir creation + `cleanup_stale_downloads()`) against temp paths without the Telegram network call
    - _Requirements: 14.1, 14.2_

  - [ ]* 10.2 Write property test for clean module imports in `test_imports.py`
    - **Property 17: All first-party modules import cleanly**
    - **Validates: Requirements 14.1**

  - [ ]* 10.3 Write property test for log credential hygiene
    - **Property 18: Logs never contain credentials**
    - **Validates: Requirements 12.1, 12.2**

- [ ] 11. Final checkpoint - Run the full suite green
  - Run the full `pytest` suite and confirm every test passes with all first-party modules importing cleanly.
  - _Requirements: 13.5, 14.1_

## Task Dependency Graph

```
1 (config/secrets/deps) ──┬──> 2 (AI engine)
                          ├──> 3 (asyncio + ddgs migration)
                          ├──> 5 (throttle)
                          ├──> 6 (defect fixes: mention + DB FKs)
                          └──> 7 (download hardening)*  (also depends on 3.6 offloading)

2, 3 ──────────> 4 (checkpoint)

3.6 (downloader offloading) ──> 7 (download hardening)

5, 6, 7 ──────> 8 (checkpoint)

1, 2, 3, 5, 6, 7 ──> 9 (test suite: conftest + coverage)

9 ──> 10 (import/boot verification)

10 ──> 11 (final checkpoint: full suite green)
```

- **Task 1** is the root: every module imports `config.py`, so secret loading and the
  dependency manifest must land first.
- **Tasks 2, 3, 5, 6** depend only on Task 1 and can proceed in any order after it.
- **Task 7** depends on Task 1 and on the downloader offloading work in Task 3.6.
- **Task 9** (tests) depends on all implementation tasks so the suite exercises final code.
- **Task 10** depends on the test scaffolding (Task 9) for fixtures and the import test.
- **Task 11** is the terminal gate requiring everything green.

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP.
- Each property test references a specific correctness property from `design.md` and the
  requirement clause it validates; property tests run a minimum of 100 iterations via
  `hypothesis`.
- Gemini, `ddgs`, and `yt-dlp` are mocked in tests so no real network access occurs.
- Checkpoints (Tasks 4, 8, 11) ensure incremental validation at logical boundaries.
- Out of scope: rotation of previously committed credentials and any deployment activity —
  these are the operator's responsibility and require no code changes here.
```
