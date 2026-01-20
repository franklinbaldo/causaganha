---
title: "🛡️ Historical Archive"
date: 2025-05-18
author: "Sentinel"
emoji: "🛡️"
type: journal
---

## 2025-05-18 - [HIGH] Stored XSS via WhatsApp Exports
**Vulnerability:** WhatsApp chat exports containing HTML/JS tags (e.g., `<script>`) were processed as plain text and rendered as raw HTML in the MkDocs output (due to `md_in_html` extension and default Markdown behavior), leading to Stored XSS.
**Learning:** Even when the primary input is text-based (chat logs), downstream components (Markdown renderers, LLMs) may interpret special characters as code or formatting. Trusting input fidelity can compromise output security.
**Prevention:** Sanitized input at the ingestion layer (`_normalize_text`) by HTML-escaping special characters. This ensures the data is stored safely and rendered as text, preventing execution while preserving the original visual content for the user.

## 2025-05-18 - [MEDIUM] Incomplete SSRF Blocklist
**Vulnerability:** The SSRF protection in `egregora.utils.network` blocked standard private ranges (RFC 1918) but missed `0.0.0.0/8` and other reserved networks (e.g., Carrier-Grade NAT, Test-Nets). On Linux systems, `0.0.0.0` often resolves to localhost, allowing attackers to bypass `127.0.0.0/8` filters and access internal services.
**Learning:** Blacklisting IP ranges is difficult to get right because of OS-specific behaviors (like 0.0.0.0 resolving to localhost) and obscure reserved ranges.
**Prevention:** Updated `DEFAULT_BLOCKED_IP_RANGES` to include `0.0.0.0/8`, `100.64.0.0/10`, and other IANA reserved ranges. Always use a comprehensive "deny-list" or, better yet, an "allow-list" of permitted CIDRs if possible.

## 2025-12-18 - [CRITICAL] Supply Chain Risk in Jules Scheduler
**Vulnerability:** The `jules_scheduler.yml` workflow executed code from an external repository (`franklinbaldo/jules_scheduler`), introducing a supply chain risk and opaque behavior.
**Learning:** Relying on external, unverified wrappers for simple API interactions adds unnecessary attack surface and complexity. "Wrap logic" often hides what is actually happening.
**Prevention:** Removed the external dependency entirely and replaced it with a local script (`scripts/run_scheduler.py`) that leverages the existing `.claude/skills/jules-api` client. This ensures all execution logic is owned and visible within the repository.

## 2025-12-18 - [CRITICAL] SQL Injection in DuckDB PRAGMA Statements
**Vulnerability:** The `get_table_columns` methods in both `SimpleDuckDBStorage` and `DuckDBStorageManager` constructed SQL queries using `f"PRAGMA table_info('{table_name}')"`. This allowed SQL injection via the `table_name` parameter because single quotes were used for interpolation without proper escaping, enabling attackers to break out of the string literal and execute arbitrary SQL commands (e.g., `DROP TABLE`).
**Learning:** DuckDB's `PRAGMA` statements do not support parameterized queries (e.g., `PRAGMA table_info(?)`), creating a trap for developers who might otherwise use parameters.
**Prevention:** Always use the `quote_identifier` utility to properly escape and double-quote identifiers when they must be interpolated into SQL strings. Never use single quotes for identifiers in f-strings.
