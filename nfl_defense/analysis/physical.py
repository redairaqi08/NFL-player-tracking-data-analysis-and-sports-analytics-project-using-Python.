"""
Analyse E — Physique (À MANIER AVEC PRUDENCE).

Question : poids / taille des rushers vs sacks ?

AVERTISSEMENT MÉTHODOLOGIQUE
----------------------------
Une corrélation N'EST PAS une cause. Un joueur lourd qui réussit des sacks ne
prouve PAS que le poids "fait" le sack. On DÉCRIT un lien statistique, on ne
l'EXPLIQUE pas. Toute fonction de ce module renvoie, à côté du résultat, ce
rappel pour qu'il figure dans la conclusion.
"""

from __future__ import annotations

import pandas as pd

from .. import config

DISCLAIMER = (
    "Rappel : corrélation != causalité. Ce lien est descriptif ; il ne prouve "
    "pas que le physique cause les sacks (facteurs confondants : poste, scheme, "
    "adversaire, volume de snaps...)."
)


def sacks_by_physique(pff: pd.DataFrame, players: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Agrège sacks/hurries par joueur rusher, joints à taille/poids.

    Retourne (DataFrame, disclaimer). Le disclaimer DOIT être affiché avec le résultat.
    """
    rush = pff[pff["pff_role"] == config.ROLE_PASS_RUSH]
    per_player = (
        rush.groupby("nflId")
        .agg(snapsRush=("playId", "count"),
             sacks=("pff_sack", "sum"),
             hurries=("pff_hurry", "sum"),
             hits=("pff_hit", "sum"))
        .reset_index()
    )
    merged = per_player.merge(
        players[["nflId", "displayName", "officialPosition",
                 "weight", "heightInches", "ageYears"]],
        on="nflId", how="left",
    )
    # Taux pour neutraliser en partie le volume de snaps.
    merged["sacksPar100Snaps"] = (merged["sacks"] / merged["snapsRush"] * 100).round(2)
    return merged.sort_values("sacks", ascending=False).reset_index(drop=True), DISCLAIMER


def weight_sack_correlation(pff: pd.DataFrame, players: pd.DataFrame,
                            min_snaps: int = 30) -> tuple[float, str]:
    """Coefficient de corrélation (Pearson) poids <-> sacks par 100 snaps.

    Filtré sur les joueurs ayant au moins `min_snaps` snaps de rush.
    Retourne (r, disclaimer).
    """
    table, _ = sacks_by_physique(pff, players)
    table = table[table["snapsRush"] >= min_snaps].dropna(
        subset=["weight", "sacksPar100Snaps"]
    )
    if len(table) < 3:
        return float("nan"), DISCLAIMER
    r = table["weight"].corr(table["sacksPar100Snaps"])
    return round(float(r), 3), DISCLAIMER
