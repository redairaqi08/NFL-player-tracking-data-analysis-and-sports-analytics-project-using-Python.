"""
Analyse D — Déplacements (tracking).

Questions :
    - Vitesse de pointe des rushers.
    - Distance couverte par les joueurs de couverture.
    - Où se placent les défenseurs au snap, puis à l'arrivée de la passe.

Garde-fou mémoire : on travaille sur UNE action à la fois (tracking déjà filtré
par data_loader.load_tracking_play), ou par chunks pour les agrégats de match.
"""

from __future__ import annotations

import pandas as pd

from .. import config


def _defensive_players(play_tracking: pd.DataFrame, pff: pd.DataFrame,
                       game_id: int, play_id: int) -> pd.DataFrame:
    """Jointure tracking x pff pour ne garder que les joueurs défensifs de l'action,
    avec leur rôle (Pass Rush / Coverage)."""
    roles = pff[(pff["gameId"] == game_id) & (pff["playId"] == play_id)][
        ["nflId", "pff_role"]
    ]
    merged = play_tracking.merge(roles, on="nflId", how="inner")
    defensive = {config.ROLE_PASS_RUSH, config.ROLE_COVERAGE}
    return merged[merged["pff_role"].isin(defensive)]


def peak_speed_per_player(play_tracking: pd.DataFrame) -> pd.DataFrame:
    """Vitesse de pointe (s max) et distance totale (somme dis) par joueur de l'action."""
    if play_tracking.empty:
        return pd.DataFrame()
    return (
        play_tracking.groupby(["nflId", "team"])
        .agg(vitessePointe=("s", "max"),
             distanceTotale=("dis", "sum"),
             accelMax=("a", "max"))
        .reset_index()
        .sort_values("vitessePointe", ascending=False)
    )


def positions_at_event(play_tracking: pd.DataFrame, event: str) -> pd.DataFrame:
    """Positions (x, y) de tous les joueurs à un évènement donné.

    Évènements utiles : 'ball_snap', 'pass_forward', 'pass_arrived'.
    """
    if play_tracking.empty:
        return pd.DataFrame()
    return play_tracking[play_tracking["event"] == event][
        ["nflId", "team", "x", "y", "s", "dir", "o"]
    ].reset_index(drop=True)


def rusher_peak_speed_for_play(
    play_tracking: pd.DataFrame, pff: pd.DataFrame,
    game_id: int, play_id: int,
) -> pd.DataFrame:
    """Vitesse de pointe des seuls pass rushers d'une action (tracking x pff)."""
    def_players = _defensive_players(play_tracking, pff, game_id, play_id)
    rushers = def_players[def_players["pff_role"] == config.ROLE_PASS_RUSH]
    if rushers.empty:
        return pd.DataFrame()
    return (
        rushers.groupby("nflId")
        .agg(vitessePointe=("s", "max"), distanceTotale=("dis", "sum"))
        .reset_index()
        .sort_values("vitessePointe", ascending=False)
    )
