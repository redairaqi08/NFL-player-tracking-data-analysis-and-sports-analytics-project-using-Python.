"""
Analyse C — Contexte.

Questions :
    - Quelle défense sur 3e down & long ?
    - Défenseurs dans la box vs yards concédés.
    - Formation de l'attaque vs réponse de la défense.
"""

from __future__ import annotations

import pandas as pd


def third_and_long(plays: pd.DataFrame, min_yards: int = 7) -> pd.DataFrame:
    """Performance des défenses sur 3e down & long (yardsToGo >= min_yards)."""
    df = plays[(plays["down"] == 3) & (plays["yardsToGo"] >= min_yards)]
    df = df.dropna(subset=["pff_passCoverage"])
    out = (
        df.groupby("pff_passCoverage")
        .agg(
            nActions=("playId", "count"),
            yardsConcedesMoyen=("playResult", "mean"),
            tauxStop=("playResult", lambda s: (s < 7).mean()),  # < first down
        )
        .reset_index()
    )
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    out["tauxStop"] = (out["tauxStop"] * 100).round(1)
    return out.sort_values("yardsConcedesMoyen").reset_index(drop=True)


def box_vs_yards(plays: pd.DataFrame) -> pd.DataFrame:
    """Nombre de défenseurs dans la box vs yards concédés."""
    df = plays.dropna(subset=["defendersInBox", "playResult"])
    out = (
        df.groupby("defendersInBox")
        .agg(
            nActions=("playId", "count"),
            yardsConcedesMoyen=("playResult", "mean"),
            tauxSack=("isSack", "mean"),
        )
        .reset_index()
        .sort_values("defendersInBox")
    )
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    out["tauxSack"] = (out["tauxSack"] * 100).round(1)
    return out


def offense_formation_vs_defense(plays: pd.DataFrame) -> pd.DataFrame:
    """Formation offensive vs couverture choisie et résultat moyen."""
    df = plays.dropna(subset=["offenseFormation", "pff_passCoverageType"])
    return df.pivot_table(
        index="offenseFormation",
        columns="pff_passCoverageType",
        values="playResult",
        aggfunc="mean",
    ).round(2)
