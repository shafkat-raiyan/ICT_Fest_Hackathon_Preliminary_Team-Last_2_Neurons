# Bug Report

<!-- Document each fixed bug below using the template from AGENTS.md.
     Keep entries ordered by bug number. Only include bugs you actually fixed. -->

## Bug 1: Access Token Lifetime
- **File/Line:** app/auth.py:50
- **Difficulty:** Easy
- **What was wrong:** The access token lifetime was calculated by multiplying the config value by 60, resulting in a 15-hour expiration instead of 15 minutes.
- **Why it broke behavior:** Violated Rule 8 (Access tokens expire in exactly 900 seconds).
- **Fix:** Removed the `* 60` multiplier when creating the timedelta.
- **Verified by:** [initials], via pytest (test_smoke.py core flow still works, token manually inspectable)

## Bug 2: Datetime offset dropped instead of converted to UTC
- **File/Line:** app/timeutils.py:13
- **Difficulty:** Medium
- **What was wrong:** `parse_input_datetime` called `dt.replace(tzinfo=None)` on
  offset-aware inputs, which strips the offset but keeps the wall-clock numbers
  instead of converting them to UTC.
- **Why it broke behavior:** Violated Rule 1. An input like
  `2030-01-01T15:00:00+06:00` was stored as `15:00` naive instead of `09:00`
  UTC, so all subsequent comparisons (conflict, quota window, availability) used
  the wrong instant.
- **Fix:** Replaced with `dt.astimezone(timezone.utc).replace(tzinfo=None)` so
  the offset is applied before the (naive-UTC) value is stored.
- **Verified by:** manual curl (booking with `+06:00` offset now returns
  `09:00:00+00:00`).

## Bug 3: Conflict check uses non-strict bounds (back-to-back rejected)
- **File/Line:** app/routers/bookings.py:50
- **Difficulty:** Medium
- **What was wrong:** `_has_conflict` used `b.start_time <= end and start <=
  b.end_time` (non-strict `<=`) instead of the spec's strict `<` comparison.
- **Why it broke behavior:** Violated Rule 3. Back-to-back bookings (one ending
  exactly when the other starts) were wrongly rejected as `ROOM_CONFLICT`,
  though the spec explicitly allows them.
- **Fix:** Changed `<=` to `<` on both bounds: `b.start_time < end and start <
  b.end_time`.
- **Verified by:** SR, via pytest script (back-to-back booking now succeeds,
  true overlap still returns 409 ROOM_CONFLICT).

## Bug 4: Booking window validation — grace window, missing min duration, missing end≤start guard
- **File/Line:** app/routers/bookings.py:86-94
- **Difficulty:** Medium
- **What was wrong:** Three issues: (1) `start <= now - timedelta(seconds=300)`
  gave a 5-minute past grace window; (2) no `end <= start` guard, so negative
  durations slipped through (`int(-1.0) == -1.0` passes whole-hours check, `-1 >
  8` is False); (3) `MIN_DURATION_HOURS` (1) was defined but never checked, so
  0-hour bookings passed.
- **Why it broke behavior:** Violated Rule 2 (start strictly future — no grace;
  end strictly after start; duration whole hours, min 1, max 8).
- **Fix:** Changed past check to `start <= now`; added `end <= start` guard;
  added `duration_hours < MIN_DURATION_HOURS` to the range check.
- **Verified by:** SR, via pytest script (past start, end==start, end<start,
  9-hour all return 400; valid 1h and 8h return 201).


