---
title: "🛡️ [MEDIUM] TOCTOU in Avatar Download"
date: 2025-12-25
author: "Sentinel"
emoji: "🛡️"
type: journal
---

## 🛡️ 2025-12-25 - [MEDIUM] Time-of-Check to Time-of-Use (TOCTOU) in Avatar Download
**Observation:** The `download_avatar_from_url` function in `src/egregora/agents/avatar.py` was vulnerable to a Time-of-Check to Time-of-Use (TOCTOU) attack. It first validated the avatar URL using `validate_public_url`, which performed a `HEAD` request to check the destination. Subsequently, it made a separate `GET` request to download the image content. An attacker could exploit the time gap between these two requests by serving a safe response for the `HEAD` check and then a redirect to a malicious, private URL for the `GET` request.

**Action:**
1.  **RED:** Wrote a failing test (`tests/unit/utils/test_network_sentinel.py`) that simulated the exploit using `respx` to prove the vulnerability. The test mocked a safe initial response and a malicious redirect on the subsequent download request.
2.  **GREEN:** Refactored the validation logic.
    *   Simplified `validate_public_url` in `src/egregora/utils/network.py` to only validate the IP of a single, given URL without following redirects.
    *   Moved the validation into an `httpx` `request` event hook within `download_avatar_from_url`. This ensures that every URL in a request chain (including the initial URL and any redirects) is validated just-in-time, immediately before the request is sent.
3.  **REFACTOR:** Ensured the new exploit test passed, confirming the vulnerability was closed. Updated a related, now-obsolete test in `test_network.py` to align with the new, more secure behavior of `validate_public_url`.

**Reflection:** Security validation that involves network resources must be performed as close to the time of use as possible. Separating checks (`HEAD` request) from actions (`GET` request) creates a window for race conditions. Using just-in-time validation mechanisms, like the `httpx` event hooks, is a robust pattern for mitigating TOCTOU vulnerabilities. The initial implementation's `response` hook was a good idea but insufficient; a `request` hook is required for true pre-send validation.
