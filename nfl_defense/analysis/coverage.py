"""
Analyse B — Couverture.

Questions :
    - Man vs Zone : qui concède le moins de yards ?
    - Cover-0 à Cover-6 : résultat de chacune.
    - Croisement pression x couverture : la meilleure paire (matrice tactique).
"""

from __future__ import annotations

import pandas as pd


def man_vs_zone(plays: pd.DataFrame) -> pd.DataFrame:
    """Comparaison Man / Zone : yards concédés, sacks, taux de complétion."""
    df = plays.dropna(subset=["pff_passCoverageType"])
    out = (
        df.groupby("pff_passCoverageType")
        .agg(
            nActions=("playId", "count"),
            yardsConcedesMoyen=("playResult", "mean"),
            tauxComplete=("isComplete", "mean"),
            tauxSack=("isSack", "mean"),
            tauxInt=("isInt", "mean"),
        )
        .reset_index()
    )
    for c in ("tauxComplete", "tauxSack", "tauxInt"):
        out[c] = (out[c] * 100).round(1)
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    return out.sort_values("yardsConcedesMoyen").reset_index(drop=True)


def by_coverage_scheme(plays: pd.DataFrame) -> pd.DataFrame:
    """Résultat détaillé par schéma (Cover-0 ... Cover-6, 2-Man, Quarters...)."""
    df = plays.dropna(subset=["pff_passCoverage"])
    out = (
        df.groupby("pff_passCoverage")
        .agg(
            nActions=("playId", "count"),
            yardsConcedesMoyen=("playResult", "mean"),
            tauxComplete=("isComplete", "mean"),
            tauxInt=("isInt", "mean"),
        )
        .reset_index()
    )
    out["tauxComplete"] = (out["tauxComplete"] * 100).round(1)
    out["tauxInt"] = (out["tauxInt"] * 100).round(1)
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    return out.sort_values("yardsConcedesMoyen").reset_index(drop=True)


def tactical_matrix(plays: pd.DataFrame, value: str = "playResult") -> pd.DataFrame:
    """MATRICE TACTIQUE : pression (lignes) x couverture (colonnes).

    Réponse directe à la question du projet. La valeur agrégée par défaut est
    la moyenne des yards concédés (playResult). Remplacer `value` par "isSack"
    pour voir le taux de sack à la place.

    Retourne un tableau croisé (pivot) prêt pour une heatmap.
    """
    df = plays.dropna(subset=["rusherBucket", "pff_passCoverage", value])
    pivot = df.pivot_table(
        index="rusherBucket",
        columns="pff_passCoverage",
        values=value,
        aggfunc="mean",
    )
    return pivot.round(2)


def tactical_matrix_counts(plays: pd.DataFrame) -> pd.DataFrame:
    """Nombre d'actions par case de la matrice tactique (pour pondérer la lecture)."""
    df = plays.dropna(subset=["rusherBucket", "pff_passCoverage"])
    return df.pivot_table(
        index="rusherBucket",
        columns="pff_passCoverage",
        values="playId",
        aggfunc="count",
    )
