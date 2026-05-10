"""AlphaBeast - main application.

Single-window CustomTkinter app to combine a user prompt with up to 16 mega prompts,
copy the result, send it to an AI provider, browse history and saved prompts.
"""
from __future__ import annotations

import logging
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

import config
from ai_providers import PROVIDERS, ProviderError, send_to_provider
from prompt_builder import build_ultimate_prompt
from updater import APP_VERSION as UPDATER_VERSION, updater

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

APP_TITLE = "AlphaBeast · Triskell Studio"
APP_W, APP_H = 1340, 880
BRAND_NAME = "TRISKELL STUDIO"
BRAND_VERSION = f"v{UPDATER_VERSION}"
BRAND_URL = "https://triskell-studio.fr"

# Triskell Studio design system — tokens copied from triskell-studio.fr/css/style.css
DARK_PALETTE = {
    # Base layers (darkest → lighter)
    "bg":            "#08080F",
    "panel":         "#08080F",   # alias for bg, used for top/footer
    "panel_alt":     "#0D0D1A",
    "panel_card":    "#0F0F1C",
    "tag_bg":        "#1A1A2E",
    "tag_bg_hover":  "#252540",
    "input_bg":      "#13131F",
    "border":        "#3D3D5A",
    "border_2":      "#4A4A66",

    # Brand triskell trio (the 3 spirals) — identiques en clair et sombre
    "indigo":        "#6366F1",
    "indigo_dk":     "#4F46E5",
    "violet":        "#8B5CF6",
    "orange":        "#F97316",

    # Aliases used across the app
    "accent":        "#6366F1",   # primary CTA = indigo (matches site nav)
    "accent_hover":  "#4F46E5",
    "accent_dim":    "#312E81",   # indigo-900 for badges
    "brand":         "#8B5CF6",   # violet for logo accents
    "brand_glow":    "#A78BFA",

    # Status & utility
    "danger":        "#EF4444",
    "ok":            "#10B981",
    "warn":          "#F59E0B",
    "pink":          "#EC4899",
    "cyan":          "#06B6D4",

    # Text
    "text_strong":   "#FFFFFF",   # texte fort sur surfaces panel (titres, wordmark)
    "text":          "#E2E8F0",
    "tag_fg":        "#E2E8F0",
    "muted":         "#94A3B8",
    "muted_dim":     "#64748B",
}

LIGHT_PALETTE = {
    # Base layers (light surfaces, soft layered greys)
    "bg":            "#F4F4F8",
    "panel":         "#FFFFFF",
    "panel_alt":     "#FFFFFF",
    "panel_card":    "#F7F7FB",
    "tag_bg":        "#EEF0F4",
    "tag_bg_hover":  "#E2E5EE",
    "input_bg":      "#FFFFFF",
    "border":        "#D6DAE3",
    "border_2":      "#C2C7D2",

    # Brand triskell trio — versions désaturées en mode clair (les versions
    # vives qui marchent sur fond noir deviennent agressives sur blanc).
    "indigo":        "#4F46E5",   # indigo-600 (plus profond)
    "indigo_dk":     "#4338CA",
    "violet":        "#6D28D9",   # violet-700 — beaucoup moins flashy que #8B5CF6
    "orange":        "#EA580C",   # orange-600 — un cran plus dense

    "accent":        "#4F46E5",
    "accent_hover":  "#4338CA",
    "accent_dim":    "#E0E7FF",   # indigo-100 pour fond léger de hover
    "brand":         "#6D28D9",
    "brand_glow":    "#7C3AED",   # violet-600, lisible sur blanc

    "danger":        "#DC2626",
    "ok":            "#059669",
    "warn":          "#D97706",
    "pink":          "#DB2777",
    "cyan":          "#0891B2",

    "text_strong":   "#0F172A",   # slate-900 — titres
    "text":          "#1E293B",   # slate-800 — corps
    "tag_fg":        "#1E293B",
    "muted":         "#64748B",
    "muted_dim":     "#94A3B8",
}

# PALETTE est un dict mutable que App.__init__ remplit selon le thème actif
# AVANT toute construction de widgets. Les références PALETTE["xxx"] dispersées
# dans le code lisent donc toujours les bonnes valeurs.
PALETTE: dict[str, str] = dict(DARK_PALETTE)

# Combos recommandees dans le PDF "Bibliotheque de prompts auto-adresses",
# plus un preset metier Triskell Studio (production de sites web).
PRESETS = [
    {
        "name": "Production de sites",
        "icon": "🌐",
        "color": "indigo",
        "ids": ["14", "13", "06", "00"],
        "desc": "Pour assembler un site web complet sans validations à mi-parcours.",
    },
    {
        "name": "Build d'app",
        "icon": "💻",
        "color": "indigo",
        "ids": ["00", "06", "13"],
        "desc": "Pour coder une app de bout en bout, sans pause, sans LLM-ismes.",
    },
    {
        "name": "Décision stratégique",
        "icon": "🎯",
        "color": "violet",
        "ids": ["01", "04", "05", "10"],
        "desc": "Pour trancher un choix difficile en mode argumentation contradictoire.",
    },
    {
        "name": "Recherche & veille",
        "icon": "🔍",
        "color": "violet",
        "ids": ["02", "07", "15"],
        "desc": "Pour creuser un sujet et restituer dense, sans hallucinations.",
    },
    {
        "name": "Apprentissage profond",
        "icon": "📚",
        "color": "orange",
        "ids": ["03", "08", "09"],
        "desc": "Pour comprendre un concept en profondeur, des fondations vers le haut.",
    },
    {
        "name": "Diagnostic complexe",
        "icon": "🔬",
        "color": "orange",
        "ids": ["14", "02", "12"],
        "desc": "Pour démêler un problème ambigu et débusquer ce qui cloche vraiment.",
    },
    {
        "name": "Projet long",
        "icon": "⏳",
        "color": "pink",
        "ids": ["00", "11", "12"],
        "desc": "Pour piloter un projet dans la durée sans perdre le fil ni dériver.",
    },
    {
        "name": "Critique honnête",
        "icon": "⚔",
        "color": "pink",
        "ids": ["01", "04", "06"],
        "desc": "Pour faire challenger une idée et avoir un retour cash, sans complaisance.",
    },
]


# --------- Brand fonts loading -----------------------------------------------

FONT_DISPLAY = "Syne"        # headings, brand wordmark
FONT_BODY = "Inter"          # everything else
FONT_MONO = "Consolas"       # output box, code-like

# Resolved at App init via _load_brand_fonts(). Default to Segoe UI fallback.
RESOLVED_DISPLAY = "Segoe UI"
RESOLVED_BODY = "Segoe UI"


def _load_brand_fonts() -> tuple[str, str]:
    """Register bundled Syne + Inter TTFs for the current process so tk picks
    them up. Returns (display_font, body_font), with Segoe UI fallback."""
    import os
    from pathlib import Path

    fonts_dir = Path(__file__).parent / "assets" / "fonts"
    candidates = {
        FONT_DISPLAY: fonts_dir / "Syne-Regular.ttf",
        FONT_BODY: fonts_dir / "Inter-Regular.ttf",
    }

    if os.name == "nt":
        try:
            import ctypes
            FR_PRIVATE = 0x10
            for fam, path in candidates.items():
                if path.exists():
                    ctypes.windll.gdi32.AddFontResourceExW(
                        str(path), FR_PRIVATE, 0
                    )
        except Exception as exc:
            logger.warning("font registration failed: %s", exc)

    try:
        import tkinter.font as tkfont
        import tkinter as _tk
        _root = _tk._default_root
        owns_tmp = _root is None
        if owns_tmp:
            _root = _tk.Tk()
            _root.withdraw()
        fams = set(tkfont.families())
        if owns_tmp:
            _root.destroy()
        display = FONT_DISPLAY if FONT_DISPLAY in fams else RESOLVED_BODY
        body = FONT_BODY if FONT_BODY in fams else RESOLVED_BODY
        return display, body
    except Exception:
        return RESOLVED_BODY, RESOLVED_BODY


def _resolve_asset(*parts) -> "Path":
    """Resolve an asset path that works both in dev and in PyInstaller bundle.

    PyInstaller copies bundled datas (cf. `datas` dans alphabeast.spec) sous
    `sys._MEIPASS`. En dev, on tombe sur le dossier source du projet.
    """
    from pathlib import Path
    import sys
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base).joinpath(*parts)
    return Path(__file__).parent.joinpath(*parts)


def _apply_window_icon(window) -> None:
    """Définit l'icône de la fenêtre (barre des tâches Windows + alt-tab).

    Sans cet appel, Tk affiche son icône par défaut (le carré gris cassé)
    OU, en dev (`python app.py`), l'icône de `python.exe` (carré bleu).

    Double approche :
    1. `iconbitmap(default=...)` → barre de titre + alt-tab (Toplevel inclus)
    2. `iconphoto(True, PhotoImage(...))` → taskbar Windows (mode dev surtout).
       En .exe PyInstaller la ressource embedded suffit, mais en dev
       Windows colle au launcher python.exe sans iconphoto.
    """
    try:
        ico = _resolve_asset("assets", "icon.ico")
        if ico.exists():
            window.iconbitmap(default=str(ico))
        else:
            logger.warning("icon.ico introuvable : %s", ico)
    except Exception as exc:
        logger.warning("iconbitmap set failed: %s", exc)

    # iconphoto fallback — utilise icon.png (256x256) pour overrider
    # l'icône python.exe en dev mode + propage à toutes les fenêtres enfants.
    try:
        from PIL import Image, ImageTk
        png = _resolve_asset("assets", "icon.png")
        if png.exists():
            img = Image.open(str(png))
            # Reference gardée en attribut pour empêcher le GC qui fait
            # disparaître l'icône silencieusement après quelques secondes.
            window._icon_photo_ref = ImageTk.PhotoImage(img)
            window.iconphoto(True, window._icon_photo_ref)
    except Exception as exc:
        logger.debug("iconphoto set failed: %s", exc)


def _set_app_user_model_id(app_id: str = "triskell.alphabeast") -> None:
    """Windows : groupe correctement les fenêtres dans la barre des tâches.

    Sans ça, deux instances de l'app apparaissent séparément, ou l'icône
    pinned ne lance pas la même AppUserModelID que l'instance qui démarre.
    À appeler le plus tôt possible (avant la 1ère fenêtre).
    """
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as exc:
        logger.debug("AppUserModelID set failed: %s", exc)


def _apply_dark_titlebar(window, dark: bool = True) -> None:
    """Force titlebar dark/light on Windows 10/11 via DWM.

    `dark=True` (défaut) → titlebar sombre, cohérent avec le thème par défaut.
    `dark=False` → titlebar claire, utilisé en mode clair.
    """
    def collect_hwnds():
        import ctypes
        hwnds = []
        try:
            hwnds.append(ctypes.windll.user32.GetParent(window.winfo_id()))
        except Exception:
            pass
        try:
            hwnds.append(window.winfo_id())
        except Exception:
            pass
        try:
            frame = window.wm_frame()
            if isinstance(frame, str):
                hwnds.append(int(frame, 16))
            elif isinstance(frame, int):
                hwnds.append(frame)
        except Exception:
            pass
        return [h for h in hwnds if h]

    def do_it():
        try:
            import ctypes
            window.update_idletasks()
            value = ctypes.c_int(1 if dark else 0)
            for hwnd in collect_hwnds():
                # Essaie les deux constantes DWMA (20 = Win10 v1909+, 19 = older).
                for attr in (20, 19):
                    try:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, attr,
                            ctypes.byref(value), ctypes.sizeof(value),
                        )
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug("dark titlebar not applied: %s", exc)

    # Plusieurs essais pour les Toplevel dont le HWND n'est pas immédiat.
    # Pas de bind <Map> (déclenchait une boucle infinie).
    try:
        window.after(80, do_it)
        window.after(300, do_it)
    except Exception:
        do_it()


def _load_app_logo(size: int):
    """Load the brand chat-bubble icon at the requested size.

    Source : `landing/public/img/icon.png` — c'est le brand asset officiel
    (chat bubble violet rempli, sparkles, fond rounded square sombre) utilisé
    sur la landing prompt-builder.triskell-studio.fr. Fallback sur
    `assets/logo.png` si la source landing n'est pas dispo (cas .exe bundle
    où on ne ship pas le dossier landing/).

    Pipeline :
    1. Charge la PNG RGBA.
    2. Flip horizontal (miroir) — la bulle pointe à droite, sparkles à gauche.
    3. Bbox + pad carré centré pour éviter toute distorsion au resize.
    4. Resize Lanczos.

    PAS de recoloration : l'asset est déjà à la bonne nuance violette brand.
    Strip du fond rounded-square sombre vers transparence (THRESHOLD=80
    suffit pour cet asset car la bulle brand est claire et bien contrastée).
    Crop serré sur le pictogramme (pas de marge de sécurité) pour maximiser
    la taille visible quand l'icône est downsamplée à 24-32px (taskbar).
    """
    from pathlib import Path
    from PIL import Image

    # Sources candidates par ordre de préférence
    here = Path(__file__).parent
    candidates = [
        here / "landing" / "public" / "img" / "icon.png",  # brand officiel
        here / "assets" / "icon_brand.png",                 # copie locale (PyInstaller)
        here / "assets" / "logo.png",                       # legacy fallback
    ]
    logo_path = next((p for p in candidates if p.exists()), None)

    if logo_path is not None:
        try:
            img = Image.open(logo_path).convert("RGBA")

            # Flip horizontal — bulle pointe à droite, sparkles à gauche.
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

            # Strip du fond sombre rounded-square → transparent. Threshold
            # plus généreux (80) que la version legacy (40) car le fond du
            # brand asset est navy uni avec léger gradient — sans seuil
            # plus haut, des pixels du gradient survivent et créent un halo.
            px = img.load()
            w, h = img.size
            THRESHOLD = 80
            for y in range(h):
                for x in range(w):
                    r, g, b, a = px[x, y]
                    if a == 0:
                        continue
                    if r <= THRESHOLD and g <= THRESHOLD and b <= THRESHOLD:
                        px[x, y] = (r, g, b, 0)

            # Bbox sur le pictogramme uniquement (le fond est maintenant
            # transparent), crop carré centré sans marge de sécurité.
            bbox = img.getbbox()
            if not bbox:
                return img.resize((size, size), Image.LANCZOS)
            x0, y0, x1, y1 = bbox
            cw, ch = x1 - x0, y1 - y0
            side = max(cw, ch)
            cx = (x0 + x1) // 2
            cy = (y0 + y1) // 2
            half = side // 2
            sx0 = max(0, cx - half)
            sy0 = max(0, cy - half)
            sx1 = min(w, sx0 + side)
            sy1 = min(h, sy0 + side)
            if sx1 - sx0 != side:
                sx0 = max(0, sx1 - side)
            if sy1 - sy0 != side:
                sy0 = max(0, sy1 - side)
            margin = 0  # crop serré, pas de marge
            sx0 = max(0, sx0 - margin)
            sy0 = max(0, sy0 - margin)
            sx1 = min(w, sx1 + margin)
            sy1 = min(h, sy1 + margin)
            img = img.crop((sx0, sy0, sx1, sy1))
            # Resize final
            return img.resize((size, size), Image.LANCZOS)
        except Exception as exc:
            logger.debug("logo load failed: %s", exc)
    return _make_triskell_logo(size)


def _make_triskell_logo(size: int, bg_hex: str = "#08080F"):
    """Fallback : render the Triskell triskell mark (3 colored spirals + center dot).

    Used only when assets/logo.png is missing. Path mirrors triskell-studio.fr.
    """
    import math
    from PIL import Image, ImageDraw

    SCALE = 4
    s = (size * SCALE) / 36.0
    img = Image.new("RGBA", (size * SCALE, size * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def cubic(p0, p1, p2, p3, n=24):
        out = []
        for i in range(n + 1):
            t = i / n
            mt = 1 - t
            x = (mt ** 3) * p0[0] + 3 * (mt ** 2) * t * p1[0] + 3 * mt * (t ** 2) * p2[0] + (t ** 3) * p3[0]
            y = (mt ** 3) * p0[1] + 3 * (mt ** 2) * t * p1[1] + 3 * mt * (t ** 2) * p2[1] + (t ** 3) * p3[1]
            out.append((x, y))
        return out

    teardrop = []
    teardrop += cubic((18, 18), (20, 15), (22, 10), (20, 6))
    teardrop += cubic((20, 6), (18, 2), (13, 3), (13, 7.5))
    teardrop += cubic((13, 7.5), (13, 12), (16, 15.5), (18, 18))

    def rotate(pts, deg, cx=18, cy=18):
        a = math.radians(deg)
        c, si = math.cos(a), math.sin(a)
        return [(cx + (x - cx) * c - (y - cy) * si, cy + (x - cx) * si + (y - cy) * c) for x, y in pts]

    def to_pixels(pts):
        return [(x * s, y * s) for x, y in pts]

    for i, color in enumerate(("#6366F1", "#8B5CF6", "#F97316")):
        draw.polygon(to_pixels(rotate(teardrop, i * 120)), fill=color)

    cx_pix = 18 * s
    hole_r = 2.8 * s
    draw.ellipse(
        [cx_pix - hole_r, cx_pix - hole_r, cx_pix + hole_r, cx_pix + hole_r],
        fill=bg_hex,
    )

    return img.resize((size, size), Image.LANCZOS)


class TagWidget(ctk.CTkFrame):
    """A chip with name + tagline. Click name/tagline to preview, x to remove."""

    def __init__(self, master, mp: dict, on_remove, on_preview):
        super().__init__(
            master,
            corner_radius=14,
            fg_color=PALETTE["tag_bg"],
            border_width=1,
            border_color=PALETTE["border_2"],
        )
        self.mp = mp

        badge = ctk.CTkLabel(
            self,
            text=f" {mp['id']} ",
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["violet"],
            corner_radius=8,
            font=(RESOLVED_BODY, 10, "bold"),
        )
        badge.pack(side="left", padx=(8, 8), pady=8)
        badge.bind("<Button-1>", lambda _e: on_preview(mp))

        text_block = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        text_block.pack(side="left", padx=(0, 6), pady=4)
        name_lbl = ctk.CTkLabel(
            text_block,
            text=mp["name"],
            text_color=PALETTE["tag_fg"],
            font=(RESOLVED_BODY, 12, "bold"),
            anchor="w",
            cursor="hand2",
        )
        name_lbl.pack(anchor="w")
        if mp.get("tagline"):
            tagline_lbl = ctk.CTkLabel(
                text_block,
                text=mp["tagline"],
                text_color=PALETTE["muted"],
                font=(RESOLVED_BODY, 10),
                anchor="w",
                cursor="hand2",
            )
            tagline_lbl.pack(anchor="w")
            tagline_lbl.bind("<Button-1>", lambda _e: on_preview(mp))
        text_block.bind("<Button-1>", lambda _e: on_preview(mp))
        name_lbl.bind("<Button-1>", lambda _e: on_preview(mp))

        btn = ctk.CTkButton(
            self,
            text="✕",
            width=22,
            height=22,
            corner_radius=11,
            fg_color="transparent",
            hover_color=PALETTE["danger"],
            text_color=PALETTE["muted"],
            font=(RESOLVED_BODY, 11, "bold"),
            command=lambda: on_remove(mp),
            border_width=1,
            border_color=PALETTE["border_2"],
        )
        btn.pack(side="left", padx=(2, 6), pady=4)


class WelcomeWindow(ctk.CTkToplevel):
    """First-launch onboarding modal — quick intro to the product."""

    def __init__(self, master, on_close):
        super().__init__(master)
        self.title("Bienvenue dans AlphaBeast")
        self.geometry("680x720")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
        self._on_close = on_close

        wrap = ctk.CTkFrame(self, fg_color=PALETTE["bg"])
        wrap.pack(fill="both", expand=True)

        try:
            self._logo_img = ctk.CTkImage(
                light_image=_load_app_logo(80),
                dark_image=_load_app_logo(80),
                size=(80, 80),
            )
            ctk.CTkLabel(wrap, image=self._logo_img, text="").pack(pady=(28, 8))
        except Exception:
            ctk.CTkLabel(
                wrap, text="◆",
                font=(RESOLVED_DISPLAY, 56, "bold"),
                text_color=PALETTE["violet"],
            ).pack(pady=(28, 8))

        ctk.CTkLabel(
            wrap, text="Bienvenue dans AlphaBeast",
            font=(RESOLVED_DISPLAY, 24, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(pady=(4, 4))
        ctk.CTkLabel(
            wrap, text="Sors tes IA du mode validation par defaut.",
            font=(RESOLVED_BODY, 13),
            text_color=PALETTE["muted"],
        ).pack(pady=(0, 18))

        steps_frame = ctk.CTkFrame(wrap, fg_color="transparent")
        steps_frame.pack(fill="x", padx=32, pady=4)

        steps = [
            ("1", "Écris ton prompt",
             "Une demande, un brief, une question — tout ce que tu veux envoyer à une IA."),
            ("2", "Pioche un preset (ou des Méga Prompts)",
             "Production de sites · Build d'app · Décision stratégique · Recherche & veille…"),
            ("3", "Génère et envoie",
             "Le Prompt Ultime est généré, puis envoyé à Claude / GPT / Gemini / Mistral / Grok."),
        ]
        for num, title, desc in steps:
            row = ctk.CTkFrame(
                steps_frame, fg_color=PALETTE["panel_card"],
                border_width=1, border_color=PALETTE["border_2"],
                corner_radius=12,
            )
            row.pack(fill="x", pady=5)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=12)
            ctk.CTkLabel(
                inner, text=f" {num} ",
                font=(RESOLVED_BODY, 12, "bold"),
                text_color=PALETTE["text_strong"],
                fg_color=PALETTE["accent"], corner_radius=12,
            ).pack(side="left", padx=(0, 12))
            txt = ctk.CTkFrame(inner, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                txt, text=title,
                font=(RESOLVED_BODY, 13, "bold"),
                text_color=PALETTE["text_strong"],
                anchor="w",
            ).pack(fill="x", anchor="w")
            ctk.CTkLabel(
                txt, text=desc,
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted"],
                anchor="w", justify="left", wraplength=520,
            ).pack(fill="x", anchor="w", pady=(2, 0))

        tip = ctk.CTkFrame(
            wrap, fg_color=PALETTE["accent_dim"],
            corner_radius=10, border_width=1, border_color=PALETTE["accent"],
        )
        tip.pack(fill="x", padx=32, pady=(18, 4))
        ctk.CTkLabel(
            tip,
            text="💡  Astuce : configure d'abord ta clé API dans Paramètres pour pouvoir envoyer à l'IA. Sinon tu peux juste générer + copier le prompt et le coller ailleurs.",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["text_strong"],
            wraplength=560, justify="left",
        ).pack(padx=14, pady=10)

        bar = ctk.CTkFrame(wrap, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=32, pady=(20, 24))
        ctk.CTkButton(
            bar, text="Ouvrir Paramètres",
            width=170, height=42,
            font=(RESOLVED_BODY, 12, "bold"),
            text_color=PALETTE["text"],
            fg_color="transparent",
            hover_color=PALETTE["tag_bg"],
            border_width=1, border_color=PALETTE["text"],
            command=self._open_settings,
        ).pack(side="left")
        ctk.CTkButton(
            bar, text="C'est parti  →",
            width=170, height=42,
            font=(RESOLVED_BODY, 13, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=self._dismiss,
        ).pack(side="right")
        self.bind("<Escape>", lambda _e: self._dismiss())
        self.bind("<Return>", lambda _e: self._dismiss())

    def _dismiss(self):
        try:
            self._on_close(open_settings=False)
        finally:
            self.destroy()

    def _open_settings(self):
        try:
            self._on_close(open_settings=True)
        finally:
            self.destroy()


class AboutWindow(ctk.CTkToplevel):
    """Branded About dialog with clickable website link."""

    def __init__(self, master):
        super().__init__(master)
        self.title("A propos")
        self.geometry("560x500")
        self.transient(master)
        self.resizable(False, False)
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)

        wrap = ctk.CTkFrame(self, fg_color=PALETTE["panel"], corner_radius=0)
        wrap.pack(fill="both", expand=True)

        # Big triskell logo
        try:
            self._logo_img_about = ctk.CTkImage(
                light_image=_load_app_logo(96),
                dark_image=_load_app_logo(96),
                size=(96, 96),
            )
            ctk.CTkLabel(wrap, image=self._logo_img_about, text="").pack(pady=(36, 0))
        except Exception:
            ctk.CTkLabel(
                wrap, text="◆",
                font=(RESOLVED_DISPLAY, 72, "bold"),
                text_color=PALETTE["violet"],
            ).pack(pady=(36, 0))

        # Brand wordmark
        wordmark = ctk.CTkFrame(wrap, fg_color="transparent")
        wordmark.pack(pady=(10, 0))
        ctk.CTkLabel(
            wordmark, text="triskell",
            font=(RESOLVED_DISPLAY, 28, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left")
        ctk.CTkLabel(
            wordmark, text="  S T U D I O",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["muted"],
        ).pack(side="left", pady=(11, 0))

        ctk.CTkLabel(
            wrap, text="AlphaBeast",
            font=(RESOLVED_DISPLAY, 18, "bold"),
            text_color=PALETTE["text"],
        ).pack(pady=(14, 0))

        ctk.CTkLabel(
            wrap, text=BRAND_VERSION,
            font=(RESOLVED_BODY, 11), text_color=PALETTE["muted"],
        ).pack(pady=(0, 20))

        ctk.CTkLabel(
            wrap,
            text=(
                "Combine ton prompt avec une bibliotheque de Mega Prompts\n"
                "et envoie le résultat à Claude, GPT, Gemini, Mistral ou Grok."
            ),
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["tag_fg"],
            justify="center",
        ).pack(pady=(0, 22))

        # Clickable website link
        link = ctk.CTkLabel(
            wrap,
            text=BRAND_URL,
            font=(RESOLVED_BODY, 12, "underline"),
            text_color=PALETTE["brand"],
            cursor="hand2",
        )
        link.pack()
        link.bind("<Button-1>", lambda _e: webbrowser.open(BRAND_URL))

        ctk.CTkLabel(
            wrap,
            text="Source des Mega Prompts : Bibliotheque de prompts auto-adresses",
            font=(RESOLVED_BODY, 9),
            text_color=PALETTE["muted_dim"],
        ).pack(pady=(18, 0))

        ctk.CTkButton(
            wrap, text="Fermer", width=130, height=36,
            command=self.destroy,
            fg_color=PALETTE["accent"], hover_color=PALETTE["accent_hover"],
            border_width=1,
            border_color=PALETTE["border_2"],
        ).pack(pady=26)
        self.bind("<Escape>", lambda _e: self.destroy())


class MegaPromptEditor(ctk.CTkToplevel):
    """Form to create or edit a Mega Prompt."""

    CATEGORIES = [
        "Coding",
        "Conseil",
        "Recherche",
        "Reflexion",
        "Strategie",
        "Ecriture",
        "Communication",
        "Apprentissage",
        "Diagnostic",
        "Custom",
    ]

    def __init__(self, master, mp: dict | None, on_save):
        super().__init__(master)
        self.is_new = mp is None
        self.mp = dict(mp) if mp else {
            "id": "", "name": "", "tagline": "",
            "category": "Custom", "content": "",
        }
        self.on_save = on_save
        self.title(
            "Nouveau Mega Prompt" if self.is_new
            else f"Editer Mega Prompt #{self.mp.get('id', '')}"
        )
        self.geometry("780x720")
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)

        # Header
        header = ctk.CTkFrame(self, height=58, corner_radius=0, fg_color=PALETTE["panel"])
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="✎  " + ("Nouveau Mega Prompt" if self.is_new else f"Editer #{self.mp['id']}"),
            font=(RESOLVED_DISPLAY, 16, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left", padx=18)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(14, 0))

        def field_label(text: str) -> None:
            ctk.CTkLabel(
                body, text=text,
                font=(RESOLVED_BODY, 11, "bold"),
                text_color=PALETTE["muted"],
                anchor="w",
            ).pack(fill="x", pady=(10, 4))

        # Style commun pour CTkEntry (palette Triskell — évite le gris CTk par défaut)
        _entry_kw = dict(
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            text_color=PALETTE["text"],
            placeholder_text_color=PALETTE["muted_dim"],
            corner_radius=8,
        )

        field_label("Nom court")
        self.name_entry = ctk.CTkEntry(
            body, height=36, placeholder_text="Ex: Anti-distraction",
            font=(RESOLVED_BODY, 12),
            **_entry_kw,
        )
        self.name_entry.pack(fill="x")
        if self.mp.get("name"):
            self.name_entry.insert(0, self.mp["name"])

        field_label("Tagline (description courte)")
        self.tagline_entry = ctk.CTkEntry(
            body, height=36,
            placeholder_text="Ex: Couper court aux digressions",
            font=(RESOLVED_BODY, 12),
            **_entry_kw,
        )
        self.tagline_entry.pack(fill="x")
        if self.mp.get("tagline"):
            self.tagline_entry.insert(0, self.mp["tagline"])

        field_label("Categorie")
        self.cat_var = ctk.StringVar(value=self.mp.get("category", "Custom"))
        ctk.CTkOptionMenu(
            body, values=self.CATEGORIES, variable=self.cat_var,
            height=36,
            fg_color=PALETTE["tag_bg"],
            button_color=PALETTE["accent"],
            button_hover_color=PALETTE["accent_hover"],
        ).pack(fill="x")

        field_label("Contenu (le prompt complet)")
        self.content_box = ctk.CTkTextbox(
            body, font=(RESOLVED_BODY, 12), wrap="word",
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            text_color=PALETTE["text"],
            border_width=1, border_color=PALETTE["border"],
            height=320,
        )
        self.content_box.pack(fill="both", expand=True, pady=(0, 12))
        if self.mp.get("content"):
            self.content_box.insert("1.0", self.mp["content"])

        # Action bar
        bar = ctk.CTkFrame(self, fg_color=PALETTE["panel"], height=66, corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        ctk.CTkButton(
            bar, text="Annuler", width=120, height=38,
            command=self.destroy,
            fg_color="transparent",
            border_width=1, border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
        ).pack(side="right", padx=(8, 18), pady=14)
        ctk.CTkButton(
            bar,
            text=("✓  Creer" if self.is_new else "✓  Enregistrer"),
            width=160, height=38,
            command=self._save,
            fg_color=PALETTE["accent"], hover_color=PALETTE["accent_hover"],
            font=(RESOLVED_BODY, 12, "bold"),
            border_width=1,
            border_color=PALETTE["border_2"],
        ).pack(side="right", pady=14)

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-Return>", lambda _e: self._save())
        self.name_entry.focus()

    def _save(self) -> None:
        name = self.name_entry.get().strip()
        tagline = self.tagline_entry.get().strip()
        content = self.content_box.get("1.0", "end").strip()
        category = self.cat_var.get().strip() or "Custom"
        if not name:
            messagebox.showwarning("Champ requis", "Le nom est obligatoire.")
            return
        if not content:
            messagebox.showwarning("Champ requis", "Le contenu du prompt est vide.")
            return
        self.mp.update({
            "name": name, "tagline": tagline,
            "category": category, "content": content,
        })
        self.on_save(self.mp, is_new=self.is_new)
        self.destroy()


class LibraryWindow(ctk.CTkToplevel):
    """Browse, search, edit, delete and add Mega Prompts."""

    def __init__(self, master, mega_prompts: list[dict], on_change):
        super().__init__(master)
        self.title("Bibliotheque des Mega Prompts")
        self.geometry("960x720")
        self.transient(master)
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
        self.mega_prompts = mega_prompts
        self.on_change = on_change
        self._search_query = ""

        # Header
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color=PALETTE["panel"])
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="📚  Bibliotheque des Mega Prompts",
            font=(RESOLVED_DISPLAY, 17, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left", padx=18)
        ctk.CTkButton(
            header, text="+  Nouveau Mega Prompt",
            height=36, width=200,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color=PALETTE["accent"], hover_color=PALETTE["accent_hover"],
            command=self._on_new,
            border_width=1,
            border_color=PALETTE["border_2"],
        ).pack(side="right", padx=18, pady=16)

        # Search bar
        search_bar = ctk.CTkFrame(self, height=58, corner_radius=0, fg_color=PALETTE["panel_alt"])
        search_bar.pack(fill="x")
        search_bar.pack_propagate(False)
        ctk.CTkLabel(
            search_bar, text="🔍",
            font=(RESOLVED_BODY, 14),
            text_color=PALETTE["muted"],
        ).pack(side="left", padx=(18, 6))
        self.search_entry = ctk.CTkEntry(
            search_bar, height=34,
            placeholder_text="Rechercher par nom, categorie, tagline ou contenu...",
            font=(RESOLVED_BODY, 12),
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["border"],
            border_width=1,
            text_color=PALETTE["text"],
            placeholder_text_color=PALETTE["muted_dim"],
            corner_radius=8,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 18), pady=12)
        self.search_entry.bind("<KeyRelease>", lambda _e: self._on_search())

        # List container
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=PALETTE["panel_alt"])
        self.list_frame.pack(fill="both", expand=True)

        self._render_list()
        self.bind("<Escape>", lambda _e: self.destroy())

    def _on_search(self) -> None:
        self._search_query = self.search_entry.get().strip().lower()
        self._render_list()

    def _filtered(self) -> list[dict]:
        if not self._search_query:
            return list(self.mega_prompts)
        q = self._search_query
        return [
            mp for mp in self.mega_prompts
            if q in mp.get("name", "").lower()
            or q in mp.get("category", "").lower()
            or q in mp.get("tagline", "").lower()
            or q in mp.get("content", "").lower()
            or q in mp.get("id", "").lower()
        ]

    def _render_list(self) -> None:
        for w in self.list_frame.winfo_children():
            w.destroy()
        items = self._filtered()
        if not items:
            ctk.CTkLabel(
                self.list_frame,
                text="Aucun mega prompt ne correspond.",
                font=(RESOLVED_BODY, 12),
                text_color=PALETTE["muted"],
            ).pack(pady=40)
            return
        for mp in items:
            self._render_card(mp)

    def _render_card(self, mp: dict) -> None:
        card = ctk.CTkFrame(
            self.list_frame, corner_radius=10,
            fg_color=PALETTE["panel_card"],
            border_width=1, border_color=PALETTE["border"],
        )
        card.pack(fill="x", padx=10, pady=6)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 4))
        top.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            top, text=f" {mp['id']} ",
            font=(RESOLVED_BODY, 10, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent_dim"], corner_radius=8,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ctk.CTkLabel(
            top, text=mp.get("name", ""),
            font=(RESOLVED_BODY, 14, "bold"),
            text_color=PALETTE["text_strong"],
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            top,
            text=f"[{mp.get('category', 'Autre')}]",
            font=(RESOLVED_BODY, 10, "bold"),
            text_color=PALETTE["violet"],
        ).grid(row=0, column=2, padx=10, sticky="w")

        if mp.get("tagline"):
            ctk.CTkLabel(
                card, text=mp["tagline"],
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted"],
                anchor="w", justify="left",
                wraplength=860,
            ).pack(fill="x", padx=14, pady=(0, 4))

        # Action bar
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(2, 10))
        ctk.CTkButton(
            actions, text="👁  Voir", width=90, height=30,
            font=(RESOLVED_BODY, 11, "bold"),
            fg_color="transparent",
            border_width=1, border_color=PALETTE["text"],
            text_color=PALETTE["text"],
            hover_color=PALETTE["tag_bg"],
            command=lambda m=mp: PreviewWindow(self, m),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions, text="✎  Editer", width=100, height=30,
            font=(RESOLVED_BODY, 11, "bold"),
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color=PALETTE["text_strong"],
            command=lambda m=mp: self._on_edit(m),
            border_width=1,
            border_color=PALETTE["border_2"],
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            actions, text="🗑  Supprimer", width=110, height=30,
            fg_color="transparent",
            border_width=1, border_color=PALETTE["danger"],
            text_color=PALETTE["danger"],
            hover_color=PALETTE["danger"],
            command=lambda m=mp: self._on_delete(m),
        ).pack(side="left", padx=4)

    def _on_new(self) -> None:
        MegaPromptEditor(self, mp=None, on_save=self._after_save)

    def _on_edit(self, mp: dict) -> None:
        MegaPromptEditor(self, mp=mp, on_save=self._after_save)

    def _on_delete(self, mp: dict) -> None:
        if not messagebox.askyesno(
            "Confirmer",
            f"Supprimer definitivement le Mega Prompt #{mp['id']} '{mp['name']}' ?",
        ):
            return
        self.mega_prompts = [m for m in self.mega_prompts if m["id"] != mp["id"]]
        try:
            config.save_mega_prompts(self.mega_prompts)
        except OSError as exc:
            messagebox.showerror("Erreur", f"Sauvegarde echouee: {exc}")
            return
        self.on_change(self.mega_prompts)
        self._render_list()

    def _after_save(self, mp: dict, is_new: bool) -> None:
        if is_new:
            mp["id"] = self._next_id()
            self.mega_prompts.append(mp)
        else:
            for i, existing in enumerate(self.mega_prompts):
                if existing["id"] == mp["id"]:
                    self.mega_prompts[i] = mp
                    break
        try:
            config.save_mega_prompts(self.mega_prompts)
        except OSError as exc:
            messagebox.showerror("Erreur", f"Sauvegarde echouee: {exc}")
            return
        self.on_change(self.mega_prompts)
        self._render_list()

    def _next_id(self) -> str:
        max_id = -1
        for mp in self.mega_prompts:
            try:
                v = int(mp.get("id", "0"))
                if v > max_id:
                    max_id = v
            except ValueError:
                continue
        return f"{max_id + 1:02d}"


class PreviewWindow(ctk.CTkToplevel):
    """Display the full content of a mega prompt for inspection."""

    def __init__(self, master, mp: dict):
        super().__init__(master)
        self.title(f"Mega Prompt {mp['id']} — {mp['name']}")
        self.geometry("780x600")
        self.transient(master)
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)

        header = ctk.CTkFrame(self, fg_color=PALETTE["panel_alt"], corner_radius=0, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text=f"#{mp['id']}  ·  {mp['name']}",
            font=(RESOLVED_DISPLAY, 16, "bold"),
            text_color=PALETTE["text_strong"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(12, 0))
        ctk.CTkLabel(
            header,
            text=mp.get("tagline", ""),
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 10))

        textbox = ctk.CTkTextbox(
            self, font=(RESOLVED_BODY, 12), wrap="word", corner_radius=8,
            fg_color=PALETTE["input_bg"],
            text_color=PALETTE["text"],
            border_width=1, border_color=PALETTE["border"],
        )
        textbox.pack(fill="both", expand=True, padx=14, pady=14)
        textbox.insert("1.0", mp.get("content", ""))
        textbox.configure(state="disabled")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(
            bar, text="Fermer", command=self.destroy, width=110,
            fg_color="transparent", border_width=1,
            border_color=PALETTE["muted"], text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
        ).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())


class SettingsWindow(ctk.CTkToplevel):
    """API keys + provider/model picker."""

    def __init__(self, master, settings: dict[str, Any], on_save):
        super().__init__(master)
        self.title("Paramètres — Clés API & Modèles")
        self.geometry("720x800")
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
        self.settings = settings
        self.on_save = on_save
        self._key_entries: dict[str, ctk.CTkEntry] = {}

        # DECISION: aligner le scrollable sur la palette Triskell pour éviter
        # le gris CustomTkinter par défaut qui casse l'identité visuelle.
        wrapper = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
            fg_color=PALETTE["bg"],
            scrollbar_fg_color=PALETTE["bg"],
            scrollbar_button_color=PALETTE["tag_bg"],
            scrollbar_button_hover_color=PALETTE["tag_bg_hover"],
        )
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            wrapper,
            text="Clés API",
            font=(RESOLVED_DISPLAY, 18, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(anchor="w", pady=(0, 10))

        info = ctk.CTkLabel(
            wrapper,
            text=(
                "Stockees en local dans settings.json. "
                "Ne sont jamais envoyees ailleurs que vers le provider choisi."
            ),
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
            wraplength=560,
            justify="left",
        )
        info.pack(anchor="w", pady=(0, 16))

        for pid, info in PROVIDERS.items():
            row = ctk.CTkFrame(wrapper, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(
                row,
                text=info["label"],
                font=(RESOLVED_BODY, 12, "bold"),
                text_color=PALETTE["text_strong"],
                width=170,
                anchor="w",
            ).pack(side="left")
            entry = ctk.CTkEntry(
                row,
                show="*",
                placeholder_text=f"sk-... ({pid})",
                width=300,
                height=34,
                fg_color=PALETTE["input_bg"],
                border_color=PALETTE["border"],
                border_width=1,
                text_color=PALETTE["text"],
                placeholder_text_color=PALETTE["muted_dim"],
                corner_radius=8,
            )
            current = self.settings.get("api_keys", {}).get(info["key_field"], "")
            if current:
                entry.insert(0, current)
            entry.pack(side="left", padx=(8, 0))
            self._key_entries[info["key_field"]] = entry

            # Lien "Obtenir une clé" — ouvre la console du provider dans le navigateur.
            # Permet à l'utilisateur d'aller créer une clé en 1 clic au lieu de
            # chercher l'URL à la main.
            console_url = info.get("console_url")
            if console_url:
                ctk.CTkButton(
                    row,
                    text="↗  Obtenir",
                    width=80, height=34,
                    corner_radius=8,
                    font=(RESOLVED_BODY, 10, "bold"),
                    fg_color="transparent",
                    text_color=PALETTE["accent"],
                    hover_color=PALETTE["accent_dim"],
                    border_width=1, border_color=PALETTE["accent"],
                    command=lambda url=console_url: webbrowser.open(url),
                ).pack(side="left", padx=(6, 0))

        # Le toggle de thème vit dans la top-bar (☀/🌙). On reflète juste le
        # mode courant ici pour ne pas l'écraser quand l'utilisateur sauvegarde
        # les paramètres.
        self.appearance_var = ctk.StringVar(
            value=self.settings.get("appearance_mode", "dark")
        )

        # ----- Updates section -----
        ctk.CTkLabel(
            wrapper, text="Mises à jour",
            font=(RESOLVED_DISPLAY, 18, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(anchor="w", pady=(20, 8))

        upd_card = ctk.CTkFrame(
            wrapper, fg_color=PALETTE["panel_card"],
            corner_radius=10, border_width=1,
            border_color=PALETTE["border"],
        )
        upd_card.pack(fill="x", pady=4)

        self._upd_status_lbl = ctk.CTkLabel(
            upd_card,
            text=f"Version installée : v{UPDATER_VERSION}",
            font=(RESOLVED_BODY, 12, "bold"),
            text_color=PALETTE["text_strong"],
            anchor="w",
        )
        self._upd_status_lbl.pack(fill="x", padx=14, pady=(12, 2))
        self._upd_detail_lbl = ctk.CTkLabel(
            upd_card,
            text="Clique sur 'Verifier maintenant' pour chercher une nouvelle version.",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
            anchor="w",
            justify="left",
            wraplength=520,
        )
        self._upd_detail_lbl.pack(fill="x", padx=14, pady=(0, 8))

        upd_actions = ctk.CTkFrame(upd_card, fg_color="transparent")
        upd_actions.pack(fill="x", padx=14, pady=(0, 12))
        self._upd_check_btn = ctk.CTkButton(
            upd_actions, text="Vérifier maintenant",
            width=170, height=34,
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=lambda: updater.check_for_updates(async_=True),
        )
        self._upd_check_btn.pack(side="left")
        self._upd_install_btn = ctk.CTkButton(
            upd_actions, text="Installer la mise à jour",
            width=200, height=34,
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["violet"],
            hover_color="#7C3AED",
            border_width=1, border_color=PALETTE["border_2"],
            command=updater.install,
        )
        self._upd_install_btn.pack(side="left", padx=(8, 0))
        self._upd_install_btn.configure(state="disabled")

        # Hook listener and refresh once
        updater.add_listener(self._on_updater_status)
        self._on_updater_status(updater.status)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(
            btn_row,
            text="Annuler",
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            btn_row,
            text="Enregistrer",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=self._save,
            border_width=1,
            border_color=PALETTE["border_2"],
        ).pack(side="right")

    def _save(self) -> None:
        keys = {pid: e.get().strip() for pid, e in self._key_entries.items()}
        self.settings["api_keys"] = keys
        self.settings["appearance_mode"] = self.appearance_var.get()
        try:
            config.save_settings(self.settings)
        except OSError as exc:
            messagebox.showerror("Erreur", f"Sauvegarde impossible: {exc}")
            return
        ctk.set_appearance_mode(self.settings["appearance_mode"])
        self.on_save(self.settings)
        self.destroy()

    def destroy(self) -> None:  # type: ignore[override]
        try:
            updater.remove_listener(self._on_updater_status)
        except Exception:
            pass
        super().destroy()

    def _on_updater_status(self, st) -> None:
        """Marshalled to UI thread via after()."""
        try:
            self.after(0, self._render_updater_status, st)
        except Exception:
            pass

    def _render_updater_status(self, st) -> None:
        if not self.winfo_exists():
            return
        phase = st.phase
        nv = st.next_version or "?"
        if phase == "idle":
            self._upd_status_lbl.configure(text=f"Version installée : v{st.current_version}")
            self._upd_detail_lbl.configure(
                text="Clique sur 'Verifier maintenant' pour chercher une nouvelle version.",
                text_color=PALETTE["muted"],
            )
            self._upd_check_btn.configure(state="normal", text="Vérifier maintenant")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "checking":
            self._upd_detail_lbl.configure(
                text="Verification en cours...", text_color=PALETTE["muted"],
            )
            self._upd_check_btn.configure(state="disabled", text="Verification...")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "not-available":
            self._upd_detail_lbl.configure(
                text=f"Tu es à jour. Dernière version : v{nv}.",
                text_color=PALETTE["ok"],
            )
            self._upd_check_btn.configure(state="normal", text="Vérifier maintenant")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "available":
            self._upd_detail_lbl.configure(
                text=f"Nouvelle version v{nv} disponible. Telechargement en cours...",
                text_color=PALETTE["accent"],
            )
            self._upd_check_btn.configure(state="disabled", text="Telechargement...")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "downloading":
            self._upd_detail_lbl.configure(
                text=f"Telechargement de v{nv} : {st.percent}%  ({st.bytes_per_second // 1024} Ko/s)",
                text_color=PALETTE["accent"],
            )
            self._upd_check_btn.configure(state="disabled", text=f"{st.percent}%")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "ready":
            self._upd_detail_lbl.configure(
                text=f"v{nv} pret a etre installe. Clique sur 'Installer' (l'app va redemarrer).",
                text_color=PALETTE["orange"],
            )
            self._upd_check_btn.configure(state="normal", text="Vérifier maintenant")
            self._upd_install_btn.configure(state="normal")
        elif phase == "error":
            self._upd_detail_lbl.configure(
                text=f"Erreur : {st.message}", text_color=PALETTE["danger"],
            )
            self._upd_check_btn.configure(state="normal", text="Reessayer")
            self._upd_install_btn.configure(state="disabled")


class ResponseWindow(ctk.CTkToplevel):
    """Polished modal showing the AI response with metadata header + actions."""

    def __init__(self, master, title: str, content: str,
                 provider_id: str = "", model: str = "", char_count: int = 0):
        super().__init__(master)
        self.title(title)
        self.geometry("960x740")
        self.transient(master)
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
        self._content = content

        # Header strip with provider + model + count
        header = ctk.CTkFrame(self, fg_color=PALETTE["panel"], height=72, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=18, pady=10)
        ctk.CTkLabel(
            left,
            text="🤖  Reponse IA",
            font=(RESOLVED_DISPLAY, 16, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(anchor="w")
        provider_lbl = (
            f"{provider_id}  ·  {model}" if provider_id and model
            else "AI Response"
        )
        meta = f"{provider_lbl}  ·  {len(content)} caracteres  ·  ~{max(1, len(content)//4)} tokens"
        ctk.CTkLabel(
            left, text=meta,
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).pack(anchor="w", pady=(2, 0))

        border_line = ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"], corner_radius=0)
        border_line.pack(fill="x")

        # Body
        textbox = ctk.CTkTextbox(
            self,
            font=(RESOLVED_BODY, 13),
            wrap="word",
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
        )
        textbox.pack(fill="both", expand=True, padx=16, pady=16)
        textbox.insert("1.0", content)
        textbox.configure(state="normal")

        # Action bar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 16))

        def copy() -> None:
            self.clipboard_clear()
            self.clipboard_append(self._content)
            self.update()
            # Brief visual feedback on the button
            copy_btn.configure(text="✓  Copie !", fg_color=PALETTE["ok"])
            self.after(1400, lambda: copy_btn.configure(
                text="📋  Copier la reponse", fg_color=PALETTE["accent"]
            ))

        def export() -> None:
            from datetime import datetime
            path = filedialog.asksaveasfilename(
                title="Exporter la reponse IA",
                defaultextension=".md",
                initialfile=f"reponse_{provider_id or 'ai'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                filetypes=[("Markdown", "*.md"), ("Texte", "*.txt"), ("Tout fichier", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._content)
                export_btn.configure(text="✓  Exporte !", fg_color=PALETTE["ok"])
                self.after(1400, lambda: export_btn.configure(
                    text="⤓  Exporter", fg_color=PALETTE["tag_bg"]
                ))
            except OSError as exc:
                messagebox.showerror("Erreur", f"Export impossible: {exc}")

        ctk.CTkButton(
            bar,
            text="Fermer",
            width=110, height=40,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
            command=self.destroy,
        ).pack(side="left")
        export_btn = ctk.CTkButton(
            bar,
            text="⤓  Exporter",
            width=130, height=40,
            font=(RESOLVED_BODY, 12, "bold"),
            text_color=PALETTE["text"],
            fg_color=PALETTE["tag_bg"],
            hover_color=PALETTE["accent_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=export,
        )
        export_btn.pack(side="right", padx=(8, 0))
        copy_btn = ctk.CTkButton(
            bar,
            text="📋  Copier la reponse",
            width=200, height=40,
            font=(RESOLVED_BODY, 13, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=copy,
        )
        copy_btn.pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Control-c>", lambda _e: copy())


class HistoryWindow(ctk.CTkToplevel):
    """Browse generated history + saved prompts."""

    def __init__(self, master, on_load):
        super().__init__(master)
        self.title("Historique & Prompts sauvegardes")
        self.geometry("980x680")
        self.transient(master)
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
        self.on_load = on_load

        tabs = ctk.CTkTabview(
            self, corner_radius=8,
            fg_color=PALETTE["panel_alt"],
            segmented_button_fg_color=PALETTE["panel_card"],
            segmented_button_selected_color=PALETTE["accent"],
            segmented_button_selected_hover_color=PALETTE["accent_hover"],
            segmented_button_unselected_color=PALETTE["panel_card"],
            segmented_button_unselected_hover_color=PALETTE["tag_bg"],
            text_color=PALETTE["text_strong"],
        )
        tabs.pack(fill="both", expand=True, padx=12, pady=12)
        tabs.add("Historique")
        tabs.add("Sauvegardes")

        self._build_list(tabs.tab("Historique"), config.load_history(), kind="history")
        self._build_list(
            tabs.tab("Sauvegardes"), config.load_saved_prompts(), kind="saved"
        )

    def _build_list(self, parent, items: list[dict], kind: str) -> None:
        if not items:
            ctk.CTkLabel(
                parent,
                text=f"Aucun element ({kind}).",
                font=(RESOLVED_BODY, 13),
                text_color=PALETTE["muted"],
            ).pack(pady=40)
            return
        scroll = ctk.CTkScrollableFrame(
            parent, corner_radius=0, fg_color=PALETTE["panel_alt"],
        )
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        for entry in items:
            card = ctk.CTkFrame(
                scroll, corner_radius=10,
                fg_color=PALETTE["panel_card"],
                border_width=1, border_color=PALETTE["border"],
            )
            card.pack(fill="x", padx=4, pady=6)
            header = entry.get("title") or entry.get("timestamp") or "(sans titre)"
            preview = (entry.get("ultimate_prompt") or "")[:160].replace("\n", " ")
            ctk.CTkLabel(
                card,
                text=header,
                font=(RESOLVED_BODY, 12, "bold"),
                text_color=PALETTE["text_strong"],
                anchor="w",
            ).pack(fill="x", padx=12, pady=(8, 0))
            ctk.CTkLabel(
                card,
                text=preview + ("..." if len(preview) >= 160 else ""),
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted"],
                anchor="w",
                justify="left",
                wraplength=860,
            ).pack(fill="x", padx=12, pady=(2, 8))
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=(0, 8))
            ctk.CTkButton(
                row,
                text="Charger",
                width=110,
                font=(RESOLVED_BODY, 11, "bold"),
                text_color=PALETTE["text_strong"],
                fg_color=PALETTE["accent"],
                hover_color=PALETTE["accent_hover"],
                command=lambda e=entry: self._load(e),
                border_width=1,
                border_color=PALETTE["border_2"],
            ).pack(side="right")

    def _load(self, entry: dict) -> None:
        self.on_load(entry)
        self.destroy()


class App(ctk.CTk):
    def __init__(self) -> None:
        # Identifie l'app dans Windows AVANT de créer la fenêtre,
        # sinon la barre des tâches groupe mal et l'icône pinned est cassée.
        _set_app_user_model_id("triskell.alphabeast")

        super().__init__()
        self.settings = config.load_settings()
        self.mega_prompts = config.load_mega_prompts()
        self.selected_megas: list[dict] = []
        self.current_ultimate: str = ""

        # Thème : sombre par défaut (brand dark-first), clair via setting persisté.
        # On bascule la palette mutable AVANT _build_ui pour que tous les widgets
        # construits ensuite lisent les bonnes valeurs.
        mode = self.settings.get("appearance_mode", "dark")
        if mode not in ("dark", "light"):
            mode = "dark"
        self._apply_palette(mode)
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")
        self.settings["appearance_mode"] = mode

        # Load bundled brand fonts (Syne + Inter) before any widget creation.
        global RESOLVED_DISPLAY, RESOLVED_BODY
        RESOLVED_DISPLAY, RESOLVED_BODY = _load_brand_fonts()
        logger.info("Fonts: display=%s, body=%s", RESOLVED_DISPLAY, RESOLVED_BODY)

        self.title(APP_TITLE)
        self.geometry(f"{APP_W}x{APP_H}")
        self.minsize(1080, 700)
        self.configure(fg_color=PALETTE["bg"])

        # Icône de fenêtre (barre des tâches + alt-tab). Sans ça, Tk affiche
        # son icône grise par défaut au lieu du logo Triskell.
        _apply_window_icon(self)

        self._build_ui()
        self._bind_shortcuts()
        _apply_dark_titlebar(self, dark=(mode == "dark"))

        # Animation : fade-in de la fenêtre au démarrage (alpha 0 → 1 sur ~250ms)
        try:
            self.attributes("-alpha", 0.0)
            self.after(20, self._fade_in_step, 0)
        except Exception:
            pass

        # Background update check 5s after launch (non-blocking)
        updater.add_listener(self._on_global_update_status)
        self.after(5000, lambda: updater.check_for_updates(async_=True))

        # Welcome dialog on first launch (when no API key has been configured yet)
        self.after(400, self._maybe_show_welcome)

    def _apply_palette(self, mode: str) -> None:
        """Bascule la palette mutable globale sur le thème demandé.
        Les widgets déjà construits ne se restylent pas — utiliser au démarrage
        ou inviter à redémarrer après bascule via le toggle."""
        target = LIGHT_PALETTE if mode == "light" else DARK_PALETTE
        PALETTE.clear()
        PALETTE.update(target)

    def _toggle_theme(self) -> None:
        """Bouton ☀/🌙 du top-bar : bascule clair/sombre, persiste, redémarre."""
        current = self.settings.get("appearance_mode", "dark")
        new_mode = "light" if current == "dark" else "dark"
        self.settings["appearance_mode"] = new_mode
        try:
            config.save_settings(self.settings)
        except OSError as exc:
            self._set_status(f"Sauvegarde thème impossible: {exc}", warn=True)
            return
        ctk.set_appearance_mode(new_mode)
        # CustomTkinter ne restyle pas les widgets déjà créés à la volée :
        # on rebuild en relançant _build_ui après destruction des enfants.
        self._apply_palette(new_mode)
        self._rebuild_ui()
        _apply_dark_titlebar(self, dark=(new_mode == "dark"))
        self._set_status(
            f"Mode {'clair' if new_mode == 'light' else 'sombre'} activé.",
            ok=True,
        )

    def _rebuild_ui(self) -> None:
        """Détruit tous les widgets enfants et reconstruit l'UI avec la palette
        active. Utilisé pour appliquer un changement de thème sans redémarrage.
        Préserve : selected_megas, current_ultimate, brouillon utilisateur."""
        # Capture du contenu utilisateur AVANT destruction des widgets
        try:
            saved_input = (
                ""
                if getattr(self, "_input_has_placeholder", True)
                else self.input_box.get("1.0", "end").rstrip("\n")
            )
        except Exception:
            saved_input = ""
        saved_output = self.current_ultimate or ""

        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        self.configure(fg_color=PALETTE["bg"])
        self._output_empty = True
        self._build_ui()

        # Restaure les contenus
        if saved_input:
            try:
                self._input_has_placeholder = False
                self.input_box.delete("1.0", "end")
                self.input_box.configure(text_color=PALETTE["text"])
                self.input_box.insert("1.0", saved_input)
            except Exception:
                pass
        if saved_output:
            try:
                self._output_empty = False
                self.output_box.configure(state="normal")
                self.output_box.delete("1.0", "end")
                self.output_box.insert("1.0", saved_output)
                self.current_ultimate = saved_output
            except Exception:
                pass
        try:
            self._refresh_tags()
            self._update_input_count()
            self._update_output_count()
        except Exception:
            pass

    def _fade_in_step(self, step: int) -> None:
        """13 paliers × 20ms ≈ 260ms total — assez subtil pour ne pas distraire."""
        steps_total = 13
        try:
            alpha = min(1.0, step / steps_total)
            self.attributes("-alpha", alpha)
            if step < steps_total:
                self.after(20, self._fade_in_step, step + 1)
        except Exception:
            pass

    @staticmethod
    def _hex_to_rgb(h: str) -> tuple[int, int, int] | None:
        if not isinstance(h, str) or not h.startswith("#") or len(h) != 7:
            return None
        try:
            return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        except ValueError:
            return None

    @staticmethod
    def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"

    @classmethod
    def _lerp_hex(cls, a: str, b: str, t: float) -> str:
        ra = cls._hex_to_rgb(a) or (0, 0, 0)
        rb = cls._hex_to_rgb(b) or (0, 0, 0)
        t = max(0.0, min(1.0, t))
        return cls._rgb_to_hex(tuple(int(ra[i] + (rb[i] - ra[i]) * t) for i in range(3)))

    def _animate_attr(self, widget, attr: str, src: str, dst: str,
                      frames: int = 6, interval: int = 22, _i: int = 0) -> None:
        """Interpole `attr` d'un widget de src → dst en `frames` paliers.
        Ne raise pas si le widget est détruit pendant l'animation."""
        try:
            t = _i / frames
            color = self._lerp_hex(src, dst, t)
            widget.configure(**{attr: color})
        except Exception:
            return
        if _i < frames:
            try:
                widget.after(interval, self._animate_attr, widget, attr, src, dst,
                             frames, interval, _i + 1)
            except Exception:
                pass

    # ----- Breathing pulse sur le bouton "Générer" quand il est prêt -----

    def _start_generate_breathing(self) -> None:
        """Anime le fg_color du generate_btn entre deux oranges en sinusoïde
        (cycle ~2.4s). Donne l'impression que le bouton "respire" pour signaler
        qu'il est prêt à être cliqué — sans clignoter de manière agressive."""
        if getattr(self, "_breathing_active", False):
            return
        self._breathing_active = True
        self._breathing_phase = 0
        self._breathing_step()

    def _stop_generate_breathing(self) -> None:
        self._breathing_active = False

    def _breathing_step(self) -> None:
        if not getattr(self, "_breathing_active", False):
            return
        try:
            import math
            cycle = 60  # 60 frames × 40ms = 2.4s par cycle complet
            self._breathing_phase = (self._breathing_phase + 1) % cycle
            t = (math.sin(self._breathing_phase * 2 * math.pi / cycle) + 1) / 2
            color = self._lerp_hex("#F97316", "#FB923C", t)  # orange-500 ↔ orange-400
            # Ne touche au bouton que s'il est encore en mode "ready" (orange)
            current = self.generate_btn.cget("fg_color")
            cur_hex = current if isinstance(current, str) else (current[0] if current else "")
            if cur_hex.upper().startswith("#F") or cur_hex.upper().startswith("#E"):
                self.generate_btn.configure(fg_color=color)
        except Exception:
            self._breathing_active = False
            return
        try:
            self.after(40, self._breathing_step)
        except Exception:
            pass

    def _pulse_output_border(self) -> None:
        """Animation : flash de bordure sur la zone Prompt Ultime quand une
        génération réussit. Donne un retour visuel net à l'utilisateur."""
        if not hasattr(self, "output_box"):
            return
        try:
            base = PALETTE["border"]
            pulse_color = PALETTE["accent"]
            # Allume → laisse 350ms → éteint progressivement en 4 paliers
            self.output_box.configure(border_color=pulse_color)
            self.after(350, lambda: self.output_box.configure(border_color=PALETTE["violet"]))
            self.after(550, lambda: self.output_box.configure(border_color=PALETTE["accent"]))
            self.after(750, lambda: self.output_box.configure(border_color=base))
        except Exception:
            pass

    def _maybe_show_welcome(self) -> None:
        keys = self.settings.get("api_keys", {})
        any_key = any((v or "").strip() for v in keys.values())
        if any_key:
            return  # already configured, skip the onboarding
        WelcomeWindow(self, on_close=self._on_welcome_close)

    def _on_welcome_close(self, open_settings: bool) -> None:
        if open_settings:
            self.after(200, self._open_settings)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-Return>", lambda _e: self._on_generate())
        self.bind("<Control-s>", lambda _e: self._save_current())
        self.bind("<Control-e>", lambda _e: self._export_to_file())
        self.bind("<Control-l>", lambda _e: self._clear_megas())
        self.bind("<F1>", lambda _e: self._open_about())

    def _build_ui(self) -> None:
        # Main window uses grid (more deterministic than pack for fixed top/bottom
        # bars + expanding middle). Row 2 = body, weight=1 → fills leftover space.
        # Rows 0,1,3,4,5,6 = chrome, fixed heights.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Top bar with full Triskell branding
        topbar = ctk.CTkFrame(self, height=140, corner_radius=0, fg_color=PALETTE["panel"])
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)

        # Subtle bottom border line under the topbar
        border_line = ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"], corner_radius=0)
        border_line.grid(row=1, column=0, sticky="ew")

        brand_block = ctk.CTkFrame(topbar, fg_color="transparent", cursor="hand2")
        brand_block.pack(side="left", padx=20, pady=10)
        brand_block.bind("<Button-1>", lambda _e: self._open_about())

        # Triskell logo (3 spirals) rendered via PIL
        try:
            self._logo_img_topbar = ctk.CTkImage(
                light_image=_load_app_logo(120),
                dark_image=_load_app_logo(120),
                size=(120, 120),
            )
            logo = ctk.CTkLabel(
                brand_block, image=self._logo_img_topbar, text="", cursor="hand2",
            )
        except Exception as exc:
            logger.warning("logo render failed (%s) — fallback diamond", exc)
            logo = ctk.CTkLabel(
                brand_block, text="◆", font=(RESOLVED_DISPLAY, 26, "bold"),
                text_color=PALETTE["violet"], cursor="hand2",
            )
        logo.pack(side="left", padx=(0, 12))
        logo.bind("<Button-1>", lambda _e: self._open_about())

        # Wordmark: "triskell" + "STUDIO" matching site typography
        text_block = ctk.CTkFrame(brand_block, fg_color="transparent", cursor="hand2")
        text_block.pack(side="left")

        wordmark = ctk.CTkFrame(text_block, fg_color="transparent")
        wordmark.pack(anchor="w")
        ctk.CTkLabel(
            wordmark, text="triskell",
            font=(RESOLVED_DISPLAY, 19, "bold"),
            text_color=PALETTE["text_strong"],
            cursor="hand2",
        ).pack(side="left")
        ctk.CTkLabel(
            wordmark, text="  S T U D I O",
            font=(RESOLVED_BODY, 9, "bold"),
            text_color=PALETTE["muted"],
            cursor="hand2",
        ).pack(side="left", pady=(8, 0))

        ctk.CTkLabel(
            text_block,
            text=f"AlphaBeast  ·  {BRAND_VERSION}",
            font=(RESOLVED_BODY, 10),
            text_color=PALETTE["muted_dim"],
            anchor="w",
            cursor="hand2",
        ).pack(anchor="w")
        # Make every label in the brand block clickable
        for w in (text_block, wordmark, *wordmark.winfo_children(), *text_block.winfo_children()):
            try:
                w.bind("<Button-1>", lambda _e: self._open_about())
            except Exception:
                pass

        ctk.CTkButton(
            topbar,
            text="⚙  Paramètres",
            width=132, height=38,
            corner_radius=10,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg_hover"],
            command=self._open_settings,
        ).pack(side="right", padx=(6, 14), pady=14)
        ctk.CTkButton(
            topbar,
            text="🕘  Historique",
            width=132, height=38,
            corner_radius=10,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg_hover"],
            command=self._open_history,
        ).pack(side="right", padx=6, pady=14)
        ctk.CTkButton(
            topbar,
            text="📚  Bibliothèque",
            width=144, height=38,
            corner_radius=10,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["accent"],
            text_color=PALETTE["accent"],
            hover_color=PALETTE["accent_dim"],
            command=self._open_library,
        ).pack(side="right", padx=6, pady=14)
        # Toggle thème clair/sombre — pictogramme reflète le mode CIBLE
        # (soleil = passer en clair, lune = passer en sombre)
        theme_icon = "☀" if self.settings.get("appearance_mode", "dark") == "dark" else "🌙"
        ctk.CTkButton(
            topbar,
            text=theme_icon,
            width=38, height=38,
            corner_radius=19,
            font=(RESOLVED_BODY, 14, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg_hover"],
            command=self._toggle_theme,
        ).pack(side="right", padx=(6, 6), pady=14)
        ctk.CTkButton(
            topbar,
            text="?",
            width=38, height=38,
            corner_radius=19,
            font=(RESOLVED_BODY, 14, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg_hover"],
            command=self._open_welcome,
        ).pack(side="right", padx=(6, 6), pady=14)

        # Slogan centré dans l'espace libre de la topbar (entre le brand et les
        # boutons d'action). pack avec side="left", expand=True, fill="x" → la
        # zone résiduelle est avalée et le label se centre dedans.
        slogan = ctk.CTkLabel(
            topbar,
            text="Forge le prompt.  Dompte la bête.",
            font=(RESOLVED_DISPLAY, 16, "bold"),
            text_color=PALETTE["muted"],
        )
        slogan.pack(side="left", expand=True, fill="x", padx=20)

        # Main split
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=14, pady=14)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # LEFT - input + selection
        left = ctk.CTkFrame(
            body, corner_radius=12,
            fg_color=PALETTE["panel_alt"],
            border_width=1, border_color=PALETTE["border"],
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        # weight=1 laisse l'input absorber l'espace résiduel ; minsize=90 garantit
        # qu'il n'est jamais écrasé à 0 mais reste compact pour libérer de la place
        # au reste (8 cartes preset + tags + sélection active) sur petits écrans.
        # Le textarea scrolle en interne si l'utilisateur tape un prompt long.
        left.grid_rowconfigure(1, weight=1, minsize=90)

        input_header = ctk.CTkFrame(left, fg_color="transparent")
        input_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        input_header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            input_header, text=" 1 ",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent"], corner_radius=10,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        title1_wrap = ctk.CTkFrame(input_header, fg_color="transparent")
        title1_wrap.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            title1_wrap,
            text="Écris ton prompt de base",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left")
        ctk.CTkLabel(
            title1_wrap,
            text="  (décris ton besoin en langage naturel)",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).pack(side="left")
        self.input_count = ctk.CTkLabel(
            input_header,
            text="0 car.",
            font=(RESOLVED_BODY, 10),
            text_color=PALETTE["muted_dim"],
        )
        self.input_count.grid(row=0, column=2, sticky="e", padx=(0, 8))
        # Bouton "Effacer" — vide le textarea en 1 clic
        ctk.CTkButton(
            input_header, text="✕  Effacer",
            width=84, height=28,
            corner_radius=14,
            font=(RESOLVED_BODY, 10, "bold"),
            text_color=PALETTE["muted"],
            fg_color="transparent",
            hover_color=PALETTE["tag_bg_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=self._clear_input,
        ).grid(row=0, column=3, sticky="e")

        self.input_box = ctk.CTkTextbox(
            left,
            font=(RESOLVED_BODY, 15),
            wrap="word",
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
            height=100,  # initial hauteur ; l'expand de row 1 fait grossir si la place existe
        )
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))

        # Bouton "Améliorer le prompt de base" — flotte au coin bas-droit du textarea
        # (place in_=textbox → suit ses dimensions quand row 1 grandit). fg_color opaque
        # = panel_alt pour découper visuellement le bouton du fond du textarea.
        self.improve_btn = ctk.CTkButton(
            left, text="✨  Améliorer le prompt de base",
            width=210, height=30,
            corner_radius=15,
            font=(RESOLVED_BODY, 10, "bold"),
            text_color=PALETTE["accent"],
            text_color_disabled=PALETTE["accent"],
            fg_color=PALETTE["panel_alt"],
            hover_color=PALETTE["accent_dim"],
            border_width=1, border_color=PALETTE["accent"],
            command=self._improve_input,
        )
        self.improve_btn.place(
            in_=self.input_box, relx=1.0, rely=1.0, anchor="se", x=-10, y=-10,
        )
        self.input_box.bind("<KeyRelease>", lambda _e: self._update_input_count())
        # Subtle placeholder behavior
        self._input_placeholder = (
            "Ex: Code-moi une appli desktop qui... / Critique honnetement mon plan de... / "
            "Résume ce document...\n\n(Ctrl+Enter pour générer)"
        )
        self._show_input_placeholder()
        self.input_box.bind("<FocusIn>", self._on_input_focus_in)
        self.input_box.bind("<FocusOut>", self._on_input_focus_out)

        # Step 2 header
        step2_header = ctk.CTkFrame(left, fg_color="transparent")
        step2_header.grid(row=2, column=0, sticky="ew", padx=14, pady=(10, 4))
        step2_header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            step2_header, text=" 2 ",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["violet"], corner_radius=10,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        title2_wrap = ctk.CTkFrame(step2_header, fg_color="transparent")
        title2_wrap.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            title2_wrap,
            text="Choisis tes Mega Prompts",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left")
        ctk.CTkLabel(
            title2_wrap,
            text="  (active des comportements pour orienter l'IA)",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).pack(side="left")

        ctk.CTkLabel(
            left,
            text="Option A — un preset (combos recommandés) :",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).grid(row=3, column=0, sticky="w", padx=(46, 14), pady=(2, 4))

        presets_row = ctk.CTkFrame(
            left, corner_radius=8, fg_color=PALETTE["panel_card"],
        )
        presets_row.grid(row=4, column=0, sticky="ew", padx=(46, 14), pady=(0, 6))

        # Cartes preset : grille 2 colonnes × 4 rangées (8 combos), avec une
        # icône colorée à gauche et nom + phrase explicative à droite.
        # Hover : passe au fg coloré assorti (cohérent avec le badge gauche).
        per_row = 2
        presets_row.grid_columnconfigure(tuple(range(per_row)), weight=1, uniform="preset")

        for i, preset in enumerate(PRESETS):
            row, col = divmod(i, per_row)
            color_key = preset.get("color", "accent")
            preset_color = PALETTE.get(color_key, PALETTE["accent"])

            card = ctk.CTkFrame(
                presets_row,
                corner_radius=12,
                fg_color=PALETTE["panel_alt"],
                border_width=1,
                border_color=PALETTE["border_2"],
                cursor="hand2",
            )
            card.grid(row=row, column=col, sticky="ew", padx=6, pady=5)

            # Icône colorée dans une pastille — donne un vrai repère visuel
            icon_lbl = ctk.CTkLabel(
                card,
                text=preset.get("icon", "✦"),
                font=(RESOLVED_DISPLAY, 18, "bold"),
                text_color=preset_color,
                width=44, height=44,
                fg_color=PALETTE["panel_card"],
                corner_radius=10,
                cursor="hand2",
            )
            icon_lbl.pack(side="left", padx=(12, 10), pady=12)

            # Bloc texte : nom (gras, blanc) + phrase explicative (muted)
            text_block = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
            text_block.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=10)

            name_lbl = ctk.CTkLabel(
                text_block,
                text=preset["name"],
                font=(RESOLVED_BODY, 13, "bold"),
                text_color=PALETTE["text_strong"],
                anchor="w",
                cursor="hand2",
            )
            name_lbl.pack(fill="x", anchor="w")

            desc_lbl = ctk.CTkLabel(
                text_block,
                text=preset["desc"],
                font=(RESOLVED_BODY, 10),
                text_color=PALETTE["muted"],
                anchor="w",
                justify="left",
                wraplength=280,
                cursor="hand2",
            )
            desc_lbl.pack(fill="x", anchor="w", pady=(2, 0))

            def _apply(_e, p=preset):
                self._apply_preset(p)
            def _enter(_e, c=card, ic=icon_lbl, col=preset_color):
                # Fondu de la bordure border_2 → couleur de catégorie + bg snap
                self._animate_attr(c, "border_color", PALETTE["border_2"], col, frames=6, interval=20)
                c.configure(fg_color=PALETTE["tag_bg"])
                ic.configure(fg_color=PALETTE["panel_alt"])
            def _leave(_e, c=card, ic=icon_lbl, col=preset_color):
                self._animate_attr(c, "border_color", col, PALETTE["border_2"], frames=6, interval=20)
                c.configure(fg_color=PALETTE["panel_alt"])
                ic.configure(fg_color=PALETTE["panel_card"])
            for w in (card, icon_lbl, text_block, name_lbl, desc_lbl):
                w.bind("<Button-1>", _apply)
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)

        # Mega selector row
        sel_row = ctk.CTkFrame(left, fg_color="transparent")
        sel_row.grid(row=5, column=0, sticky="ew", padx=(46, 14), pady=(4, 6))
        sel_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sel_row,
            text=f"Option B — un par un parmi {len(self.mega_prompts)} :",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).grid(row=0, column=0, sticky="w", columnspan=3)

        mega_names = [
            f"{mp['id']}  ·  {mp['name']}  —  {mp.get('tagline', '')}"
            for mp in self.mega_prompts
        ]
        self._mega_label_to_id = {
            label: mp["id"] for label, mp in zip(mega_names, self.mega_prompts)
        }
        self.mega_var = ctk.StringVar(
            value=mega_names[0] if mega_names else "(aucun)"
        )
        self.mega_dropdown = ctk.CTkOptionMenu(
            sel_row,
            values=mega_names or ["(aucun)"],
            variable=self.mega_var,
            width=560,
            height=36,
            font=(RESOLVED_BODY, 12),
            dropdown_font=(RESOLVED_BODY, 12),
            fg_color=PALETTE["tag_bg"],
            button_color=PALETTE["accent"],
            button_hover_color=PALETTE["accent_hover"],
            dropdown_fg_color=PALETTE["panel_card"],
            dropdown_text_color=PALETTE["text"],
            dropdown_hover_color=PALETTE["accent_dim"],
        )
        self.mega_dropdown.grid(row=1, column=0, sticky="w", pady=(4, 0))
        ctk.CTkButton(
            sel_row,
            text="+  Ajouter",
            width=118, height=36,
            corner_radius=12,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            text_color=PALETTE["accent"],
            hover_color=PALETTE["accent_dim"],
            command=self._on_add_mega,
            border_width=1,
            border_color=PALETTE["accent"],
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        ctk.CTkButton(
            sel_row,
            text="Tout retirer",
            width=118, height=36,
            corner_radius=12,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg_hover"],
            command=self._clear_megas,
        ).grid(row=1, column=2, sticky="w", padx=(6, 0), pady=(4, 0))

        # Tags container — visual feedback of step 2
        tags_header = ctk.CTkFrame(left, fg_color="transparent")
        tags_header.grid(row=6, column=0, sticky="ew", padx=(46, 14), pady=(8, 4))
        tags_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            tags_header,
            text="↓  Selection active",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["muted"],
        ).grid(row=0, column=0, sticky="w")
        self.tags_count = ctk.CTkLabel(
            tags_header,
            text="0 / 16",
            font=(RESOLVED_BODY, 10, "bold"),
            text_color=PALETTE["violet"],
        )
        self.tags_count.grid(row=0, column=1, sticky="e")

        self.tags_frame = ctk.CTkScrollableFrame(
            left, height=100, corner_radius=8, fg_color=PALETTE["panel_card"]
        )
        self.tags_frame.grid(row=7, column=0, sticky="ew", padx=(46, 14), pady=(0, 12))

        # Step 3 lives in a sticky bar pinned at the bottom of the window
        # (built after the footer below) — keeps the primary CTA always visible
        # quel que soit le redimensionnement du panneau gauche.

        # RIGHT - output + send controls
        right = ctk.CTkFrame(
            body, corner_radius=12,
            fg_color=PALETTE["panel_alt"],
            border_width=1, border_color=PALETTE["border"],
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        header_row = ctk.CTkFrame(right, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 4))
        header_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            header_row, text=" 4 ",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["violet"], corner_radius=10,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        title4_wrap = ctk.CTkFrame(header_row, fg_color="transparent")
        title4_wrap.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            title4_wrap, text="Prompt Ultime",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left")
        ctk.CTkLabel(
            title4_wrap,
            text="  (résultat prêt à copier, sauvegarder ou envoyer à l'IA)",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).pack(side="left")
        self.output_count = ctk.CTkLabel(
            header_row,
            text="",
            font=(RESOLVED_BODY, 10),
            text_color=PALETTE["muted_dim"],
        )
        self.output_count.grid(row=0, column=2, sticky="e", padx=(0, 10))
        # status_label : widget conservé en mémoire pour que _set_status() et
        # le loader ne cassent pas, MAIS pas affiché (le label "Prêt" en
        # permanence dans le header était visuellement bruyant).
        self.status_label = ctk.CTkLabel(
            header_row,
            text="",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["ok"],
        )
        # Bouton "Effacer" la sortie
        ctk.CTkButton(
            header_row, text="✕  Effacer",
            width=84, height=28,
            corner_radius=14,
            font=(RESOLVED_BODY, 10, "bold"),
            text_color=PALETTE["muted"],
            fg_color="transparent",
            hover_color=PALETTE["tag_bg_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=self._clear_output,
        ).grid(row=0, column=4, sticky="e", padx=(0, 6))
        ctk.CTkButton(
            header_row,
            text="⤓",
            width=28,
            height=28,
            corner_radius=14,
            font=(RESOLVED_BODY, 14, "bold"),
            fg_color="transparent",
            text_color=PALETTE["text"],
            hover_color=PALETTE["tag_bg"],
            command=self._export_to_file,
            border_width=1,
            border_color=PALETTE["border_2"],
        ).grid(row=0, column=5, sticky="e")

        self.output_box = ctk.CTkTextbox(
            right,
            font=(FONT_MONO, 14),
            wrap="word",
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.output_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))

        # Preview container : occupe la même cellule que output_box, mais en
        # mode CTkLabel stackés (couleurs et polices garanties — les tags Tk
        # sur CTkTextbox ne survivent pas à l'appearance system de CTk).
        # Visible quand _output_empty=True, masqué pendant l'affichage du prompt.
        self.preview_container = ctk.CTkScrollableFrame(
            right,
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.preview_container.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self.output_box.grid_remove()  # par défaut on montre l'aperçu structure
        self._show_output_empty_state()

        # Send to AI controls
        send_row = ctk.CTkFrame(right, fg_color="transparent")
        send_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))
        send_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            send_row,
            text="IA :",
            font=(RESOLVED_BODY, 12),
            text_color=PALETTE["muted"],
        ).grid(row=0, column=0, sticky="w")
        provider_labels = [PROVIDERS[k]["label"] for k in PROVIDERS]
        self._provider_label_to_id = {PROVIDERS[k]["label"]: k for k in PROVIDERS}
        current_pid = self.settings.get("selected_provider", "anthropic")
        current_label = PROVIDERS.get(current_pid, list(PROVIDERS.values())[0])["label"]

        self.provider_var = ctk.StringVar(value=current_label)
        self.provider_menu = ctk.CTkOptionMenu(
            send_row,
            values=provider_labels,
            variable=self.provider_var,
            command=self._on_provider_change,
            fg_color=PALETTE["tag_bg"],
            button_color=PALETTE["accent"],
            button_hover_color=PALETTE["accent_hover"],
        )
        self.provider_menu.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        self.model_var = ctk.StringVar()
        self.model_menu = ctk.CTkOptionMenu(
            send_row,
            values=["(modele)"],
            variable=self.model_var,
            fg_color=PALETTE["tag_bg"],
            button_color=PALETTE["accent"],
            button_hover_color=PALETTE["accent_hover"],
            width=220,
        )
        self.model_menu.grid(row=0, column=2, sticky="e")
        self._refresh_model_menu(current_pid)

        # Bottom action row
        bottom = ctk.CTkFrame(right, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 12))
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            bottom,
            text="📋  Copier",
            command=self._copy_ultimate,
            fg_color=PALETTE["tag_bg"],
            hover_color=PALETTE["tag_bg_hover"],
            text_color=PALETTE["text"],
            height=44,
            corner_radius=12,
            font=(RESOLVED_BODY, 12, "bold"),
            border_width=1,
            border_color=PALETTE["border_2"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            bottom,
            text="💾  Sauvegarder",
            command=self._save_current,
            fg_color=PALETTE["tag_bg"],
            hover_color=PALETTE["tag_bg_hover"],
            text_color=PALETTE["text"],
            height=44,
            corner_radius=12,
            font=(RESOLVED_BODY, 12, "bold"),
            border_width=1,
            border_color=PALETTE["border_2"],
        ).grid(row=0, column=1, sticky="ew", padx=4)
        self.send_btn = ctk.CTkButton(
            bottom,
            text="🚀  Envoyer a l'IA",
            command=self._on_send,
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            text_color=PALETTE["text_strong"],
            height=44,
            corner_radius=12,
            font=(RESOLVED_BODY, 13, "bold"),
            border_width=0,
        )
        self.send_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # Step 3 sticky bar (row 3 + 4) — pinned above the footer.
        # Refonte v1.5.2 : suppression du badge "3" + sous-titre redondant. La barre
        # devient une zone CTA pure : un seul bouton hero qui occupe toute la largeur,
        # text dynamique (mute par _update_generate_state quand pas prêt). Plus impactant
        # qu'un petit bouton serré contre 3 labels qui se concurrencent.
        step3_bar_border = ctk.CTkFrame(
            self, height=1, corner_radius=0, fg_color=PALETTE["border"]
        )
        step3_bar_border.grid(row=3, column=0, sticky="ew")
        step3_bar = ctk.CTkFrame(
            self, height=84, corner_radius=0, fg_color=PALETTE["panel_alt"]
        )
        step3_bar.grid(row=4, column=0, sticky="ew")
        step3_bar.grid_propagate(False)

        self.generate_btn = ctk.CTkButton(
            step3_bar,
            text="✨   Générer    (Ctrl+Enter)",
            height=56,
            corner_radius=14,
            font=(RESOLVED_DISPLAY, 16, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent_dim"],
            hover_color=PALETTE["accent"],
            command=self._on_generate,
            border_width=0,
        )
        self.generate_btn.pack(fill="both", expand=True, padx=24, pady=14)

        # Footer brand line with mini logo + wordmark + clickable URL (rows 5 + 6)
        footer_border = ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"], corner_radius=0)
        footer_border.grid(row=5, column=0, sticky="ew")
        footer = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=PALETTE["panel"])
        footer.grid(row=6, column=0, sticky="ew")
        footer.grid_propagate(False)

        footer_left = ctk.CTkFrame(footer, fg_color="transparent")
        footer_left.pack(side="left", padx=18)

        try:
            self._logo_img_footer = ctk.CTkImage(
                light_image=_load_app_logo(18),
                dark_image=_load_app_logo(18),
                size=(18, 18),
            )
            ctk.CTkLabel(footer_left, image=self._logo_img_footer, text="").pack(
                side="left", padx=(0, 8), pady=2
            )
        except Exception:
            pass

        ctk.CTkLabel(
            footer_left, text="triskell",
            font=(RESOLVED_DISPLAY, 10, "bold"),
            text_color=PALETTE["text_strong"],
        ).pack(side="left")
        ctk.CTkLabel(
            footer_left, text="  STUDIO  ·  ",
            font=(RESOLVED_BODY, 8, "bold"),
            text_color=PALETTE["muted"],
        ).pack(side="left", pady=(2, 0))
        link_lbl = ctk.CTkLabel(
            footer_left,
            text="triskell-studio.fr",
            font=(RESOLVED_BODY, 9, "bold", "underline"),
            text_color=PALETTE["brand"],
            cursor="hand2",
        )
        link_lbl.pack(side="left")
        link_lbl.bind("<Button-1>", lambda _e: webbrowser.open(BRAND_URL))
        ctk.CTkLabel(
            footer_left,
            text=f"  ·  {len(self.mega_prompts)} Mega Prompts",
            font=(RESOLVED_BODY, 9),
            text_color=PALETTE["muted_dim"],
        ).pack(side="left")
        ctk.CTkLabel(
            footer,
            text=(
                "Ctrl+Enter Générer  ·  Ctrl+S Sauvegarder  ·  Ctrl+E Exporter"
                "  ·  Ctrl+L Tout retirer  ·  F1 A propos"
            ),
            font=(RESOLVED_BODY, 9),
            text_color=PALETTE["muted_dim"],
        ).pack(side="right", padx=18)

        self._refresh_tags()
        self._update_input_count()

    # --------------- Mega prompt selection ---------------

    def _on_add_mega(self) -> None:
        choice = self.mega_var.get()
        if not choice or choice == "(aucun)":
            return
        mp_id = self._mega_label_to_id.get(choice)
        if mp_id is None:
            return
        mp = next((m for m in self.mega_prompts if m["id"] == mp_id), None)
        if mp is None:
            return
        if any(m["id"] == mp["id"] for m in self.selected_megas):
            self._set_status(f"Deja selectionne : {mp['name']}.", warn=True)
            return
        self.selected_megas.append(mp)
        self._refresh_tags()
        self._set_status(f"Ajoute : {mp['name']}.", ok=True)

    def _remove_mega(self, mp: dict) -> None:
        self.selected_megas = [m for m in self.selected_megas if m["id"] != mp["id"]]
        self._refresh_tags()

    def _clear_megas(self) -> None:
        self.selected_megas = []
        self._refresh_tags()

    def _clear_input(self) -> None:
        """Vide le textarea du prompt de base. Bouton ✕ Effacer du panneau 1."""
        try:
            self.input_box.delete("1.0", "end")
            self._update_input_count()
            self._show_input_placeholder()
            self._set_status("Prompt effacé.")
        except Exception as exc:
            logger.warning("clear input failed: %s", exc)

    _IMPROVE_META_PROMPT = (
        "Tu es un expert en ingénierie de prompts. L'utilisateur a écrit un "
        "brouillon de prompt de base. Ta mission : reformuler ce brouillon en "
        "un prompt plus clair, plus précis et plus complet, sans changer son "
        "intention.\n\n"
        "Règles strictes :\n"
        "- Garde la langue d'origine de l'utilisateur.\n"
        "- Reste fidèle à l'intention initiale — ne fais pas dévier le sujet, "
        "n'invente pas de contraintes que l'utilisateur n'a pas mentionnées.\n"
        "- Ajoute la structure, le contexte et les précisions qui manquent "
        "souvent : objectif, livrable attendu, format de sortie, contraintes, "
        "audience, ton/style si pertinent.\n"
        "- Si le brouillon est déjà détaillé, contente-toi de le polir et de "
        "le structurer (paragraphes, puces).\n"
        "- Ne rajoute AUCUN méta-commentaire, AUCUNE explication, AUCUN "
        "préambule type \"Voici la version améliorée :\", AUCUNE balise "
        "markdown englobante, AUCUN guillemet autour du résultat.\n"
        "- Réponds UNIQUEMENT par le prompt amélioré, brut, prêt à être collé "
        "dans une zone de texte.\n\n"
        "Brouillon de l'utilisateur :\n"
        "<<<\n{user_prompt}\n>>>"
    )

    def _improve_input(self) -> None:
        """Envoie le prompt de base à l'IA pour le développer/structurer,
        puis remplace le contenu du textarea par la version améliorée."""
        if getattr(self, "_input_has_placeholder", False):
            self._set_status("Écris d'abord un brouillon à améliorer.", warn=True)
            return
        user = self.input_box.get("1.0", "end").strip()
        if not user:
            self._set_status("Écris d'abord un brouillon à améliorer.", warn=True)
            return

        provider_id = self._provider_label_to_id.get(
            self.provider_var.get(), "anthropic"
        )
        model = self.model_var.get()
        api_keys = self.settings.get("api_keys", {})
        meta = self._IMPROVE_META_PROMPT.format(user_prompt=user)

        self.improve_btn.configure(state="disabled")
        self._start_improve_animation()
        try:
            self.generate_btn.configure(state="disabled")
        except Exception:
            pass
        self._set_status(f"Amélioration du prompt via {provider_id} / {model}...")
        self._start_loading_indicator()

        def worker() -> None:
            try:
                resp = send_to_provider(provider_id, model, meta, api_keys)
            except ProviderError as exc:
                self.after(0, lambda: self._on_improve_error(str(exc)))
                return
            except Exception as exc:
                logger.exception("unexpected provider error during improve")
                self.after(0, lambda: self._on_improve_error(f"Erreur inattendue: {exc}"))
                return
            self.after(0, lambda: self._on_improve_ok(resp))

        threading.Thread(target=worker, daemon=True).start()

    def _on_improve_ok(self, resp: str) -> None:
        self._stop_loading_indicator()
        self._stop_improve_animation()
        self.improve_btn.configure(state="normal", text="✨  Améliorer le prompt de base")
        try:
            self.generate_btn.configure(state="normal")
        except Exception:
            pass
        improved = (resp or "").strip()
        # Strip stray markdown fences or wrapping quotes some models add despite instructions
        if improved.startswith("```") and improved.endswith("```"):
            inner = improved[3:-3].strip()
            if "\n" in inner:
                first_line, rest = inner.split("\n", 1)
                if first_line.strip().isalpha() and len(first_line.strip()) <= 20:
                    inner = rest
            improved = inner.strip()
        if len(improved) >= 2 and improved[0] == improved[-1] and improved[0] in ('"', "'", "«", "»"):
            improved = improved[1:-1].strip()
        if not improved:
            self._set_status("L'IA a renvoyé une réponse vide.", warn=True)
            return
        self._input_has_placeholder = False
        self.input_box.delete("1.0", "end")
        self.input_box.configure(text_color=PALETTE["text"])
        self.input_box.insert("1.0", improved)
        self._update_input_count()
        self._set_status("Prompt amélioré.", ok=True)

    def _on_improve_error(self, msg: str) -> None:
        self._stop_loading_indicator()
        self._stop_improve_animation()
        self.improve_btn.configure(state="normal", text="✨  Améliorer le prompt de base")
        try:
            self.generate_btn.configure(state="normal")
        except Exception:
            pass
        self._set_status(msg, warn=True)
        messagebox.showerror("Erreur amélioration", msg)

    def _clear_output(self) -> None:
        """Vide le textarea du prompt ultime généré. Bouton ✕ Effacer du panneau 4."""
        try:
            self.output_box.configure(state="normal")
            self.output_box.delete("1.0", "end")
            self.output_box.configure(state="disabled")
            self.current_ultimate = ""
            try:
                self.output_count.configure(text="")
            except Exception:
                pass
            self._set_status("Sortie effacée.")
        except Exception as exc:
            logger.warning("clear output failed: %s", exc)

    def _refresh_tags(self) -> None:
        for w in self.tags_frame.winfo_children():
            w.destroy()
        n = len(self.selected_megas)
        self.tags_count.configure(
            text=f"{n} / 16",
            text_color=PALETTE["violet"] if n > 0 else PALETTE["muted_dim"],
        )
        if not self.selected_megas:
            empty = ctk.CTkLabel(
                self.tags_frame,
                text=(
                    "Aucun Méga-prompt actif. Pioche un preset ci-dessus, "
                    "ou ajoute-en individuellement."
                ),
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted_dim"],
            )
            empty.pack(anchor="w", padx=12, pady=18)
            self._update_generate_state()
            self._refresh_structure_preview()
            return
        per_row = 2
        row_frames: list[ctk.CTkFrame] = []
        for i, mp in enumerate(self.selected_megas):
            if i % per_row == 0:
                rf = ctk.CTkFrame(self.tags_frame, fg_color="transparent")
                rf.pack(fill="x", padx=4, pady=3)
                row_frames.append(rf)
            TagWidget(
                row_frames[-1],
                mp,
                on_remove=self._remove_mega,
                on_preview=self._preview_mega,
            ).pack(side="left", padx=4, pady=2, fill="x", expand=True)
        self._update_generate_state()
        self._refresh_structure_preview()

    def _refresh_structure_preview(self) -> None:
        """Si l'utilisateur n'a pas encore généré, on rafraîchit l'aperçu de
        structure du panneau 4 pour qu'il reflète la sélection en cours."""
        if getattr(self, "_output_empty", True) and hasattr(self, "output_box"):
            self._show_output_empty_state()

    def _apply_preset(self, preset: dict) -> None:
        self.selected_megas = [m for m in self.mega_prompts if m["id"] in preset["ids"]]
        self._refresh_tags()
        self._set_status(f"Preset applique : {preset['name']} — {preset['desc']}.", ok=True)

    def _preview_mega(self, mp: dict) -> None:
        PreviewWindow(self, mp)

    # --------------- Generation & actions ---------------

    def _on_generate(self) -> None:
        if getattr(self, "_input_has_placeholder", False):
            self._set_status("Ecris un prompt de base d'abord.", warn=True)
            return
        user = self.input_box.get("1.0", "end").strip()
        if not user:
            self._set_status("Ecris un prompt de base d'abord.", warn=True)
            return
        try:
            self.current_ultimate = build_ultimate_prompt(user, self.selected_megas)
        except (ValueError, TypeError) as exc:
            self._set_status(f"Erreur: {exc}", warn=True)
            return
        self._output_empty = False
        self._swap_to_output()
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", self.current_ultimate)
        self._update_output_count()
        n = len(self.selected_megas)
        self._set_status(
            f"Prompt ultime genere ({n} mega prompt{'s' if n != 1 else ''}).",
            ok=True,
        )
        self._pulse_output_border()
        try:
            config.append_history(
                {
                    "title": (user[:60] + ("..." if len(user) > 60 else "")),
                    "user_prompt": user,
                    "mega_ids": [m["id"] for m in self.selected_megas],
                    "ultimate_prompt": self.current_ultimate,
                    "timestamp": _now_str(),
                },
                limit=int(self.settings.get("history_limit", 20) or 20),
            )
        except OSError as exc:
            logger.warning("history append failed: %s", exc)

    def _copy_ultimate(self) -> None:
        if getattr(self, "_output_empty", False):
            self._set_status("Rien a copier — genere d'abord un prompt.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Rien a copier.", warn=True)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self._set_status("Prompt ultime copie dans le presse-papier.", ok=True)

    def _save_current(self) -> None:
        if getattr(self, "_output_empty", False):
            self._set_status("Génère un prompt avant de sauvegarder.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Génère un prompt avant de sauvegarder.", warn=True)
            return
        items = config.load_saved_prompts()
        if getattr(self, "_input_has_placeholder", False):
            title = f"Prompt {_now_str()}"
        else:
            title = (
                self.input_box.get("1.0", "end").strip()[:60]
                or f"Prompt {_now_str()}"
            )
        items.insert(
            0,
            {
                "title": title,
                "ultimate_prompt": text,
                "mega_ids": [m["id"] for m in self.selected_megas],
                "timestamp": _now_str(),
            },
        )
        try:
            config.save_saved_prompts(items)
            self._set_status("Prompt ultime sauvegarde.", ok=True)
        except OSError as exc:
            self._set_status(f"Erreur sauvegarde: {exc}", warn=True)

    def _on_send(self) -> None:
        if getattr(self, "_output_empty", False):
            self._set_status("Génère d'abord un prompt ultime.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Génère d'abord un prompt ultime.", warn=True)
            return
        provider_id = self._provider_label_to_id.get(
            self.provider_var.get(), "anthropic"
        )
        model = self.model_var.get()
        api_keys = self.settings.get("api_keys", {})

        self.send_btn.configure(state="disabled", text="⏳  Envoi en cours...")
        self.generate_btn.configure(state="disabled")
        self._set_status(f"Appel a {provider_id} / {model}...")
        self._start_loading_indicator()

        def worker() -> None:
            try:
                resp = send_to_provider(provider_id, model, text, api_keys)
            except ProviderError as exc:
                self.after(0, lambda: self._on_send_error(str(exc)))
                return
            except Exception as exc:  # safety net
                logger.exception("unexpected provider error")
                self.after(0, lambda: self._on_send_error(f"Erreur inattendue: {exc}"))
                return
            self.after(0, lambda: self._on_send_ok(resp, provider_id, model))

        threading.Thread(target=worker, daemon=True).start()

    def _on_send_ok(self, resp: str, provider_id: str, model: str) -> None:
        self._stop_loading_indicator()
        self.send_btn.configure(state="normal", text="🚀  Envoyer a l'IA")
        self.generate_btn.configure(state="normal")
        self._set_status(f"Reponse recue de {provider_id}.", ok=True)
        ResponseWindow(
            self,
            f"Reponse - {provider_id} / {model}",
            resp,
            provider_id=provider_id,
            model=model,
        )

    def _on_send_error(self, msg: str) -> None:
        self._stop_loading_indicator()
        self.send_btn.configure(state="normal", text="🚀  Envoyer a l'IA")
        self.generate_btn.configure(state="normal")
        self._set_status(msg, warn=True)
        messagebox.showerror("Erreur IA", msg)

    # ----- Animation du bouton "Améliorer le prompt" -----
    # Spinner qui tourne + nombre de points qui varie, refresh ~120ms.
    # Sans ça, les ~10s d'attente IA laissent croire que l'app a planté.

    _IMPROVE_SPINNER_FRAMES = ("◐", "◓", "◑", "◒")

    def _start_improve_animation(self) -> None:
        self._improve_animating = True
        self._improve_anim_phase = 0
        self._tick_improve_animation()

    def _stop_improve_animation(self) -> None:
        self._improve_animating = False

    def _tick_improve_animation(self) -> None:
        if not getattr(self, "_improve_animating", False):
            return
        phase = self._improve_anim_phase
        frame = self._IMPROVE_SPINNER_FRAMES[phase % len(self._IMPROVE_SPINNER_FRAMES)]
        dots = "." * (1 + (phase % 3))
        try:
            self.improve_btn.configure(text=f"{frame}  Amélioration en cours{dots}")
        except Exception:
            return
        self._improve_anim_phase = phase + 1
        self.after(120, self._tick_improve_animation)

    # ----- Loading indicator (spinner-like animation in status label) -----

    def _start_loading_indicator(self) -> None:
        self._loading = True
        self._loading_phase = 0
        self._tick_loading()

    def _stop_loading_indicator(self) -> None:
        self._loading = False

    def _tick_loading(self) -> None:
        if not getattr(self, "_loading", False):
            return
        # Trois points qui pulsent en vague — chaque point a sa propre phase,
        # décalée de 1 tick → effet "Knight Rider" lisible et fluide.
        DOT_FULL = "●"
        DOT_DIM = "·"
        phase = self._loading_phase % 6
        # Pour 3 dots, on veut 3 phases "actives" successives, puis 3 inactives
        dots = []
        for i in range(3):
            # Le dot i s'allume à la phase i, s'éteint à la phase i+3
            on = (phase % 6) in (i, i + 1)  # chaque dot reste allumé 2 ticks
            dots.append(DOT_FULL if on else DOT_DIM)
        prefix = " ".join(dots)
        self._loading_phase += 1
        current = self.status_label.cget("text")
        # Strip de l'ancien préfixe (icônes ou loading dots)
        rest = current.lstrip("●✓⚠◐◓◑◒· ")
        self.status_label.configure(
            text=f"{prefix}   {rest}", text_color=PALETTE["accent"]
        )
        self.after(160, self._tick_loading)

    # --------------- Provider/model handling ---------------

    def _on_provider_change(self, label: str) -> None:
        pid = self._provider_label_to_id.get(label, "anthropic")
        self.settings["selected_provider"] = pid
        self._refresh_model_menu(pid)
        try:
            config.save_settings(self.settings)
        except OSError as exc:
            logger.warning("settings save failed: %s", exc)

    def _refresh_model_menu(self, provider_id: str) -> None:
        models = PROVIDERS.get(provider_id, {}).get("models", [])
        if not models:
            models = ["(aucun)"]
        self.model_menu.configure(values=models)
        current = self.settings.get("selected_model", "")
        if current in models:
            self.model_var.set(current)
        else:
            self.model_var.set(models[0])
            self.settings["selected_model"] = models[0]

    # --------------- History dialog ---------------

    def _open_settings(self) -> None:
        SettingsWindow(self, self.settings, on_save=self._on_settings_saved)

    def _on_global_update_status(self, st) -> None:
        try:
            self.after(0, self._render_global_update, st)
        except Exception:
            pass

    def _render_global_update(self, st) -> None:
        if not self.winfo_exists():
            return
        if st.phase == "ready":
            self._set_status(
                f"Mise à jour v{st.next_version} prête — voir Paramètres pour installer",
                ok=True,
            )
        elif st.phase == "available":
            self._set_status(
                f"Mise à jour v{st.next_version} disponible - telechargement en cours",
            )

    def _on_settings_saved(self, settings: dict) -> None:
        self.settings = settings
        self._set_status("Paramètres enregistrés.")

    def _open_history(self) -> None:
        HistoryWindow(self, on_load=self._load_from_history)

    def _open_about(self) -> None:
        AboutWindow(self)

    def _open_welcome(self) -> None:
        WelcomeWindow(self, on_close=lambda open_settings=False: (
            self.after(200, self._open_settings) if open_settings else None
        ))

    def _open_library(self) -> None:
        LibraryWindow(self, list(self.mega_prompts), on_change=self._on_library_change)

    def _on_library_change(self, mega_prompts: list[dict]) -> None:
        """Called when the library was modified (CRUD). Refresh main UI bits."""
        self.mega_prompts = mega_prompts
        # Drop selected megas that no longer exist
        existing_ids = {m["id"] for m in mega_prompts}
        self.selected_megas = [m for m in self.selected_megas if m["id"] in existing_ids]
        # Refresh dropdown values
        self._refresh_mega_dropdown()
        self._refresh_tags()
        self._set_status("Bibliotheque mise a jour.", ok=True)

    def _refresh_mega_dropdown(self) -> None:
        mega_names = [
            f"{mp['id']}  ·  {mp['name']}  —  {mp.get('tagline', '')}"
            for mp in self.mega_prompts
        ]
        self._mega_label_to_id = {
            label: mp["id"] for label, mp in zip(mega_names, self.mega_prompts)
        }
        if not mega_names:
            mega_names = ["(aucun)"]
        self.mega_dropdown.configure(values=mega_names)
        if self.mega_var.get() not in mega_names:
            self.mega_var.set(mega_names[0])

    def _export_to_file(self) -> None:
        if getattr(self, "_output_empty", False):
            self._set_status("Génère d'abord un prompt avant d'exporter.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Rien à exporter.", warn=True)
            return
        path = filedialog.asksaveasfilename(
            title="Exporter le Prompt Ultime",
            defaultextension=".txt",
            initialfile=f"prompt_ultime_{_now_str().replace(':', '-').replace(' ', '_')}.txt",
            filetypes=[("Texte", "*.txt"), ("Markdown", "*.md"), ("Tout fichier", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self._set_status(f"Exporte : {path}", ok=True)
        except OSError as exc:
            self._set_status(f"Erreur export: {exc}", warn=True)
            messagebox.showerror("Erreur", f"Export impossible: {exc}")

    def _load_from_history(self, entry: dict) -> None:
        user_prompt = entry.get("user_prompt") or ""
        ultimate = entry.get("ultimate_prompt") or ""
        if user_prompt:
            self._input_has_placeholder = False
            self.input_box.delete("1.0", "end")
            self.input_box.configure(text_color=PALETTE["tag_fg"])
            self.input_box.insert("1.0", user_prompt)
        if ultimate:
            self._output_empty = False
            self._swap_to_output()
            self.output_box.delete("1.0", "end")
            self.output_box.insert("1.0", ultimate)
            self.current_ultimate = ultimate
            self._update_output_count()
        ids = entry.get("mega_ids") or []
        self.selected_megas = [m for m in self.mega_prompts if m["id"] in ids]
        self._refresh_tags()
        self._update_input_count()
        self._set_status("Charge depuis l'historique.", ok=True)

    # --------------- Status helper ---------------

    def _set_status(self, text: str, warn: bool = False, ok: bool = False) -> None:
        if warn:
            color = PALETTE["danger"]
            prefix = "⚠  "
        elif ok:
            color = PALETTE["ok"]
            prefix = "✓  "
        else:
            color = PALETTE["muted"]
            prefix = "●  "
        self.status_label.configure(text=prefix + text, text_color=color)

    # ----- Input placeholder + counters -----

    def _show_input_placeholder(self) -> None:
        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", self._input_placeholder)
        self.input_box.configure(text_color=PALETTE["muted"])
        self._input_has_placeholder = True

    def _on_input_focus_in(self, _e=None) -> None:
        if getattr(self, "_input_has_placeholder", False):
            self.input_box.delete("1.0", "end")
            self.input_box.configure(text_color=PALETTE["text"])
            self._input_has_placeholder = False

    def _on_input_focus_out(self, _e=None) -> None:
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            self._show_input_placeholder()
        self._update_input_count()

    def _update_generate_state(self) -> None:
        """Reflect readiness in the Generate button: ready (vivid) vs not (dim)."""
        if not hasattr(self, "generate_btn"):
            return
        has_input = (
            not getattr(self, "_input_has_placeholder", True)
            and bool(self.input_box.get("1.0", "end").strip())
        )
        has_megas = bool(self.selected_megas)
        ready = has_input and has_megas

        if ready:
            self.generate_btn.configure(
                fg_color=PALETTE["orange"],
                hover_color="#EA580C",  # orange-600, légère assombrissement au survol
                text="✨   Generer le Prompt Ultime    (Ctrl+Enter)",
                state="normal",
                text_color=PALETTE["text_strong"],
            )
            self._start_generate_breathing()
        elif has_input and not has_megas:
            self._stop_generate_breathing()
            self.generate_btn.configure(
                fg_color=PALETTE["accent_dim"],
                hover_color=PALETTE["accent"],
                text="↑  Choisis au moins un Mega Prompt",
                state="normal",
                text_color=PALETTE["muted"],
            )
        elif not has_input and has_megas:
            self._stop_generate_breathing()
            self.generate_btn.configure(
                fg_color=PALETTE["accent_dim"],
                hover_color=PALETTE["accent"],
                text="↑  Ecris d'abord ton prompt de base",
                state="normal",
                text_color=PALETTE["muted"],
            )
        else:
            self._stop_generate_breathing()
            self.generate_btn.configure(
                fg_color=PALETTE["accent_dim"],
                hover_color=PALETTE["accent"],
                text="✨   Générer    (Ctrl+Enter)",
                state="normal",
                text_color=PALETTE["muted"],
            )

    def _update_input_count(self) -> None:
        if getattr(self, "_input_has_placeholder", False):
            self.input_count.configure(text="0 car.", text_color=PALETTE["muted_dim"])
            self._update_generate_state()
            self._refresh_structure_preview()
            return
        text = self.input_box.get("1.0", "end").rstrip("\n")
        n = len(text)
        words = len(text.split())
        self.input_count.configure(
            text=f"{n} car. · {words} mots",
            text_color=PALETTE["muted"] if n > 0 else PALETTE["muted_dim"],
        )
        self._update_generate_state()
        self._refresh_structure_preview()

    def _update_output_count(self) -> None:
        text = self.output_box.get("1.0", "end").rstrip("\n")
        if getattr(self, "_output_empty", False):
            self.output_count.configure(text="")
            return
        n = len(text)
        words = len(text.split())
        # Rough heuristic: ~4 chars per token (English/French)
        tokens = max(1, n // 4)
        self.output_count.configure(text=f"{n} car. · {words} mots · ~{tokens} tokens")

    def _swap_to_preview(self) -> None:
        """Affiche le preview_container (CTkLabels colorés) à la place de
        output_box. Utilisé quand on est en empty-state."""
        try:
            self.output_box.grid_remove()
            self.preview_container.grid()
        except Exception:
            pass

    def _swap_to_output(self) -> None:
        """Affiche output_box (texte brut du Prompt Ultime généré) à la place
        du preview_container. Utilisé après une génération."""
        try:
            self.preview_container.grid_remove()
            self.output_box.grid()
        except Exception:
            pass

    def _show_output_empty_state(self) -> None:
        """Aperçu COLORÉ + CENTRÉ de la structure du futur Prompt Ultime, mis
        à jour en direct selon les méga-prompts sélectionnés et le brouillon.
        Utilise des CTkLabels stackés (les tags Tk sur CTkTextbox ne tiennent
        pas leurs couleurs à cause de l'appearance system de CTkTk)."""
        if not hasattr(self, "preview_container"):
            return
        # Bascule sur le container de preview
        self._swap_to_preview()

        # Reset du contenu
        for w in self.preview_container.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        cont = self.preview_container
        megas = list(getattr(self, "selected_megas", []) or [])
        n = len(megas)

        # Liste des (label, padding_horizontal) à wraplength dynamique. Un bind
        # <Configure> sur cont met à jour les wraplength quand le panneau est
        # redimensionné — sans ça, les longs textes débordent à droite.
        self._preview_wrap_labels = []

        def _on_preview_resize(event):
            w = max(120, event.width - 20)
            for lbl, pad in self._preview_wrap_labels:
                try:
                    lbl.configure(wraplength=max(120, w - pad))
                except Exception:
                    pass

        cont.bind("<Configure>", _on_preview_resize)

        # ── Titre principal (centré, orange, gros) ───────────────────────
        ctk.CTkLabel(
            cont, text="✨   APERÇU DE LA STRUCTURE",
            font=(RESOLVED_DISPLAY, 22, "bold"),
            text_color=PALETTE["orange"],
            anchor="center",
        ).pack(fill="x", pady=(24, 2))
        ctk.CTkLabel(
            cont, text="le squelette de ton futur Prompt Ultime",
            font=(RESOLVED_BODY, 12, "italic"),
            text_color=PALETTE["muted"],
            anchor="center",
        ).pack(fill="x", pady=(0, 24))

        # ── Section helper ───────────────────────────────────────────────
        def section_block(idx: int, title: str, subtitle: str, color_key: str) -> ctk.CTkFrame:
            block = ctk.CTkFrame(cont, fg_color="transparent")
            block.pack(fill="x", padx=24, pady=(8, 4))
            # Header row : badge + titre
            header = ctk.CTkFrame(block, fg_color="transparent")
            header.pack(fill="x")
            ctk.CTkLabel(
                header, text=f" {idx} ",
                font=(RESOLVED_BODY, 12, "bold"),
                text_color=PALETTE["text_strong"],
                fg_color=PALETTE[color_key],
                corner_radius=10,
            ).pack(side="left", padx=(0, 10))
            # Titre : font réduit + wraplength pour ne pas déborder sur des
            # panneaux étroits (ex: "INSTRUCTIONS COMPORTEMENTALES" est long).
            title_lbl = ctk.CTkLabel(
                header, text=title,
                font=(RESOLVED_BODY, 14, "bold"),
                text_color=PALETTE[color_key],
                anchor="w",
                justify="left",
                wraplength=320,
            )
            title_lbl.pack(side="left", fill="x", expand=True)
            self._preview_wrap_labels.append((title_lbl, 90))
            # Sous-titre
            sub_lbl = ctk.CTkLabel(
                block, text=subtitle,
                font=(RESOLVED_BODY, 11, "italic"),
                text_color=PALETTE["muted"],
                anchor="w",
                justify="left",
                wraplength=300,
            )
            sub_lbl.pack(fill="x", padx=(40, 0), pady=(0, 6))
            self._preview_wrap_labels.append((sub_lbl, 90))
            return block

        # ── 1) EN-TÊTE : méga-prompts actifs ─────────────────────────────
        b1 = section_block(
            1, "EN-TÊTE",
            "liste des méga-prompts actifs",
            "accent",
        )
        if n == 0:
            l1 = ctk.CTkLabel(
                b1, text="◌  aucun méga-prompt sélectionné",
                font=(RESOLVED_BODY, 13, "italic"),
                text_color=PALETTE["text"],
                anchor="w",
                justify="left",
                wraplength=300,
            )
            l1.pack(fill="x", padx=(40, 0), pady=(2, 0))
            self._preview_wrap_labels.append((l1, 90))
            l2 = ctk.CTkLabel(
                b1, text="choisis un preset (Option A) ou ajoute-en un par un",
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted_dim"],
                anchor="w",
                justify="left",
                wraplength=280,
            )
            l2.pack(fill="x", padx=(60, 0), pady=(0, 6))
            self._preview_wrap_labels.append((l2, 110))
        else:
            ctk.CTkLabel(
                b1, text=f"{n} méga-prompt{'s' if n > 1 else ''} actif{'s' if n > 1 else ''} :",
                font=(RESOLVED_BODY, 12, "bold"),
                text_color=PALETTE["text"],
                anchor="w",
            ).pack(fill="x", padx=(40, 0), pady=(2, 4))
            for i, mp in enumerate(megas, 1):
                row = ctk.CTkFrame(b1, fg_color="transparent")
                row.pack(fill="x", padx=(46, 0), pady=1)
                ctk.CTkLabel(
                    row, text=f"{i:>2}.",
                    font=(RESOLVED_BODY, 12),
                    text_color=PALETTE["muted_dim"],
                    width=24, anchor="e",
                ).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(
                    row, text=f"[{mp.get('id', '??')}]",
                    font=(RESOLVED_BODY, 11, "bold"),
                    text_color=PALETTE["accent"],
                    width=44, anchor="w",
                ).pack(side="left", padx=(0, 6))
                ctk.CTkLabel(
                    row, text=mp.get("name", "?"),
                    font=(RESOLVED_BODY, 13, "bold"),
                    text_color=PALETTE["brand_glow"],
                    anchor="w",
                ).pack(side="left", fill="x", expand=True)

        # ── 2) INSTRUCTIONS COMPORTEMENTALES ─────────────────────────────
        b2 = section_block(
            2, "INSTRUCTIONS COMPORTEMENTALES",
            "un bloc complet par méga-prompt activé",
            "violet",
        )
        if n == 0:
            l3 = ctk.CTkLabel(
                b2, text="◌  vide pour l'instant",
                font=(RESOLVED_BODY, 13, "italic"),
                text_color=PALETTE["text"],
                anchor="w",
                justify="left",
                wraplength=300,
            )
            l3.pack(fill="x", padx=(40, 0), pady=(2, 0))
            self._preview_wrap_labels.append((l3, 90))
            l4 = ctk.CTkLabel(
                b2, text="le bloc se remplira dès qu'un méga-prompt sera ajouté",
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted_dim"],
                anchor="w",
                justify="left",
                wraplength=280,
            )
            l4.pack(fill="x", padx=(60, 0), pady=(0, 6))
            self._preview_wrap_labels.append((l4, 110))
        else:
            for i, mp in enumerate(megas, 1):
                item = ctk.CTkFrame(
                    b2,
                    fg_color=PALETTE["panel_card"],
                    corner_radius=8,
                    border_width=1,
                    border_color=PALETTE["border"],
                )
                item.pack(fill="x", padx=(40, 0), pady=3)
                head = ctk.CTkFrame(item, fg_color="transparent")
                head.pack(fill="x", padx=10, pady=(8, 0))
                ctk.CTkLabel(
                    head, text=f"MEGA PROMPT {i}/{n}",
                    font=(RESOLVED_BODY, 11, "bold"),
                    text_color=PALETTE["violet"],
                    anchor="w",
                ).pack(side="left")
                ctk.CTkLabel(
                    head, text=f"  ::  {mp.get('name', '?')}",
                    font=(RESOLVED_BODY, 12, "bold"),
                    text_color=PALETTE["text"],
                    anchor="w",
                ).pack(side="left")
                tagline = (mp.get("tagline") or "").strip()
                if tagline:
                    ctk.CTkLabel(
                        item, text=f"↳  {tagline}",
                        font=(RESOLVED_BODY, 11, "italic"),
                        text_color=PALETTE["muted"],
                        anchor="w",
                    ).pack(fill="x", padx=10, pady=(0, 8))
                else:
                    ctk.CTkFrame(item, fg_color="transparent", height=4).pack()

        # ── 3) DEMANDE DE L'UTILISATEUR ──────────────────────────────────
        b3 = section_block(
            3, "DEMANDE DE L'UTILISATEUR",
            "ton brouillon, tel quel",
            "orange",
        )
        has_input = False
        if hasattr(self, "input_box"):
            has_input = (
                not getattr(self, "_input_has_placeholder", True)
                and bool(self.input_box.get("1.0", "end").strip())
            )
        if has_input:
            user = self.input_box.get("1.0", "end").strip()
            preview = user if len(user) <= 380 else user[:377].rstrip() + "..."
            ctk.CTkLabel(
                b3, text=preview,
                font=(RESOLVED_BODY, 13),
                text_color=PALETTE["text"],
                anchor="w",
                justify="left",
                wraplength=600,
            ).pack(fill="x", padx=(40, 16), pady=(2, 6))
        else:
            l5 = ctk.CTkLabel(
                b3, text="◌  ton brouillon apparaîtra ici",
                font=(RESOLVED_BODY, 13, "italic"),
                text_color=PALETTE["text"],
                anchor="w",
                justify="left",
                wraplength=300,
            )
            l5.pack(fill="x", padx=(40, 0), pady=(2, 0))
            self._preview_wrap_labels.append((l5, 90))
            l6 = ctk.CTkLabel(
                b3, text="écris-le dans la zone 1, à gauche",
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted_dim"],
                anchor="w",
                justify="left",
                wraplength=280,
            )
            l6.pack(fill="x", padx=(60, 0), pady=(0, 6))
            self._preview_wrap_labels.append((l6, 110))

        # ── Pied : appel à l'action (centré) ─────────────────────────────
        ctk.CTkFrame(cont, fg_color="transparent", height=18).pack()
        cta_row = ctk.CTkFrame(cont, fg_color="transparent")
        cta_row.pack(fill="x", pady=(8, 4))
        ctk.CTkLabel(
            cta_row, text="→  Clique sur",
            font=(RESOLVED_BODY, 13),
            text_color=PALETTE["muted"],
        ).pack(side="left", padx=(40, 6))
        ctk.CTkLabel(
            cta_row, text="« Generer le Prompt Ultime »",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color=PALETTE["orange"],
        ).pack(side="left")
        ctk.CTkFrame(cont, fg_color="transparent", height=4).pack()
        kbd_row = ctk.CTkFrame(cont, fg_color="transparent")
        kbd_row.pack(fill="x", pady=(2, 18))
        ctk.CTkLabel(
            kbd_row, text="ou utilise le raccourci",
            font=(RESOLVED_BODY, 12),
            text_color=PALETTE["muted"],
        ).pack(side="left", padx=(40, 8))
        ctk.CTkLabel(
            kbd_row, text="  Ctrl + Enter  ",
            font=(RESOLVED_BODY, 12, "bold"),
            text_color=PALETTE["text_strong"],
            fg_color=PALETTE["accent_dim"],
            corner_radius=6,
        ).pack(side="left")

        self._output_empty = True
        try:
            self.output_count.configure(text="")
        except Exception:
            pass


def _now_str() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
