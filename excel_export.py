# -*- coding: utf-8 -*-
"""
Mise en forme de l'export Excel : onglets séparés et clairs, couleurs
cohérentes par catégorie, en-têtes stylés, indicateurs clés, graphiques.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import PieChart, BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.utils import get_column_letter

# Une couleur par catégorie, réutilisée partout (tableaux + graphiques)
COULEURS_CATEGORIES = {
    "Alimentation": "4CAF50",
    "Logement": "2196F3",
    "Transport": "FF9800",
    "Santé": "E91E63",
    "Restaurants / Sorties": "9C27B0",
    "Loisirs / Shopping": "00BCD4",
    "Abonnements": "795548",
    "Impôts / Administration": "607D8B",
    "Épargne / Virements internes": "9E9E9E",
    "Revenus": "8BC34A",
    "Autres": "F44336",
}

GRIS_ANTHRACITE = "1F2933"
BLANC = "FFFFFF"
GRIS_CLAIR = "F3F4F6"
GRIS_BORDURE = "D1D5DB"
ROUGE_DEPENSE = "B91C1C"
VERT_REVENU = "15803D"

FONT_TITRE = Font(size=18, bold=True, color=GRIS_ANTHRACITE)
FONT_SOUS_TITRE = Font(size=11, italic=True, color="6B7280")
FONT_ENTETE = Font(bold=True, color=BLANC, size=11)
FONT_KPI_LABEL = Font(size=10, color="6B7280")

FILL_ENTETE = PatternFill("solid", fgColor=GRIS_ANTHRACITE)
FILL_ALT = PatternFill("solid", fgColor=GRIS_CLAIR)
BORDURE_BAS = Border(bottom=Side(style="thin", color=GRIS_BORDURE))

EURO = '#,##0.00 "€"'


def _couleur(categorie: str) -> str:
    return COULEURS_CATEGORIES.get(categorie, "9CA3AF")


def _style_entete(ws, row, col_debut, col_fin):
    for col in range(col_debut, col_fin + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = FONT_ENTETE
        cell.fill = FILL_ENTETE
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDURE_BAS
    ws.row_dimensions[row].height = 22


def _autosize(ws, min_width=10, max_width=42):
    for col_cells in ws.columns:
        values = [c.value for c in col_cells if c.value is not None]
        if not values:
            continue
        longueur = max(len(str(v)) for v in values)
        lettre = col_cells[0].column_letter
        ws.column_dimensions[lettre].width = min(max(longueur + 3, min_width), max_width)


def _titre(ws, texte, row=1, col=1, sous_titre=None):
    ws.cell(row=row, column=col, value=texte).font = FONT_TITRE
    if sous_titre:
        ws.cell(row=row + 1, column=col, value=sous_titre).font = FONT_SOUS_TITRE


def _kpi_card(ws, row, col, label, valeur, couleur_valeur=GRIS_ANTHRACITE, format_valeur=EURO):
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + 1)
    ws.merge_cells(start_row=row + 1, start_column=col, end_row=row + 1, end_column=col + 1)
    c_label = ws.cell(row=row, column=col, value=label)
    c_label.font = FONT_KPI_LABEL
    c_valeur = ws.cell(row=row + 1, column=col, value=valeur)
    c_valeur.font = Font(size=18, bold=True, color=couleur_valeur)
    if isinstance(valeur, (int, float)):
        c_valeur.number_format = format_valeur


def ecrire_transactions(ws, df):
    """Onglet détail : transactions regroupées par catégorie (groupes Excel
    repliables), chaque groupe précédé d'un bandeau coloré avec le total.
    Seules Date / Libellé / Montant sont affichées : la catégorie est déjà
    portée par le bandeau coloré, pas besoin de colonne en plus.
    """
    _titre(
        ws, "Transactions",
        sous_titre=f"{len(df)} opérations — regroupées par catégorie (clique sur les '-' à gauche pour replier un groupe)",
    )
    entete_row = 3
    colonnes = ["Date", "Libellé", "Montant"]
    for j, nom in enumerate(colonnes, start=1):
        ws.cell(row=entete_row, column=j, value=nom)
    _style_entete(ws, entete_row, 1, len(colonnes))

    # Ordre des catégories : celle qui pèse le plus en dépenses d'abord
    poids = (
        df.assign(_abs=df["Montant"].where(df["Montant"] < 0, 0).abs())
        .groupby("Catégorie")["_abs"].sum()
        .sort_values(ascending=False)
    )
    ordre_categories = list(poids.index)

    ws.sheet_properties.outlinePr.summaryBelow = False  # le bandeau reste visible, le détail se replie dessous

    i = entete_row + 1
    for categorie in ordre_categories:
        groupe = df[df["Catégorie"] == categorie].sort_values("Date")
        total_groupe = float(groupe["Montant"].sum())
        couleur = _couleur(categorie)

        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=len(colonnes))
        texte = f"{categorie}   —   {len(groupe)} opération(s)   —   {total_groupe:,.2f} €".replace(",", " ")
        c_bandeau = ws.cell(row=i, column=1, value=texte)
        c_bandeau.fill = PatternFill("solid", fgColor=couleur)
        c_bandeau.font = Font(color=BLANC, bold=True, size=11)
        c_bandeau.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[i].height = 20
        i += 1

        for j, row in enumerate(groupe.itertuples(index=False)):
            ws.cell(row=i, column=1, value=str(row.Date))
            ws.cell(row=i, column=2, value=row.Libellé)
            c_montant = ws.cell(row=i, column=3, value=float(row.Montant))
            c_montant.number_format = EURO
            c_montant.font = Font(color=ROUGE_DEPENSE if row.Montant < 0 else VERT_REVENU)
            if j % 2 == 1:
                for col in (1, 2, 3):
                    ws.cell(row=i, column=col).fill = FILL_ALT
            ws.row_dimensions[i].outlineLevel = 1
            i += 1

    ws.freeze_panes = f"A{entete_row + 1}"
    _autosize(ws)
    ws.column_dimensions["B"].width = 42


def ecrire_synthese_categorie(ws, synthese_df, total_depenses, total_revenus, nb_transactions):
    """Onglet synthèse : indicateurs clés + tableau par catégorie + camembert."""
    _titre(ws, "Synthèse par catégorie", sous_titre="Vue d'ensemble de tes dépenses")

    _kpi_card(ws, 4, 1, "Total dépensé", total_depenses, couleur_valeur=ROUGE_DEPENSE)
    _kpi_card(ws, 4, 3, "Total revenus", total_revenus, couleur_valeur=VERT_REVENU)
    solde = total_revenus - total_depenses
    _kpi_card(ws, 4, 5, "Solde", solde, couleur_valeur=VERT_REVENU if solde >= 0 else ROUGE_DEPENSE)
    _kpi_card(ws, 4, 7, "Transactions", nb_transactions, format_valeur="0")

    entete_row = 8
    ws.cell(row=entete_row, column=1, value="Catégorie")
    ws.cell(row=entete_row, column=2, value="Total dépensé")
    ws.cell(row=entete_row, column=3, value="% du total")
    _style_entete(ws, entete_row, 1, 3)

    total = synthese_df["Total dépensé"].sum() or 1
    for i, (_, r) in enumerate(synthese_df.iterrows(), start=entete_row + 1):
        c_nom = ws.cell(row=i, column=1, value=r["Catégorie"])
        c_nom.fill = PatternFill("solid", fgColor=_couleur(r["Catégorie"]))
        c_nom.font = Font(color=BLANC, bold=True)
        c_montant = ws.cell(row=i, column=2, value=float(r["Total dépensé"]))
        c_montant.number_format = EURO
        c_pct = ws.cell(row=i, column=3, value=float(r["Total dépensé"]) / total)
        c_pct.number_format = "0.0%"

    derniere_ligne = entete_row + len(synthese_df)

    chart = PieChart()
    chart.title = "Répartition des dépenses"
    data = Reference(ws, min_col=2, min_row=entete_row, max_row=derniere_ligne)
    labels = Reference(ws, min_col=1, min_row=entete_row + 1, max_row=derniere_ligne)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(labels)
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showPercent = True
    chart.height = 10
    chart.width = 16

    serie = chart.series[0]
    for idx, (_, r) in enumerate(synthese_df.iterrows()):
        pt = DataPoint(idx=idx)
        pt.graphicalProperties = GraphicalProperties(solidFill=_couleur(r["Catégorie"]))
        serie.data_points.append(pt)

    ws.add_chart(chart, "E8")
    _autosize(ws)


def ecrire_evolution_mensuelle(ws, pivot_mois):
    """Onglet évolution : un tableau mois x catégorie + histogramme empilé."""
    _titre(ws, "Évolution mensuelle", sous_titre="Dépenses par mois et par catégorie")
    entete_row = 4
    colonnes = ["Mois"] + list(pivot_mois.columns)
    for j, nom in enumerate(colonnes, start=1):
        ws.cell(row=entete_row, column=j, value=nom)
    _style_entete(ws, entete_row, 1, len(colonnes))

    for i, (mois, r) in enumerate(pivot_mois.iterrows(), start=entete_row + 1):
        ws.cell(row=i, column=1, value=str(mois))
        for j, cat in enumerate(pivot_mois.columns, start=2):
            c = ws.cell(row=i, column=j, value=float(r[cat]))
            c.number_format = EURO

    derniere_ligne = entete_row + len(pivot_mois)

    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.overlap = 100
    chart.title = "Dépenses par mois et catégorie"
    chart.y_axis.title = "Montant (€)"
    data = Reference(ws, min_col=2, max_col=len(colonnes), min_row=entete_row, max_row=derniere_ligne)
    cats = Reference(ws, min_col=1, min_row=entete_row + 1, max_row=derniere_ligne)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 11
    chart.width = 22

    for serie, cat in zip(chart.series, pivot_mois.columns):
        serie.graphicProperties = GraphicalProperties(solidFill=_couleur(cat))

    ws.add_chart(chart, f"A{derniere_ligne + 3}")
    _autosize(ws)


def exporter(output_path, df_export, synthese_df, pivot_mois, total_depenses, total_revenus):
    wb = Workbook()
    ws_trans = wb.active
    ws_trans.title = "Transactions"
    ecrire_transactions(ws_trans, df_export)

    ws_synth = wb.create_sheet("Par catégorie")
    ecrire_synthese_categorie(ws_synth, synthese_df, total_depenses, total_revenus, len(df_export))

    ws_mois = wb.create_sheet("Par mois")
    ecrire_evolution_mensuelle(ws_mois, pivot_mois)

    wb.save(output_path)
