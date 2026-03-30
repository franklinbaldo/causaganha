#!/usr/bin/env python3

MAGIC_VAL_0_03928 = 0.03928

"""Test contrast ratios for causaganha dashboard colors against WCAG AA standards.
WCAG AA requires:
- 4.5:1 for normal text
- 3:1 for large text (18pt+ or 14pt+ bold)
- 3:1 for UI components and borders.
"""

import pytest


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb):
    """Calculate relative luminance according to WCAG formula."""
    r, g, b = [x / 255.0 for x in rgb]

    def adjust(c):
        if c <= MAGIC_VAL_0_03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    r = adjust(r)
    g = adjust(g)
    b = adjust(b)

    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color1, color2):
    """Calculate contrast ratio between two colors."""
    lum1 = relative_luminance(hex_to_rgb(color1))
    lum2 = relative_luminance(hex_to_rgb(color2))

    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    return (lighter + 0.05) / (darker + 0.05)


# Background colors
BG_BLACK = "#050505"
BG_CARD = "#0f0f0f"


@pytest.mark.parametrize(
    ("foreground", "background", "required_ratio"),
    [
        ("#f0f0f0", BG_BLACK, 4.5),
        ("#f0f0f0", BG_CARD, 4.5),
        ("#b0b0b0", BG_BLACK, 4.5),
        ("#b0b0b0", BG_CARD, 4.5),
        ("#7c7c7c", BG_BLACK, 4.5),
        ("#7c7c7c", BG_CARD, 4.5),
        ("#00ff41", BG_BLACK, 4.5),
        ("#00cc33", BG_BLACK, 4.5),
        ("#ff3333", BG_BLACK, 4.5),
        ("#ffaa00", BG_BLACK, 4.5),
        ("#5f5f5f", BG_CARD, 3.0),
    ],
)
def test_contrast_meets_wcag(foreground, background, required_ratio):
    """Test if contrast ratio meets WCAG requirement."""
    ratio = contrast_ratio(foreground, background)
    assert ratio >= required_ratio, (
        f"Contrast {foreground} on {background}: {ratio:.2f} < {required_ratio}"
    )
