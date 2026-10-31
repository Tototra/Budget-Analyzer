# -*- coding: utf-8 -*-
"""
Règles de catégorisation par mots-clés.
Tout libellé contenant un de ces mots-clés (insensible à la casse/accents)
est classé directement, sans passer par le modèle IA.

Pour corriger une erreur : ajoute le mot-clé qui revient souvent dans la
bonne catégorie ci-dessous. Le script s'améliore avec le temps.
"""

CATEGORIES = [
    "Alimentation",
    "Logement",
    "Transport",
    "Santé",
    "Restaurants / Sorties",
    "Loisirs / Shopping",
    "Abonnements",
    "Impôts / Administration",
    "Épargne / Virements internes",
    "Revenus",
    "Autres",
]

# Catégorie à exclure des totaux de "dépenses" (virements entre tes propres
# comptes, remboursements, etc.) — modifiable.
CATEGORIE_EXCLUE_DES_DEPENSES = {"Épargne / Virements internes", "Revenus"}

# clé = catégorie, valeur = liste de mots-clés (majuscules, sans accents de préférence)
RULES = {
    "Alimentation": [
        "CARREFOUR", "LECLERC", "AUCHAN", "INTERMARCHE", "LIDL", "MONOPRIX",
        "FRANPRIX", "CASINO", "BIOCOOP", "SUPER U", "U EXPRESS", "ALDI",
        "PICARD", "GRAND FRAIS", "NATURALIA",
    ],
    "Logement": [
        "EDF", "ENGIE", "TOTALENERGIES", "LOYER", "SYNDIC", "VEOLIA",
        "SUEZ EAU", "ORANGE", "SFR", "FREE MOBILE", "BOUYGUES TELECOM",
        "ASSURANCE HABITATION", "ENEDIS",
    ],
    "Transport": [
        "SNCF", "RATP", "TOTAL ", "TOTALENERGIES STATION", "ESSO", "SHELL",
        "BP ", "UBER ", "UBER.COM", "BLABLACAR", "FLIXBUS", "NAVIGO",
        "AUTOROUTE", "VINCI AUTOROUTES", "PARKING", "ZITYSCOOT", "VELIB",
    ],
    "Santé": [
        "PHARMACIE", "DOCTOLIB", "CPAM", "MUTUELLE", "LABORATOIRE",
        "CABINET MEDICAL", "DENTISTE", "OPTICIEN", "KINE",
    ],
    "Restaurants / Sorties": [
        "UBER EATS", "DELIVEROO", "JUST EAT", "MCDONALD", "BURGER KING",
        "RESTAURANT", "BRASSERIE", "CAFE ", "BAR ", "KFC", "STARBUCKS",
    ],
    "Loisirs / Shopping": [
        "AMAZON", "FNAC", "DECATHLON", "ZARA", "H&M", "CDISCOUNT",
        "VINTED", "LEBONCOIN", "CINEMA", "UGC", "PATHE", "SEPHORA",
        "IKEA", "APPLE.COM",
    ],
    "Abonnements": [
        "NETFLIX", "SPOTIFY", "DEEZER", "DISNEY", "AMAZON PRIME",
        "YOUTUBE PREMIUM", "ICLOUD", "OPENAI", "ANTHROPIC", "CANAL+",
        "SALLE DE SPORT", "BASIC FIT", "FITNESS PARK",
    ],
    "Impôts / Administration": [
        "DGFIP", "TRESOR PUBLIC", "IMPOTS", "URSSAF", "PREFECTURE",
        "AMENDE", "ANTAI",
    ],
    "Épargne / Virements internes": [
        "VIREMENT INTERNE", "VIR INTERNE", "LIVRET A", "LDD", "PEA",
        "VIREMENT DE COMPTE A COMPTE", "EPARGNE",
    ],
    "Revenus": [
        "VIREMENT SALAIRE", "VIR SALAIRE", "SALAIRE", "CAF",
        "REMBOURSEMENT", "VIR RECU",
    ],
}


def normalize(text: str) -> str:
    """Majuscule + suppression des accents simples, pour matcher plus large."""
    if text is None:
        return ""
    text = text.upper()
    replacements = {
        "É": "E", "È": "E", "Ê": "E", "Ë": "E",
        "À": "A", "Â": "A",
        "Î": "I", "Ï": "I",
        "Ô": "O",
        "Û": "U", "Ù": "U",
        "Ç": "C",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text


def classify_by_rules(libelle: str):
    """Retourne la catégorie trouvée par mot-clé, ou None si rien ne correspond.

    En cas de plusieurs mots-clés correspondants (ex: "UBER " et "UBER EATS"),
    le mot-clé le plus long (donc le plus spécifique) gagne, pour éviter
    qu'un mot-clé générique écrase un cas plus précis.
    """
    norm = normalize(libelle)
    meilleur = None  # (longueur_mot_cle, categorie)
    for categorie, mots in RULES.items():
        for mot in mots:
            mot_norm = normalize(mot).strip()
            if mot_norm and mot_norm in norm:
                if meilleur is None or len(mot_norm) > meilleur[0]:
                    meilleur = (len(mot_norm), categorie)
    return meilleur[1] if meilleur else None
