"""
Dessin d'un terrain NFL pour servir de fond aux visualisations de tracking
(trajectoires, cartes thermiques, positions).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .. import config


def draw_field(ax: plt.Axes | None = None) -> plt.Axes:
    """Dessine un terrain NFL (120 x 53.3 yards) et retourne l'axe matplotlib."""
    if ax is None:
        _, ax = plt.subplots(figsize=(13, 6))

    # Pelouse.
    ax.add_patch(Rectangle((0, 0), config.FIELD_LENGTH, config.FIELD_WIDTH,
                           facecolor="#2e7d32", zorder=0))
    # End zones.
    ez = config.END_ZONE_LENGTH
    ax.add_patch(Rectangle((0, 0), ez, config.FIELD_WIDTH,
                           facecolor="#1b5e20", zorder=1))
    ax.add_patch(Rectangle((config.FIELD_LENGTH - ez, 0), ez, config.FIELD_WIDTH,
                           facecolor="#1b5e20", zorder=1))

    # Lignes des 10 yards (de 10 à 110).
    for x in range(10, 111, 10):
        ax.axvline(x, color="white", linewidth=1, alpha=0.6, zorder=2)

    ax.set_xlim(0, config.FIELD_LENGTH)
    ax.set_ylim(0, config.FIELD_WIDTH)
    ax.set_xlabel("Terrain (yards)")
    ax.set_ylabel("Largeur (yards)")
    ax.set_aspect("equal")
    return ax
