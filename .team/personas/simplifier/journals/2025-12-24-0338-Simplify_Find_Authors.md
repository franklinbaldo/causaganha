## 📉 2025-12-24 - Simplify `_find_authors_yml`
**Observation:** The `_find_authors_yml` function in `src/egregora/utils/filesystem.py` used a complex and brittle directory traversal loop to find the `.authors.yml` file. This made the code harder to understand and maintain.
**Action:** I replaced the traversal logic with a direct path calculation, assuming a standard project structure (`docs/posts/posts`). This simplifies the code significantly by relying on convention over complex discovery.
