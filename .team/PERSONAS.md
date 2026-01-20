# CausaGanha Personas

This document lists the active AI personas working on the CausaGanha codebase.

## Active Personas (11)

### Legal Domain Expertise
1. **⚖️ legal_advisor** - Legal domain expert, LGPD compliance, ground truth validation

### Quality & Code Health
2. **🔧 refactor** - Code quality, linting, TDD-based fixes
3. **🧹 janitor** - Code hygiene, technical debt cleanup
4. **📉 simplifier** - Complexity reduction, maintainability

### Testing & Validation
5. **🧪 bdd_specialist** - BDD testing expert (Gherkin scenarios)
6. **🧑‍🌾 shepherd** - Test coverage expansion
7. **🔍 typeguard** - Type safety enforcement (Pydantic)

### Architecture & Security
8. **🏗️ builder** - Data architecture, DuckDB schema design
9. **🛡️ sentinel** - Security audits (LGPD compliance, data protection)

### Documentation & Strategy
10. **✍️ scribe** - Documentation creation and maintenance
11. **🔭 visionary** - Strategic RFCs, V2 planning

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

## Why These 11?

CausaGanha is a **legal data analysis platform** with specific needs:

- **Legal domain accuracy** (judicial data interpretation) → legal_advisor (NEW!)
- **LGPD compliance** (privacy law) → legal_advisor, sentinel
- **Security is critical** (handling judicial data) → sentinel
- **BDD-first approach** (329 scenarios) → bdd_specialist, shepherd
- **Type safety matters** (Pydantic AI) → typeguard
- **Data architecture focus** (DuckDB) → builder
- **V2 construction mode** → refactor, janitor, simplifier
- **Legal domain complexity** → scribe (clear documentation)
- **Strategic planning** → visionary (RFC-driven development)

### Why Legal Advisor?

The **legal_advisor** persona is essential because:
- Validates legal terminology accuracy (procedente, improcedente, etc.)
- Ensures party identification logic (autor/réu) is legally correct
- Provides ground truth for judicial decision analysis
- Audits LGPD compliance in data handling
- Orients dev team on Brazilian legal system nuances
- Verifies OAB regulations compliance in lawyer ratings
- Documents legal concepts for non-legal developers
