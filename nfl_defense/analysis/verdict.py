"""
Verdict par action : la défense a-t-elle BIEN ou MAL joué, et pourquoi ?

On combine les trois axes du projet pour UNE action :
    - Tactique    : pression (nb de rushers) + couverture choisie.
    - Performance : résultat (sack / incomplète / complétée / interception),
                    yards concédés, pression générée (hurry / hit).
    - Déplacements : vitesse de pointe des rushers, distance de couverture.

Sortie = un dictionnaire lisible (note sur 100, étiquette, raisons, stats clés)
que le dashboard affiche tel quel. Tout est DESCRIPTIF et fondé sur les données
de l'action ; aucune donnée inventée.
"""

from __future__ import annotations

import pandas as pd

from .. import config


# Barème : du point de vue de la DÉFENSE (elle veut peu de yards, des sacks,
# de la pression, des passes incomplètes / interceptions).
def _result_component(pass_result: str | None, yards: float | None) -> tuple[float, str]:
    """Composante 'résultat de l'action' (0 à 55 points) + explication."""
    if pass_result == "S":  # sack
        return 55.0, "Sack réussi : le QB est plaqué, aucune progression concédée."
    if pass_result == "IN":  # interception
        return 55.0, "Interception : la défense récupère le ballon."
    if pass_result == "I":  # passe incomplète
        return 45.0, "Passe forcée à l'échec : aucun yard concédé sur l'action."
    # Passe complétée ou scramble : on note selon les yards concédés.
    if yards is None:
        return 25.0, "Résultat neutre (yards inconnus)."
    if yards <= 0:
        return 48.0, f"Attaque stoppée net ({yards:.0f} yard) malgré la réception."
    if yards <= 4:
        return 38.0, f"Gain limité à {yards:.0f} yards : défense plutôt solide."
    if yards <= 9:
        return 25.0, f"{yards:.0f} yards concédés : gain modéré."
    if yards <= 19:
        return 12.0, f"{yards:.0f} yards concédés : l'attaque gagne du terrain."
    return 2.0, f"{yards:.0f} yards concédés : grosse action pour l'attaque."


def _pressure_component(any_sack, any_hurry, any_hit, n_rushers) -> tuple[float, str]:
    """Composante 'pression sur le QB' (0 à 30 points) + explication."""
    score = 0.0
    bits = []
    if any_sack:
        score += 30
        bits.append("sack provoqué")
    elif any_hit:
        score += 20
        bits.append("QB touché (hit)")
    elif any_hurry:
        score += 14
        bits.append("QB bousculé (hurry)")
    else:
        bits.append("QB non inquiété")
    if n_rushers and n_rushers >= 5:
        score += 3
        bits.append(f"blitz à {int(n_rushers)} rushers")
    elif n_rushers:
        bits.append(f"{int(n_rushers)} rushers")
    return min(score, 30.0), ", ".join(bits)


def _speed_component(peak_rusher_speed: float | None) -> tuple[float, str]:
    """Composante 'explosivité du rush' (0 à 15 points) + explication.

    Fondée sur la vitesse de pointe (yards/s) du rusher le plus rapide.
    """
    if peak_rusher_speed is None or pd.isna(peak_rusher_speed):
        return 7.0, "Vitesse de rush non disponible."
    if peak_rusher_speed >= 7.5:
        return 15.0, f"Rush très explosif (pointe {peak_rusher_speed:.1f} yd/s)."
    if peak_rusher_speed >= 6.0:
        return 11.0, f"Rush rapide (pointe {peak_rusher_speed:.1f} yd/s)."
    if peak_rusher_speed >= 4.5:
        return 7.0, f"Rush de vitesse moyenne (pointe {peak_rusher_speed:.1f} yd/s)."
    return 3.0, f"Rush peu explosif (pointe {peak_rusher_speed:.1f} yd/s)."


def _label(score: float) -> tuple[str, str]:
    """Étiquette + emoji selon la note globale (0-100), du point de vue défense."""
    if score >= 80:
        return "Excellente défense", "🟢"
    if score >= 60:
        return "Bonne défense", "🟩"
    if score >= 40:
        return "Défense moyenne", "🟡"
    if score >= 20:
        return "Défense en difficulté", "🟠"
    return "Mauvaise défense", "🔴"


def play_verdict(
    play_row: pd.Series,
    play_tracking: pd.DataFrame | None = None,
    pff: pd.DataFrame | None = None,
) -> dict:
    """Construit le verdict complet d'une action.

    play_row       : la ligne de la table d'actions (build_play_table) pour cette action.
    play_tracking  : tracking filtré de l'action (optionnel, pour la vitesse de rush).
    pff            : table pff complète (optionnel, pour isoler les rushers).

    Retourne un dict : {score, note_sur_100, label, emoji, raisons[], stats{}}.
    """
    pass_result = play_row.get("passResult")
    yards = play_row.get("playResult")
    n_rushers = play_row.get("nRushers")

    # Vitesse de pointe du rusher le plus rapide (si tracking + pff fournis).
    peak_rusher_speed = None
    if (play_tracking is not None and not play_tracking.empty
            and pff is not None):
        from . import movement
        rushers = movement.rusher_peak_speed_for_play(
            play_tracking, pff,
            int(play_row["gameId"]), int(play_row["playId"]),
        )
        if not rushers.empty:
            peak_rusher_speed = float(rushers["vitessePointe"].max())

    # Trois composantes.
    s_res, why_res = _result_component(pass_result, yards)
    s_press, why_press = _pressure_component(
        play_row.get("anySack"), play_row.get("anyHurry"),
        play_row.get("anyHit"), n_rushers,
    )
    s_speed, why_speed = _speed_component(peak_rusher_speed)

    score = round(s_res + s_press + s_speed, 1)
    label, emoji = _label(score)

    return {
        "note_sur_100": score,
        "label": label,
        "emoji": emoji,
        "raisons": [why_res, why_press, why_speed],
        "stats": {
            "Résultat": config.PASS_RESULT_LABELS.get(pass_result, pass_result),
            "Yards concédés": yards,
            "Rushers": int(n_rushers) if pd.notna(n_rushers) else None,
            "Couverture": play_row.get("pff_passCoverage"),
            "Type couverture": play_row.get("pff_passCoverageType"),
            "Défenseurs dans la box": play_row.get("defendersInBox"),
            "Vitesse pointe rusher (yd/s)": (
                round(peak_rusher_speed, 2) if peak_rusher_speed else None),
        },
    }
