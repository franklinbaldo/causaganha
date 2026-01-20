## ⚡ 2025-12-24 - Frontmatter Parsing Optimization
**Observation:** The `sync_authors_from_posts` function in `src/egregora/utils/filesystem.py` used `frontmatter.load()`, which I suspected was inefficiently reading entire large markdown files just to get the metadata.

**Action:**
1.  I wrote a performance test using `pytest-benchmark` to establish a baseline.
2.  I implemented a custom helper function, `_load_frontmatter_only`, to read the file stream and stop after the closing `---` delimiter.
3.  I benchmarked the new implementation against the original.

**Result:** The benchmark showed no significant performance improvement, even after increasing the test file sizes to 1MB. Upon investigation, I discovered that the `python-frontmatter` library already uses an efficient regex-based approach to split the frontmatter from the content without reading the whole file into memory for parsing. My optimization was therefore redundant.

**Learning:** Always verify assumptions about third-party library performance before implementing custom optimizations. The existing solution was already efficient. I reverted all changes and removed the new test file.
