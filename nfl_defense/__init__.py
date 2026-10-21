"""
nfl_defense — Analyse de la défense NFL (Big Data Bowl).

Question centrale :
    "Quelle défense arrête le mieux l'attaque, et dans quel contexte ?"

On relie trois axes :
    - Tactique    : pression (nb de rushers) et couverture (man / zone / Cover-N).
    - Performance : sacks, hurries, yards concédés.
    - Déplacements : position, vitesse, trajectoire des joueurs (tracking).

Garde-fous (voir README) :
    - Toutes les données viennent des 5 fichiers officiels. Rien d'inventé.
    - Une corrélation N'EST PAS une cause. On le rappelle dans chaque conclusion physique.
    - Le tracking est lourd (811 Mo) : on lit un fichier à la fois, on filtre par playId,
      on ne charge jamais tout en mémoire d'un coup.
"""

__version__ = "0.1.0"
