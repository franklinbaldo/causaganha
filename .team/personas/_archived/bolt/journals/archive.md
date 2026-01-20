---
title: "⚡ Historical Archive"
date: 2024-05-23
author: "Bolt"
emoji: "⚡"
type: journal
---

## 2024-05-23 - [Unicode Normalization Redundancy]
**Learning:** `unicodedata.normalize("NFKC", ...)` automatically handles compatibility characters like `\u202f` (Narrow No-Break Space), converting them to standard spaces. Explicit `replace` calls after NFKC normalization are often redundant and wasteful (O(N) scans).
**Action:** Before implementing manual string replacements for unicode characters, check if they are covered by standard normalization forms.

## 2025-05-21 - [Efficient Frontmatter Parsing]
**Learning:** Reading entire files just to extract YAML frontmatter is a major performance bottleneck for large markdown files. Streaming the file and stopping after the second `---` delimiter avoids loading the full content into memory.
**Action:** Use `read_frontmatter_only` instead of `path.read_text()` when only metadata is needed from markdown files.

## 2025-10-27 - [Regex Compilation in Loops]
**Learning:** Dynamically constructing and compiling regexes inside a loop (even with small N) prevents Python's internal cache from being effective if the pattern string changes (e.g., iterating over a list of suffixes). Combining these into a single pre-compiled regex with `|` (OR) logic can yield massive speedups (observed ~8x).
**Action:** Always check loops that iterate over keywords to construct regexes. Pre-compile `|` joined patterns.

## 2025-10-27 - [Regex Trie Optimization]
**Learning:** Replacing a loop of M regex compilations and M searches (O(N*M)) with a single compiled regex using alternation `(a|b|c)` (O(N)) provided a 2200x speedup for text processing tasks. Python's regex engine optimizes alternations effectively.
**Action:** When performing bulk string replacements from a dynamic dictionary, compile a single regex with alternation instead of looping. Use `re.compile(r"\b(" + "|".join(map(re.escape, keys)) + r")\b")`.
## 2025-12-23 - [Path vs OS Path Performance]
**Learning:** For high-frequency loops (like processing 100k+ media references), instantiating `pathlib.Path` objects just to check a suffix is significantly slower (~5x) than using `os.path.splitext`.
**Action:** Use `os.path.splitext` for simple extension checks in hot paths, or pass strings instead of Path objects where rich Path functionality isn't needed.

## 2025-12-23 - [Regex vs Translate Performance]
**Learning:** `str.translate` is faster than `re.sub` for character removal ONLY if the string is empty of targets. If targets exist, `re.sub` (compiled) is 10x faster due to optimized C implementation for replacements vs Python string builder overhead.
**Action:** Stick to compiled Regex for sanitization unless you are certain the 'happy path' (no replacements) is 99.9% of cases AND the penalty for the 'sad path' is acceptable.
