---
title: "⚒️ Fix Broken Navigation Links"
date: 2025-12-24
author: "Forge"
emoji: "⚒️"
type: journal
---

## ⚒️ 2025-12-24 - Fix Broken Navigation Links
**Observation:** The generated demo site had broken 'About' and 'Media' links in the main navigation. The root cause was twofold: the `about.md` template was not being rendered, and the `media/index.md` template was in the wrong directory, causing it to be generated at an incorrect path that didn't match the `mkdocs.yml` nav configuration.

**Action:** I corrected the site's template structure. I moved the `media` template directory from `src/egregora/rendering/templates/site/docs/media` to `src/egregora/rendering/templates/site/docs/posts/media`. This ensures the media index page is generated at the correct `posts/media/index.md` path, aligning it with the navigation links. I also confirmed the `about.md.jinja` template was present and would be correctly processed after a clean build, which proved to be the case. After regenerating the site, I verified that both `about.md` and `posts/media/index.md` were created in the correct locations, resolving the broken links.
