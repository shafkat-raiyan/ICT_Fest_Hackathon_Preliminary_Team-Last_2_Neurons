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

## Bug 5: get_booking overwrites start_time with created_at
- **File/Line:** app/routers/bookings.py:169
- **Difficulty:** Easy
- **What was wrong:** `response["start_time"] = iso_utc(booking.created_at)`
  overwrote the booking's `start_time` with its `created_at` timestamp.
- **Why it broke behavior:** `GET /bookings/{id}` returned the wrong
  `start_time` value, diverging from the create response and Rule 2/contract.
- **Fix:** Removed the line so `serialize_booking`'s `start_time` is preserved.
- **Verified by:** SR, via pytest (detail `start_time` matches create
  `start_time`).

## Bug 6: Refund tier logic — 0% case returns 50%, and 48h boundary wrong
- **File/Line:** app/routers/bookings.py:200-209
- **Difficulty:** Medium
- **What was wrong:** (1) Used `notice_hours > 48` (int-truncated) instead of
  `≥ 48h`, so exactly 48h notice gave 50% instead of 100%. (2) The `else`
  branch (notice < 24h) returned `50` instead of `0`.
- **Why it broke behavior:** Violated Rule 6 refund tiers. Cancellations with
  <24h notice got 50% refund instead of 0%; exactly-48h notice got 50% instead
  of 100%.
- **Fix:** Replaced int-truncated `notice_hours` with direct `timedelta`
  comparisons: `notice >= 48h → 100`, `≥ 24h → 50`, `else → 0`.
- **Verified by:** SR, via pytest (72h→100%, 36h→50%, 10h→0%).

## Bug 7: Refund rounding uses banker's rounding + amount recomputed separately in RefundLog
- **File/Line:** app/routers/bookings.py:211, app/services/refunds.py:14-17
- **Difficulty:** Hard
- **What was wrong:** (1) `round()` in Python uses banker's rounding
  (round-half-to-even), but Rule 6 requires half-cents rounding up. (2) The
  cancel response computed `refund_amount_cents` via `round()` while
  `log_refund` recomputed it independently via float division + `int()`
  truncation — the two could diverge.
- **Why it broke behavior:** Violated Rule 6 ("half-cents rounding up" and "the
  amount returned by the cancel response must equal the amount stored in the
  RefundLog"). E.g. 50% of 1001 = 500.5 → `round()` gave 500, `int()` gave 500.
- **Fix:** Added shared `compute_refund_amount_cents()` using
  `Decimal.quantize(ROUND_HALF_UP)`; both cancel response and `log_refund` now
  call it so they always match.
- **Verified by:** SR, via pytest (50% of 1001 → 501; 50% of 1003 → 502;
  RefundLog amount == cancel response amount).

## Bug 8: Reference code generation is not atomic under concurrency
- **File/Line:** app/services/reference.py:17-21
- **Difficulty:** Hard
- **What was wrong:** `next_reference_code` read `_counter["value"]`, slept
  0.12s, then incremented — a classic read-modify-write race. Multiple
  concurrent threads read the same counter value during the sleep, producing
  duplicate reference codes.
- **Why it broke behavior:** Violated Rule 7 ("Every booking's
  `reference_code` is unique, including under concurrent creation").
- **Fix:** Replaced dict-counter + sleep with `itertools.count(1000)` guarded
  by a `threading.Lock` so each `next()` is atomic.
- **Verified by:** SR, via concurrency script (10 threads × 100 calls = 1000
  codes, all unique).

## Bug 9: Rate limiter is not atomic under concurrency
- **File/Line:** app/services/ratelimit.py:18-26
- **Difficulty:** Hard
- **What was wrong:** `record_and_check` read the bucket, trimmed it, slept
  0.1s, then appended and wrote back — a read-modify-write race. Concurrent
  threads all saw the same pre-append bucket state, so >20 requests could
  slip through in the 60s window.
- **Why it broke behavior:** Violated Rule 5 ("limited to 20 requests per
  rolling 60 seconds per user... must hold under concurrent requests").
- **Fix:** Wrapped the read-trim-append-write block in a `threading.Lock` so
  the check-and-record is atomic; removed the `sleep`.
- **Verified by:** SR, via concurrency script (40 concurrent requests →
  exactly 20 ok, 20 limited).




