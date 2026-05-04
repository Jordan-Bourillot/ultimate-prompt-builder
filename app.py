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
PALETTE = {
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

    # Brand triskell trio (the 3 spirals)
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
    "text":          "#E2E8F0",
    "tag_fg":        "#E2E8F0",
    "muted":         "#94A3B8",
    "muted_dim":     "#64748B",
}

# Combos recommandees dans le PDF "Bibliotheque de prompts auto-adresses",
# plus un preset metier Triskell Studio (production de sites web).
PRESETS = [
    {
        "name": "Production de sites",
        "ids": ["14", "13", "06", "00"],
        "desc": "Investigateur + Mode produit + Anti-slop + Autonomie",
    },
    {
        "name": "Build d'app",
        "ids": ["00", "06", "13"],
        "desc": "Autonomie + Anti-slop + Mode produit",
    },
    {
        "name": "Decision strategique",
        "ids": ["01", "04", "05", "10"],
        "desc": "Honnetete + Steelman + Pre-mortem + Sparring",
    },
    {
        "name": "Recherche & veille",
        "ids": ["02", "07", "15"],
        "desc": "Anti-hallu + Densite + Compression",
    },
    {
        "name": "Apprentissage profond",
        "ids": ["03", "08", "09"],
        "desc": "Premiers principes + Niveau calibre + Coach",
    },
    {
        "name": "Diagnostic complexe",
        "ids": ["14", "02", "12"],
        "desc": "Investigateur + Anti-hallu + Detection biais",
    },
    {
        "name": "Projet long",
        "ids": ["00", "11", "12"],
        "desc": "Autonomie + Memoire + Detection biais",
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


def _apply_dark_titlebar(window) -> None:
    """Force dark titlebar on Windows 10/11 via DWM. Tries both DWMA constants
    (20 = Win 10 v1909+, 19 = Win 10 v1809-v1903). Re-applies once on map event
    in case the first call lands before the HWND is real."""
    def do_it():
        try:
            import ctypes
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            value = ctypes.c_int(1)
            for attr in (20, 19):
                rc = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr,
                    ctypes.byref(value), ctypes.sizeof(value),
                )
                if rc == 0:
                    break
            # Force a redraw by toggling visibility briefly
            try:
                window.withdraw()
                window.deiconify()
            except Exception:
                pass
        except Exception as exc:
            logger.debug("dark titlebar not applied: %s", exc)
    try:
        # Apply twice: once short for normal case, once after map for slow cases
        window.after(50, do_it)
        window.bind("<Map>", lambda _e: do_it(), add="+")
    except Exception:
        do_it()


def _load_app_logo(size: int):
    """Load the recolored chat-bubble logo at the requested size.

    Falls back to the generated triskell mark if the bundled PNG is missing.
    """
    from pathlib import Path
    from PIL import Image

    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        try:
            img = Image.open(logo_path).convert("RGBA")
            return img.resize((size, size), Image.LANCZOS)
        except Exception:
            pass
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
            text_color="#FFFFFF",
            fg_color=PALETTE["accent_dim"],
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
            text_color="#FFFFFF",
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
                "et envoie le resultat a Claude, GPT, Gemini, Mistral ou Grok."
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
            text_color="#FFFFFF",
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

        field_label("Nom court")
        self.name_entry = ctk.CTkEntry(
            body, height=36, placeholder_text="Ex: Anti-distraction",
            font=(RESOLVED_BODY, 12),
        )
        self.name_entry.pack(fill="x")
        if self.mp.get("name"):
            self.name_entry.insert(0, self.mp["name"])

        field_label("Tagline (description courte)")
        self.tagline_entry = ctk.CTkEntry(
            body, height=36,
            placeholder_text="Ex: Couper court aux digressions",
            font=(RESOLVED_BODY, 12),
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
            text_color="#FFFFFF",
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
            text_color="#FFFFFF",
            fg_color=PALETTE["accent_dim"], corner_radius=8,
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ctk.CTkLabel(
            top, text=mp.get("name", ""),
            font=(RESOLVED_BODY, 14, "bold"),
            text_color="#FFFFFF",
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
            text_color="#FFFFFF",
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
            text_color="#FFFFFF",
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
        self.title("Parametres - Cles API & Modeles")
        self.geometry("640x560")
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
        self.settings = settings
        self.on_save = on_save
        self._key_entries: dict[str, ctk.CTkEntry] = {}

        wrapper = ctk.CTkScrollableFrame(self, corner_radius=0)
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            wrapper,
            text="Cles API",
            font=(RESOLVED_DISPLAY, 18, "bold"),
            text_color="#FFFFFF",
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
                text_color="#FFFFFF",
                width=170,
                anchor="w",
            ).pack(side="left")
            entry = ctk.CTkEntry(
                row,
                show="*",
                placeholder_text=f"sk-... ({pid})",
                width=360,
                height=32,
            )
            current = self.settings.get("api_keys", {}).get(info["key_field"], "")
            if current:
                entry.insert(0, current)
            entry.pack(side="left", padx=(8, 0))
            self._key_entries[info["key_field"]] = entry

        # Triskell Studio is dark-first by design — no theme toggle.
        self.appearance_var = ctk.StringVar(value="dark")

        # ----- Updates section -----
        ctk.CTkLabel(
            wrapper, text="Mises a jour",
            font=(RESOLVED_DISPLAY, 18, "bold"),
            text_color="#FFFFFF",
        ).pack(anchor="w", pady=(20, 8))

        upd_card = ctk.CTkFrame(
            wrapper, fg_color=PALETTE["panel_card"],
            corner_radius=10, border_width=1,
            border_color=PALETTE["border"],
        )
        upd_card.pack(fill="x", pady=4)

        self._upd_status_lbl = ctk.CTkLabel(
            upd_card,
            text=f"Version installee : v{UPDATER_VERSION}",
            font=(RESOLVED_BODY, 12, "bold"),
            text_color="#FFFFFF",
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
            upd_actions, text="Verifier maintenant",
            width=170, height=34,
            font=(RESOLVED_BODY, 11, "bold"),
            text_color="#FFFFFF",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            border_width=1, border_color=PALETTE["border_2"],
            command=lambda: updater.check_for_updates(async_=True),
        )
        self._upd_check_btn.pack(side="left")
        self._upd_install_btn = ctk.CTkButton(
            upd_actions, text="Installer la mise a jour",
            width=200, height=34,
            font=(RESOLVED_BODY, 11, "bold"),
            text_color="#FFFFFF",
            fg_color=PALETTE["orange"],
            hover_color="#EA580C",
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
            self._upd_status_lbl.configure(text=f"Version installee : v{st.current_version}")
            self._upd_detail_lbl.configure(
                text="Clique sur 'Verifier maintenant' pour chercher une nouvelle version.",
                text_color=PALETTE["muted"],
            )
            self._upd_check_btn.configure(state="normal", text="Verifier maintenant")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "checking":
            self._upd_detail_lbl.configure(
                text="Verification en cours...", text_color=PALETTE["muted"],
            )
            self._upd_check_btn.configure(state="disabled", text="Verification...")
            self._upd_install_btn.configure(state="disabled")
        elif phase == "not-available":
            self._upd_detail_lbl.configure(
                text=f"Tu es a jour. Derniere version : v{nv}.",
                text_color=PALETTE["ok"],
            )
            self._upd_check_btn.configure(state="normal", text="Verifier maintenant")
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
            self._upd_check_btn.configure(state="normal", text="Verifier maintenant")
            self._upd_install_btn.configure(state="normal")
        elif phase == "error":
            self._upd_detail_lbl.configure(
                text=f"Erreur : {st.message}", text_color=PALETTE["danger"],
            )
            self._upd_check_btn.configure(state="normal", text="Reessayer")
            self._upd_install_btn.configure(state="disabled")


class ResponseWindow(ctk.CTkToplevel):
    """Modal-ish window to display the AI response."""

    def __init__(self, master, title: str, content: str):
        super().__init__(master)
        self.title(title)
        self.geometry("900x700")
        self.transient(master)
        self.configure(fg_color=PALETTE["bg"])
        _apply_dark_titlebar(self)
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

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(0, 16))

        def copy() -> None:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Copie", "Reponse copiee dans le presse-papier.")

        ctk.CTkButton(
            bar,
            text="Copier la reponse",
            fg_color=PALETTE["accent"],
            hover_color=PALETTE["accent_hover"],
            command=copy,
            border_width=1,
            border_color=PALETTE["border_2"],
        ).pack(side="right")
        ctk.CTkButton(
            bar,
            text="Fermer",
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
            command=self.destroy,
        ).pack(side="right", padx=(0, 8))


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
            text_color="#FFFFFF",
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
                text_color="#FFFFFF",
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
                text_color="#FFFFFF",
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
        super().__init__()
        self.settings = config.load_settings()
        self.mega_prompts = config.load_mega_prompts()
        self.selected_megas: list[dict] = []
        self.current_ultimate: str = ""

        # Triskell Studio is a dark-first brand — force dark mode always.
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.settings["appearance_mode"] = "dark"

        # Load bundled brand fonts (Syne + Inter) before any widget creation.
        global RESOLVED_DISPLAY, RESOLVED_BODY
        RESOLVED_DISPLAY, RESOLVED_BODY = _load_brand_fonts()
        logger.info("Fonts: display=%s, body=%s", RESOLVED_DISPLAY, RESOLVED_BODY)

        self.title(APP_TITLE)
        self.geometry(f"{APP_W}x{APP_H}")
        self.minsize(1080, 700)
        self.configure(fg_color=PALETTE["bg"])

        self._build_ui()
        self._bind_shortcuts()
        _apply_dark_titlebar(self)

        # Background update check 5s after launch (non-blocking)
        updater.add_listener(self._on_global_update_status)
        self.after(5000, lambda: updater.check_for_updates(async_=True))

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-Return>", lambda _e: self._on_generate())
        self.bind("<Control-s>", lambda _e: self._save_current())
        self.bind("<Control-e>", lambda _e: self._export_to_file())
        self.bind("<Control-l>", lambda _e: self._clear_megas())
        self.bind("<F1>", lambda _e: self._open_about())

    def _build_ui(self) -> None:
        # Top bar with full Triskell branding
        topbar = ctk.CTkFrame(self, height=72, corner_radius=0, fg_color=PALETTE["panel"])
        topbar.pack(side="top", fill="x")
        topbar.pack_propagate(False)

        # Subtle bottom border line under the topbar
        border_line = ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"], corner_radius=0)
        border_line.pack(side="top", fill="x")

        brand_block = ctk.CTkFrame(topbar, fg_color="transparent", cursor="hand2")
        brand_block.pack(side="left", padx=20, pady=10)
        brand_block.bind("<Button-1>", lambda _e: self._open_about())

        # Triskell logo (3 spirals) rendered via PIL
        try:
            self._logo_img_topbar = ctk.CTkImage(
                light_image=_load_app_logo(38),
                dark_image=_load_app_logo(38),
                size=(38, 38),
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
            text_color="#FFFFFF",
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
            text="⚙  Parametres",
            width=130,
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
            command=self._open_settings,
        ).pack(side="right", padx=(6, 14), pady=14)
        ctk.CTkButton(
            topbar,
            text="🕘  Historique",
            width=130,
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
            command=self._open_history,
        ).pack(side="right", padx=6, pady=14)
        ctk.CTkButton(
            topbar,
            text="📚  Bibliotheque",
            width=140,
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["accent"],
            text_color=PALETTE["accent"],
            hover_color=PALETTE["tag_bg"],
            command=self._open_library,
        ).pack(side="right", padx=6, pady=14)

        # Main split
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=14)
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
        left.grid_rowconfigure(1, weight=1)

        input_header = ctk.CTkFrame(left, fg_color="transparent")
        input_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        input_header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            input_header, text=" 1 ",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color="#FFFFFF",
            fg_color=PALETTE["accent"], corner_radius=10,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(
            input_header,
            text="Ecris ton prompt de base",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color="#FFFFFF",
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        self.input_count = ctk.CTkLabel(
            input_header,
            text="0 car.",
            font=(RESOLVED_BODY, 10),
            text_color=PALETTE["muted_dim"],
        )
        self.input_count.grid(row=0, column=2, sticky="e")

        self.input_box = ctk.CTkTextbox(
            left,
            font=(RESOLVED_BODY, 15),
            wrap="word",
            corner_radius=8,
            fg_color=PALETTE["input_bg"],
            text_color=PALETTE["text"],
            border_width=1,
            border_color=PALETTE["border"],
        )
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self.input_box.bind("<KeyRelease>", lambda _e: self._update_input_count())
        # Subtle placeholder behavior
        self._input_placeholder = (
            "Ex: Code-moi une appli desktop qui... / Critique honnetement mon plan de... / "
            "Resume ce document...\n\n(Ctrl+Enter pour generer)"
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
            text_color="#FFFFFF",
            fg_color=PALETTE["accent"], corner_radius=10,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(
            step2_header,
            text="Choisis tes Mega Prompts",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color="#FFFFFF",
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            left,
            text="Option A — un preset (combos recommandes) :",
            font=(RESOLVED_BODY, 11),
            text_color=PALETTE["muted"],
        ).grid(row=3, column=0, sticky="w", padx=(46, 14), pady=(2, 4))

        presets_row = ctk.CTkFrame(
            left, corner_radius=8, fg_color=PALETTE["panel_card"],
        )
        presets_row.grid(row=4, column=0, sticky="ew", padx=(46, 14), pady=(0, 6))
        # 2 rows of preset chips so the 7 chips never overflow / never scroll
        per_row = 4
        preset_rows: list[ctk.CTkFrame] = []

        for i, preset in enumerate(PRESETS):
            if i % per_row == 0:
                rf = ctk.CTkFrame(presets_row, fg_color="transparent")
                rf.pack(fill="x", padx=4, pady=2)
                preset_rows.append(rf)
            # Triskell house preset (Production de sites) stays solid orange
            # to remain the visual hero. All others use a subtle outlined style.
            is_triskell = preset["name"] == "Production de sites"
            if is_triskell:
                fg = PALETTE["orange"]
                hover = "#EA580C"
                border_color = PALETTE["orange"]
                text_color = "#FFFFFF"
                label = "◆  " + preset["name"]
            else:
                fg = "transparent"
                hover = PALETTE["tag_bg_hover"]
                border_color = PALETTE["border_2"]
                text_color = PALETTE["text"]
                label = preset["name"]
            btn = ctk.CTkButton(
                preset_rows[-1],
                text=label,
                width=10,
                height=36,
                corner_radius=18,
                font=(RESOLVED_BODY, 12, "bold"),
                fg_color=fg,
                hover_color=hover,
                text_color=text_color,
                border_width=1,
                border_color=border_color,
                command=lambda p=preset: self._apply_preset(p),
            )
            btn.pack(side="left", padx=5, pady=4, fill="x", expand=True)

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
            width=110,
            height=34,
            font=(RESOLVED_BODY, 12, "bold"),
            fg_color="transparent",
            text_color=PALETTE["accent"],
            hover_color=PALETTE["tag_bg_hover"],
            command=self._on_add_mega,
            border_width=1,
            border_color=PALETTE["accent"],
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(4, 0))
        ctk.CTkButton(
            sel_row,
            text="Tout retirer",
            width=110,
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color=PALETTE["muted"],
            text_color=PALETTE["muted"],
            hover_color=PALETTE["tag_bg"],
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

        # Step 3 — Generate
        step3_header = ctk.CTkFrame(left, fg_color="transparent")
        step3_header.grid(row=8, column=0, sticky="ew", padx=14, pady=(4, 4))
        ctk.CTkLabel(
            step3_header, text=" 3 ",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color="#FFFFFF",
            fg_color=PALETTE["accent"], corner_radius=10,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            step3_header,
            text="Genere ton Prompt Ultime",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color="#FFFFFF",
        ).pack(side="left")

        # Action buttons
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.grid(row=9, column=0, sticky="ew", padx=14, pady=(4, 14))

        self.generate_btn = ctk.CTkButton(
            actions,
            text="✨   Generer    (Ctrl+Enter)",
            height=44,
            font=(RESOLVED_DISPLAY, 14, "bold"),
            text_color="#FFFFFF",
            fg_color=PALETTE["accent_dim"],
            hover_color=PALETTE["accent"],
            command=self._on_generate,
            border_width=1,
            border_color=PALETTE["border_2"],
        )
        self.generate_btn.pack(side="left", fill="x", expand=True)

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
            text_color="#FFFFFF",
            fg_color=PALETTE["violet"], corner_radius=10,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(
            header_row, text="Copie / Sauvegarde / Envoie a l'IA",
            font=(RESOLVED_BODY, 14, "bold"),
            text_color="#FFFFFF",
        ).grid(row=0, column=1, sticky="w")
        self.output_count = ctk.CTkLabel(
            header_row,
            text="",
            font=(RESOLVED_BODY, 10),
            text_color=PALETTE["muted_dim"],
        )
        self.output_count.grid(row=0, column=2, sticky="e", padx=(0, 10))
        self.status_label = ctk.CTkLabel(
            header_row,
            text="●  Pret",
            font=(RESOLVED_BODY, 11, "bold"),
            text_color=PALETTE["ok"],
        )
        self.status_label.grid(row=0, column=3, sticky="e", padx=(0, 8))
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
        ).grid(row=0, column=4, sticky="e")

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
            hover_color=PALETTE["accent_hover"],
            height=42,
            font=(RESOLVED_BODY, 12, "bold"),
            border_width=1,
            border_color=PALETTE["border_2"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            bottom,
            text="💾  Sauvegarder",
            command=self._save_current,
            fg_color=PALETTE["tag_bg"],
            hover_color=PALETTE["accent_hover"],
            height=42,
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
            height=42,
            font=(RESOLVED_BODY, 13, "bold"),
            border_width=1,
            border_color=PALETTE["border_2"],
        )
        self.send_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # Footer brand line with mini logo + wordmark + clickable URL
        footer_border = ctk.CTkFrame(self, height=1, fg_color=PALETTE["border"], corner_radius=0)
        footer_border.pack(side="bottom", fill="x")
        footer = ctk.CTkFrame(self, height=32, corner_radius=0, fg_color=PALETTE["panel"])
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)

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
            text_color="#FFFFFF",
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
                "Ctrl+Enter Generer  ·  Ctrl+S Sauvegarder  ·  Ctrl+E Exporter"
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

    def _refresh_tags(self) -> None:
        for w in self.tags_frame.winfo_children():
            w.destroy()
        n = len(self.selected_megas)
        self.tags_count.configure(
            text=f"{n} / 16",
            text_color=PALETTE["accent"] if n > 0 else PALETTE["muted_dim"],
        )
        if not self.selected_megas:
            empty = ctk.CTkLabel(
                self.tags_frame,
                text=(
                    "Aucun Mega Prompt actif.  Pioche un preset ci-dessus, "
                    "ou ajoute-en individuellement."
                ),
                font=(RESOLVED_BODY, 11),
                text_color=PALETTE["muted_dim"],
            )
            empty.pack(anchor="w", padx=12, pady=18)
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
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.insert("1.0", self.current_ultimate)
        self._update_output_count()
        n = len(self.selected_megas)
        self._set_status(
            f"Prompt ultime genere ({n} mega prompt{'s' if n != 1 else ''}).",
            ok=True,
        )
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
            self._set_status("Genere un prompt avant de sauvegarder.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Genere un prompt avant de sauvegarder.", warn=True)
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
            self._set_status("Genere d'abord un prompt ultime.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Genere d'abord un prompt ultime.", warn=True)
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
        ResponseWindow(self, f"Reponse - {provider_id} / {model}", resp)

    def _on_send_error(self, msg: str) -> None:
        self._stop_loading_indicator()
        self.send_btn.configure(state="normal", text="🚀  Envoyer a l'IA")
        self.generate_btn.configure(state="normal")
        self._set_status(msg, warn=True)
        messagebox.showerror("Erreur IA", msg)

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
        frames = ["◐", "◓", "◑", "◒"]
        f = frames[self._loading_phase % len(frames)]
        self._loading_phase += 1
        current = self.status_label.cget("text")
        # Replace leading icon if present
        rest = current.lstrip("●✓⚠◐◓◑◒ ")
        self.status_label.configure(
            text=f"{f}  {rest}", text_color=PALETTE["accent"]
        )
        self.after(180, self._tick_loading)

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
                f"Mise a jour v{st.next_version} prete - voir Parametres pour installer",
                ok=True,
            )
        elif st.phase == "available":
            self._set_status(
                f"Mise a jour v{st.next_version} disponible - telechargement en cours",
            )

    def _on_settings_saved(self, settings: dict) -> None:
        self.settings = settings
        self._set_status("Parametres enregistres.")

    def _open_history(self) -> None:
        HistoryWindow(self, on_load=self._load_from_history)

    def _open_about(self) -> None:
        AboutWindow(self)

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
            self._set_status("Genere d'abord un prompt avant d'exporter.", warn=True)
            return
        text = self.output_box.get("1.0", "end").strip()
        if not text:
            self._set_status("Rien a exporter.", warn=True)
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

    def _update_input_count(self) -> None:
        if getattr(self, "_input_has_placeholder", False):
            self.input_count.configure(text="0 car.", text_color=PALETTE["muted_dim"])
            return
        text = self.input_box.get("1.0", "end").rstrip("\n")
        n = len(text)
        words = len(text.split())
        self.input_count.configure(
            text=f"{n} car. · {words} mots",
            text_color=PALETTE["muted"] if n > 0 else PALETTE["muted_dim"],
        )

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

    def _show_output_empty_state(self) -> None:
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        msg = (
            "\n\n"
            "       Le Prompt Ultime apparaitra ici.\n\n\n"
            "       1.   Ecris ton prompt a gauche\n\n"
            "       2.   Pioche un preset, ou ajoute des Mega Prompts\n\n"
            "       3.   Clique sur  Generer le Prompt Ultime  (Ctrl+Enter)\n\n\n"
            "       Astuce :  clique sur un tag pour voir le contenu complet\n"
            "       du Mega Prompt."
        )
        self.output_box.insert("1.0", msg)
        # Apply bright color via tags for the empty state
        try:
            self.output_box.tag_add("empty", "1.0", "end")
            self.output_box.tag_config("empty", foreground=PALETTE["muted"])
        except Exception:
            pass
        self._output_empty = True
        self.output_count.configure(text="")


def _now_str() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
