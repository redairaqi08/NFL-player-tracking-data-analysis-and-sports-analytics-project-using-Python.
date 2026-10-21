"""
Animation d'une action — les joueurs bougent image par image sur le terrain.

Deux usages :
    - draw_frame()   : dessine UNE image (frame) donnée -> parfait pour un slider
                       Streamlit (on avance frame par frame, très réactif).
    - animate_play() : construit une animation matplotlib (GIF/MP4) pour le
                       pipeline CLI ou l'export.

Code couleur :
    - rouge   = pass rushers (défenseurs qui foncent sur le QB)
    - orange  = autres défenseurs (couverture)
    - bleu    = attaque
    - marron  = ballon
Chaque joueur montre aussi un petit vecteur = sa direction x vitesse.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .. import config
from .field import draw_field

# Couleurs par rôle défensif / camp.
_COLOR_RUSH = "#d50000"       # rouge vif : pass rush
_COLOR_COVER = "#ff8f00"      # orange : couverture
_COLOR_OFFENSE = "#1565c0"    # bleu : attaque
_COLOR_BALL = "#4e342e"       # marron : ballon


def _role_color(team: str, role: str | None, offense_team: str | None) -> str:
    if team == "football":
        return _COLOR_BALL
    if team == offense_team:
        return _COLOR_OFFENSE
    # Défense : distinguer rush / couverture si le rôle est connu.
    if role == config.ROLE_PASS_RUSH:
        return _COLOR_RUSH
    return _COLOR_COVER


def _attach_roles(play_tracking: pd.DataFrame, pff, game_id, play_id) -> pd.DataFrame:
    """Ajoute la colonne pff_role au tracking (pour colorer par rôle)."""
    if pff is None or game_id is None or play_id is None:
        play_tracking = play_tracking.copy()
        play_tracking["pff_role"] = None
        return play_tracking
    roles = pff[(pff["gameId"] == game_id) & (pff["playId"] == play_id)][
        ["nflId", "pff_role"]
    ]
    return play_tracking.merge(roles, on="nflId", how="left")


def draw_frame(
    play_tracking: pd.DataFrame,
    frame_id: int,
    ax: plt.Axes | None = None,
    offense_team: str | None = None,
    pff=None,
    game_id: int | None = None,
    play_id: int | None = None,
    show_trails: bool = True,
    event_label: str | None = None,
) -> plt.Axes:
    """Dessine l'image (frame) `frame_id` de l'action sur un terrain.

    show_trails : si vrai, trace la trainée parcourue jusqu'à cette frame.
    event_label : évènement à afficher en titre (ball_snap, pass_forward...).
    """
    ax = draw_field(ax)
    if play_tracking.empty:
        ax.set_title("Aucune donnée de tracking")
        return ax

    data = _attach_roles(play_tracking, pff, game_id, play_id)

    # Trainées (positions jusqu'à la frame courante).
    if show_trails:
        past = data[data["frameId"] <= frame_id]
        for (nfl_id, team), grp in past.groupby(["nflId", "team"]):
            if team == "football":
                continue
            role = grp["pff_role"].iloc[0] if "pff_role" in grp else None
            color = _role_color(team, role, offense_team)
            ax.plot(grp["x"], grp["y"], color=color, lw=0.8, alpha=0.35, zorder=4)

    # Positions à la frame courante.
    cur = data[data["frameId"] == frame_id]
    for _, p in cur.iterrows():
        color = _role_color(p["team"], p.get("pff_role"), offense_team)
        if p["team"] == "football":
            ax.scatter(p["x"], p["y"], s=60, color=color, marker="D",
                       zorder=9, edgecolor="white")
            continue
        ax.scatter(p["x"], p["y"], s=130, color=color, zorder=8,
                   edgecolor="white", linewidth=1.2)
        # Vecteur direction x vitesse (où va le joueur, à quelle vitesse).
        speed = p.get("s", 0) or 0
        ang = np.deg2rad(p.get("dir", 0) or 0)
        ax.arrow(p["x"], p["y"], speed * np.sin(ang) * 0.6, speed * np.cos(ang) * 0.6,
                 head_width=0.6, head_length=0.6, fc=color, ec=color,
                 alpha=0.8, zorder=7)
        # Numéro de maillot.
        if pd.notna(p.get("jerseyNumber")):
            ax.text(p["x"], p["y"], f"{int(p['jerseyNumber'])}",
                    color="white", fontsize=6, ha="center", va="center", zorder=10)

    title = f"Image {frame_id}"
    if event_label and event_label != "None":
        title += f"  —  {event_label}"
    ax.set_title(title)
    _legend(ax)
    return ax


def _legend(ax: plt.Axes) -> None:
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=_COLOR_RUSH,
               markersize=9, label="Pass rush"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=_COLOR_COVER,
               markersize=9, label="Couverture"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=_COLOR_OFFENSE,
               markersize=9, label="Attaque"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor=_COLOR_BALL,
               markersize=8, label="Ballon"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=7, framealpha=0.8)


def animate_play(
    play_tracking: pd.DataFrame,
    offense_team: str | None = None,
    pff=None,
    game_id: int | None = None,
    play_id: int | None = None,
    interval_ms: int = 100,
):
    """Construit une animation matplotlib de toute l'action (pour GIF/MP4).

    Retourne l'objet FuncAnimation. Sauvegarde ensuite via anim.save(...).
    """
    from matplotlib.animation import FuncAnimation

    frames = sorted(play_tracking["frameId"].unique())
    events = {}
    if "event" in play_tracking.columns:
        evt = play_tracking[play_tracking["event"].notna()]
        events = dict(zip(evt["frameId"], evt["event"]))

    fig, ax = plt.subplots(figsize=(13, 6))

    def update(frame_id):
        ax.clear()
        draw_frame(play_tracking, frame_id, ax=ax, offense_team=offense_team,
                   pff=pff, game_id=game_id, play_id=play_id,
                   event_label=events.get(frame_id))

    anim = FuncAnimation(fig, update, frames=frames, interval=interval_ms, repeat=True)
    return anim
