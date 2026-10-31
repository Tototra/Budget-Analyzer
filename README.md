# Budget Analyzer

Outil local de catégorisation automatique de relevés bancaires. Importe tes fichiers (CSV, Excel, PDF), obtiens une analyse visuelle par catégorie de dépense, et exporte le tout en Excel.

**100 % local** — aucune donnée bancaire ne quitte ta machine.

## Télécharger

Rendez-vous sur la page [Releases](https://github.com/Tototra/Budget-Analyzer/releases/latest) pour télécharger la dernière version :

- **macOS** — `BudgetAnalyzer-macOS.zip`
- **Windows** — `BudgetAnalyzer-Windows.zip`
- **Linux** — `BudgetAnalyzer-Linux.tar.gz`

### Prérequis

- [Ollama](https://ollama.ai) installé et lancé, avec un modèle :
  ```bash
  ollama pull llama3.2:3b
  ```

## Fonctionnalités

- Import multi-fichiers : CSV, Excel (.xlsx) et PDF en même temps
- Catégorisation automatique par règles (mots-clés) et IA locale (Ollama)
- Graphiques interactifs : donut par catégorie, histogramme par mois
- Export Excel mis en forme avec 3 onglets (Transactions, Par catégorie, Par mois)
- Détection automatique des formats (séparateurs, colonnes débit/crédit, etc.)
- Personnalisable : ajoute tes propres mots-clés dans `rules.py`

## Développement

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 server.py
```

L'application s'ouvre sur `http://localhost:8080`.

## Build

Les builds sont générés automatiquement par GitHub Actions à chaque tag `v*`. Pour builder manuellement :

```bash
pip install pyinstaller
# macOS
pyinstaller budget_analyzer.spec
# Windows
build_windows.bat
# Linux
bash build_linux.sh
```

## Site vitrine

Le dossier `site/` contient la landing page statique, déployée via GitHub Pages.
