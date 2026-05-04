"""Build the ultimate prompt by combining a user prompt with selected mega prompts."""
from __future__ import annotations

from datetime import datetime
from typing import Sequence


SEPARATOR = "=" * 70
SUB_SEPARATOR = "-" * 70


def build_ultimate_prompt(
    user_prompt: str, mega_prompts: Sequence[dict]
) -> str:
    """Combine the user prompt with one or more mega prompts.

    Structure:
      1. Header (rôle système, méta)
      2. Each mega prompt as a numbered block
      3. The user's actual request, clearly marked
    """
    if not isinstance(user_prompt, str):
        raise TypeError("user_prompt must be a string")
    user_prompt = user_prompt.strip()
    if not user_prompt:
        raise ValueError("Le prompt utilisateur est vide.")
    if not mega_prompts:
        return user_prompt

    parts: list[str] = []
    parts.append(SEPARATOR)
    parts.append("PROMPT ULTIME - GENERE PAR ULTIMATE PROMPT BUILDER")
    parts.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    parts.append(f"Mega Prompts actifs ({len(mega_prompts)}):")
    for i, mp in enumerate(mega_prompts, 1):
        parts.append(f"  {i}. [{mp.get('id', '??')}] {mp.get('name', 'Sans nom')}")
    parts.append(SEPARATOR)
    parts.append("")
    parts.append("INSTRUCTIONS COMPORTEMENTALES (a appliquer simultanement)")
    parts.append("")

    for i, mp in enumerate(mega_prompts, 1):
        parts.append(SUB_SEPARATOR)
        parts.append(
            f"--- MEGA PROMPT {i}/{len(mega_prompts)}: {mp.get('name', '?')} ---"
        )
        parts.append(SUB_SEPARATOR)
        parts.append(mp.get("content", "").strip())
        parts.append("")

    parts.append(SEPARATOR)
    parts.append("DEMANDE DE L'UTILISATEUR")
    parts.append(SEPARATOR)
    parts.append("")
    parts.append(user_prompt)
    parts.append("")
    parts.append(SEPARATOR)
    parts.append(
        "FIN DU PROMPT ULTIME. Reponds en appliquant TOUTES les regles ci-dessus."
    )
    parts.append(SEPARATOR)
    return "\n".join(parts)
