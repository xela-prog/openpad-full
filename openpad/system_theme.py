import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

OMARCHY_CURRENT = Path.home() / ".config" / "omarchy" / "current"
OMARCHY_NAME_FILE = OMARCHY_CURRENT / "theme.name"
OMARCHY_COLORS = OMARCHY_CURRENT / "theme" / "colors.toml"

OMARCHY_TO_OPENPAD = {
    "gruvbox":              "gruvbox",
    "everforest":           "everforest",
    "kanagawa":             "kanagawa",
    "nord":                 "nord",
    "tokyo-night":          "tokyonight",
    "catppuccin":           "catppuccin",
    "catppuccin-latte":     "catppuccin-latte",
    "rose-pine":            "rose-pine",
    "white":                "white",
}


def detect_system_theme() -> dict:
    """Detect system color scheme and return an 19-slot OpenPad theme dict."""
    if OMARCHY_NAME_FILE.exists():
        name = OMARCHY_NAME_FILE.read_text().strip().lower()
        if name in OMARCHY_TO_OPENPAD:
            from openpad.themes import THEMES
            mapped = OMARCHY_TO_OPENPAD[name]
            if mapped in THEMES:
                return dict(THEMES[mapped])

    if OMARCHY_COLORS.exists():
        palette = _parse_omarchy_colors(OMARCHY_COLORS)
        if palette:
            return _map_omarchy_to_openpad(palette)

    mode = _detect_light_dark()
    return _get_fallback_palette(mode)


def _parse_omarchy_colors(path: Path) -> Optional[dict]:
    try:
        content = path.read_text()
        colors = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("[") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value.startswith("#") and len(value) == 7:
                colors[key] = value
        return colors if colors else None
    except Exception:
        return None


def _map_omarchy_to_openpad(c: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in c:
                return c[k]
        return "#000000"

    return {
        "bg":            get("background"),
        "bg_panel":      get("color0"),
        "bg_element":    get("color8"),
        "border":        get("color0"),
        "border_active": get("accent"),
        "text":          get("foreground"),
        "text_muted":    get("color8"),
        "primary":       get("accent"),
        "secondary":     get("color4"),
        "accent":        get("color5"),
        "success":       get("color2"),
        "error":         get("color1"),
        "warning":       get("color3"),
        "syntax_kw":     get("color5"),
        "syntax_fn":     get("color4"),
        "syntax_str":    get("color2"),
        "syntax_num":    get("color3"),
        "syntax_cmt":    get("color8"),
        "syntax_type":   get("color6"),
    }


def _detect_light_dark() -> str:
    if sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2,
            )
            return "dark" if r.stdout.strip() == "Dark" else "light"
        except Exception:
            return "dark"

    elif sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            winreg.CloseKey(k)
            return "light" if v == 1 else "dark"
        except Exception:
            return "dark"

    else:
        try:
            r = subprocess.run(
                ["gdbus", "call", "--session",
                 "--dest", "org.freedesktop.portal.Desktop",
                 "--object-path", "/org/freedesktop/portal/desktop",
                 "--method", "org.freedesktop.portal.Settings.Read",
                 "org.freedesktop.appearance", "color-scheme"],
                capture_output=True, text=True, timeout=2,
            )
            if "uint32 1" in r.stdout:
                return "dark"
            if "uint32 0" in r.stdout:
                return "light"
        except Exception:
            pass
        try:
            r = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2,
            )
            if "'prefer-dark'" in r.stdout:
                return "dark"
        except Exception:
            pass
        return "dark"


def _get_fallback_palette(mode: str) -> dict:
    if mode == "light":
        return {
            "bg":           "#ffffff",
            "bg_panel":     "#f6f8fa",
            "bg_element":   "#eaeef2",
            "border":       "#d0d7de",
            "border_active":"#0969da",
            "text":         "#1f2328",
            "text_muted":   "#656d76",
            "primary":      "#0969da",
            "secondary":    "#1a7f37",
            "accent":       "#8250df",
            "success":      "#1a7f37",
            "error":        "#cf222e",
            "warning":      "#9a6700",
            "syntax_kw":    "#8250df",
            "syntax_fn":    "#0969da",
            "syntax_str":   "#1a7f37",
            "syntax_num":   "#9a6700",
            "syntax_cmt":   "#656d76",
            "syntax_type":  "#0550ae",
        }
    return {
        "bg":           "#0d1117",
        "bg_panel":     "#161b22",
        "bg_element":   "#21262d",
        "border":       "#30363d",
        "border_active":"#58a6ff",
        "text":         "#c9d1d9",
        "text_muted":   "#8b949e",
        "primary":      "#58a6ff",
        "secondary":    "#3fb950",
        "accent":       "#bc8cff",
        "success":      "#3fb950",
        "error":        "#f85149",
        "warning":      "#d29922",
        "syntax_kw":    "#bc8cff",
        "syntax_fn":    "#58a6ff",
        "syntax_str":   "#3fb950",
        "syntax_num":   "#d29922",
        "syntax_cmt":   "#8b949e",
        "syntax_type":  "#76e3ea",
    }
