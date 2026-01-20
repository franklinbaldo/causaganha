---
title: "💣 Structured Exceptions for WhatsApp Media Delivery"
date: 2025-12-26
author: "Sapper"
emoji: "💣"
type: journal
---

## 💣 2025-12-26 - Summary

**Observation:** The `deliver_media` method in `src/egregora/input_adapters/whatsapp/adapter.py` was a prime example of the "Look Before You Leap" anti-pattern. It swallowed critical errors like `zipfile.BadZipFile`, `KeyError`, and `OSError`, returning `None` instead of raising an exception. This forced the caller to handle nullable returns and completely obscured the root cause of failures, violating the "Trigger, Don't Confirm" principle.

**Action:** I executed a full Test-Driven Development refactoring.
1.  **Established Hierarchy:** I created a new `MediaDeliveryError` exception hierarchy in `src/egregora/input_adapters/whatsapp/exceptions.py`, with specific exceptions like `InvalidMediaReferenceError`, `MissingZipPathError`, `ZipPathNotFoundError`, `MediaNotFoundError`, and `MediaExtractionError`.
2.  **RED (Tests):** I created a new test file, `tests/unit/input_adapters/whatsapp/test_adapter.py`, and wrote a suite of failing tests that asserted the new, specific exceptions were raised under various failure conditions.
3.  **GREEN (Refactor):** I refactored `deliver_media` and its helpers to remove all nullable returns and defensive checks. They now raise the new, context-rich exceptions, preserving the original stack trace with `raise ... from e`.
4.  **Updated Contract:** I changed the method's type hint from `-> Document | None` to `-> Document`, making the non-nullable return contract explicit.

**Reflection:** This was a successful mission, hardening a critical data ingestion pathway. The failure modes are now explicit, structured, and informative. The `parse` method in the same `adapter.py` file still has some general exception handling (`except WhatsAppParsingError as e: ... raise`). While it re-raises the exception, a future session could investigate if there's an opportunity to provide even more specific context at the adapter level, perhaps by wrapping it in an `AdapterParsingError` that includes the `input_path`. This would provide a consistent error-handling contract for all methods on the adapter.
