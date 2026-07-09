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
