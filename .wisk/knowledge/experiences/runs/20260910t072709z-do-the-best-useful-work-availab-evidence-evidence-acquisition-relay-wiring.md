---
type: "RunEvidence"
id: "run-evidence/20260910t072709z-do-the-best-useful-work-availab/evidence-acquisition-relay-wiring"
run: "runs/20260910T072709Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "src/tse_processual/acquisition.py, tests/tse_processual/test_acquisition.py, deployment/relay/README.md, knowledge/backlog/issue-985.md"
summary: "RED: added tests/tse_processual/test_acquisition.py cases for _make_client()/_default_opener() (ImportError, functions didn't exist). GREEN: acquisition.py gained _make_client() (httpx.Client wired with common.relay.relay_transport_from_env(), same pattern as src/stj_acordaos/client.py and src/tjro_juris/client.py), a _StreamingResponse adapter exposing .read()/.geturl() to satisfy the pre-existing Opener contract, and download_official_zip()'s opener default switched from urllib.request.urlopen to this relay-aware _default_opener. Six new tests confirm: relay transport picked up only when RELAY_URL/RELAY_TOKEN set; direct connection otherwise; chunked streaming reproduces the exact payload; redirects are followed with geturl() reporting the true final hop; and critically, when relayed, geturl() still reports the real TSE URL (not the relay's own URL) -- verified first by hand against httpx+RelayTransport+MockTransport before writing it as a test, since download_official_zip()'s validate_official_url(final_url) call would silently break every relayed download otherwise. All 6 new tests plus the pre-existing 6 tse_processual/test_acquisition.py tests pass unmodified (they inject their own opener, untouched by this change). Updated deployment/relay/README.md and knowledge/backlog/issue-985.md's unblock_condition to document the new path without claiming it's live-verified (last_verified_run_id/last_verified_at deliberately left untouched -- no live network check was redone this round)."
goal: "run-goals/20260910t072709z-do-the-best-useful-work-availab/goal-tse-relay-wiring"
---

# RunEvidence
