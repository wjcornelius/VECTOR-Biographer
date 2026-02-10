# TV-Optimized Styles for Cognitive Substrate GUI
"""
Settings optimized for viewing on a TV from couch distance.
"""

import customtkinter as ctk

# TV Display Settings
TV_SETTINGS = {
    # Font sizes (larger for TV viewing - doubled for readability)
    'font_size_title': 32,
    'font_size_large': 28,
    'font_size_medium': 36,
    'font_size_small': 28,
    'font_size_tiny': 16,  # For compact buttons
    'font_size_status': 20,

    # Font family
    'font_family': 'Segoe UI',

    # Spacing
    'padding_large': 20,
    'padding_medium': 15,
    'padding_small': 10,
    'corner_radius': 12,

    # Component sizes
    'button_height': 45,
    'entry_height': 40,
    'scrollbar_width': 16,

    # Layout proportions
    'conversation_width_ratio': 0.60,
    'sidebar_width_ratio': 0.40,
    'bottom_panel_height': 200,
    'status_bar_height': 50,
}

# Color Theme (Dark mode for comfortable viewing)
COLORS = {
    # Backgrounds
    'bg_primary': '#1a1a2e',        # Deep blue-black
    'bg_secondary': '#16213e',      # Slightly lighter
    'bg_panel': '#0f3460',          # Panel background
    'bg_card': '#1f4068',           # Card/item background

    # Text
    'text_primary': '#e8e8e8',      # Main text
    'text_secondary': '#a0a0a0',    # Secondary text
    'text_accent': '#00d9ff',       # Highlighted text
    'text_muted': '#6b6b6b',        # Muted text

    # Accents
    'accent_primary': '#00d9ff',    # Cyan accent
    'accent_secondary': '#ff6b6b',  # Coral accent
    'accent_success': '#4ade80',    # Green for success
    'accent_warning': '#fbbf24',    # Yellow for warning

    # Borders
    'border_subtle': '#2a2a4e',
    'border_accent': '#00d9ff',

    # Special
    'recording_active': '#ff4444',  # Red recording indicator
    'memory_highlight': '#2d5a3d',  # Green highlight for memories
}

# Semantic colors for memory types
MEMORY_COLORS = {
    'self_knowledge': '#3b82f6',    # Blue
    'life_events': '#22c55e',       # Green
    'stories': '#f59e0b',           # Amber
    'relationships': '#ec4899',     # Pink
    'fears': '#ef4444',             # Red
    'wisdom': '#8b5cf6',            # Purple
    'decisions': '#06b6d4',         # Cyan
    'mistakes': '#f97316',          # Orange
    'default': '#64748b',           # Slate
}

def get_font(size_key: str, bold: bool = False) -> tuple:
    """Get font tuple for CustomTkinter widgets."""
    size = TV_SETTINGS.get(f'font_size_{size_key}', TV_SETTINGS['font_size_medium'])
    weight = 'bold' if bold else 'normal'
    return (TV_SETTINGS['font_family'], size, weight)

def apply_tv_theme():
    """Apply the TV-optimized dark theme globally."""
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('blue')

def get_memory_color(table_name: str) -> str:
    """Get color for a specific memory type/table."""
    return MEMORY_COLORS.get(table_name, MEMORY_COLORS['default'])

# Font presets for easy access
FONTS = {
    'title': get_font('title', bold=True),
    'heading': get_font('large', bold=True),
    'body': get_font('medium'),
    'body_bold': get_font('medium', bold=True),
    'small': get_font('small'),
    'tiny': get_font('tiny'),  # For compact viz buttons
    'status': get_font('status'),
}
