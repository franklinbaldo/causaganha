title = "Consolidate CSS and Fix Shadowing Bug"
status = "todo"
tags = ["ux", "frontend", "bug"]
priority = "high"
assignee = "forge"
author = "curator"

[description]
summary = "The CSS architecture is fragmented, causing the 'Portal' theme styles in `docs/` to shadow the structural layout styles in `overrides/`, breaking the homepage navigation and post card rendering."
context = """
MkDocs prioritizes files in `docs/` over `overrides/`.
Currently, `src/egregora/rendering/templates/site/docs/stylesheets/extra.css` (Portal Theme) overwrites `src/egregora/rendering/templates/site/overrides/stylesheets/extra.css` (Structure/Layout).
This results in missing styles for `.homepage-navigation`, `.nav-card`, and incorrect styling for `.post-card-modern` (which expects `.md-post--card` styles or similar).
"""

[spec]
bdd = """
Given the fragmented CSS architecture
When I merge the content of `src/egregora/rendering/templates/site/docs/stylesheets/extra.css` INTO `src/egregora/rendering/templates/site/overrides/stylesheets/extra.css`
And I ensure that `.md-post--card` styles are applied to `.post-card-modern` (or classes are unified)
And I delete the redundant `src/egregora/rendering/templates/site/docs/stylesheets/extra.css`
Then the generated site should display correct styles for BOTH the 'Portal' visual theme AND the homepage layout components (navigation, cards).
"""

[implementation]
files = [
    "src/egregora/rendering/templates/site/overrides/stylesheets/extra.css",
    "src/egregora/rendering/templates/site/docs/stylesheets/extra.css"
]
