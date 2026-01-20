---
title: "⚡ Text Normalization Optimization Attempt"
date: 2025-12-31
author: "Bolt"
emoji: "⚡"
type: journal
---

## ⚡ 2025-12-31 - Summary

**Observation:** The `_normalize_text` function in `src/egregora/input_adapters/whatsapp/parsing.py` used a regex to remove invisible characters. Based on my past experience, I hypothesized that `str.translate` would be more performant.

**Action:**
1.  I followed a strict TDD approach, first writing a correctness test and a `pytest-benchmark` test.
2.  I implemented the optimization, replacing the `re.sub` call with `str.translate`.
3.  I ran the benchmarks and compared the results.

**Result:** The benchmark showed that the `str.translate` implementation was slightly slower on the "happy path" (no invisible characters) and significantly slower when invisible characters were present. The original `re.sub` implementation was more performant in both cases.

**Learning:** This was another valuable lesson in the limits of optimization. While `str.translate` is often faster than `re.sub`, it's not a universal rule. The overhead of the translation table and the function call itself can negate the gains, especially for simple substitutions. I reverted all changes and kept the original, more performant implementation.

**Reflection:** I need to be more critical of my assumptions and rely on data-driven decisions. In the future, I will focus on optimizations that are more likely to have a significant impact, such as I/O-bound operations or algorithmic improvements, rather than micro-optimizations that may not yield the expected results.
