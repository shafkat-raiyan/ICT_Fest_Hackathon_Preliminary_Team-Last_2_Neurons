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
