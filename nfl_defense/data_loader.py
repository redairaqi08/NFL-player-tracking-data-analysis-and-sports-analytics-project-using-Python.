"""
Chargement et jointures des données.

Règles (garde-fous) :
    - Toutes les données viennent des 5 fichiers officiels. Rien d'inventé.
    - games.csv, plays.csv, players.csv, pffScoutingData.csv tiennent en mémoire.
    - Le tracking est LOURD (811 Mo) : on NE charge JAMAIS tout d'un coup.
      On lit un fichier (= un match) à la fois, et on filtre par playId.

Les chaînes "NA" présentes dans les fichiers sont converties en NaN au chargement.
"""

from __future__ import annotations

import functools
from pathlib import Path

import pandas as pd

from . import config

# "NA" est la sentinelle de valeur manquante dans ces fichiers.
_NA_VALUES = ["NA", "", "NaN", "nan", "None"]


# ---------------------------------------------------------------------------
# Fichiers "légers" : chargés en entier (et mis en cache).
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _cache_key(data_dir: str) -> str:
    return data_dir


def load_games(data_dir: Path | None = None) -> pd.DataFrame:
    """Charge games.csv : 1 ligne = 1 match (équipes, semaine, date)."""
    data_dir = config.get_data_dir(data_dir)
    return pd.read_csv(data_dir / config.GAMES_FILE, na_values=_NA_VALUES)


def load_plays(data_dir: Path | None = None) -> pd.DataFrame:
    """Charge plays.csv : 1 ligne = 1 action (le cœur de l'analyse)."""
    data_dir = config.get_data_dir(data_dir)
    return pd.read_csv(data_dir / config.PLAYS_FILE, na_values=_NA_VALUES)


def load_players(data_dir: Path | None = None) -> pd.DataFrame:
    """Charge players.csv : taille, poids, naissance, poste, nom."""
    data_dir = config.get_data_dir(data_dir)
    df = pd.read_csv(data_dir / config.PLAYERS_FILE, na_values=_NA_VALUES)
    df["heightInches"] = df["height"].map(_height_to_inches)
    df["ageYears"] = _age_from_birthdate(df["birthDate"])
    return df


def load_pff(data_dir: Path | None = None) -> pd.DataFrame:
    """Charge pffScoutingData.csv : 1 ligne = 1 joueur sur 1 action."""
    data_dir = config.get_data_dir(data_dir)
    df = pd.read_csv(data_dir / config.PFF_FILE, na_values=_NA_VALUES)
    # Les flags pff_sack / pff_hurry / pff_hit valent 1 ou NaN -> 0/1 propre.
    for col in ("pff_sack", "pff_hurry", "pff_hit"):
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    return df


# ---------------------------------------------------------------------------
# Helpers de conversion (players.csv)
# ---------------------------------------------------------------------------

def _height_to_inches(height: object) -> float:
    """'6-4' -> 76.0 pouces. Renvoie NaN si illisible."""
    if not isinstance(height, str) or "-" not in height:
        return float("nan")
    try:
        feet, inches = height.split("-")
        return int(feet) * 12 + int(inches)
    except (ValueError, TypeError):
        return float("nan")


def _age_from_birthdate(birth: pd.Series, ref_year: int = 2021) -> pd.Series:
    """Âge approximatif (année de référence - année de naissance)."""
    dt = pd.to_datetime(birth, errors="coerce")
    return (ref_year - dt.dt.year).astype("Float64")


# ---------------------------------------------------------------------------
# Tactique par action : résumé pff_role agrégé au niveau (gameId, playId).
# ---------------------------------------------------------------------------

def rusher_counts_per_play(pff: pd.DataFrame) -> pd.DataFrame:
    """Compte, par action, le nombre de pass rushers et les flags de pression.

    Retourne un DataFrame indexé par (gameId, playId) avec :
        nRushers  : nombre de joueurs en "Pass Rush"
        anySack / anyHurry / anyHit : 1 si au moins un sur l'action
    """
    rush = pff[pff["pff_role"] == config.ROLE_PASS_RUSH]
    grp = rush.groupby(["gameId", "playId"])
    out = grp.agg(
        nRushers=("nflId", "count"),
        anySack=("pff_sack", "max"),
        anyHurry=("pff_hurry", "max"),
        anyHit=("pff_hit", "max"),
    ).reset_index()
    out["rusherBucket"] = out["nRushers"].map(config.rusher_bucket)
    return out


def build_play_table(data_dir: Path | None = None) -> pd.DataFrame:
    """Table d'analyse principale : plays enrichi de la tactique de pression.

    = plays.csv  +  (nb de rushers, sacks/hurries/hits par action)  +  semaine/équipes.
    1 ligne = 1 action. C'est la base des analyses A, B, C et E.
    """
    plays = load_plays(data_dir)
    games = load_games(data_dir)
    pff = load_pff(data_dir)

    pressure = rusher_counts_per_play(pff)

    df = plays.merge(
        pressure, on=["gameId", "playId"], how="left"
    ).merge(
        games[["gameId", "week", "gameDate", "homeTeamAbbr", "visitorTeamAbbr"]],
        on="gameId", how="left",
    )

    # Libellé lisible du résultat de passe.
    df["passResultLabel"] = df["passResult"].map(config.PASS_RESULT_LABELS)
    # Flag sack au niveau action (depuis passResult, indépendant du pff).
    df["isSack"] = (df["passResult"] == "S").astype(int)
    df["isComplete"] = (df["passResult"] == "C").astype(int)
    df["isInt"] = (df["passResult"] == "IN").astype(int)
    return df


# ---------------------------------------------------------------------------
# Tracking : lecture par match, filtrage par action. On ne charge jamais tout.
# ---------------------------------------------------------------------------

def tracking_path(game_id: int, data_dir: Path | None = None) -> Path:
    data_dir = config.get_data_dir(data_dir)
    return data_dir / config.TRACKING_DIR / f"{config.TRACKING_PREFIX}{game_id}.csv"


def load_tracking_play(
    game_id: int,
    play_id: int,
    data_dir: Path | None = None,
) -> pd.DataFrame:
    """Charge le tracking d'UNE SEULE action.

    Lit le fichier du match par morceaux (chunks) et ne garde que les lignes
    de la playId demandée : empreinte mémoire minimale, conforme au garde-fou.
    """
    path = tracking_path(game_id, data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Fichier tracking introuvable : {path}")

    keep = []
    for chunk in pd.read_csv(path, na_values=_NA_VALUES, chunksize=200_000):
        sel = chunk[chunk["playId"] == play_id]
        if not sel.empty:
            keep.append(sel)
    if not keep:
        return pd.DataFrame()
    out = pd.concat(keep, ignore_index=True)
    return out.sort_values(["nflId", "frameId"]).reset_index(drop=True)


def iter_tracking_game(
    game_id: int,
    data_dir: Path | None = None,
    chunksize: int = 200_000,
):
    """Itère sur le tracking d'un match par chunks (générateur).

    Utile pour agréger (ex. vitesse de pointe) sans tout charger en mémoire.
    """
    path = tracking_path(game_id, data_dir)
    if not path.exists():
        raise FileNotFoundError(f"Fichier tracking introuvable : {path}")
    yield from pd.read_csv(path, na_values=_NA_VALUES, chunksize=chunksize)


def list_tracking_games(data_dir: Path | None = None) -> list[int]:
    """Liste les gameId pour lesquels un fichier de tracking existe."""
    data_dir = config.get_data_dir(data_dir)
    tdir = data_dir / config.TRACKING_DIR
    ids = []
    for p in sorted(tdir.glob(f"{config.TRACKING_PREFIX}*.csv")):
        stem = p.stem.replace(config.TRACKING_PREFIX, "")
        if stem.isdigit():
            ids.append(int(stem))
    return ids
