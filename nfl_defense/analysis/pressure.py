"""
Analyse A — Pression.

Questions :
    - Combien de rushers (3/4/5/6+) -> taux de sack, de hurry, yards concédés ?
    - Envoyer plus de monde paie-t-il ?
    - Effet du down & distance.

Entrée : la table d'actions construite par data_loader.build_play_table().
"""

from __future__ import annotations

import pandas as pd


def pressure_summary(plays: pd.DataFrame) -> pd.DataFrame:
    """Résumé par bucket de rushers : sacks, hurries, yards concédés moyens."""
    df = plays.dropna(subset=["rusherBucket"])
    out = (
        df.groupby("rusherBucket")
        .agg(
            nActions=("playId", "count"),
            tauxSack=("isSack", "mean"),
            tauxHurry=("anyHurry", "mean"),
            tauxComplete=("isComplete", "mean"),
            yardsConcedesMoyen=("playResult", "mean"),
        )
        .reset_index()
        .sort_values("rusherBucket")
    )
    out["tauxSack"] = (out["tauxSack"] * 100).round(1)
    out["tauxHurry"] = (out["tauxHurry"] * 100).round(1)
    out["tauxComplete"] = (out["tauxComplete"] * 100).round(1)
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    return out


def pressure_by_down(plays: pd.DataFrame) -> pd.DataFrame:
    """Taux de sack par (down, bucket de rushers)."""
    df = plays.dropna(subset=["rusherBucket", "down"])
    out = (
        df.groupby(["down", "rusherBucket"])
        .agg(
            nActions=("playId", "count"),
            tauxSack=("isSack", "mean"),
            yardsConcedesMoyen=("playResult", "mean"),
        )
        .reset_index()
    )
    out["tauxSack"] = (out["tauxSack"] * 100).round(1)
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    return out


def best_defenses_pressure(plays: pd.DataFrame, min_actions: int = 50) -> pd.DataFrame:
    """Classement des défenses par yards concédés (toutes pressions confondues).

    min_actions : seuil de volume pour éviter les classements sur trop peu d'actions.
    """
    df = plays.dropna(subset=["defensiveTeam", "playResult"])
    out = (
        df.groupby("defensiveTeam")
        .agg(
            nActions=("playId", "count"),
            yardsConcedesMoyen=("playResult", "mean"),
            tauxSack=("isSack", "mean"),
            tauxHurry=("anyHurry", "mean"),
        )
        .reset_index()
    )
    out = out[out["nActions"] >= min_actions]
    out["yardsConcedesMoyen"] = out["yardsConcedesMoyen"].round(2)
    out["tauxSack"] = (out["tauxSack"] * 100).round(1)
    out["tauxHurry"] = (out["tauxHurry"] * 100).round(1)
    return out.sort_values("yardsConcedesMoyen").reset_index(drop=True)
