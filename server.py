# -*- coding: utf-8 -*-
"""
Budget Analyzer — Serveur Flask.
Lance avec :  python3 server.py
"""
import io
import json
import os
import tempfile
import webbrowser
from pathlib import Path
from threading import Timer

import pandas as pd
from flask import Flask, request, jsonify, send_from_directory, send_file

from parsers import parse_file
from rules import CATEGORIE_EXCLUE_DES_DEPENSES, classify_by_rules
from ollama_classify import classify_with_ai
from excel_export import exporter, COULEURS_CATEGORIES

app = Flask(__name__, static_folder="static", static_url_path="")


# ─── Routes statiques ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/health")
def health():
    """Vérifie si Ollama est joignable et qu'un modèle est disponible."""
    import requests as req
    result = {"ollama": False, "model": False, "model_name": None, "models": []}
    try:
        r = req.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            result["ollama"] = True
            models = r.json().get("models", [])
            result["models"] = [m["name"] for m in models]
            if models:
                result["model"] = True
                result["model_name"] = models[0]["name"]
    except Exception:
        pass
    return jsonify(result)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """Reçoit un ou plusieurs fichiers, renvoie les données catégorisées."""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    all_dfs = []
    errors = []

    for f in files:
        try:
            if f.filename.lower().endswith(".pdf"):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    f.save(tmp.name)
                    df = parse_file(tmp.name, f.filename)
                    os.unlink(tmp.name)
            else:
                df = parse_file(f.stream, f.filename)
            all_dfs.append(df)
        except Exception as e:
            errors.append({"file": f.filename, "error": str(e)})

    if not all_dfs:
        return jsonify({"error": "Aucun fichier exploitable", "details": errors}), 400

    df = pd.concat(all_dfs, ignore_index=True)

    # Catégoriser
    cache = {}
    categories = []
    for row in df.itertuples(index=False):
        lib = row.Libellé
        if lib in cache:
            categories.append(cache[lib])
        else:
            cat = classify_by_rules(lib)
            if cat is None:
                cat = classify_with_ai(lib, row.Montant)
            cache[lib] = cat
            categories.append(cat)

    df["Catégorie"] = categories

    # Calculs
    depenses = df[~df["Catégorie"].isin(CATEGORIE_EXCLUE_DES_DEPENSES)].copy()
    depenses["Dépense"] = depenses["Montant"].apply(lambda x: -x if x < 0 else 0)
    total_dep = float(depenses["Dépense"].sum())
    total_rev = float(df[df["Montant"] > 0]["Montant"].sum())

    # Synthèse par catégorie
    synthese = (
        depenses.groupby("Catégorie")["Dépense"].sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    synthese.columns = ["categorie", "total"]
    synthese = synthese[synthese["total"] > 0]
    total_all = synthese["total"].sum() or 1
    synthese["pct"] = (synthese["total"] / total_all * 100).round(1)
    synthese["color"] = synthese["categorie"].map(
        lambda c: f"#{COULEURS_CATEGORIES.get(c, '9CA3AF')}"
    )

    # Par mois
    df["Mois"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m")
    dep_mois = df[~df["Catégorie"].isin(CATEGORIE_EXCLUE_DES_DEPENSES)].copy()
    dep_mois["Dépense"] = dep_mois["Montant"].apply(lambda x: -x if x < 0 else 0)
    pivot = dep_mois.pivot_table(
        index="Mois", columns="Catégorie", values="Dépense", aggfunc="sum", fill_value=0
    ).sort_index()

    # Transactions groupées par catégorie
    groupes = {}
    poids = (
        df.assign(_abs=df["Montant"].where(df["Montant"] < 0, 0).abs())
        .groupby("Catégorie")["_abs"].sum()
        .sort_values(ascending=False)
    )
    for cat in poids.index:
        g = df[df["Catégorie"] == cat].sort_values("Date")
        groupes[cat] = {
            "total": float(g["Montant"].sum()),
            "count": len(g),
            "color": f"#{COULEURS_CATEGORIES.get(cat, '9CA3AF')}",
            "transactions": g[["Date", "Libellé", "Montant"]].to_dict(orient="records"),
        }

    return jsonify({
        "kpi": {
            "total_depenses": round(total_dep, 2),
            "total_revenus": round(total_rev, 2),
            "solde": round(total_rev - total_dep, 2),
            "nb_transactions": len(df),
        },
        "synthese": synthese.to_dict(orient="records"),
        "mois": {
            "labels": list(pivot.index),
            "datasets": [
                {
                    "label": col,
                    "data": [round(float(v), 2) for v in pivot[col]],
                    "color": f"#{COULEURS_CATEGORIES.get(col, '9CA3AF')}",
                }
                for col in pivot.columns
            ],
        },
        "groupes": groupes,
        "errors": errors,
    })


@app.route("/api/export", methods=["POST"])
def export_excel():
    """Reçoit les mêmes fichiers et renvoie le fichier Excel."""
    files = request.files.getlist("files")
    all_dfs = []
    for f in files:
        try:
            if f.filename.lower().endswith(".pdf"):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    f.save(tmp.name)
                    df = parse_file(tmp.name, f.filename)
                    os.unlink(tmp.name)
            else:
                df = parse_file(f.stream, f.filename)
            all_dfs.append(df)
        except Exception:
            continue

    if not all_dfs:
        return jsonify({"error": "Aucun fichier exploitable"}), 400

    df = pd.concat(all_dfs, ignore_index=True)

    cache = {}
    categories = []
    methodes = []
    for row in df.itertuples(index=False):
        lib = row.Libellé
        if lib in cache:
            cat, meth = cache[lib]
        else:
            cat = classify_by_rules(lib)
            if cat is not None:
                meth = "règle"
            else:
                cat = classify_with_ai(lib, row.Montant)
                meth = "IA locale"
            cache[lib] = (cat, meth)
        categories.append(cat)
        methodes.append(meth)

    df["Catégorie"] = categories
    df["Méthode"] = methodes
    df["Mois"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m")

    depenses = df[~df["Catégorie"].isin(CATEGORIE_EXCLUE_DES_DEPENSES)].copy()
    depenses["Dépense"] = depenses["Montant"].apply(lambda x: -x if x < 0 else 0)

    synthese = (
        depenses.groupby("Catégorie")["Dépense"].sum()
        .sort_values(ascending=False).reset_index()
    )
    synthese.columns = ["Catégorie", "Total dépensé"]
    synthese = synthese[synthese["Total dépensé"] > 0]

    pivot = depenses.pivot_table(
        index="Mois", columns="Catégorie", values="Dépense", aggfunc="sum", fill_value=0
    ).sort_index()

    total_dep = float(depenses["Dépense"].sum())
    total_rev = float(df[df["Montant"] > 0]["Montant"].sum())

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        exporter(tmp.name, df, synthese, pivot, total_dep, total_rev)
        return send_file(tmp.name, as_attachment=True, download_name="budget_analyzer.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/api/export-save", methods=["POST"])
def export_save():
    """Comme /api/export mais sauvegarde le fichier sur le Bureau et retourne le chemin.
    Utilisé quand pywebview bloque les téléchargements blob."""
    files_list = request.files.getlist("files")
    all_dfs = []
    for f in files_list:
        try:
            if f.filename.lower().endswith(".pdf"):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    f.save(tmp.name)
                    df = parse_file(tmp.name, f.filename)
                    os.unlink(tmp.name)
            else:
                df = parse_file(f.stream, f.filename)
            all_dfs.append(df)
        except Exception:
            continue

    if not all_dfs:
        return jsonify({"error": "Aucun fichier exploitable"}), 400

    df = pd.concat(all_dfs, ignore_index=True)

    cache = {}
    categories = []
    methodes = []
    for row in df.itertuples(index=False):
        lib = row.Libellé
        if lib in cache:
            cat, meth = cache[lib]
        else:
            cat = classify_by_rules(lib)
            if cat is not None:
                meth = "règle"
            else:
                cat = classify_with_ai(lib, row.Montant)
                meth = "IA locale"
            cache[lib] = (cat, meth)
        categories.append(cat)
        methodes.append(meth)

    df["Catégorie"] = categories
    df["Méthode"] = methodes
    df["Mois"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m")

    depenses = df[~df["Catégorie"].isin(CATEGORIE_EXCLUE_DES_DEPENSES)].copy()
    depenses["Dépense"] = depenses["Montant"].apply(lambda x: -x if x < 0 else 0)

    synthese = (
        depenses.groupby("Catégorie")["Dépense"].sum()
        .sort_values(ascending=False).reset_index()
    )
    synthese.columns = ["Catégorie", "Total dépensé"]
    synthese = synthese[synthese["Total dépensé"] > 0]

    pivot = depenses.pivot_table(
        index="Mois", columns="Catégorie", values="Dépense", aggfunc="sum", fill_value=0
    ).sort_index()

    total_dep = float(depenses["Dépense"].sum())
    total_rev = float(df[df["Montant"] > 0]["Montant"].sum())

    # Sauvegarde sur le Bureau
    desktop = os.path.expanduser("~/Desktop")
    output_path = os.path.join(desktop, "budget_analyzer.xlsx")
    # Si le fichier existe déjà, ajoute un numéro
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(desktop, f"budget_analyzer_{counter}.xlsx")
        counter += 1

    exporter(output_path, df, synthese, pivot, total_dep, total_rev)
    return jsonify({"path": output_path, "filename": os.path.basename(output_path)})


# ─── Main ─────────────────────────────────────────────────────────────────────

def start_server(port):
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    try:
        import webview

        # Lance Flask dans un thread séparé
        server_thread = Timer(0.5, start_server, args=[port])
        server_thread.daemon = True
        server_thread.start()

        # Fenêtre native
        webview.create_window(
            "Budget Analyzer",
            f"http://localhost:{port}",
            width=1100,
            height=750,
            min_size=(800, 500),
        )
        webview.start()

    except ImportError:
        # Fallback : ouvre dans le navigateur si pywebview n'est pas installé
        def open_browser():
            webbrowser.open(f"http://localhost:{port}")

        Timer(1.5, open_browser).start()
        print(f"\n  Budget Analyzer -> http://localhost:{port}\n")
        app.run(host="127.0.0.1", port=port, debug=False)
