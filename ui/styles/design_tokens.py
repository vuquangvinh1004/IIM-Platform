"""Design tokens for the IIMP shell.

These tokens mirror the product-level DESIGN.md and provide a single owner
for shell-level visual decisions used by QSS.
"""
from __future__ import annotations


COLORS = {
    "background": "#F3F0E8",
    "on_background": "#1E2B36",
    "surface": "#FBF9F4",
    "on_surface": "#22313D",
    "surface_container_low": "#F6F2EA",
    "surface_container": "#ECE6DB",
    "surface_container_high": "#E2DBCF",
    "surface_container_highest": "#D7CDBF",
    "surface_variant": "#E9E2D6",
    "outline": "#A79A8B",
    "outline_variant": "#D8D0C4",
    "primary": "#173A5E",
    "on_primary": "#FFFFFF",
    "primary_container": "#2C618D",
    "secondary": "#1F6B5D",
    "on_secondary": "#FFFFFF",
    "secondary_container": "#D9EEE8",
    "on_secondary_container": "#123F36",
    "tertiary": "#8D571C",
    "on_tertiary": "#FFFFFF",
    "tertiary_container": "#F4DCBE",
    "on_tertiary_container": "#5E3811",
    "error": "#B0413E",
    "on_error": "#FFFFFF",
    "error_container": "#F6DBDA",
    "on_error_container": "#5D1F1D",
    "success": "#2F7A55",
    "on_success": "#FFFFFF",
    "success_container": "#DCEEDB",
    "warning": "#B36A1F",
    "on_warning": "#FFFFFF",
}

FONTS = {
    "display": '"Aptos Display", "Segoe UI Variable Display", "Segoe UI"',
    "body": '"Aptos", "Segoe UI Variable Text", "Segoe UI"',
    "label": '"Bahnschrift", "Segoe UI Semibold", "Segoe UI"',
}

RADII = {
    "sm": 6,
    "md": 10,
    "lg": 16,
    "xl": 24,
    "pill": 999,
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 20,
    "xl": 32,
    "xxl": 48,
}


def rgba(hex_color: str, alpha: int) -> str:
    """Convert a ``#RRGGBB`` color into a QSS-friendly ``rgba(...)`` string."""
    value = hex_color.lstrip("#")
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"