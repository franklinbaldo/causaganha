# Frontend Architecture Guide

The Astro + Svelte + Panda CSS frontend that this file used to describe was removed in #1715 ("reset web architecture to clean zero-backend DataJud static reader"). `web/` no longer has `src/`, a `package.json`, or any Node build.

The current frontend is a static page. See [`web/README.md`](web/README.md) for the architecture and `web/public/index.html` for the implementation. Query contracts are documented in [`web/queries/README.md`](web/queries/README.md).
