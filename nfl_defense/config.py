"""
Configuration centrale : chemins des données et constantes du terrain.

Dossier de données — surchargeable (par ordre de priorité) :
    1. argument --data-dir en ligne de commande (voir main.py) ;
    2. variable d'environnement NFL_DATA_DIR ;
    3. valeur par défaut ci-dessous (dépôt cloné à côté du projet).

Données : Big Data Bowl — dépôt
github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data
Les CSV sont dans le sous-dossier `data/`.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Dossier des données ------------------------------------------------------

# Par défaut : on suppose que le dépôt de données est cloné en voisin
# sous le nom `nfl-data`, et que les CSV sont dans `nfl-data/data`.
# Exemple d'arborescence attendue :
#   <parent>/
#     NFL-player-tracking-.../   (ce projet)
#     nfl-data/data/             (les CSV + tracking/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = _PROJECT_ROOT.parent / "nfl-data" / "data"


def get_data_dir(override: str | os.PathLike | None = None) -> Path:
    """Retourne le dossier de données effectif.

    Priorité : override explicite > variable d'env NFL_DATA_DIR > défaut.
    Si le chemin fourni pointe vers un dossier contenant un sous-dossier
    `data/`, on bascule automatiquement dedans (tolérance d'usage).
    """
    if override:
        path = Path(override).expanduser().resolve()
    elif os.environ.get("NFL_DATA_DIR"):
        path = Path(os.environ["NFL_DATA_DIR"]).expanduser().resolve()
    else:
        path = DEFAULT_DATA_DIR

    # Tolérance : si on nous donne la racine du dépôt, descendre dans data/.
    if (path / "data" / PLAYS_FILE).exists():
        path = path / "data"
    return path


# --- Noms de fichiers ---------------------------------------------------------

GAMES_FILE = "games.csv"
PLAYS_FILE = "plays.csv"
PLAYERS_FILE = "players.csv"
PFF_FILE = "pffScoutingData.csv"
TRACKING_DIR = "tracking"
TRACKING_PREFIX = "tracking_"  # tracking/tracking_<gameId>.csv

# --- Dossier de sortie --------------------------------------------------------

OUTPUT_DIR = _PROJECT_ROOT / "outputs"

# --- Constantes du terrain NFL ------------------------------------------------

FIELD_LENGTH = 120.0          # yards (2 end zones de 10 yards incluses)
FIELD_WIDTH = 53.3            # yards
END_ZONE_LENGTH = 10.0        # yards

# --- Vocabulaire métier (valeurs réelles des fichiers) ------------------------

# passResult dans plays.csv.
PASS_RESULT_LABELS = {
    "C": "Passe réussie",
    "I": "Passe ratée",
    "S": "Sack",
    "R": "Scramble",
    "IN": "Interception",
}

# pff_role dans pffScoutingData.csv. Le rôle des rushers est "Pass Rush".
ROLE_PASS_RUSH = "Pass Rush"
ROLE_COVERAGE = "Coverage"
ROLE_PASS_BLOCK = "Pass Block"
ROLE_PASS_ROUTE = "Pass Route"
ROLE_PASSER = "Pass"

# Type de couverture dans plays.csv (pff_passCoverageType).
COVERAGE_TYPE_MAN = "Man"
COVERAGE_TYPE_ZONE = "Zone"

# Buckets de pression (nombre de pass rushers).
RUSHER_BUCKETS = {
    3: "3 rushers",
    4: "4 rushers (standard)",
    5: "5 rushers (blitz léger)",
    6: "6+ rushers (gros blitz)",
}


def rusher_bucket(n_rushers: int) -> str:
    """Transforme un nombre de rushers en libellé de bucket (<=3 et 6+ regroupés)."""
    if n_rushers <= 3:
        return RUSHER_BUCKETS[3]
    if n_rushers == 4:
        return RUSHER_BUCKETS[4]
    if n_rushers == 5:
        return RUSHER_BUCKETS[5]
    return RUSHER_BUCKETS[6]
