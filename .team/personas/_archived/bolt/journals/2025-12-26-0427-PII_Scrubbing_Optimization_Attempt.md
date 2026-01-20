---
title: "⚡ PII Scrubbing Optimization Attempt"
date: 2025-12-26
author: "Bolt"
emoji: "⚡"
type: journal
---

## ⚡ 2025-12-26 - PII Scrubbing Optimization
**Observation:** The `scrub_pii` function in `src/egregora/input_adapters/whatsapp/parsing.py` used two separate regex substitutions to redact emails and phone numbers, resulting in two passes over the input text. Based on my previous experience with "Regex Trie Optimization," I hypothesized that combining these into a single regex pass would improve performance.

**Action:**
1.  I followed a strict TDD approach, first writing a correctness test and a `pytest-benchmark` test.
2.  My initial benchmark with small, PII-dense data showed a performance *degradation*.
3.  I revised the benchmark to use larger, more realistic text with sparse PII.
4.  I ran a new baseline test on the original code, then re-ran the benchmark on my optimized single-pass implementation.

**Result:** The benchmark consistently showed that the single-pass implementation (mean: ~1.38ms) was approximately 26% slower than the original two-pass implementation (mean: ~1.09ms). The performance overhead of the more complex combined regex and the Python replacer function call outweighed the benefit of avoiding a second scan of the string.

**Learning:** This was a critical lesson in the limits of optimization. While combining regex patterns is often a valid strategy, the overhead of Python function calls within a `.sub()` operation can negate the gains, especially when the number of matches is low. The original, simpler two-pass approach was more performant in this real-world scenario. I reverted the production code to its original state but kept the new, more realistic benchmark test to prevent future performance regressions. Always benchmark with representative data.

**Reflection:** The initial assumption about the optimization was wrong. This highlights the importance of TDD and benchmarking. In the future, I will be more skeptical of optimizations that involve calling Python functions from within a regex substitution, especially for low-density patterns. I should investigate if there are more performant ways to achieve the same result, perhaps with more advanced regex features that don't require a Python callback.
