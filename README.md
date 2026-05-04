# Ultimate Prompt Builder

Mini-app desktop Python (CustomTkinter, mode sombre) pour combiner ton prompt avec
1+ des **16 Mega Prompts** de la "Bibliotheque de prompts auto-adresses" et envoyer
directement le resultat a Claude / GPT / Gemini / Mistral / Grok.

## Installation

```bash
pip install -r requirements.txt
```

Python 3.10+ recommande (teste sur 3.12).

## Lancement

```bash
python app.py
```

Ou sous Windows : double-clique sur `run.bat`.

## Premiere utilisation

1. Clique sur **Parametres** (en haut a droite) et colle au moins une cle API.
2. Choisis le provider et le modele dans la barre IA.
3. Ecris ton prompt de base dans la grande zone de gauche.
4. Ajoute un ou plusieurs Mega Prompts via le menu deroulant + bouton **+ Ajouter**.
5. Clique **Generer le Prompt Ultime** (ou `Ctrl+Enter`).
6. Le prompt ultime apparait a droite. Tu peux :
   - **Copier** (presse-papier),
   - **Sauvegarder** (`Ctrl+S`, va dans `saved_prompts.json`),
   - **Envoyer a l'IA** (la reponse s'affiche dans une fenetre).

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| `Ctrl+Enter` | Generer le Prompt Ultime |
| `Ctrl+S` | Sauvegarder le prompt courant |

## Tests

```bash
python test_app.py
```

17 tests, tous verts.

## Structure

Voir `PROJECT_STATE.md`.
