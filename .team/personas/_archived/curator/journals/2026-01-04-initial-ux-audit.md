# Curator Journal: Initial UX Audit of Egregora MkDocs Blog

**Date**: 2026-01-04
**Persona**: Curator (UX/UI Designer)
**Task**: First comprehensive UX audit of generated MkDocs blog

## Context

This is my first pass as the Curator persona evaluating Egregora's MkDocs blog output. The demo site was generated (though AI content generation failed due to API permissions), which gave me a clean look at the baseline UX/UI before any content populates it.

## What I Audited

### Site Structure
- **Location**: `/home/user/egregora/demo/`
- **Configuration**: `demo/.egregora/mkdocs.yml`
- **Content**: `demo/docs/*.md`
- **Template Source**: `src/egregora/output_adapters/mkdocs/`

### Key Pages Reviewed
1. **Homepage** (`demo/docs/index.md`) - Entry point with empty state
2. **About** (`demo/docs/about.md`) - Explainer of the system
3. **MkDocs Configuration** (`demo/.egregora/mkdocs.yml`) - All UX decisions live here

## Critical Findings

### 🚨 HIGH PRIORITY Issues

#### 1. Missing Custom CSS File
**Impact**: High - Prevents any custom styling
**Evidence**: `mkdocs.yml` references `stylesheets/extra.css` but file doesn't exist
**User Impact**: Site uses only default Material theme, no custom UX improvements possible
**Recommendation**: Create `demo/docs/stylesheets/extra.css` with baseline improvements

#### 2. Generic Color Palette (Teal/Amber)
**Impact**: Medium-High - Branding and distinctiveness
**Evidence**: `theme.palette.primary: teal` and `accent: amber` are Material defaults
**User Impact**: Site looks like every other Material for MkDocs blog
**Recommendation**: Design custom palette reflecting "collective consciousness" theme

#### 3. Missing Favicon
**Impact**: Medium - Professional appearance
**Evidence**: No favicon configuration in theme
**User Impact**: Generic browser icon, unprofessional in bookmarks/tabs
**Recommendation**: Design and add custom favicon + apple-touch-icon

#### 4. Google Analytics Placeholder
**Impact**: Low-Medium - Broken feature or privacy concern
**Evidence**: `extra.analytics.property: "__GOOGLE_ANALYTICS_KEY__"` is a placeholder
**User Impact**: Either doesn't work or tracks without user knowing
**Recommendation**: Remove entirely (privacy-first) or make explicitly optional

### ⚠️ MEDIUM PRIORITY Issues

#### 5. Empty State Messaging
**Impact**: Medium - First impressions
**Evidence**: "No posts yet. Run `egregora write`" is functional but cold
**User Impact**: New users see technical command, not welcoming guidance
**Recommendation**: More engaging empty state with visual element

#### 6. Social Card Images (404 Errors)
**Impact**: Medium - Social sharing
**Evidence**: Build log shows 404 for og:image URLs
**User Impact**: Sharing on Twitter/Facebook shows no preview image
**Recommendation**: Debug social plugin image generation

#### 7. Navigation Structure
**Impact**: Low-Medium - Information architecture
**Evidence**: "Media" at top level, "Journal" exists but not in nav
**User Impact**: Media feels elevated beyond its importance
**Recommendation**: Restructure nav hierarchy

#### 8. Generic Site Name ("demo")
**Impact**: Low - Branding
**Evidence**: `site_name: demo` in mkdocs.yml
**User Impact**: No brand identity
**Recommendation**: Choose distinctive name (or let Egregora generate from data?)

## Template Architecture Discovery

**Key Finding**: Templates are NOT in separate `.md` or `.jinja2` files. They're embedded in Python code at:

- **Main adapter**: `src/egregora/output_adapters/mkdocs/adapter.py`
- **Scaffolding**: `src/egregora/output_adapters/mkdocs/scaffolding.py`
- **Site generator**: `src/egregora/output_adapters/mkdocs/site_generator.py`

This means UX changes require editing Python code, not template files. The Forge persona will need to modify these source files to implement UX improvements.

## Positive Observations

### ✅ What's Already Good

1. **Solid Foundation**: Material for MkDocs is an excellent choice
2. **Rich Features**: Navigation instant loading, search, dark mode all enabled
3. **Good Plugins**: Blog plugin, RSS, social cards, minification configured
4. **Accessibility**: Semantic nav features, TOC integration
5. **Clean Content**: About page is clear and well-structured
6. **Privacy-First**: UUID anonymization prominently explained

## Decisions Made (Autonomous)

### Decision 1: Create TODO.ux.toml (Not docs/ux-vision.md First)
**Why**: The prompt mentions both files, but TODO.ux.toml is actionable tasks while ux-vision.md is reference.
**Rationale**: Start with tactical (what needs fixing) before strategic (design system vision).
**Created**: `TODO.ux.toml` with 10 tasks (4 high, 4 medium, 2 low priority)

### Decision 2: Assigned Tasks to Forge vs. Curator
**Why**: Some tasks require code changes (Forge), others require design decisions (Curator).
**Rationale**:
- **Forge tasks**: Implement CSS, fix 404s, add favicon (code/files)
- **Curator tasks**: Color palette, analytics decision, UX vision (design)

### Decision 3: Prioritized Missing CSS as #1
**Why**: This blocks all other styling improvements.
**Rationale**: Fix the foundation before painting the walls.

### Decision 4: Analytics - Recommend Removal
**Why**: Privacy-first is a core value, and analytics are currently broken anyway.
**Rationale**: Simpler to remove than to make properly optional. Users can add later if needed.

### Decision 5: Did NOT Propose Human-Required Features
**Why**: Curator prompt emphasizes "100% autonomous generation".
**Rationale**: All proposed improvements can be populated by Egregora from data:
- Color palette: Generated from theme/mood analysis
- Site name: Generated from conversation topics
- Empty state: Template-driven, no manual input

## Tasks Created

Created `TODO.ux.toml` with:
- **4 high priority** tasks (missing CSS, color palette, favicon, analytics)
- **4 medium priority** tasks (empty state, social images, navigation, site name)
- **2 low priority** tasks (ux-vision.md, typography scale)

Each task includes:
- **WHY** it matters
- **WHAT** to change
- **HOW** to verify success
- **WHERE** files live
- Template source location

## Challenges Encountered

### Challenge 1: API Key Permissions
**Issue**: Demo generation failed with 403 Forbidden from Gemini API.
**Impact**: No actual blog posts to evaluate.
**Decision**: Evaluated empty state and scaffold instead. This was actually useful - exposed the baseline UX before content.

### Challenge 2: Finding Template Sources
**Issue**: Expected `.jinja2` or `.md` template files in `src/`, found Python code instead.
**Discovery**: Templates are embedded in Python source, not separate files.
**Decision**: Documented this in TODO.ux.toml for Forge's benefit.

### Challenge 3: Can't Actually View in Browser
**Issue**: Running as CLI agent, can't open browser to visually inspect.
**Workaround**: Read source files (mkdocs.yml, index.md, about.md) and analyzed configuration. Relied on build logs for 404 errors.

## Lessons Learned

### 1. Empty States Are Features
The "No posts yet" message is actually a feature worth improving, not just an error state. First impressions matter.

### 2. Configuration IS UX
The `mkdocs.yml` file contains almost all UX decisions - color palette, navigation structure, plugin enablement. Treating config as UX surface area.

### 3. Template Architecture Varies
Not all projects use separate template files. Egregora embeds templates in Python code, which is valid but requires coordinating with code-focused personas (Forge).

### 4. Autonomy Requires Research
Curator prompt emphasizes autonomy ("NEVER ask humans"). This required:
- Glob/grep searches to find template locations
- Reading build logs to identify issues
- Making decisions based on UX principles

### 5. TOMLtasks Require Precision
Each task in TODO.ux.toml needs to be self-contained with enough context for another persona (Forge) to implement without asking questions.

## Next Steps

1. **Forge implements high-priority tasks**: Missing CSS, favicon, social images
2. **Curator designs color palette**: Research "collective consciousness" themes, create palette
3. **Create docs/ux-vision.md**: Document design system as it evolves
4. **Iterate on lower-priority tasks**: Typography, navigation structure

## Metrics to Track (Future)

Once improvements are implemented, track:
- **Lighthouse Accessibility Score**: Target 90+
- **Lighthouse Performance**: Target <1s First Contentful Paint
- **Contrast Ratios**: WCAG AA minimum (4.5:1)
- **Build Warnings**: Target 0 warnings

## Meta: Curator Persona Effectiveness

**What worked well**:
- Autonomous decision-making (didn't get stuck asking for permission)
- Systematic evaluation (reviewed config, content, logs)
- Created actionable tasks with clear verification criteria

**What could improve**:
- Would benefit from actual browser inspection (screenshots?)
- Could use automated accessibility testing (axe-core, Lighthouse)
- Template architecture section in prompt could be clearer

---

**Curator's Note**: This was a successful first audit. The site has a solid foundation (Material for MkDocs), but needs custom UX polish to match Egregora's unique "collective consciousness" positioning. The TODO.ux.toml now serves as a roadmap for the Forge persona to implement improvements.
