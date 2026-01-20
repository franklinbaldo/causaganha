# CausaGanha Personas

This document lists the active AI personas working on the CausaGanha codebase.

## Active Personas (10)

### Quality & Code Health
1. **🔧 refactor** - Code quality, linting, TDD-based fixes
2. **🧹 janitor** - Code hygiene, technical debt cleanup
3. **📉 simplifier** - Complexity reduction, maintainability

### Testing & Validation
4. **🧪 bdd_specialist** - BDD testing expert (Gherkin scenarios)
5. **🧑‍🌾 shepherd** - Test coverage expansion
6. **🔍 typeguard** - Type safety enforcement (Pydantic)

### Architecture & Security
7. **🏗️ builder** - Data architecture, DuckDB schema design
8. **🛡️ sentinel** - Security audits (LGPD compliance, data protection)

### Documentation & Strategy
9. **✍️ scribe** - Documentation creation and maintenance
10. **🔭 visionary** - Strategic RFCs, V2 planning

## Archived Personas

The following personas were archived as they're not needed for CausaGanha's current phase:

- absolutist (strict enforcement)
- artisan (code craftsmanship - overlaps with refactor)
- bolt (performance optimization - not critical for V2 yet)
- curator (UX/UI - not relevant for data platform)
- essentialist (pragmatic cuts - overlaps with simplifier)
- forge (feature implementation - too broad)
- franklin (user persona)
- lore (system historian)
- oracle (support agent)
- organizer (project organization - overlaps with janitor)
- sapper (exception handling - too specific)
- sheriff (test stability - overlaps with shepherd)
- streamliner (data optimization - overlaps with builder)

## Why These 10?

CausaGanha is a **legal data analysis platform** with specific needs:

- **Security is critical** (handling judicial data) → sentinel
- **BDD-first approach** (329 scenarios) → bdd_specialist, shepherd
- **Type safety matters** (Pydantic AI) → typeguard
- **Data architecture focus** (DuckDB) → builder
- **V2 construction mode** → refactor, janitor, simplifier
- **Legal domain complexity** → scribe (clear documentation)
- **Strategic planning** → visionary (RFC-driven development)
