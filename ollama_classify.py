# -*- coding: utf-8 -*-
"""
Classification des libellés non reconnus par les règles.
Mode hybride :
  - Si Ollama est disponible : utilise le modèle local pour classifier
  - Sinon : renvoie "Autres" (l'utilisateur peut corriger dans rules.py)
"""
import json
import requests

from rules import CATEGORIES

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
MODEL = "llama3.2:3b"

PROMPT_TEMPLATE = """Tu catégorises des lignes de relevé bancaire français. Choisis UNE catégorie
dans cette liste FERMÉE :
{categories}

Règles importantes :
- "Épargne / Virements internes" est réservé aux vrais virements entre comptes
  du même titulaire (livret, épargne, compte à compte). Un paiement par carte
  chez un commerçant ou un site marchand n'est JAMAIS un virement interne,
  même si tu ne reconnais pas le nom.
- Un paiement à un commerçant/service inconnu que tu ne reconnais pas va dans
  "Loisirs / Shopping" si c'est probablement un achat, sinon "Autres".
- Ne réponds jamais par une catégorie absente de la liste.

Exemples :
Libellé: "CB PAYPAL *SOMEBOUTIQUE123" -> {{"categorie": "Loisirs / Shopping"}}
Libellé: "VIR LIVRET A" -> {{"categorie": "Épargne / Virements internes"}}
Libellé: "PRLV INCONNU XYZ" -> {{"categorie": "Autres"}}

Libellé à classer : "{libelle}"
Montant : {montant}

Réponds UNIQUEMENT avec un JSON de la forme exacte :
{{"categorie": "UNE_DES_CATEGORIES_CI_DESSUS"}}
Aucun texte avant ou après le JSON."""


# ── Détection d'Ollama ───────────────────────────────────────────────────────

_ollama_status = None  # None = pas encore vérifié, True/False après


def check_ollama() -> dict:
    """Vérifie si Ollama est joignable et qu'un modèle est disponible.
    Retourne {"ollama": bool, "model": bool, "model_name": str|None, "models": list}
    """
    result = {"ollama": False, "model": False, "model_name": None, "models": []}
    try:
        r = requests.get(OLLAMA_TAGS_URL, timeout=3)
        if r.status_code == 200:
            result["ollama"] = True
            models = r.json().get("models", [])
            result["models"] = [m["name"] for m in models]
            if models:
                result["model"] = True
                result["model_name"] = models[0]["name"]
    except Exception:
        pass
    return result


def is_ollama_available() -> bool:
    """Cache le résultat pour ne pas checker à chaque transaction."""
    global _ollama_status
    if _ollama_status is None:
        status = check_ollama()
        _ollama_status = status["ollama"] and status["model"]
    return _ollama_status


def reset_ollama_check():
    """Force un re-check (appelé quand l'utilisateur installe Ollama)."""
    global _ollama_status
    _ollama_status = None


# ── Classification ───────────────────────────────────────────────────────────

def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def classify_with_ai(libelle: str, montant: float) -> tuple[str, str]:
    """Classifie un libellé.
    Retourne (catégorie, méthode).
    Si Ollama est dispo : utilise l'IA.
    Sinon : renvoie "Autres" avec méthode "non classé".
    """
    if not is_ollama_available():
        return "Autres", "non classé"

    prompt = PROMPT_TEMPLATE.format(
        categories="\n".join(f"- {c}" for c in CATEGORIES),
        libelle=libelle,
        montant=montant,
    )
    try:
        raw = _call_ollama(prompt)
        data = json.loads(raw)
        categorie = data.get("categorie", "").strip()
        if categorie in CATEGORIES:
            return categorie, "IA locale"
        for c in CATEGORIES:
            if c.lower() in categorie.lower() or categorie.lower() in c.lower():
                return c, "IA locale"
        return "Autres", "IA locale"
    except Exception:
        return "Autres", "non classé"
