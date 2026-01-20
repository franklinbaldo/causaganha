---
title: "🛡️ Added Regression Test for SSRF Error Masking"
date: 2025-12-26
author: "Sentinel"
emoji: "🛡️"
type: journal
---

## 🛡️ 2025-12-26 - Summary

**Observation:** I suspected that a generic exception handler in the `download_avatar_from_url` function might be masking specific SSRF-related error messages. If an attacker attempted an SSRF attack via a redirect, the logs would show a generic download failure, hiding the security event.

**Action:** I wrote a new security test in `tests/security/test_avatar_security.py` to explicitly simulate this attack vector. The test used `respx` to mock a public URL that redirects to a blocked private IP. I asserted that the specific SSRF error message was propagated. The test passed, proving that the existing implementation using an `httpx` request hook was already correctly handling this case.

**Reflection:** Although no vulnerability was found, the addition of this regression test hardens the codebase. It now explicitly prevents future code changes from accidentally introducing this error-masking bug. It's a valuable reminder that security tests should not only check that an attack is blocked, but also that it is logged and reported correctly.
