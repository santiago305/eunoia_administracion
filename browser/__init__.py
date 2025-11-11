"""Adaptadores de navegador (Playwright/CDP)."""

from .cdp import connect_browser_over_cdp
from .login import ensure_login

__all__ = ["connect_browser_over_cdp", "ensure_login"]