# Source acquisition: traceable success, explicit failure

The new `research_ops` layer acquires public documents into a content-addressed local cache. It does **not** alter frozen packets, generate hypotheses or claim a live research service. It uses Python's maintained HTTPS and SQLite libraries rather than adding an ingestion service dependency.

## Acquire a filing pair

Use the existing Python environment. Choose a local cache and a **new** receipt path. Supply your own descriptive project/contact User-Agent; never imitate another organization or rotate identities to evade a denial.

```sh
python -m research_ops --cache artifacts/research_ops_cache --user-agent "Your research project contact@example.org" --receipt artifacts/pair-attempt.json annual-pair --cik 320193 --as-of 2026-10-14
```

The command fetches SEC submissions, validates parallel metadata arrays and selects the latest two eligible 10-Ks with distinct reporting periods. It excludes amendments and filings dated after the cutoff. It then fetches both primary documents. A partial acquisition remains `blocked` rather than a completed pair. Historical submissions may require a separately specified older-file workflow; the command does not invent missing filings or silently substitute forms.

Every successful source has a URL, SHA-256, bytes, media type, first/current retrieval time, last successful check time and available ETag/Last-Modified validators. A conditional HTTP 304 refreshes the check time without changing the document identity or original retrieval time. A changed 200 creates a new content-addressed blob; the former blob remains available. The attempt log records failures separately. SQLite handles are explicitly closed, including on Windows.

## Boundaries and recovery

- Only approved HTTPS hosts are allowed, including redirects. SEC hosts are the defaults; `--allow-host` requires an explicit additional host. Never add a host merely to evade source restrictions.
- One cache instance sends at most two requests per second. Use one sequential acquisition process; this is not a distributed/global rate limiter.
- Timeout/transport errors, 429 and selected 5xx responses get at most three attempts. Honor Retry-After; defer rather than retry early when the requested delay exceeds the bounded local wait. A 403 stops immediately.
- Reject invalid/empty/oversized payloads, unsupported media types, malformed JSON and known access-error pages returned with HTTP 200.
- Verify cached bytes before reuse. A corrupt blob stops the operation and is preserved for diagnosis; do not overwrite it under the same evidence identity.
- After a transient failure, rerun with the **same cache and a new receipt**. No prior successful check time is refreshed by a failure. Offline reads require an explicit maximum age and expose the latest failed attempt as well as the last successful check.
- Keep machine caches and study reviewer data out of Git. Publish source receipts only after checking their contents. Do not publish restricted news or licensed bodies.

Example bounded offline read:

```sh
python -m research_ops --cache artifacts/research_ops_cache --user-agent "Your research project contact@example.org" --receipt artifacts/cached-attempt.json cached https://data.sec.gov/submissions/CIK0000320193.json --max-age 3600
```

## What this establishes

Current acquisition timestamps establish what this client retrieved and checked now. Filtering a current SEC metadata response by filing date is **not** proof of historical point-in-time availability, unchanged document versions or an investable information set. Live source availability and analyst usefulness are separate evaluation gates.

The implementation has offline failure/recovery tests. [Live probe outcomes](source_acquisition_live_receipt.json) separately record a successful public control fetch/revalidation (HTTP 200 → 304) and an SEC submissions denial (HTTP 403). A blocked SEC probe must not be described as successful live filing ingestion.
