"""Validated appearance settings for Home media-type labels."""

import re

from app import config
from app.models import MediaTypes

HOME_MEDIA_TYPE_CHIP_TYPES = tuple(
    media_type.value
    for media_type in MediaTypes
    if media_type.value
    not in {
        MediaTypes.SEASON.value,
        MediaTypes.EPISODE.value,
        MediaTypes.COMIC_ISSUE.value,
    }
)
HOME_MEDIA_TYPE_CHIP_STYLES = {"solid", "soft", "outline"}
SRGB_LINEAR_THRESHOLD = 0.04045
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def default_media_type_chip_color(media_type: str) -> str:
    """Return the canonical media palette color used when no override exists."""
    media_config = config.get_config(media_type) or {}
    return media_config.get("stats_color", "#6B7280").upper()


def normalize_media_type_chip_colors(colors) -> dict[str, str]:
    """Keep only known media types with safe six-digit hexadecimal colors."""
    if not isinstance(colors, dict):
        return {}
    return {
        media_type: color.upper()
        for media_type, color in colors.items()
        if media_type in HOME_MEDIA_TYPE_CHIP_TYPES
        and isinstance(color, str)
        and HEX_COLOR_PATTERN.fullmatch(color)
    }


def media_type_chip_preferences(user, media_type: str) -> dict[str, str]:
    """Resolve a safe color, contrast color and style for one rendered label."""
    colors = normalize_media_type_chip_colors(user.home_media_type_chip_colors)
    color = colors.get(media_type, default_media_type_chip_color(media_type))
    style = user.home_media_type_chip_style
    if style not in HOME_MEDIA_TYPE_CHIP_STYLES:
        style = "soft"
    luminance = _relative_luminance(color)
    dark_contrast = (luminance + 0.05) / (_relative_luminance("#111827") + 0.05)
    light_contrast = 1.05 / (luminance + 0.05)
    contrast = "#111827" if dark_contrast >= light_contrast else "#FFFFFF"

    return {"color": color, "contrast": contrast, "style": style}


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= SRGB_LINEAR_THRESHOLD
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return sum(
        value * weight
        for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )
