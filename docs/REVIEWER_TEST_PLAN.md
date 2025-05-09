# Reviewer Test Plan

This document outlines the suggested steps a reviewer could take to verify the core functionality of the Event Integration Microservice, specifically focusing on data synchronization and API endpoint behavior as per `TASK.md`.

## Prerequisites

- [ ] Project's `README.md` has been followed for initial setup (dependencies installed, `.env` configured).
- [ ] Application services have been started successfully (via `make build && make up`).
- [ ] Reviewer has access to:
  - [ ] A terminal for running commands.
  - [ ] An API client (e.g., Postman, `curl`).
  - [ ] A PostgreSQL client (e.g., `psql`, DBeaver) or can use `docker exec` for `psql`.
  - [ ] The application logs (either via `docker logs` or files).
  - [ ] The provider's example XML responses from `TASK.md` for comparison.
  - [ ] Except for the tests, launch the application with `source .env && make build && make up` and curl http://localhost:8080/v1/health/ to ensure the application is running.

## Part 0: launch pytest

- **Action:** Launch pytest: `make clean && make build && make up test_env=true` and, in a new terminal, `source .env.test && poetry run pytest`
- **Expected Result:**
  - [ ] All tests pass.
- **Rationale:** Ensures the tests are working.

## Part 1: Initial Data Synchronization Verification

**Goal:** Verify that the system can fetch, parse, and store data from the provider correctly.

### [ ] Step 1.1: Identify Provider Configuration

- **Action:** Check the application's configuration (e.g., `.env` file, `config/settings.py` or equivalent based on project structure) to confirm the `PROVIDER_URL` (or equivalent primary provider URL) is set to the official challenge URL: `https://provider.code-challenge.feverup.com/api/events`.
- **Rationale:** Ensures testing against the correct data source.

### [ ] Step 1.2: Trigger/Observe Initial Sync

- ** Observe Scheduled Sync:** As the task is scheduled (via Celery Beat), check its schedule. The reviewer might need to wait for it to run or be informed on how to expedite this for testing or manually change the schedule.
- **Action (Logging):** While the sync is expected to run, monitor the Celery worker logs in real-time.
- **Expected Log Output:**
  - [ ] Messages indicating the `sync_provider_events` task has started for the configured provider(s).
  - [ ] Logs from `ProviderClient` showing attempts to fetch data (e.g., "Fetching events XML from provider...").
  - [ ] Logs indicating successful XML fetch from the provider.
  - [ ] Logs from the XML parser (e.g., "Successfully parsed X events..." or specific parsing errors if any part of the XML is problematic, detailing which part).
  - [ ] Logs from `EventRepository` (e.g., "Upserting X events...", "Marking Y stale events...").
  - [ ] Message indicating the task has completed successfully for each provider.
- **Rationale:** Confirms the sync mechanism is operational and provides insights into its progress and any immediate issues.

### [ ] Step 1.3: Database Verification (Post-Sync)

- **Action: Inspect the tables**

  - [ ] `SELECT * FROM events;` (will change as syncs are repeated along the three provider calls)
  - [ ] Verify the data in the tables matches XML.
  - [ ] Verify `ever_online` is `TRUE` if XML `sell_mode` was "online", `FALSE` otherwise.
  - [ ] Verify `first_seen_at` and `last_seen_at` are populated and look reasonable.
  - [ ] Verify `ever_online` changes according with the XML `sell_mode` and the live provider data.

- **Rationale:** Confirms accurate and complete persistence of XML data, including relationships and crucial flags like `ever_online`.

## Part 2: Test the `/events/search` API Endpoint

**Goal:** Verify the API endpoint functions according to the Swagger specification and requirements. The base URL for API calls will be assumed as `http://localhost:<port>` (e.g., `http://localhost:8080` if Nginx is on 8080) followed by `/v1/events/search`.

### [ ] Step 2.1: Basic Successful Query

- **Action:** `GET http://localhost:8080/v1/events/search?starts_at=2021-01-01T00:00:00Z&ends_at=2021-12-31T23:59:59Z` (adjust dates)
- **Expected Result:**
  - [ ] HTTP Status: `200 OK`.
  - [ ] Response Body (JSON): Adheres to `SuccessResponseSchema` from Swagger.
  - [ ] Verify event data in the response matches the data in the database.
- **Rationale:** Core functionality check for retrieving and formatting event data.

### [ ] Step 2.2: Query with No Results

- **Action:** `GET http://localhost:8080/v1/events/search?starts_at=2000-01-01T00:00:00Z&ends_at=2000-01-02T23:59:59Z` (a range with no expected data).
- **Expected Result:**
  - [ ] HTTP Status: `200 OK`.
  - [ ] Response Body: `{"data": {"events": []}, "error": null}`.
- **Rationale:** Ensures correct handling of empty result sets.

### [ ] Step 2.3: Query Parameter Validation - Invalid Date Range

- **Action:** `GET http://localhost:8080/v1/events/search?starts_at=2023-03-12T00:00:00Z&ends_at=2023-03-10T23:59:59Z` (`starts_at` after `ends_at`).
- **Expected Result:**
  - [ ] HTTP Status: `400 Bad Request`.
  - [ ] Response Body: Error object detailing the validation error.
- **Rationale:** Checks input validation for logical errors.

### [ ] Step 2.4: Query Parameter Validation - Missing Parameter

- **Action:** `GET http://localhost:8080/v1/events/search?starts_at=2023-03-10T00:00:00Z` (missing `ends_at`).
- **Expected Result:**
  - [ ] HTTP Status: `400 Bad Request`.
  - [ ] Response Body: Error object indicating `ends_at` is required.
- **Rationale:** Checks input validation for missing required fields.

### [ ] Step 2.5: Query Parameter Validation - Malformed Date

- **Action:** `GET http://localhost:8080/v1/events/search?starts_at=not-a-date&ends_at=2023-03-12T23:59:59Z`.
- **Expected Result:**
  - [ ] HTTP Status: `400 Bad Request`.
  - [ ] Response Body: Error object indicating `starts_at` is not a valid date format.
- **Rationale:** Checks input validation for data type/format errors.

## Part 3: Test "Real-world conditions" (from TASK.md)

### [ ] Step 3.1: Provider API Down/Slow

- **Action: Simulate provider outage.**
  - Temporarily change the `PROVIDER_URL` in the `.env` file to an invalid/unreachable address or one that simulates errors (e.g., `http://localhost:12345/nonexistent`).
  - Restart both the app and the celery worker for the config change to take effect.
- **Verification:**
  - [ ] Celery worker logs show `ProviderClient` attempting retries and eventually failing for that provider (logging connection errors, timeouts, or HTTP errors).
  - [ ] The sync task completes its attempt for that provider but does not crash.
  - [ ] Make API calls to `/v1/events/search` with valid parameters for data synced _before_ the outage.
  - [ ] The API endpoint _continues to work normally_, serving data from the database.
- **Rationale:** Tests resilience of the sync process and the decoupling of the API from live provider status, a key requirement.
- **Action: Restore provider URL**
  - Change `PROVIDER_URL` back to the correct one in `.env` and restart/reconfigure.
  - [ ] Trigger sync again and verify it can now fetch data.
