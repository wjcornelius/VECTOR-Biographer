# Cognitive Substrate GUI Package
"""
GUI components for the Voice Biographer system.
Optimized for TV display with large, readable fonts.
"""

from .main_window import MainWindow
from .styles import TV_SETTINGS, apply_tv_theme

__all__ = ['MainWindow', 'TV_SETTINGS', 'apply_tv_theme']
