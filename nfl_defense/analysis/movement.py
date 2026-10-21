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


def player_stats_for_play(
    play_tracking: pd.DataFrame,
    pff: pd.DataFrame | None = None,
    players: pd.DataFrame | None = None,
    game_id: int | None = None,
    play_id: int | None = None,
) -> pd.DataFrame:
    """Tableau des DONNÉES CLÉS par joueur sur une action.

    Colonnes : joueur, équipe, rôle (si pff), vitesse de pointe, vitesse moyenne,
    accélération max, distance totale parcourue. Trié par vitesse de pointe.

    Si `players` est fourni, ajoute le nom et le poste officiel.
    """
    if play_tracking.empty:
        return pd.DataFrame()

    play = play_tracking[play_tracking["team"] != "football"]
    stats = (
        play.groupby(["nflId", "team"])
        .agg(
            vitessePointe=("s", "max"),
            vitesseMoyenne=("s", "mean"),
            accelMax=("a", "max"),
            distanceTotale=("dis", "sum"),
        )
        .reset_index()
    )

    # Rôle (Pass Rush / Coverage / ...) depuis pff.
    if pff is not None and game_id is not None and play_id is not None:
        roles = pff[(pff["gameId"] == game_id) & (pff["playId"] == play_id)][
            ["nflId", "pff_role", "pff_positionLinedUp"]
        ]
        stats = stats.merge(roles, on="nflId", how="left")

    # Nom + poste depuis players.
    if players is not None:
        stats = stats.merge(
            players[["nflId", "displayName", "officialPosition"]],
            on="nflId", how="left",
        )

    for col in ("vitessePointe", "vitesseMoyenne", "accelMax", "distanceTotale"):
        stats[col] = stats[col].round(2)
    return stats.sort_values("vitessePointe", ascending=False).reset_index(drop=True)


def frame_events(play_tracking: pd.DataFrame) -> dict:
    """Associe les évènements clés (ball_snap, pass_forward, pass_arrived...) au frameId.

    Pratique pour marquer les moments importants sur l'animation / le slider.
    """
    if play_tracking.empty or "event" not in play_tracking.columns:
        return {}
    evt = play_tracking[
        play_tracking["event"].notna() & (play_tracking["event"] != "None")
    ][["frameId", "event"]].drop_duplicates()
    return dict(zip(evt["frameId"], evt["event"]))
