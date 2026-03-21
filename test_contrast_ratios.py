#!/usr/bin/env python3
"""Test contrast ratios for causaganha dashboard colors against WCAG AA standards.
WCAG AA requires:
- 4.5:1 for normal text
- 3:1 for large text (18pt+ or 14pt+ bold)
- 3:1 for UI components and borders.
"""


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb):
    """Calculate relative luminance according to WCAG formula."""
    r, g, b = [x / 255.0 for x in rgb]

    def adjust(c):
        if c <= 0.03928:
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


def test_contrast(name, foreground, background, required_ratio=4.5):
    """Test if contrast ratio meets requirement."""
    ratio = contrast_ratio(foreground, background)
    return ratio >= required_ratio


# Background colors
bg_black = "#050505"
bg_card = "#0f0f0f"

test_contrast("cyber-text on black", "#f0f0f0", bg_black, 4.5)
test_contrast("cyber-text on card", "#f0f0f0", bg_card, 4.5)
test_contrast("cyber-muted on black", "#b0b0b0", bg_black, 4.5)
test_contrast("cyber-muted on card", "#b0b0b0", bg_card, 4.5)
test_contrast("cyber-gray on black", "#7c7c7c", bg_black, 4.5)
test_contrast("cyber-gray on card", "#7c7c7c", bg_card, 4.5)

test_contrast("cyber-primary (green) on black", "#00ff41", bg_black, 4.5)
test_contrast("cyber-secondary on black", "#00cc33", bg_black, 4.5)
test_contrast("cyber-danger on black", "#ff3333", bg_black, 4.5)
test_contrast("cyber-warning on black", "#ffaa00", bg_black, 4.5)

test_contrast("cyber-border on card", "#5f5f5f", bg_card, 3.0)
