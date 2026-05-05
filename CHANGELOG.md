# Changelog

## v1.4.0 — 2026-05-05
- **Auto-updater Pattern A** : lit `prompt-builder.triskell-studio.fr/version.json` (manifest landing standard Triskell), fallback GitHub Releases pour la rétro-compat
- **Bugfix icône taskbar/alt-tab** : AppUserModelID `triskell.alphabeast` + `_apply_window_icon` propagé aux Toplevel — fini l'icône grise Tk par défaut
- **Boutons "Effacer"** sur l'input et la sortie générée
- **Palette unifiée** : champs et scrollables alignés Triskell (plus de gris CTk par défaut), hover violet (#7C3AED) au lieu de orange
- **Hiérarchie des presets retirée** : tous en outline uniforme (le preset "maison" surligné créait de la confusion)
- **Accents fixés** dans les libellés ("Version installée", "Dernière version", "Tu es à jour")
- **Installeur renommé** : `AlphaBeast_setup_X.Y.Z.exe` (le binaire interne reste `UltimatePromptBuilder.exe` pour préserver l'auto-update). Les v1.3.x devront mettre à jour manuellement la 1ère fois.

## v1.3.0 — 2026-05-04
- **Onboarding** : Welcome dialog au 1er lancement (3 étapes guidées + raccourci Paramètres)
- **Bouton "?"** dans le topbar pour rouvrir le guide à tout moment
- **Bouton Generate state-aware** : devient vif quand prompt + mega prêts, indique ce qui manque sinon
- **Fenêtre Réponse IA** refaite : header avec métadonnées (provider, modèle, char count, tokens), bouton Copier avec feedback visuel, bouton Exporter en .md, raccourci Ctrl+C
- **Mega prompts enrichis** :
  - 00 Autonomie : généralisée hors coding (livre, étude, événement, dossier financement)
  - 11 Mémoire de projet : applicable à tout projet long, pas seulement code
  - 13 Mode produit : couvre code/contenu/offre/campagne/lancement
  - Section "QUAND NE PAS UTILISER" ajoutée aux 13 autres prompts
  - Exemples contextuels multi-domaine sur 03/05/14
- Rebrand interne : Ultimate Prompt Builder → AlphaBeast (paths binaires inchangés pour compat auto-updater)

## v1.2.0 — 2026-05-04
- Auto-updater (mirror Studio PDF / DéliNote pattern)
- Bibliothèque CRUD : éditer / créer / supprimer les Mega Prompts
- Branding Triskell Studio complet (palette site, logo triskell PIL, fonts Syne + Inter)
- 7 presets (incluant "Production de sites" maison)
- Étapes numérotées 1-2-3-4 pour clarifier le parcours
- Mode sombre forcé + titlebar Windows en sombre (DWM)
- 5 providers IA : Anthropic, OpenAI, Google, Mistral, xAI

## v1.0.0 — 2026-05-04
- Première release
- 16 Mega Prompts du PDF "Bibliothèque de prompts auto-adressés"
- UI CustomTkinter mode sombre
- Génération du Prompt Ultime + envoi direct à l'IA
- Historique + sauvegarde + export
