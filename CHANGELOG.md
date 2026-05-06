# Changelog

## v1.5.3 — 2026-05-06
### Logo polish
- **Source = brand asset officiel landing** (`landing/public/img/icon.png` — chat bubble violet rempli, sparkles, version polie utilisée sur prompt-builder.triskell-studio.fr) au lieu de la version recolorée outline. Le brand est cohérent partout : landing + app desktop + taskbar Windows.
- **Fond rounded-square sombre stripé → transparence** (THRESHOLD=80, plus généreux que la version legacy à 40 — le fond navy du brand asset a un léger gradient qui survivait sinon). L'icône s'intègre désormais nativement à n'importe quel fond UI.
- **Crop serré sur le pictogramme** (suppression de la marge de sécurité `side // 24`) → +20% de surface visible quand l'icône est downsamplée à 24-32 px (taskbar Windows, alt-tab).

### Dev mode
- **Fallback `iconphoto` (PIL PhotoImage)** dans `_apply_window_icon` en plus de `iconbitmap` : override l'icône `python.exe` qui apparaissait à la place du chat-bubble en mode dev. Reference gardée en attribut `_icon_photo_ref` pour empêcher le GC qui faisait disparaître l'icône silencieusement après quelques secondes.

## v1.5.2 — 2026-05-06
### UX & branding
- **Logo en miroir horizontal** (queue à droite, sparkles à gauche) — meilleur alignement visuel avec le wordmark "triskell STUDIO" placé à droite. Recoloration violet préservée.
- **`icon.ico` regénéré à partir du chat-bubble** (au lieu du fallback 3 spirales) — la barre de titre Windows + l'icône taskbar / alt-tab + l'icône des dialogues secondaires (Settings, Welcome, Bibliothèque, Historique) reflètent désormais le logo de l'app, pas un placeholder.

### Step 3 — refonte CTA
- **Bouton "Générer" hero plein-largeur** : suppression du badge "3" et du sous-titre verbeux qui se concurrençaient. La barre EST le bouton (height=56, font 16pt, `fill="both", expand=True`). Le texte mute déjà tout seul selon l'état de readiness ("↑ Choisis un Mega Prompt", "↑ Écris ton prompt de base") — plus besoin de labels d'accompagnement.
- **Hauteur barre** : 72 → 84 px pour respirer.

### Paramètres
- **Boutons "↗ Obtenir" à droite de chaque clé API** : ouvre la console du provider directement dans le navigateur (Anthropic / OpenAI / Google AI Studio / Mistral / xAI). Plus besoin de chercher l'URL à la main.
- **Fenêtre Paramètres 640×560 → 720×800** : tout s'affiche sans scroll (Clés API + 5 entries + Mises à jour + Annuler/Enregistrer).

### Mega Prompts
- **"00 Autonomie continue" durci** (5511 → 8581 chars) : passage en framing "OPÉRATEUR AUTONOME" (rôle contraint), réduction des motifs d'arrêt 4 → 3, liste exhaustive des 11 formulations interrogatives bannies, nouvelle règle 16 "Momentum maximum" (≥1 étape complète + démarrage de la suivante par message), auto-audit en 3 questions avant chaque message, exemples concrets de transformations méta-commentaires → action.

## v1.5.1 — 2026-05-06
### Bugfix UI
- **Bouton "Générer" invisible** : sur les écrans où la fenêtre rentrait juste, le bouton était poussé hors-écran par les 8 cartes preset (en grille 2×4) cumulées au textarea + tags + sel_row. Refonte du layout principal en `grid` (au lieu de `pack`) avec `step3_bar` épinglé sur sa propre row dédiée (`row=4`, `height=72`, `grid_propagate(False)`) — le CTA est maintenant **toujours visible**, peu importe la hauteur de la fenêtre.
- **Panneau gauche compacté** : `minsize` du textarea passé de 240 → 160 px pour libérer l'espace nécessaire à `Option B` + dropdown + `Selection active` + tags sur écrans 1080p.

## v1.5.0 — 2026-05-06
### Nouvelles fonctionnalités
- **Bouton "✨ Améliorer le prompt de base"** dans le panneau 1 : envoie ton brouillon à l'IA sélectionnée avec un méta-prompt qui le structure et le précise sans dévier de l'intention. Loader, gestion d'erreur, strip auto des fences markdown / guillemets parasites.
- **Mode clair** : toggle ☀/🌙 dans la top-bar. Palette `LIGHT_PALETTE` complète (slate-leaning, violet désaturé pour ne pas agresser les yeux), `_rebuild_ui` qui détruit + reconstruit l'UI sans redémarrage tout en préservant brouillon + prompt ultime + méga-prompts actifs. Titlebar Windows DWM bascule en clair/sombre cohérente avec le thème.
- **Aperçu de structure dynamique** dans le panneau 4 : remplace le texte statique par un squelette en CTkLabels stackés (couleurs garanties, contrairement aux tags Tk dans CTkTextbox). Titre Syne 22 pt orange, sections 1/2/3 avec badges colorés indigo/violet/orange, méga-prompts numérotés avec ID et nom mis en valeur, brouillon affiché en aperçu, CTA `« Generer le Prompt Ultime »` orange + raccourci `Ctrl+Enter`. Mise à jour live au moindre changement de sélection ou de saisie.

### UI refondue
- **Logo bulle agrandi** 38 → 120 px (topbar 100 px). PNG source nettoyé : strip automatique des pixels proches du noir → transparence, recadrage en bbox carré centré sans distorsion, recolorisation **monochrome indigo** (700 → 500 → 300) pour cohérence brand.
- **Cartes preset refaites** : 8 combos (ajout de **⚔ Critique honnête**) en grille 2×4 équilibrée. Chaque carte = pastille icône colorée + nom gras + **phrase explicative** ("Pour assembler un site web complet sans validations à mi-parcours.") au lieu de la liste cryptique des méga-prompts. Hover en fondu (interpolation de bordure 130 ms) vers la couleur de catégorie.
- **Sous-titres explicatifs** à côté de chaque titre de section (étapes 1/2/3/4).
- **Couleurs ajoutées** : badge étape 2 violet, badge étape 3 orange, dégradé indigo→violet→orange du trio brand. Bouton "Generer" passe orange quand prêt. Compteur "X/16" et badges TagWidget en violet quand actif.
- **Boutons polis** : `corner_radius` cohérents (10/12/14), hauteurs harmonisées (28/36/44/48), bordures retirées sur les CTAs solides, hover plus contrastés (`accent_dim` / `tag_bg_hover`).
- **Spinner amélioré** : 3 points qui défilent en vague (`● · ·` → `· ● ·` → `· · ●`) au lieu du caractère qui tourne.
- **Label "● Prêt"** masqué dans le header panneau 4 (widget conservé pour les statuts d'erreur, juste sorti de la grille).

### Animations
- **Fade-in de la fenêtre** au démarrage (alpha 0 → 1 en 13 paliers × 20 ms ≈ 260 ms).
- **Breathing pulse** sur le bouton "Generer" quand il devient "ready" : sinusoïde douce entre orange-500 et orange-400, cycle 2.4 s. S'arrête automatiquement aux transitions d'état.
- **Pulse de bordure** sur la zone Prompt Ultime à chaque génération réussie (flash accent → violet → border en 750 ms).
- **Hover en fondu** sur les 8 cartes preset (130 ms).

### Sous le capot
- Refactor `PALETTE` en `DARK_PALETTE` / `LIGHT_PALETTE`, dict mutable rempli au démarrage selon le setting. Nouvelle clé `text_strong` (sub blanc/noir selon le thème) — tous les `text_color="#FFFFFF"` du fichier basculés vers `PALETTE["text_strong"]`.
- Helpers d'animation génériques : `_hex_to_rgb`, `_lerp_hex`, `_animate_attr`, `_breathing_step`, `_swap_to_preview/_swap_to_output`, `_apply_palette`, `_rebuild_ui`.
- Bug fix : `left.grid_rowconfigure(1, weight=1, minsize=240)` — la zone d'input du panneau 1 ne peut plus être écrasée à 0 px quand les cartes preset prennent beaucoup de place.

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
