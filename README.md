# Analyse de la défense NFL — Big Data Bowl

**Question centrale : quelle défense arrête le mieux l'attaque, et dans quel contexte ?**

On relie trois axes et on demande *« quoi marche, et quand ? »* :

| Axe | Ce qu'on regarde |
|-----|------------------|
| **Tactique** | pression (nb de rushers) et couverture (Man / Zone, Cover-0…Cover-6) |
| **Performance** | sacks, hurries, yards concédés, complétions, interceptions |
| **Déplacements** | position, vitesse, trajectoire des joueurs (données de tracking) |

---

## 1. Données

Projet construit sur le dataset **NFL Big Data Bowl** :
[`ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data`](https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data) — les CSV sont dans le sous-dossier `data/`.

| Fichier | Contenu | Clé de jointure |
|---------|---------|-----------------|
| `games.csv` | équipes, semaine, date | `gameId` |
| `plays.csv` | 1 ligne = 1 action (le cœur) | `gameId, playId` |
| `players.csv` | taille, poids, naissance, poste | `nflId` |
| `pffScoutingData.csv` | 1 ligne = 1 joueur sur 1 action (rôle, sack/hurry/hit) | `gameId, playId, nflId` |
| `tracking/tracking_<gameId>.csv` | position image par image (~10 img/s) | `gameId, playId, nflId, frameId` |

Colonnes réellement utilisées (vérifiées sur les fichiers) : `pff_passCoverage`,
`pff_passCoverageType` (Man/Zone/Other), `passResult`, `playResult`, `down`,
`yardsToGo`, `defendersInBox`, `offenseFormation`, `pff_role` (`Pass Rush`,
`Coverage`…), `pff_sack/hurry/hit`, et pour le tracking `x, y, s, a, dis, o,
dir, event`.

### Où placer les données

Par défaut, le code cherche le dossier `data/` dans un dépôt de données cloné
**à côté** de ce projet, sous le nom `nfl-data` :

```
<parent>/
├── NFL-player-tracking-.../   ← ce projet
└── nfl-data/data/             ← les CSV + tracking/
```

Pour le cloner :

```bash
git clone https://github.com/ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data.git nfl-data
```

On peut aussi pointer vers n'importe quel dossier :

```bash
export NFL_DATA_DIR=/chemin/vers/data      # variable d'environnement
# ou
python main.py --data-dir /chemin/vers/data
```

---

## 2. Installation

```bash
pip install -r requirements.txt
```

Dépendances : pandas, numpy, matplotlib, seaborn, streamlit.

---

## 3. Lancer les analyses

### Pipeline complet (tableaux + images)

```bash
python main.py
```

Produit dans `outputs/` :

- `matrice_tactique.png` — **la réponse directe** : pression × couverture, couleur = yards concédés ;
- `contexte_box.png` — yards concédés selon le nombre de défenseurs dans la box ;
- `physique_scatter.png` — poids vs sacks (avec rappel corrélation ≠ causalité) ;
- `trajectoires.png` et `carte_thermique.png` — exploitent le tracking sur une action.

…et imprime les tableaux de synthèse (pression, Man vs Zone, Cover-N,
3e & long, classement des défenses, top sacks).

Pour viser une action précise (visuels de tracking) :

```bash
python main.py --play 2021090900 97
```

### Dashboard interactif (relie les 3 axes)

```bash
streamlit run dashboard/app.py
```

On filtre un contexte (défense, down, formation, nb de rushers) et on voit d'un
coup : la tactique choisie (matrice), le résultat (yards / sacks / complétion),
et le mouvement sur le terrain (trajectoires + carte thermique d'une action du
filtre courant).

---

## 4. Structure du projet

```
nfl_defense/
├── config.py            chemins de données + constantes terrain + buckets de pression
├── data_loader.py       chargement, jointures, lecture tracking par action (mémoire maîtrisée)
├── analysis/
│   ├── pressure.py      A. pression : rushers → sacks / hurries / yards
│   ├── coverage.py      B. couverture : Man vs Zone, Cover-N, MATRICE TACTIQUE
│   ├── context.py       C. contexte : 3e & long, box, formation
│   ├── movement.py      D. déplacements : vitesse de pointe, positions au snap/arrivée
│   └── physical.py      E. physique : poids/taille vs sacks (DESCRIPTIF)
└── viz/
    ├── field.py         dessin du terrain NFL
    └── plots.py         heatmaps, barres, nuage, trajectoires, carte thermique
main.py                  pipeline CLI
dashboard/app.py         dashboard Streamlit à filtres
tests/test_helpers.py    tests légers (logique pure)
```

---

## 5. Garde-fous (respectés dans le code)

- **Rien d'inventé** : toutes les données viennent des 5 fichiers officiels.
- **Pas d'autre dataset** ajouté au hasard.
- **Corrélation ≠ causalité** : le module `physical.py` renvoie systématiquement
  un *disclaimer* affiché avec tout résultat sur le physique. Un joueur lourd qui
  fait des sacks ne prouve pas que le poids « fait » le sack.
- **Tracking lourd (811 Mo)** : on lit **un fichier (un match) à la fois**, on
  **filtre par `playId`** (`load_tracking_play` lit par chunks), on ne charge
  **jamais tout en mémoire d'un coup**.

---

## 6. Première brique

La **matrice tactique pression × couverture** (`matrice_tactique.png`) répond
directement à la question, puis la **carte thermique** sur une action-type
exploite le tracking immédiatement.
