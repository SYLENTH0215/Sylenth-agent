# Requirements Document

## Introduction

This feature hardens the SYLENTH Agent Telegram bot (Python, aiogram 3.x) for production operation. The work addresses confirmed security, concurrency, correctness, and dependency defects in the existing codebase, adds sensible production hardening (download concurrency limits, network retry with timeouts, download cleanup, enforced database foreign keys, and log hygiene), migrates the deprecated web-search dependency, and establishes a lightweight automated test suite plus a clean import/boot verification bar.

The scope is limited to fixing known issues and adding targeted hardening. No broad architectural restructuring is performed. Existing committed secrets are out of scope for automated rotation; the user remains responsible for rotating any previously exposed credentials.

## Glossary

- **Bot**: The SYLENTH Agent Telegram application as a whole, including all modules below.
- **Configuration_Module**: The `config.py` module that supplies runtime settings such as the Telegram bot token, the AI API key, and the administrator identifier.
- **AI_Engine**: The `bot/ai_engine.py` module that generates responses using the Google Gemini client and tool calling.
- **Search_Module**: The `bot/search.py` module that performs web searches.
- **Download_Manager**: The `bot/downloader.py` module that downloads videos and music.
- **File_Analyzer**: The `bot/file_analyzer.py` module that extracts text from uploaded files.
- **Throttle_Middleware**: The `middlewares/throttle.py` anti-flood middleware.
- **Group_Handler**: The `handlers/group.py` module that processes group and supergroup messages.
- **Database_Layer**: The `database.py` module that persists users, conversations, and memories in SQLite.
- **CI_Pipeline**: The GitHub Actions workflow defined in `.github/workflows/main.yml`.
- **Test_Suite**: The automated pytest test collection added by this feature.
- **Environment_Variable**: A named value supplied to the process via the operating environment or an optional `.env` file.
- **GitHub_Secret**: An encrypted value stored in the GitHub repository and exposed to the CI_Pipeline at runtime.
- **Hardcoded_Secret**: A credential value written as a literal in a source file.
- **Event_Loop**: The asyncio event loop that runs the Bot.
- **Blocking_Call**: A synchronous operation that runs on the Event_Loop thread and prevents other coroutines from progressing until it returns.
- **Network_Operation**: An AI generation request or web/media network request issued by the Bot.

## Requirements

### Requirement 1: Secret loading from the environment

**User Story:** As an operator, I want all credentials loaded from the environment, so that no live secrets are committed to source control.

#### Acceptance Criteria

1. THE Configuration_Module SHALL read the Telegram bot token from an Environment_Variable named `BOT_TOKEN`.
2. THE Configuration_Module SHALL read the AI API key from an Environment_Variable named `GEMINI_API_KEY`.
3. THE Configuration_Module SHALL read the administrator identifier from an Environment_Variable named `ADMIN_ID`.
4. THE Configuration_Module SHALL contain no Hardcoded_Secret value for the bot token, the AI API key, or the administrator identifier.
5. WHERE a `.env` file is present in the project root, THE Configuration_Module SHALL load Environment_Variable values from that file.
6. WHERE a required Environment_Variable is also defined in the process environment, THE Configuration_Module SHALL use the process environment value in preference to the `.env` file value.
7. IF a required Environment_Variable (`BOT_TOKEN`, `GEMINI_API_KEY`, or `ADMIN_ID`) is absent or empty at startup, THEN THE Configuration_Module SHALL raise an error that names the missing Environment_Variable.
8. WHEN the administrator identifier is read, THE Configuration_Module SHALL expose the administrator identifier as an integer value.
9. THE Configuration_Module SHALL retain a `.env.example` file that lists `BOT_TOKEN`, `GEMINI_API_KEY`, and `ADMIN_ID` with placeholder values and no real credentials.

### Requirement 2: CI secret injection

**User Story:** As an operator, I want the CI workflow to inject secrets from GitHub Secrets, so that the bot runs in CI without exposing credentials in the workflow file.

#### Acceptance Criteria

1. THE CI_Pipeline SHALL provide the `BOT_TOKEN`, `GEMINI_API_KEY`, and `ADMIN_ID` Environment_Variable values to the bot run step from corresponding GitHub_Secret entries.
2. THE CI_Pipeline SHALL contain no Hardcoded_Secret value for the bot token, the AI API key, or the administrator identifier.

### Requirement 3: Non-blocking AI generation

**User Story:** As a user, I want the bot to stay responsive during AI generation, so that one request does not freeze the whole bot.

#### Acceptance Criteria

1. WHEN the AI_Engine sends a message to the Google Gemini client, THE AI_Engine SHALL execute the synchronous Gemini call off the Event_Loop thread so that the call is not a Blocking_Call on the Event_Loop.
2. WHEN the AI_Engine issues a Network_Operation to the Google Gemini client, THE AI_Engine SHALL apply a finite timeout to that Network_Operation.
3. IF a Network_Operation to the Google Gemini client exceeds its timeout, THEN THE AI_Engine SHALL return a response of type `error` carrying the existing Uzbek error message.
4. IF a Network_Operation to the Google Gemini client fails with a transient error, THEN THE AI_Engine SHALL retry the Network_Operation up to a bounded retry count before returning a response of type `error`.
5. WHILE the AI_Engine processes its tool-calling loop, THE AI_Engine SHALL execute each Gemini call within that loop off the Event_Loop thread.

### Requirement 4: Modernized asyncio loop access

**User Story:** As a maintainer, I want current asyncio APIs used for offloading work, so that the bot remains compatible with supported Python versions and avoids deprecated calls.

#### Acceptance Criteria

1. THE Search_Module SHALL offload its synchronous search work to a worker thread without calling the deprecated `asyncio.get_event_loop()` API.
2. THE Download_Manager SHALL offload its synchronous download and search work to a worker thread without calling the deprecated `asyncio.get_event_loop()` API.
3. THE File_Analyzer SHALL offload its synchronous file-reading work to a worker thread without calling the deprecated `asyncio.get_event_loop()` API.

### Requirement 5: Web-search dependency migration

**User Story:** As a maintainer, I want the search code on the maintained `ddgs` package, so that the bot does not depend on the deprecated `duckduckgo_search` package.

#### Acceptance Criteria

1. THE Search_Module SHALL perform web searches using the `ddgs` package.
2. THE Search_Module SHALL contain no import of the `duckduckgo_search` package.
3. THE Bot dependency manifest SHALL list `ddgs` and SHALL NOT list `duckduckgo-search`.
4. WHEN a web search returns results, THE Search_Module SHALL produce the same formatted result structure (numbered title, body, and link entries) that the current implementation produces.
5. IF a web search raises an error, THEN THE Search_Module SHALL return the existing Uzbek error message.

### Requirement 6: Throttle coverage for messages and callbacks

**User Story:** As an operator, I want anti-flood protection on both messages and button presses, so that abusive callback traffic is also rate limited.

#### Acceptance Criteria

1. THE Throttle_Middleware SHALL be registered for message updates.
2. THE Throttle_Middleware SHALL be registered for callback query updates.
3. THE Throttle_Middleware SHALL accept both message events and callback query events without raising a type error.
4. WHEN the Throttle_Middleware throttles a message event, THE Throttle_Middleware SHALL send the throttle warning to the originating user once per throttle burst.
5. WHEN the Throttle_Middleware throttles a callback query event, THE Throttle_Middleware SHALL acknowledge the callback query with the throttle warning rather than calling a message-only reply method.
6. WHEN an event carries no originating user, THE Throttle_Middleware SHALL pass the event to the next handler without throttling.

### Requirement 7: Group mention detection correctness

**User Story:** As a group user, I want the bot to recognize when it is mentioned regardless of letter case, so that mentions reliably trigger a response.

#### Acceptance Criteria

1. WHEN a group message contains an `@mention` of the Bot username in any letter case, THE Group_Handler SHALL detect the Bot as mentioned.
2. WHEN a group message contains a Telegram `mention` entity referencing the Bot username, THE Group_Handler SHALL detect the Bot as mentioned using a consistent letter-case comparison.

### Requirement 8: File analyzer exception handling correctness

**User Story:** As a maintainer, I want the file analyzer fallback to use valid exception handling, so that file-type fallback behaves predictably.

#### Acceptance Criteria

1. THE File_Analyzer SHALL handle the fallback text-read path using exception clauses that are valid and non-redundant.
2. IF the File_Analyzer fallback text read fails to decode the file, THEN THE File_Analyzer SHALL return the existing unsupported-file-type message.

### Requirement 9: Enforced and correct database foreign keys

**User Story:** As a maintainer, I want referential integrity enforced against a valid key, so that conversation and memory rows reference real users.

#### Acceptance Criteria

1. THE Database_Layer SHALL define the `conversations.user_id` foreign key and the `user_memory.user_id` foreign key to reference the primary key column of the `users` table.
2. WHEN the Database_Layer opens a SQLite connection that performs writes constrained by foreign keys, THE Database_Layer SHALL enable `PRAGMA foreign_keys = ON` for that connection.
3. THE Database_Layer SHALL preserve the existing public function signatures for user, conversation, and memory operations.

### Requirement 10: Download concurrency, isolation, and cleanup

**User Story:** As an operator, I want downloads bounded and cleaned up, so that the server does not exhaust resources or accumulate stale files.

#### Acceptance Criteria

1. THE Download_Manager SHALL limit the number of concurrent download operations to a fixed maximum.
2. WHILE the concurrent download maximum is reached, THE Download_Manager SHALL make additional download requests wait until a slot becomes available.
3. WHEN the Download_Manager writes a downloaded file, THE Download_Manager SHALL use an output path scheme that prevents collisions between concurrent downloads of the same media identifier.
4. WHEN a downloaded file has been sent or has failed to send, THE Download_Manager SHALL remove that file from the downloads directory.
5. WHEN the Bot starts, THE Download_Manager SHALL remove stale files remaining in the downloads directory from previous runs.

### Requirement 11: Network operation timeouts and retries

**User Story:** As an operator, I want network operations bounded and retried, so that transient failures do not hang or permanently break a request.

#### Acceptance Criteria

1. WHEN the Download_Manager issues a media Network_Operation, THE Download_Manager SHALL apply a finite socket timeout to that Network_Operation.
2. IF a media Network_Operation fails with a transient error, THEN THE Download_Manager SHALL retry that Network_Operation up to a bounded retry count before returning an error result.
3. WHEN the Search_Module issues a web-search Network_Operation, THE Search_Module SHALL apply a finite timeout to that Network_Operation.

### Requirement 12: Log hygiene

**User Story:** As an operator, I want logs free of secrets, so that credentials are not leaked through log output.

#### Acceptance Criteria

1. THE Bot SHALL exclude the bot token, the AI API key, and the administrator identifier from log output.
2. WHEN the Bot logs an error for a failed Network_Operation, THE Bot SHALL record the error without including any credential value.

### Requirement 13: Automated test suite

**User Story:** As a maintainer, I want a lightweight automated test suite, so that core logic is verified and regressions are caught.

#### Acceptance Criteria

1. THE Test_Suite SHALL include tests that verify the safety filter accepts safe text and rejects banned content and prompt-injection attempts.
2. THE Test_Suite SHALL include tests that verify video-URL detection and music-request detection for representative inputs.
3. THE Test_Suite SHALL include tests that verify long-message splitting produces chunks within the Telegram length limit.
4. THE Test_Suite SHALL include tests that verify Database_Layer user, conversation, and memory logic against a temporary database.
5. WHEN the Test_Suite runs through pytest, THE Test_Suite SHALL complete without any test failure.

### Requirement 14: Clean import and boot verification

**User Story:** As a maintainer, I want the project to import and boot cleanly, so that the hardened code is confirmed runnable.

#### Acceptance Criteria

1. WHEN every first-party module of the Bot is imported with the required Environment_Variable values present, THE Bot SHALL complete those imports without raising an error.
2. WHEN the Bot startup routine runs with the required Environment_Variable values present, THE Bot SHALL initialize the Database_Layer and the downloads directory without raising an error.
