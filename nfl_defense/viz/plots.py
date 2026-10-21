"""
Visualisations du projet.

    - tactical_matrix_heatmap : MATRICE TACTIQUE (pression x couverture).
    - context_bars            : barres par contexte (down & distance...).
    - physique_scatter        : nuage poids/taille vs sacks (avec disclaimer).
    - play_trajectories       : trajectoires des joueurs d'une action (tracking).
    - play_heatmap            : carte thermique des positions défensives (tracking).

Toutes les fonctions acceptent un `ax` optionnel et renvoient la figure ou l'axe,
pour pouvoir être réutilisées dans le dashboard Streamlit.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from .. import config
from .field import draw_field


def tactical_matrix_heatmap(matrix, counts=None, ax=None, title=None):
    """Heatmap de la matrice tactique. Couleur = yards concédés (plus clair = mieux)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 4.5))
    annot = matrix.round(1)
    sns.heatmap(matrix, annot=annot, fmt=".1f", cmap="RdYlGn_r",
                linewidths=0.5, ax=ax, cbar_kws={"label": "Yards concédés (moy.)"})
    ax.set_title(title or "Matrice tactique — pression x couverture\n"
                 "(vert = la défense concède peu, rouge = concède beaucoup)")
    ax.set_xlabel("Couverture")
    ax.set_ylabel("Pression (nb de rushers)")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    return ax


def context_bars(df, x, y, ax=None, title=None, ylabel=None):
    """Barres génériques par contexte (ex. yards concédés par bucket de rushers)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=df, x=x, y=y, ax=ax, color="#1565c0")
    ax.set_title(title or f"{y} par {x}")
    ax.set_ylabel(ylabel or y)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.1f}",
                    (p.get_x() + p.get_width() / 2, p.get_height()),
                    ha="center", va="bottom", fontsize=9)
    return ax


def physique_scatter(df, x="weight", y="sacksPar100Snaps", ax=None,
                     disclaimer=None):
    """Nuage physique vs sacks. Le disclaimer corrélation!=causalité est affiché."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 6))
    sns.scatterplot(data=df, x=x, y=y, size="snapsRush",
                    sizes=(20, 300), alpha=0.6, ax=ax, legend="brief")
    ax.set_title("Physique vs sacks (lien DESCRIPTIF, pas causal)")
    ax.set_xlabel("Poids (livres)" if x == "weight" else x)
    ax.set_ylabel("Sacks pour 100 snaps de rush")
    msg = disclaimer or "Rappel : corrélation != causalité."
    ax.text(0.5, -0.18, msg, transform=ax.transAxes, ha="center",
            fontsize=8, style="italic", color="#b71c1c", wrap=True)
    return ax


def play_trajectories(play_tracking, ax=None, offense_team=None, title=None):
    """Trajectoires de tous les joueurs d'une action, sur un terrain.

    offense_team : abréviation de l'équipe en attaque (colorée différemment).
    """
    ax = draw_field(ax)
    if play_tracking.empty:
        ax.set_title("Aucune donnée de tracking pour cette action")
        return ax
    for (nfl_id, team), grp in play_tracking.groupby(["nflId", "team"]):
        grp = grp.sort_values("frameId")
        if team == "football":
            ax.plot(grp["x"], grp["y"], color="#6d4c41", lw=2, zorder=6)
            continue
        color = "#ffb300" if team == offense_team else "#e53935"
        ax.plot(grp["x"], grp["y"], color=color, lw=1.4, alpha=0.9, zorder=5)
        ax.scatter(grp["x"].iloc[0], grp["y"].iloc[0], color=color,
                   s=25, zorder=7, edgecolor="white")  # position au snap
    ax.set_title(title or "Trajectoires des joueurs (jaune = attaque, rouge = défense)")
    return ax


def play_heatmap(play_tracking, ax=None, bins=40, title=None):
    """Carte thermique de densité des positions (toutes frames) sur une action."""
    ax = draw_field(ax)
    if play_tracking.empty:
        ax.set_title("Aucune donnée de tracking pour cette action")
        return ax
    players = play_tracking[play_tracking["team"] != "football"]
    ax.hist2d(players["x"], players["y"], bins=bins,
              range=[[0, config.FIELD_LENGTH], [0, config.FIELD_WIDTH]],
              cmap="hot", alpha=0.6, zorder=4)
    ax.set_title(title or "Carte thermique des positions (densité joueurs)")
    return ax
