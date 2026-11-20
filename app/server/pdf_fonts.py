from __future__ import annotations
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def try_register_korean_fonts() -> dict:
    """Try to register Korean fonts if a ttf exists.

    Search order:
      1) ENV: ARTBIZ_FONT_REGULAR / ARTBIZ_FONT_BOLD (absolute paths)
      2) /app/assets/fonts/*.ttf  (mounted or bundled by user)
      3) /usr/share/fonts/* (if available in container)

    Returns dict: {regular: name, bold: name} if registered else {}.
    """
    candidates = []
    env_r = os.getenv("ARTBIZ_FONT_REGULAR")
    env_b = os.getenv("ARTBIZ_FONT_BOLD")
    if env_r and os.path.exists(env_r):
        candidates.append(("ArtBizKR", env_r))
    if env_b and os.path.exists(env_b):
        candidates.append(("ArtBizKR-Bold", env_b))

    # assets fonts
    from app.core.settings import PROJECT_ROOT
    assets_dir = str(PROJECT_ROOT / "assets" / "fonts")
    if os.path.isdir(assets_dir):
        for fn in os.listdir(assets_dir):
            if fn.lower().endswith(".ttf"):
                path = os.path.join(assets_dir, fn)
                name = os.path.splitext(fn)[0]
                candidates.append((name, path))

    # system fonts (best-effort)
    for root in ["/usr/share/fonts", "/usr/local/share/fonts"]:
        if os.path.isdir(root):
            for dirpath, _, files in os.walk(root):
                for fn in files:
                    if fn.lower().endswith(".ttf") and ("noto" in fn.lower() or "nanum" in fn.lower()):
                        path = os.path.join(dirpath, fn)
                        name = os.path.splitext(fn)[0]
                        candidates.append((name, path))

    registered = {}
    # prefer explicit env if present
    try:
        if env_r and os.path.exists(env_r):
            pdfmetrics.registerFont(TTFont("ArtBizKR", env_r))
            registered["regular"] = "ArtBizKR"
        if env_b and os.path.exists(env_b):
            pdfmetrics.registerFont(TTFont("ArtBizKR-Bold", env_b))
            registered["bold"] = "ArtBizKR-Bold"
    except Exception:
        registered = {}

    if registered:
        return registered

    # fallback: try any candidate pair
    reg_name = None
    bold_name = None
    for name, path in candidates:
        try:
            pdfmetrics.registerFont(TTFont(name, path))
            if reg_name is None:
                reg_name = name
            if bold_name is None and ("bold" in name.lower() or "bd" in name.lower()):
                bold_name = name
        except Exception:
            continue

    if reg_name:
        return {"regular": reg_name, "bold": bold_name or reg_name}

    return {}
