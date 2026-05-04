# PROJECT_STATE — AlphaBeast

## Vision
App desktop locale Python qui combine un prompt utilisateur avec un ou plusieurs des
16 Mega Prompts (PDF "Bibliotheque de prompts auto-adresses") pour produire un
"Prompt Ultime", le copier ou l'envoyer directement a une IA (Claude, GPT, Gemini,
Mistral, Grok). Cible : un utilisateur unique, machine locale, mode sombre, fluide.

## Etat courant
**Toutes phases terminees.** App livree, testable, lancable.

| Phase | Statut |
|-------|--------|
| 0 — Setup deps | OK |
| 1 — Donnees 16 mega prompts | OK |
| 2 — Modules config / providers / builder | OK |
| 3 — UI CustomTkinter (fenetre principale) | OK |
| 4 — Dialogs Settings + Historique + Reponse IA | OK |
| 5 — Suite de tests (17 tests, 100% pass) | OK |
| 6 — Smoke test headless | OK |
| 7 — Doc + scripts | OK |

## Structure des fichiers
```
ultimate_prompt_app/
├── app.py               # Entree principale + UI CustomTkinter
├── config.py            # I/O JSON (settings, history, saved, mega prompts)
├── ai_providers.py      # 5 providers (Anthropic, OpenAI, Google, Mistral, xAI)
├── prompt_builder.py    # Generation du Prompt Ultime
├── mega_prompts.json    # Les 16 Mega Prompts (extraits du PDF)
├── settings.json        # Cles API + preferences (genere au 1er lancement)
├── history.json         # Historique des derniers prompts (cap configurable)
├── saved_prompts.json   # Prompts sauvegardes manuellement
├── test_app.py          # 17 tests unitaires + integration
├── requirements.txt
├── run.bat              # Lance l'app sous Windows
├── PROJECT_STATE.md     # Ce fichier
├── BACKLOG.md           # Idees hors-scope reportees
└── README.md
```

## Endpoints / API externes
- Anthropic : `POST https://api.anthropic.com/v1/messages` (header `x-api-key`)
- OpenAI : `POST https://api.openai.com/v1/chat/completions` (Bearer)
- Google : `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=...`
- Mistral : `POST https://api.mistral.ai/v1/chat/completions` (Bearer)
- xAI : `POST https://api.x.ai/v1/chat/completions` (Bearer)

## Variables d'environnement requises
**Aucune** — toutes les cles API sont saisies via la fenetre Parametres et
stockees dans `settings.json` local (en clair, single-user — voir DETTE).

## Decisions structurantes
1. **Python 3.12 + CustomTkinter 5.2.2** : moderne, mode sombre par defaut, sans
   dependances natives lourdes.
2. **Pas de SDK officiels (openai, anthropic)** : `requests` direct contre les
   endpoints REST. Avantage : zero churn de version, code identique pour 5 providers.
3. **JSON plats pour persistance** : settings.json, history.json, saved_prompts.json,
   mega_prompts.json. Ecriture atomique (`.tmp` + `os.replace`).
4. **Threading pour l'envoi a l'IA** : worker `threading.Thread`, callback via
   `self.after(0, ...)` pour rester thread-safe Tk.
5. **Mega prompts en ASCII** : pas d'accents, pour eviter tout probleme d'encodage
   sur clipboard Windows / console.
6. **Tags chips custom** au lieu d'une listbox : meilleure UX, removable individuellement.
7. **Catalogue de modeles fige** par provider (mis a jour manuellement) plutot
   qu'auto-discovery (qui couterait des appels API juste pour lister).

## Hypotheses non verifiees
- Les noms de modeles (claude-sonnet-4-5, gpt-4o, etc.) sont valides chez les
  providers a date. Si un nom evolue, l'utilisateur peut adapter PROVIDERS dans
  `ai_providers.py`.
- L'API Google Gemini renvoie bien `candidates[0].content.parts[*].text` — verifie
  documentairement, pas avec une vraie cle.

## Risques identifies
| Risque | Proba | Mitigation |
|--------|-------|------------|
| Cle API en clair sur disque | Moyenne | Documenter; envisager keyring (BACKLOG) |
| Timeout des longues reponses IA | Moyenne | `DEFAULT_TIMEOUT=120s`. Si insuffisant, ajustable dans `ai_providers.py` |
| API d'un provider change de format | Faible | Erreurs taggees ProviderError avec contexte; user voit le message |
| Mega prompts trop longs > token limit | Moyenne | Pas de troncature; le provider renverra une 400, message affiche |

## TODOs reportes
Aucun. Tout le scope du brief est livre.

## Glossaire
- **Mega Prompt** : un des 16 prompts comportementaux du PDF (Honnetete brutale,
  Anti-slop, etc.).
- **Prompt Ultime** : concatenation structuree d'un prompt utilisateur + N Mega
  Prompts, formate par `prompt_builder.build_ultimate_prompt`.
- **Provider** : fournisseur IA (anthropic, openai, google, mistral, xai).

## DETTE TECHNIQUE ASSUMEE
- Cles API stockees en clair dans `settings.json` (pas de keyring/DPAPI). Acceptable
  pour usage local single-user.
- Pas de venv configure : utilisation de Python global. L'utilisateur peut creer un
  venv s'il prefere isoler les deps.
- Pas de streaming des reponses IA : on attend la reponse complete. Acceptable pour
  la majorite des cas (< 30s typiques).
- Pas de gestion multi-tour de conversation : chaque appel est une requete
  independante. Conforme au brief "Generer / Envoyer une fois".
- Pas d'i18n : strings UI en francais, contenus mega prompts ASCII (sans accents).
