"""Auto-updater pour AlphaBeast.

Pattern hybride (depuis v1.4.0) :
    1. Pattern A — Manifest landing : lit https://prompt-builder.triskell-studio.fr/version.json
       (standard Triskell, decouple du repo GitHub).
    2. Pattern B — GitHub Releases API : fallback si le manifest est inaccessible
       (compat retro pour les v1.3.x installes avant la migration).

Le canal "beta" passe directement par GitHub Releases (le manifest ne contient
que la stable).

Phases : idle | checking | available | not-available | downloading | ready | error

Workflow :
    1. App demarre -> check passif (manifest puis fallback GitHub)
    2. Si version plus recente -> telechargement silencieux en arriere-plan
    3. Quand le download est fini -> notif (phase=ready)
    4. User clique "Installer" -> on lance l'installeur, l'app quitte
"""
from __future__ import annotations

import fnmatch
import json
import logging
import os
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("updater")

# --- A configurer ---
APP_VERSION = "1.5.1"
GITHUB_OWNER = "Jordan-Bourillot"
GITHUB_REPO = "ultimate-prompt-builder"
UPDATE_INSTALLER_PATTERN = "AlphaBeast_setup_*.exe"
# Pattern A — manifest landing (standard Triskell). Si inaccessible, fallback GitHub.
MANIFEST_URL = "https://prompt-builder.triskell-studio.fr/version.json"


# =========================================================================
#  Comparaison de versions
# =========================================================================

def parse_version(v: str) -> tuple[tuple[int, ...], str]:
    """'v1.2.0-beta.1' -> ((1, 2, 0), 'beta.1')"""
    v = (v or "0.0.0").lstrip("vV").strip()
    if "-" in v:
        main, pre = v.split("-", 1)
    else:
        main, pre = v, ""
    parts: list[int] = []
    for p in main.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts), pre


def is_newer(latest: str, current: str) -> bool:
    l_parts, l_pre = parse_version(latest)
    c_parts, c_pre = parse_version(current)
    if l_parts > c_parts:
        return True
    if l_parts < c_parts:
        return False
    if not l_pre and c_pre:
        return True
    if l_pre and not c_pre:
        return False
    return l_pre > c_pre


# =========================================================================
#  Etat
# =========================================================================

@dataclass
class UpdateStatus:
    phase: str = "idle"  # idle|checking|available|not-available|downloading|ready|error
    current_version: str = APP_VERSION
    next_version: str = ""
    release_notes: str = ""
    percent: int = 0
    bytes_per_second: int = 0
    message: str = ""
    download_url: str = ""
    download_size: int = 0
    installer_path: str = ""
    is_prerelease: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# =========================================================================
#  Singleton
# =========================================================================

class _Updater:
    def __init__(self) -> None:
        self.status = UpdateStatus(current_version=APP_VERSION)
        self._listeners: list[Callable[[UpdateStatus], None]] = []
        self._download_thread: Optional[threading.Thread] = None
        self._stop_download = threading.Event()
        self._channel = "stable"  # 'stable' | 'beta'

    def add_listener(self, cb: Callable[[UpdateStatus], None]) -> None:
        self._listeners.append(cb)

    def remove_listener(self, cb: Callable[[UpdateStatus], None]) -> None:
        try:
            self._listeners.remove(cb)
        except ValueError:
            pass

    def set_channel(self, channel: str) -> None:
        if channel in ("stable", "beta"):
            self._channel = channel

    def _broadcast(self) -> None:
        for cb in list(self._listeners):
            try:
                cb(self.status)
            except Exception:
                logger.exception("listener callback raised")

    def _set(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self.status, k, v)
        self._broadcast()

    # ---------- API publique ----------

    def check_for_updates(self, async_: bool = True) -> None:
        if self.status.phase in ("checking", "downloading"):
            return
        if async_:
            threading.Thread(target=self._do_check, daemon=True).start()
        else:
            self._do_check()

    def install(self) -> bool:
        if self.status.phase != "ready" or not self.status.installer_path:
            return False
        installer = self.status.installer_path
        if not os.path.exists(installer):
            self._set(phase="error", message="Installeur introuvable apres telechargement.")
            return False
        try:
            subprocess.Popen(
                [installer, "/SILENT", "/NORESTART"],
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
                close_fds=True,
            )
            threading.Timer(1.5, lambda: os._exit(0)).start()
            return True
        except Exception as e:
            self._set(phase="error", message=f"Lancement installeur impossible : {e}")
            return False

    # ---------- Logique interne ----------

    def _api_url_latest(self) -> str:
        return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

    def _api_url_all(self) -> str:
        return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases?per_page=10"

    def _http_json(self, url: str, timeout: float = 12.0) -> Optional[object]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"UltimatePromptBuilder/{APP_VERSION}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def _try_manifest(self) -> Optional[dict]:
        """Pattern A — lit le manifest landing. Renvoie None en cas d'echec
        (le caller fallback sur GitHub)."""
        try:
            req = urllib.request.Request(
                MANIFEST_URL,
                headers={"User-Agent": f"AlphaBeast/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode("utf-8"))
            if not isinstance(data, dict) or "version" not in data:
                return None
            return data
        except Exception as e:
            logger.info("manifest unreachable, fallback GitHub : %s", e)
            return None

    def _do_check(self) -> None:
        self._set(phase="checking", message="")
        try:
            # Canal beta -> directement GitHub (le manifest ne contient que la stable)
            if self._channel == "beta":
                self._do_check_github()
                return

            # Canal stable -> Pattern A (manifest) en premier
            manifest = self._try_manifest()
            if manifest is not None:
                self._do_check_manifest(manifest)
                return

            # Fallback Pattern B (GitHub Releases) si manifest inaccessible
            self._do_check_github()
        except Exception as e:
            logger.exception("check failed")
            self._set(phase="error", message=f"Verification echouee : {e}")

    def _do_check_manifest(self, manifest: dict) -> None:
        """Pattern A — process une reponse manifest landing."""
        version = str(manifest.get("version", "")).strip()
        if not version:
            self._set(phase="error", message="Manifest invalide : version manquante.")
            return
        if not is_newer(version, APP_VERSION):
            self._set(phase="not-available", next_version=version)
            return

        download_url = str(manifest.get("url", "")).strip()
        if not download_url:
            self._set(phase="error", message="Manifest invalide : url manquante.")
            return

        notes = str(manifest.get("notes", "")).strip()
        self._set(
            phase="available",
            next_version=version,
            release_notes=notes,
            download_url=download_url,
            download_size=int(manifest.get("size", 0) or 0),
            is_prerelease=False,
        )
        self._start_download()

    def _do_check_github(self) -> None:
        """Pattern B — process une reponse GitHub Releases (legacy + canal beta)."""
        if self._channel == "beta":
            releases = self._http_json(self._api_url_all())
            if not releases:
                self._set(phase="not-available")
                return
            latest = releases[0]
        else:
            latest = self._http_json(self._api_url_latest())
            if not latest:
                self._set(phase="not-available")
                return

        tag = latest.get("tag_name", "") if isinstance(latest, dict) else ""
        clean_tag = tag.lstrip("vV")
        if not is_newer(tag, APP_VERSION):
            self._set(phase="not-available", next_version=clean_tag)
            return

        installer_asset = None
        for asset in latest.get("assets", []):
            name = asset.get("name", "")
            if fnmatch.fnmatch(name, UPDATE_INSTALLER_PATTERN):
                installer_asset = asset
                break

        if not installer_asset:
            self._set(
                phase="error",
                message=f"Aucun installeur trouve dans la release {tag}.",
            )
            return

        self._set(
            phase="available",
            next_version=tag.lstrip("v"),
            release_notes=latest.get("body", "") or "",
            download_url=installer_asset.get("browser_download_url", ""),
            download_size=installer_asset.get("size", 0),
            is_prerelease=bool(latest.get("prerelease", False)),
        )
        self._start_download()

    def _start_download(self) -> None:
        if self._download_thread and self._download_thread.is_alive():
            return
        self._stop_download.clear()
        self._download_thread = threading.Thread(target=self._do_download, daemon=True)
        self._download_thread.start()

    def _do_download(self) -> None:
        url = self.status.download_url
        if not url:
            self._set(phase="error", message="URL de telechargement manquante.")
            return

        self._set(phase="downloading", percent=0, bytes_per_second=0)

        tmp_dir = Path(tempfile.gettempdir()) / "UltimatePromptBuilder_updates"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        target = tmp_dir / f"UltimatePromptBuilder_setup_{self.status.next_version}.exe"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"UltimatePromptBuilder/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                total = int(r.headers.get("Content-Length", "0") or "0") or self.status.download_size or 0
                downloaded = 0
                start = time.time()
                last_broadcast = 0.0

                with open(target, "wb") as f:
                    while True:
                        if self._stop_download.is_set():
                            self._set(phase="error", message="Telechargement annule.")
                            return
                        chunk = r.read(64 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_broadcast >= 0.4 or downloaded == total:
                            elapsed = max(0.001, now - start)
                            bps = int(downloaded / elapsed)
                            pct = int(downloaded * 100 / total) if total else 0
                            self._set(
                                phase="downloading",
                                percent=pct,
                                bytes_per_second=bps,
                            )
                            last_broadcast = now

            self._set(phase="ready", installer_path=str(target), percent=100)
        except Exception as e:
            logger.exception("download failed")
            self._set(phase="error", message=f"Telechargement echoue : {e}")


# Singleton global
updater = _Updater()
