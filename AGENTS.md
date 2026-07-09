# AGENTS.md

## What this repo is

CoWork is a FastAPI coworking-space booking API. **This is a bug-fixing task.**
`README.md` is the authoritative spec/contract — the codebase contains
**intentional bugs that violate it**. Your job is to fix the code so it matches
the contract exactly; do not "improve" the contract. Grading is black-box
against `README.md` (paths, status codes, error codes, JSON field names, JWT
claims must be preserved verbatim).

When code and README disagree, **trust the README**.

## Commands

- Run service: `docker compose up --build` (port 8000; env `JWT_SECRET`,
  `DATABASE_URL` set in `docker-compose.yml`)
- Local tests: `pip install -r requirements.txt && pytest`
- Single test: `pytest tests/test_smoke.py::test_core_flow`
- No lint, typecheck, formatter, or CI config exists. No migrations.

## Architecture

- Entrypoint `app/main.py` → `app:app`. Tables are created on import via
  `Base.metadata.create_all(bind=engine)` — no migration scripts. SQLite single
  file at `DATABASE_URL` (default `./cowork.db`; container `/app/data/cowork.db`).
- Routers in `app/routers/` (`auth`, `rooms`, `bookings`, `admin`, `health`).
  Services in `app/services/` (`ratelimit`, `reference`, `refunds`, `stats`,
  `export`, `notifications`). `app/cache.py` holds in-memory response caches.
- Several pieces of state live **in process memory** and reset on restart:
  revoked access tokens (`app/auth.py:_revoked_tokens`), rate-limit buckets
  (`services/ratelimit.py`), reference counter (`services/reference.py`),
  room stats (`services/stats.py`), report/availability caches (`cache.py`).
  These are also **not thread-safe / not atomic** — relevant because the spec
  requires several invariants to hold under concurrent requests.

## Kinds of intentional bugs to hunt (verified present)

The bugs span the whole contract; don't assume one area is clean. Examples of
the patterns you'll find, not an exhaustive list:

- **Auth/JWT**: access-token lifetime uses wrong time units vs. spec's "exactly
  900 seconds"; logout blacklist checks the wrong JWT claim; refresh tokens are
  not actually single-use.
- **Booking window**: conflict check uses non-strict bounds (back-to-back must
  be allowed); past-`start_time` has a grace window (spec: none); missing
  minimum-duration and `end ≤ start` guards.
- **Listing**: wrong sort direction, wrong offset formula, hardcoded limit
  ignoring the `limit` param.
- **Detail/cancel**: a response field gets overwritten with the wrong value;
  refund-tier logic produces wrong percentages (incl. 0% case); rounding uses
  banker's rounding instead of "half-cents round up"; refund is logged before
  the booking status flip and with a separately recomputed amount.
- **Registration**: duplicate username returns the existing user instead of
  `409 USERNAME_TAKEN`.
- **Concurrency**: reference codes, conflict checks, quota, rate limit, and
  single-refund-per-cancel all rely on non-atomic in-memory state with `sleep`
  calls interspersed — the spec explicitly requires these to hold under
  concurrent requests.
- **Datetimes**: `timeutils.parse_input_datetime` drops `tzinfo` instead of
  converting offset → UTC (spec rule #1).

## Contest rules (from `ICT_Fest_Hackathon_Preliminary_Guideline.md`)

The guideline doc is the full problem statement; `README.md` is the contract.
Both describe the same rules — trust `README.md` for exact field names/codes, but
note these contest-only facts from the guideline:

- **Scoring**: Easy bugs = 3 pts, Medium = 5 pts, Hard = 10 pts.
- **Tie-breaker #1**: harder bugs solved ranks higher.
- **Tie-breaker #2**: a `bug_report.md` in the repo root (optional, manual
  eval). For each bug it should list: file(s)/line(s), what the bug was and why
  it caused wrong behavior, and how it was fixed. If you fix bugs, write this
  file — it costs little and only helps on ties.
- Submission: fork the starter, leave the fork network before editing, make the
  repo public within 1 hour of the competition end.

## bug_report.md template

Document each bug in `bug_report.md` (repo root) using this exact format:

```
## Bug N: [short name]
- **File/Line:** app/path/to/file.py:LINE
- **What was wrong:** [what the code did incorrectly]
- **Why it broke behavior:** [which Rule/contract it violated + observed effect]
- **Fix:** [what you changed]
- **Verified by:** [initials], via [manual curl / pytest / concurrency script]
```

- Keep entries ordered by bug number. One section per bug.
- Only include bugs you actually fixed; don't list unfixed issues.

## Constraints when fixing

- Preserve the exact API contract from `README.md` — paths, status codes, error
  codes (`ROOM_CONFLICT`, `QUOTA_EXCEEDED`, `RATE_LIMITED`, `ALREADY_CANCELLED`,
  `BOOKING_NOT_FOUND`, `ROOM_NOT_FOUND`, `FORBIDDEN`, `INVALID_BOOKING_WINDOW`,
  `USERNAME_TAKEN`, `INVALID_CREDENTIALS`, `UNAUTHORIZED`), JSON field names,
  and JWT claims (`sub`, `org`, `role`, `jti`, `iat`, `exp`, `type`).
- Multi-tenancy: users/admins may only ever see/act on their own org's data;
  cross-org IDs behave as non-existent → `404`.
- Datetimes are stored naive UTC; responses must carry an explicit UTC
  designator.
- If you add columns/tables, note SQLite won't migrate an existing `.db` file —
  delete the local `*.db` (it's gitignored) or rely on the fresh container
  volume.
