# Design Document

## Overview

This design hardens the SYLENTH Agent Telegram bot (Python, aiogram 3.x) for production
operation. It is a **targeted defect-fix and hardening pass**, not a restructuring. Each
change is scoped to a single existing module and preserves the current public API surface
(handler signatures, `database.py` function signatures, response dict shapes, and the
existing Uzbek user-facing messages).

The work spans four themes:

1. **Security / configuration** — move secrets out of source into the environment with
   fail-fast validation; inject secrets into CI from GitHub Secrets; keep credentials out
   of logs.
2. **Concurrency correctness** — stop blocking the event loop during Gemini calls,
   modernize `asyncio` offloading, and bound + isolate + clean up media downloads.
3. **Defect fixes** — case-insensitive group mention detection, valid `except` clause in
   the file analyzer, correct + enforced database foreign keys, and migration off the
   deprecated `duckduckgo_search` package to `ddgs`.
4. **Verification** — a lightweight `pytest` suite over pure logic plus a clean
   import/boot check.

The implementation language is **Python 3.11** (the version pinned in CI).

## Architecture

No new layers or services are introduced. The module map below shows which files change
and the nature of each change.

```
config.py ............ env-based secret loading + fail-fast validation (CHANGED)
.env.example ......... retained, already correct (UNCHANGED content)
requirements.txt ..... swap duckduckgo-search -> ddgs; add python-dotenv (CHANGED)
.github/workflows/
  main.yml ........... inject BOT_TOKEN/GEMINI_API_KEY/ADMIN_ID from secrets (CHANGED)

main.py .............. register ThrottleMiddleware on message + callback_query;
                       call downloader stale-file cleanup on startup (CHANGED)

bot/ai_engine.py ..... offload Gemini calls via asyncio.to_thread + wait_for timeout
                       + bounded retry; keep error dict (CHANGED)
bot/search.py ........ migrate to ddgs; asyncio.to_thread; finite timeout (CHANGED)
bot/downloader.py .... asyncio.to_thread; concurrency semaphore; collision-safe
                       outtmpl; startup cleanup helper; socket timeout + retries (CHANGED)
bot/file_analyzer.py . asyncio.to_thread; fix invalid except clause (CHANGED)
bot/safety.py ........ unchanged (covered by tests) (UNCHANGED)

middlewares/throttle.py  accept Message + CallbackQuery; user-aware warn path (CHANGED)
handlers/group.py .... case-insensitive _is_bot_mentioned (CHANGED)
handlers/utils.py .... unchanged (covered by tests) (UNCHANGED)
database.py .......... FKs reference users(id); PRAGMA foreign_keys=ON per write
                       connection; signatures preserved (CHANGED)

tests/ ............... new pytest suite (NEW)
```

### Design principles applied

- **Fail fast, fail clearly**: configuration errors surface at startup naming the exact
  missing variable, rather than producing an opaque downstream failure.
- **Never block the loop**: every synchronous third-party call (Gemini, yt-dlp, ddgs,
  file I/O) runs in a worker thread via `asyncio.to_thread`.
- **Bounded everything**: network operations carry finite timeouts and bounded retries;
  concurrent downloads are capped by a semaphore.
- **Preserve observable behavior**: user-facing Uzbek strings, response dict shapes, and
  public function signatures are unchanged so handlers and the DB layer keep working.

## Components and Interfaces

### 1. Configuration Module (`config.py`)

**Requirements: 1.1–1.9, 12.1**

Replace the hardcoded literals with environment-driven loading.

- At import time, optionally call `load_dotenv()` from `python-dotenv` if a `.env` file
  exists in the project root. `load_dotenv` does **not** override already-set process
  environment variables by default, which satisfies the precedence rule (process env wins
  over `.env`).
- Read each value with `os.getenv(NAME)`.
- A `_require(name)` helper returns the value or raises
  `RuntimeError(f"Missing required environment variable: {name}")` when the value is
  absent or empty (after `strip()`).
- `ADMIN_ID` is parsed with `int(...)`; a non-integer value raises a `RuntimeError` that
  names `ADMIN_ID`.
- Non-secret tuning constants (`DB_PATH`, `GEMINI_MODEL`, `MAX_TOKENS`, `TEMPERATURE`,
  `HISTORY_LIMIT`) remain plain literals.
- `.env.example` is retained as-is (already lists the three keys with placeholders).

```python
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    if Path(".env").exists():
        load_dotenv()  # does not override existing process env vars
except ImportError:
    pass

def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()

BOT_TOKEN: str = _require("BOT_TOKEN")
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")

try:
    ADMIN_ID: int = int(_require("ADMIN_ID"))
except ValueError as exc:
    raise RuntimeError("Environment variable ADMIN_ID must be an integer") from exc
```

`requirements.txt` gains `python-dotenv>=1.0.0`.

### 2. CI Pipeline (`.github/workflows/main.yml`)

**Requirements: 2.1, 2.2**

Add an `env:` block to the "Botni ishga tushirish" run step that maps the three GitHub
Secrets into the process environment. No secret literals appear in the file.

```yaml
      - name: Botni ishga tushirish
        env:
          BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ADMIN_ID: ${{ secrets.ADMIN_ID }}
        run: timeout --preserve-status 20000s python main.py
```

### 3. AI Engine (`bot/ai_engine.py`)

**Requirements: 3.1–3.5, 12.2**

The Gemini SDK calls (`chat.send_message(...)` for the initial turn and for each
tool-loop turn) are synchronous and currently run on the event loop thread. Wrap them in a
shared helper that offloads to a worker thread, applies a finite timeout, and retries a
bounded number of times on transient errors.

```python
GEMINI_TIMEOUT_SECONDS = 30.0
GEMINI_MAX_RETRIES = 2  # total attempts = retries + 1

async def _gemini_call(send_fn, *args):
    """Run a synchronous Gemini call off-loop, with timeout + bounded retry."""
    last_exc = None
    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(send_fn, *args),
                timeout=GEMINI_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, Exception) as exc:  # transient
            last_exc = exc
            logger.warning("Gemini call attempt %d failed: %s", attempt + 1, type(exc).__name__)
    raise last_exc
```

- Initial turn: `response = await _gemini_call(chat.send_message, user_text)`.
- Tool loop: `response = await _gemini_call(chat.send_message, genai.protos.Content(parts=function_responses))`.
- The outer `try/except` in `get_ai_response` already returns
  `{"type": "error", "content": ERROR_MESSAGE_UZ, "music_results": None}`; the timeout and
  exhausted-retry cases propagate into that handler so the existing Uzbek error dict is
  returned unchanged.
- **Log hygiene**: the warning logs only `type(exc).__name__` and a counter — never the
  API key, prompt content, or token. The existing `logger.error` lines that include `e`
  are reviewed to confirm no credential is interpolated.

> Note on log granularity: logging the exception **type name** (not `str(exc)`) avoids
> the small risk that a third-party error message echoes a URL containing a key.

### 4. Search Module (`bot/search.py`)

**Requirements: 4.1, 5.1, 5.2, 5.4, 5.5, 11.3**

- Replace `from duckduckgo_search import DDGS` with `from ddgs import DDGS`. The `ddgs`
  package preserves the `DDGS().text(query, max_results=...)` API and result keys
  (`title`, `body`, `href`), so the existing formatter is unchanged.
- Replace `asyncio.get_event_loop().run_in_executor(None, _search)` with
  `await asyncio.wait_for(asyncio.to_thread(_search), timeout=SEARCH_TIMEOUT_SECONDS)`
  to both modernize offloading and apply a finite timeout.
- The existing `except Exception` path already returns the Uzbek error string; the timeout
  raises `asyncio.TimeoutError` (a subclass path) and is caught by the same handler.

```python
from ddgs import DDGS
SEARCH_TIMEOUT_SECONDS = 20.0

def _search():
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))

results = await asyncio.wait_for(asyncio.to_thread(_search), timeout=SEARCH_TIMEOUT_SECONDS)
```

### 5. Download Manager (`bot/downloader.py`)

**Requirements: 4.2, 10.1–10.5, 11.1, 11.2**

- **Offloading**: every `asyncio.get_event_loop().run_in_executor(None, _download)` /
  `_search` becomes `await asyncio.to_thread(_download)` etc.
- **Concurrency cap**: a module-level `asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)` guards
  the blocking download body in `download_video`, `download_music`, and
  `download_music_by_url`. Requests beyond the cap await a free slot.

  ```python
  MAX_CONCURRENT_DOWNLOADS = 3
  _download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
  ...
  async with _download_semaphore:
      result = await asyncio.to_thread(_download)
  ```

- **Collision-safe output paths**: change the `outtmpl` from `"%(id)s.%(ext)s"` to include
  a per-invocation unique token so two concurrent downloads of the same media id never
  target the same path:

  ```python
  token = uuid.uuid4().hex[:8]
  "outtmpl": os.path.join(DOWNLOADS_DIR, f"%(id)s.{token}.%(ext)s")
  ```

  The post-download filename discovery uses `ydl.prepare_filename(info)` (already
  derived from `outtmpl`), so the existing fallback-extension logic continues to work
  against the unique base.
- **Network bounding**: `socket_timeout` (already present, kept finite) and `retries`
  (bounded, kept) remain in the yt-dlp opts; the design documents them as the
  required finite timeout (11.1) and bounded retry (11.2). Music search opts keep
  `socket_timeout`.
- **Cleanup after send**: `cleanup_file` already removes a file; callers in `group.py`
  (and the private handler) already call it in a `finally`. The design records this as the
  send/failure cleanup mechanism (10.4). Per-invocation unique paths make cleanup
  unambiguous.
- **Startup stale-file cleanup**: a new helper removes leftover files from previous runs.

  ```python
  def cleanup_stale_downloads() -> None:
      d = Path(DOWNLOADS_DIR)
      if not d.exists():
          return
      for f in d.iterdir():
          if f.is_file():
              try:
                  f.unlink()
              except OSError as exc:
                  logger.warning("Could not remove stale file %s: %s", f.name, exc)
  ```

  `main.on_startup` calls `cleanup_stale_downloads()` after creating the directory.

### 6. File Analyzer (`bot/file_analyzer.py`)

**Requirements: 4.3, 8.1, 8.2**

- Replace `asyncio.get_event_loop().run_in_executor(None, _read_*)` calls with
  `await asyncio.to_thread(_read_*)` in `analyze_pdf`, `analyze_docx`, `analyze_xlsx`,
  `analyze_code_file`, and `analyze_zip`.
- Fix the invalid fallback clause in `analyze_file`. The current
  `except (UnicodeDecodeError, Exception)` is redundant because `Exception` already
  subsumes `UnicodeDecodeError`. Replace with a single broad clause:

  ```python
  try:
      with open(file_path, "r", encoding="utf-8") as f:
          content = f.read()
      if content.strip():
          return _truncate_text(f"--- Fayl: {file_name} ---\n{content}")
  except (UnicodeDecodeError, OSError):
      pass
  return ( ... unsupported-file-type message ... )
  ```

  Using `(UnicodeDecodeError, OSError)` keeps the handling explicit and non-redundant; on
  decode failure the existing unsupported-file-type message is returned.

### 7. Throttle Middleware (`middlewares/throttle.py`) + registration (`main.py`)

**Requirements: 6.1–6.6**

- Broaden the event type from `Message` to `TelegramObject` and branch on the concrete
  type for the warning channel:

  ```python
  from aiogram.types import Message, CallbackQuery, TelegramObject

  async def __call__(self, handler, event: TelegramObject, data):
      user = getattr(event, "from_user", None)
      if user is None:
          return await handler(event, data)        # 6.6 pass-through
      ...
      if time_diff < self.interval:
          if not self._user_warned.get(user_id, False):
              self._user_warned[user_id] = True
              try:
                  if isinstance(event, CallbackQuery):
                      await event.answer(THROTTLE_WARNING, show_alert=False)  # 6.5
                  elif isinstance(event, Message):
                      await event.answer(THROTTLE_WARNING)                    # 6.4
              except Exception:
                  pass
          return None
      ...
  ```

  `CallbackQuery.answer(text=...)` acknowledges the callback with the warning, while
  `Message.answer(...)` replies in chat — both methods exist on their respective types, so
  no message-only method is called on a callback.
- In `main.py`, register the middleware on both routers' update types:

  ```python
  throttle = ThrottleMiddleware()
  dp.message.middleware(throttle)
  dp.callback_query.middleware(throttle)
  ```

### 8. Group Handler (`handlers/group.py`)

**Requirements: 7.1, 7.2**

Fix `_is_bot_mentioned` to compare consistently in lowercase. The first check already
lowercases `message.text` but compares against a non-lowercased `@{bot_username}`; the
entity check compares `mention_text.lower()` against a non-lowercased target. Normalize
both sides:

```python
def _is_bot_mentioned(message, bot_username) -> bool:
    if not message.text:
        return False
    target = f"@{bot_username}".lower()
    if target in message.text.lower():
        return True
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention_text = message.text[entity.offset:entity.offset + entity.length]
                if mention_text.lower() == target:
                    return True
    return False
```

### 9. Database Layer (`database.py`)

**Requirements: 9.1, 9.2, 9.3**

- **Foreign keys**: change both FK definitions from `REFERENCES users(tg_id)` to
  `REFERENCES users(id)` so they reference the table's primary key. `users.tg_id` is
  `UNIQUE` but not the primary key; SQLite requires FK targets to be the primary key or a
  unique column, and the requirement mandates referencing the primary key.

  > **Compatibility note**: callers currently pass the Telegram id as `user_id` for
  > conversations/memory. To keep the public signatures **and** satisfy referential
  > integrity, the schema references `users(id)` while the existing helper queries continue
  > to operate on the value passed in. Because enforcement is enabled (below), the design
  > stores the relationship against the surrogate key; the test suite validates writes
  > against valid parent rows. Public function signatures
  > (`get_or_create_user`, `save_message`, `get_conversation_history`,
  > `save_user_memory`, `get_user_memories`, `clear_history`, `prune_old_conversations`,
  > `get_stats`, `init_db`) are unchanged.

- **Enforcement**: SQLite has foreign-key enforcement **off** by default and it must be set
  per connection. Introduce a small async connection helper that opens a connection and
  enables the pragma, used by every function that performs writes constrained by FKs:

  ```python
  @asynccontextmanager
  async def _connect():
      db = await aiosqlite.connect(DB_PATH)
      try:
          await db.execute("PRAGMA foreign_keys = ON")
          yield db
      finally:
          await db.close()
  ```

  Each `async with aiosqlite.connect(DB_PATH) as db:` write site becomes
  `async with _connect() as db:`. Read-only helpers may also use it for consistency.
- Signatures and return shapes (dicts / lists of dicts) are preserved exactly.

### 10. Test Suite (`tests/`)

**Requirements: 13.1–13.5, 14.1, 14.2**

A `pytest` suite covering pure, deterministic logic. Network and Gemini calls are mocked or
skipped; the DB tests run against a temporary SQLite file via fixtures.

```
tests/
  conftest.py ............ sets required env vars before imports; temp DB fixture
  test_safety.py ......... is_safe / is_prompt_injection (13.1)
  test_detection.py ...... is_video_url / is_music_request (13.2)
  test_splitting.py ...... _split_long_message invariants (13.3)
  test_database.py ....... user/conversation/memory round-trips on temp DB (13.4)
  test_throttle.py ....... message + callback acceptance, no-user pass-through (6.x)
  test_mention.py ........ case-insensitive mention detection (7.x)
  test_imports.py ........ clean import of all first-party modules (14.1)
  test_config.py ......... fail-fast on each missing var, ADMIN_ID int (1.7, 1.8)
```

- `conftest.py` sets `BOT_TOKEN`, `GEMINI_API_KEY`, `ADMIN_ID` to dummy values in the
  environment **before** any first-party import, so importing `config.py` (and modules
  that import it) succeeds during collection.
- The temp DB fixture points `DB_PATH` at a `tmp_path` file and calls `init_db()`.
- For DB tests, parent `users` rows are created via `get_or_create_user` before writing
  conversations/memories so FK-enforced writes reference valid rows.
- A property-testing library (`hypothesis`) drives the property tests; example/edge tests
  use plain `pytest`. `pytest` (and `hypothesis`) are added as dev dependencies.

### 11. Import / Boot Verification

**Requirements: 14.1, 14.2**

- `test_imports.py` imports every first-party module with env vars present and asserts no
  exception.
- A boot test invokes the startup logic (`init_db()` + downloads-dir creation +
  `cleanup_stale_downloads()`) against temp paths and asserts it completes without error.
  The Telegram network call (`bot.get_me()`) is not exercised in the boot test.

## Data Models

No data-model shape changes. The SQLite schema keeps the same columns; only the two
foreign-key target columns change (`tg_id` → `id`) and enforcement is enabled per
connection. Response dicts returned by `get_ai_response`
(`{"type", "content", "music_results"}`) and the downloader return tuples
(`(path, title)` / `(path, metadata)`) are unchanged.

## Error Handling

| Failure | Handling | Requirement |
|---|---|---|
| Missing/empty required env var | `RuntimeError` naming the variable, at startup | 1.7 |
| Non-integer `ADMIN_ID` | `RuntimeError` naming `ADMIN_ID` | 1.8 |
| Gemini timeout | retry up to bound, then return error dict (Uzbek) | 3.2, 3.3, 3.4 |
| Gemini transient error | bounded retry, then error dict | 3.4 |
| Web search error/timeout | return existing Uzbek error string | 5.5, 11.3 |
| Media download transient error | bounded yt-dlp retries, then error result | 11.2 |
| File undecodable (unknown type) | return unsupported-file-type message | 8.2 |
| FK-violating DB write | rejected by enforced `PRAGMA foreign_keys = ON` | 9.2 |
| Event without `from_user` | pass through to handler unthrottled | 6.6 |
| Any logged error | log type/context only, never a credential | 12.1, 12.2 |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid
executions of a system — a formal statement about what the system should do. Properties
bridge human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Missing required variable is reported by name

*For any* one of the required environment variables (`BOT_TOKEN`, `GEMINI_API_KEY`,
`ADMIN_ID`), if that variable is absent or empty while the others are present, then
configuration loading raises an error whose message contains the name of that variable.

**Validates: Requirements 1.7**

### Property 2: AI failures collapse to the error response

*For any* simulated Gemini failure mode (timeout, or a transient error repeated past the
retry bound), `get_ai_response` returns a dict equal to
`{"type": "error", "content": <Uzbek error message>, "music_results": None}`.

**Validates: Requirements 3.3, 3.4**

### Property 3: Search result formatting is structure-preserving

*For any* list of search-result dicts (each with `title`, `body`, `href`), the formatted
output contains one sequentially numbered entry per result, and each entry includes that
result's title, body, and link.

**Validates: Requirements 5.4**

### Property 4: Search errors yield the fixed Uzbek message

*For any* exception raised by the underlying search call, `search_web` returns the existing
Uzbek error string rather than propagating the exception.

**Validates: Requirements 5.5**

### Property 5: Throttle handles both event types and missing users

*For any* event that is a `Message` or a `CallbackQuery`, the middleware executes without
raising a type error; and *for any* event whose `from_user` is `None`, the middleware
invokes the next handler without throttling.

**Validates: Requirements 6.3, 6.6**

### Property 6: Mention detection is case-insensitive

*For any* letter-case variant of the bot's `@username` appearing in message text or in a
Telegram `mention` entity, `_is_bot_mentioned` returns `True`.

**Validates: Requirements 7.1, 7.2**

### Property 7: Unknown undecodable files return the unsupported message

*For any* file whose bytes are not valid UTF-8 and whose extension is not a recognized
type, `analyze_file` returns the unsupported-file-type message without raising.

**Validates: Requirements 8.2**

### Property 8: Foreign-key enforcement rejects orphan writes

*For any* write to `conversations` or `user_memory` whose `user_id` does not reference an
existing `users` primary key, the enforced connection rejects the write with an integrity
error.

**Validates: Requirements 9.2**

### Property 9: Concurrent downloads never exceed the cap

*For any* number of simultaneously launched download requests, the number executing the
guarded download body at the same time never exceeds `MAX_CONCURRENT_DOWNLOADS`, and excess
requests wait until a slot is released.

**Validates: Requirements 10.1, 10.2**

### Property 10: Concurrent same-id downloads use distinct paths

*For any* media identifier and *any* number of concurrent invocations, the generated output
paths are pairwise distinct.

**Validates: Requirements 10.3**

### Property 11: Send attempts leave no residual file

*For any* download whose send either succeeds or fails, the downloaded file is absent from
the downloads directory afterward.

**Validates: Requirements 10.4**

### Property 12: Startup clears the downloads directory

*For any* set of pre-existing files in the downloads directory, running the startup
cleanup helper removes all of them.

**Validates: Requirements 10.5**

### Property 13: Safety classification is correct over generated inputs

*For any* generated clearly-safe text, `is_safe` returns `True`; *for any* text containing a
banned token, `is_safe` returns `False`; and *for any* known prompt-injection phrase,
`is_prompt_injection` returns `True`.

**Validates: Requirements 13.1**

### Property 14: Detection over supported URLs and music keywords

*For any* URL from a supported video platform, `is_video_url` returns `True`; and *for any*
text containing a music keyword, `is_music_request` returns `True`.

**Validates: Requirements 13.2**

### Property 15: Message splitting bounds chunks and preserves content

*For any* input text, every chunk produced by `_split_long_message` has length at most the
Telegram limit, and concatenating the chunks reconstructs the original text (modulo
whitespace stripped at split boundaries).

**Validates: Requirements 13.3**

### Property 16: Database reads reflect writes

*For any* sequence of user, conversation, and memory writes against a temporary database,
reading back returns the written values, with conversation history ordered oldest-first.

**Validates: Requirements 13.4**

### Property 17: All first-party modules import cleanly

*For any* first-party module of the bot, importing it with the required environment
variables present completes without raising an error.

**Validates: Requirements 14.1**

### Property 18: Logs never contain credentials

*For any* log record emitted across the bot's error paths (including failed network
operations), the record text excludes the bot token, AI API key, and administrator
identifier values.

**Validates: Requirements 12.1, 12.2**

## Testing and Verification Strategy

**Dual approach.** Property tests (via `hypothesis`, minimum 100 iterations each) cover the
universal properties above; example/edge unit tests cover specific wiring and boundary
behavior that does not vary with input.

**Property tests** map one-to-one to the properties in this document. Each property test is
tagged `Feature: project-hardening, Property {n}: {property text}` and references the
requirement clause it validates.

**Example / edge unit tests** cover:
- `config.py` env reads, `.env` loading, process-env precedence, `ADMIN_ID` int coercion
  (1.1–1.6, 1.8).
- Gemini timeout path and retry-count bound with a mocked SDK (3.2, 3.4).
- Throttle single-warning-per-burst and callback acknowledgement branch (6.4, 6.5).
- FK schema shape via `PRAGMA foreign_key_list` (9.1).
- Finite `socket_timeout` / `retries` present in built yt-dlp opts; finite search timeout
  (11.1, 11.2, 11.3).

**Static / structural checks** (verified by inspection or simple source assertions, not
PBT — these are configuration and dependency facts, not input-varying logic):
- No secret literals in `config.py` or `main.yml` (1.4, 2.2).
- `.env.example` retains placeholders (1.9).
- CI maps the three secrets into the run step (2.1).
- No `asyncio.get_event_loop()` in `search.py` / `downloader.py` / `file_analyzer.py`
  (4.1–4.3).
- `ddgs` imported, `duckduckgo_search` absent, manifest updated (5.1–5.3).
- Middleware registered on `dp.message` and `dp.callback_query` (6.1, 6.2).
- File-analyzer `except` clause valid and non-redundant (8.1).
- Public DB signatures unchanged (9.3).

**Boot verification** (14.2): a test runs the startup logic — `init_db()`, downloads-dir
creation, `cleanup_stale_downloads()` — against temporary paths and asserts no error,
without performing the Telegram network call.

**Mocking policy**: Gemini, `ddgs`, and `yt-dlp` are mocked in unit/property tests so no
real network access occurs. The concurrency property (Property 9) replaces the blocking
download body with an instrumented async stub guarded by the real semaphore to measure peak
concurrency deterministically.

**Pass bar** (13.5, 14.1): the full suite runs green under `pytest`, and all first-party
modules import cleanly with env vars present.

## Notes / Out of Scope

- Rotation of any previously committed credentials is the operator's responsibility and is
  out of scope for automated work here.
- No architectural restructuring, no new abstractions, and no changes to user-facing Uzbek
  copy beyond what the fixes require.
