# Déploiement & première release

Tout est prêt côté code. Il te reste 4 actions manuelles (les seules choses
que je ne peux pas faire à ta place).

---

## ⚡ Premier déploiement — résumé en 4 étapes

| Étape | Quoi | Combien de temps |
|-------|------|------------------|
| 1. Build l'exe | Double-clic sur `build.bat` | ~3 min |
| 2. Build l'installeur | Double-clic sur `build_installer.bat` | ~1 min |
| 3. Crée le repo GitHub + 1ère release | Web GitHub | ~5 min |
| 4. Déploie la landing sur Netlify | Web Netlify | ~3 min |

Total : **~12 minutes**.

---

## ÉTAPE 1 — Construire l'exécutable

```cmd
build.bat
```

Ce que ça fait :
1. Crée un venv `.venv/` si manquant.
2. Installe PyInstaller + deps de build.
3. Génère l'icône `assets/icon.ico` (multi-résolutions) depuis le logo PIL.
4. Lance PyInstaller avec `ultimate_prompt_builder.spec`.
5. Sortie : **`dist/UltimatePromptBuilder/UltimatePromptBuilder.exe`**

Si ça plante, le message d'erreur exact s'affiche — la cause la plus fréquente
est un module manquant : ajoute-le dans `hiddenimports` du `.spec` puis relance.

---

## ÉTAPE 2 — Construire l'installeur Windows

**Pré-requis** : [Inno Setup 6](https://jrsoftware.org/isdl.php) (gratuit, ~3 Mo).
Choisis la version standard (unicode), française.

```cmd
build_installer.bat
```

Ce que ça fait :
1. Vérifie qu'Inno Setup est installé.
2. Lit la version depuis `updater.py` (ex: `1.2.0`).
3. Compile `installer/ultimate_prompt_builder.iss`.
4. Sortie : **`installer_output/UltimatePromptBuilder_setup_1.2.0.exe`** (~30 Mo).

Cet `.exe` est ce que tu vas distribuer (download direct + asset GitHub Release).

---

## ÉTAPE 3 — GitHub : repo + première release

### 3a. Créer le repo

```cmd
cd "C:\Users\jorda\OneDrive\Bureau\Triskell Studio\Prompts\ultimate_prompt_app"
git init
git add .
git commit -m "Initial commit — Ultimate Prompt Builder v1.2.0"
git branch -M main
```

Ensuite, sur https://github.com/new :
- **Repository name** : `ultimate-prompt-builder`
- **Owner** : `Jordan-Bourillot` (déjà configuré dans `updater.py`)
- **Public**
- Pas de README/LICENSE auto (déjà fournis localement)

Puis :
```cmd
git remote add origin https://github.com/Jordan-Bourillot/ultimate-prompt-builder.git
git push -u origin main
```

### 3b. Créer la première release

Sur https://github.com/Jordan-Bourillot/ultimate-prompt-builder/releases/new :
- **Tag** : `v1.2.0`
- **Title** : `v1.2.0 — Première release publique`
- **Description** : copie le contenu du `CHANGELOG.md` (section v1.2.0)
- **Attach binary** : drag-drop `installer_output/UltimatePromptBuilder_setup_1.2.0.exe`
- **Publish release**

L'auto-updater va automatiquement détecter cette release et toutes les suivantes
(via l'API publique GitHub Releases).

### 3c. Pour les mises à jour suivantes

1. Bump `APP_VERSION` dans `updater.py` (ex: `"1.3.0"`)
2. Ajoute une section dans `CHANGELOG.md`
3. Commit + push
4. Re-run `build.bat` puis `build_installer.bat`
5. Crée une nouvelle release sur GitHub avec le nouveau tag + asset

Les utilisateurs verront la mise à jour proposée dans Paramètres au prochain
lancement (vérification auto 5s après le démarrage).

---

## ÉTAPE 4 — Landing sur Netlify

### 4a. Push la landing dans son propre repo (ou sous-dossier)

Option simple : déploie directement depuis le dossier `landing/`.

```cmd
cd landing
npm install -g netlify-cli   # si pas déjà fait
netlify init                  # crée un nouveau site Netlify
netlify deploy --prod         # déploie en prod
```

### 4b. Connecter le sous-domaine

Dans le dashboard Netlify du nouveau site :
1. **Domain settings** → **Add custom domain** → `prompt-builder.triskell-studio.fr`
2. Ajoute un enregistrement CNAME chez ton registrar pointant vers le sous-domaine Netlify (ex: `nervous-lion-1234.netlify.app`)
3. SSL automatique via Let's Encrypt (~1 min)

### 4c. Lien de téléchargement

Tu as 2 options pour le bouton "Télécharger" de la landing :

**Option A — redirection vers GitHub Release (recommandé, zéro maintenance)**

Édite `landing/public/index.html`, remplace :
```html
<a id="download-btn" href="/_dl/UltimatePromptBuilder_setup_latest.exe" download>
```
par :
```html
<a id="download-btn" href="https://github.com/Jordan-Bourillot/ultimate-prompt-builder/releases/latest/download/UltimatePromptBuilder_setup_1.2.0.exe" download>
```
(à mettre à jour à chaque release pour pointer vers la version courante)

**Option B — héberger l'installeur sur Netlify**

Crée `landing/public/_dl/` et copie-y l'installeur :
```cmd
mkdir landing\public\_dl
copy installer_output\UltimatePromptBuilder_setup_1.2.0.exe landing\public\_dl\UltimatePromptBuilder_setup_latest.exe
netlify deploy --prod
```

---

## ✅ Checklist finale

- [ ] `build.bat` → `dist/UltimatePromptBuilder/UltimatePromptBuilder.exe` existe
- [ ] `build_installer.bat` → `installer_output/UltimatePromptBuilder_setup_1.2.0.exe` existe
- [ ] Repo GitHub `Jordan-Bourillot/ultimate-prompt-builder` public et pushé
- [ ] Release `v1.2.0` créée avec l'installeur en asset
- [ ] Site Netlify lié à `prompt-builder.triskell-studio.fr`
- [ ] CNAME chez ton registrar configuré
- [ ] Bouton télécharger pointe vers la bonne URL

Une fois ces 7 cases cochées, l'auto-updater fonctionne en boucle fermée :
chaque future release sur GitHub sera automatiquement détectée et installée
en 1 clic par tes utilisateurs.

---

## Ce que je fais déjà à chaque release future

À chaque fois que tu veux sortir une nouvelle version, dis-moi simplement :
> "release v1.3.0 avec ces changements : [liste]"

Je m'occupe de :
1. Bumper `APP_VERSION` dans `updater.py`
2. Ajouter une section dans `CHANGELOG.md`
3. Mettre à jour `BRAND_VERSION` (auto via l'import)
4. Te lister les commandes à lancer

Toi tu fais juste : `build.bat`, `build_installer.bat`, et créer la release sur GitHub web (drag-drop l'asset). 5 minutes.
