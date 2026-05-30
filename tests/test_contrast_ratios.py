#!/usr/bin/env python3

"""Test contrast ratios for causaganha dashboard colors against WCAG AA standards.
WCAG AA requires:
- 4.5:1 for normal text
- 3:1 for large text (18pt+ or 14pt+ bold)
- 3:1 for UI components and borders.
"""

import pytest

WCAG_SRGB_LUMINANCE_THRESHOLD = 0.03928


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb):
    """Calculate relative luminance according to WCAG formula."""
    r, g, b = [x / 255.0 for x in rgb]

    def adjust(c):
        if c <= WCAG_SRGB_LUMINANCE_THRESHOLD:
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


# Legacy dark dashboard colors.
BG_BLACK = "#050505"
BG_CARD = "#0f0f0f"

# Canonical modernist tokens from web/src/styles/tokens.css.
MODERN_LIGHT = {
    "--color-paper-00": "#FBF8F1",
    "--color-paper-10": "#F5F1E8",
    "--color-paper-20": "#EDE7D8",
    "--color-text-modern": "#2E2A24",
    "--color-text-muted": "#6B6455",
    "--color-text-heading": "#1A1814",
    "--color-danger-modern": "#C8472E",
    "--color-warning-modern-deep": "#7A5818",
}

MODERN_DARK = {
    "--color-paper-00": "#103025",
    "--color-paper-10": "#0A2118",
    "--color-paper-20": "#051711",
    "--color-text-modern": "#C8DCCB",
    "--color-text-muted": "#7AA38B",
    "--color-text-heading": "#EAF2E5",
    "--color-danger-modern": "#E55A40",
    "--color-warning-modern": "#E6BC68",
}


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


@pytest.mark.parametrize(
    ("foreground_token", "background_token"),
    [
        ("--color-text-modern", "--color-paper-10"),
        ("--color-text-muted", "--color-paper-10"),
        ("--color-text-heading", "--color-paper-00"),
        ("--color-danger-modern", "--color-paper-00"),
        ("--color-warning-modern-deep", "--color-paper-00"),
    ],
)
def test_modern_light_tokens_meet_wcag(foreground_token, background_token):
    ratio = contrast_ratio(MODERN_LIGHT[foreground_token], MODERN_LIGHT[background_token])
    assert ratio >= 4.5, f"Contrast {foreground_token} on {background_token}: {ratio:.2f} < 4.5"


@pytest.mark.parametrize(
    ("foreground_token", "background_token"),
    [
        ("--color-text-modern", "--color-paper-10"),
        ("--color-text-muted", "--color-paper-10"),
        ("--color-text-heading", "--color-paper-00"),
        ("--color-danger-modern", "--color-paper-10"),
        ("--color-warning-modern", "--color-paper-20"),
    ],
)
def test_modern_dark_tokens_meet_wcag(foreground_token, background_token):
    ratio = contrast_ratio(MODERN_DARK[foreground_token], MODERN_DARK[background_token])
    assert ratio >= 4.5, f"Contrast {foreground_token} on {background_token}: {ratio:.2f} < 4.5"
