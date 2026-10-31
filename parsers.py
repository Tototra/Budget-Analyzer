# -*- coding: utf-8 -*-
"""
Parseurs de relevés bancaires : CSV, Excel (.xlsx/.xls), PDF.
Chaque parseur renvoie un DataFrame avec les colonnes Date, Libellé, Montant.
"""
import re
import pandas as pd

CANDIDATES = {
    "date": ["date", "date operation", "date de l'operation", "date comptable",
             "date valeur", "date de valeur"],
    "libelle": ["libelle", "libellé", "description", "intitule", "intitulé",
                "detail", "détail", "libelle operation", "libellé opération",
                "communication"],
    "montant": ["montant", "amount", "montant eur", "montant (eur)"],
    "debit": ["debit", "débit", "montant débit", "debit (eur)"],
    "credit": ["credit", "crédit", "montant crédit", "credit (eur)"],
}


def _guess_column(columns, keys):
    norm_cols = {c: c.strip().lower() for c in columns}
    for col, norm in norm_cols.items():
        if norm in keys:
            return col
    for col, norm in norm_cols.items():
        if any(k in norm for k in keys):
            return col
    return None


def _build_dataframe(df, date_col=None, libelle_col=None, montant_col=None):
    """À partir d'un DataFrame brut, détecte les colonnes et renvoie un
    DataFrame propre avec Date / Libellé / Montant."""
    df.columns = [str(c).strip() for c in df.columns]

    date_col = date_col or _guess_column(df.columns, CANDIDATES["date"])
    libelle_col = libelle_col or _guess_column(df.columns, CANDIDATES["libelle"])
    montant_col = montant_col or _guess_column(df.columns, CANDIDATES["montant"])

    if montant_col is None:
        debit_col = _guess_column(df.columns, CANDIDATES["debit"])
        credit_col = _guess_column(df.columns, CANDIDATES["credit"])
        if debit_col and credit_col:
            debit = pd.to_numeric(
                df[debit_col].astype(str).str.replace(",", ".").str.replace(r"\s", "", regex=True),
                errors="coerce",
            ).fillna(0)
            credit = pd.to_numeric(
                df[credit_col].astype(str).str.replace(",", ".").str.replace(r"\s", "", regex=True),
                errors="coerce",
            ).fillna(0)
            df["__montant__"] = credit - debit.abs()
            montant_col = "__montant__"

    missing = []
    if date_col is None:
        missing.append("date")
    if libelle_col is None:
        missing.append("libellé")
    if montant_col is None:
        missing.append("montant")
    if missing:
        raise ValueError(
            f"Colonnes non trouvées : {missing}.\n"
            f"Colonnes disponibles : {list(df.columns)}"
        )

    out = pd.DataFrame({
        "Date": df[date_col].astype(str),
        "Libellé": df[libelle_col].astype(str),
        "Montant": pd.to_numeric(
            df[montant_col].astype(str).str.replace(",", ".").str.replace(r"\s", "", regex=True),
            errors="coerce",
        ),
    }).dropna(subset=["Montant"])
    out = out[out["Montant"] != 0]
    return out.reset_index(drop=True)


# ── CSV ──────────────────────────────────────────────────────────────────────

def parse_csv(file_path_or_buffer, sep=None, decimal=None):
    """Lit un CSV. Détecte automatiquement le séparateur si non précisé."""
    if sep is None:
        # lecture des premières lignes pour deviner
        if hasattr(file_path_or_buffer, "read"):
            sample = file_path_or_buffer.read(4096)
            file_path_or_buffer.seek(0)
            if isinstance(sample, bytes):
                sample = sample.decode("utf-8", errors="replace")
        else:
            with open(file_path_or_buffer, "r", encoding="utf-8", errors="replace") as f:
                sample = f.read(4096)
        sep = ";" if sample.count(";") > sample.count(",") else ","

    decimal = decimal or ("," if sep == ";" else ".")
    df = pd.read_csv(file_path_or_buffer, sep=sep, decimal=decimal, engine="python",
                     encoding="utf-8", encoding_errors="replace")
    return _build_dataframe(df)


# ── Excel ────────────────────────────────────────────────────────────────────

def parse_excel(file_path_or_buffer):
    """Lit un fichier .xlsx / .xls. Prend la première feuille avec assez de colonnes."""
    xls = pd.ExcelFile(file_path_or_buffer)
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        if len(df.columns) >= 3 and len(df) >= 1:
            try:
                return _build_dataframe(df)
            except ValueError:
                continue
    raise ValueError(
        f"Aucune feuille exploitable trouvée. Feuilles : {xls.sheet_names}"
    )


# ── PDF ──────────────────────────────────────────────────────────────────────

def parse_pdf(file_path_or_buffer):
    """Extrait les transactions d'un relevé bancaire PDF.
    Essaie d'abord l'extraction de tableaux (pdfplumber), puis
    tombe en fallback sur l'extraction de texte avec regex.
    """
    import pdfplumber

    # ── Tentative 1 : tableaux pdfplumber ──
    all_rows = []
    with pdfplumber.open(file_path_or_buffer) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and any(row):
                        all_rows.append([str(c).strip() if c else "" for c in row])

    if len(all_rows) > 2:
        # la première ligne qui ressemble à un en-tête
        header = all_rows[0]
        data = all_rows[1:]
        df = pd.DataFrame(data, columns=header)
        try:
            return _build_dataframe(df)
        except ValueError:
            pass  # on tente le fallback texte

    # ── Tentative 2 : regex sur le texte brut ──
    # Pattern courant : DD/MM/YYYY  libellé  montant (avec virgule décimale)
    pattern = re.compile(
        r"(\d{2}[/.-]\d{2}[/.-]\d{2,4})"   # date
        r"\s+"
        r"(.+?)"                             # libellé (non-greedy)
        r"\s+"
        r"(-?\d[\d\s]*[.,]\d{2})"            # montant
    )
    rows = []
    with pdfplumber.open(file_path_or_buffer) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                m = pattern.search(line)
                if m:
                    date, libelle, montant = m.group(1), m.group(2).strip(), m.group(3)
                    montant = montant.replace(" ", "").replace(",", ".")
                    rows.append({"Date": date, "Libellé": libelle, "Montant": float(montant)})

    if not rows:
        raise ValueError(
            "Impossible d'extraire les transactions de ce PDF. "
            "Essaie d'exporter ton relevé en CSV depuis le site de ta banque — "
            "c'est le format le plus fiable."
        )

    return pd.DataFrame(rows)


# ── Dispatch ─────────────────────────────────────────────────────────────────

def parse_file(file_path_or_buffer, filename: str):
    """Détecte le format par l'extension et appelle le bon parseur."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        return parse_csv(file_path_or_buffer)
    elif ext in ("xlsx", "xls"):
        return parse_excel(file_path_or_buffer)
    elif ext == "pdf":
        return parse_pdf(file_path_or_buffer)
    else:
        raise ValueError(
            f"Format '.{ext}' non supporté. Formats acceptés : CSV, Excel (.xlsx), PDF."
        )
