# -*- coding: utf-8 -*-
"""
Classification des libellés non reconnus par les règles, via un modèle
Ollama tournant en local (http://localhost:11434).
"""
import json
import requests

from rules import CATEGORIES

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"  # modèle léger déjà installé, suffisant pour ce classement

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


def classify_with_ai(libelle: str, montant: float) -> str:
    """Interroge le modèle local et renvoie une catégorie valide (ou 'Autres')."""
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
            return categorie
        # tentative de correspondance approximative
        for c in CATEGORIES:
            if c.lower() in categorie.lower() or categorie.lower() in c.lower():
                return c
        return "Autres"
    except Exception:
        return "Autres"
