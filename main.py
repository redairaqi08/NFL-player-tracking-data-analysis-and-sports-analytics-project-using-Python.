"""
Pipeline en ligne de commande — Analyse de la défense NFL.

Répond à : "Quelle défense arrête le mieux l'attaque, et dans quel contexte ?"

Il produit, dans le dossier outputs/ :
    1. la MATRICE TACTIQUE (pression x couverture)         -> réponse directe ;
    2. une carte thermique + trajectoires sur une action   -> exploite le tracking ;
    3. les tableaux de synthèse (pression, couverture, contexte, physique).

Usage :
    python main.py                      # dossier de données par défaut
    python main.py --data-dir /chemin   # dossier explicite
    python main.py --play 2021090900 97 # action précise pour les visuels tracking

Garde-fous respectés : données uniquement issues des 5 fichiers ; tracking lu
par match et filtré par action ; disclaimer corrélation!=causalité sur le physique.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend fichier (pas d'affichage interactif)
import matplotlib.pyplot as plt

from nfl_defense import config, data_loader
from nfl_defense.analysis import context, coverage, physical, pressure, movement
from nfl_defense.viz import plots


def _print_table(title: str, df) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    print(df.to_string(index=False))


def run(data_dir: Path | None, play_ref: tuple[int, int] | None) -> None:
    out = config.OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    print("Chargement des données (plays + pff + games)...")
    plays = data_loader.build_play_table(data_dir)
    print(f"  {len(plays):,} actions chargées.")

    # ------------------------------------------------------------------ A. Pression
    _print_table("A. PRESSION — effet du nombre de rushers",
                 pressure.pressure_summary(plays))
    _print_table("A. PRESSION — meilleures défenses (yards concédés)",
                 pressure.best_defenses_pressure(plays).head(10))

    # ------------------------------------------------------------------ B. Couverture
    _print_table("B. COUVERTURE — Man vs Zone", coverage.man_vs_zone(plays))
    _print_table("B. COUVERTURE — par schéma (Cover-N)",
                 coverage.by_coverage_scheme(plays))

    # --- MATRICE TACTIQUE (réponse directe) ---
    matrix = coverage.tactical_matrix(plays, value="playResult")
    counts = coverage.tactical_matrix_counts(plays)
    _print_table("MATRICE TACTIQUE — yards concédés (pression x couverture)", matrix)

    ax = plots.tactical_matrix_heatmap(matrix, counts)
    fig_path = out / "matrice_tactique.png"
    ax.figure.tight_layout()
    ax.figure.savefig(fig_path, dpi=130)
    plt.close(ax.figure)
    print(f"\n[image] Matrice tactique -> {fig_path}")

    # ------------------------------------------------------------------ C. Contexte
    _print_table("C. CONTEXTE — 3e down & long (>=7)", context.third_and_long(plays))
    _print_table("C. CONTEXTE — défenseurs dans la box vs yards",
                 context.box_vs_yards(plays))

    box = context.box_vs_yards(plays)
    ax = plots.context_bars(box, x="defendersInBox", y="yardsConcedesMoyen",
                            title="Yards concédés selon le nb de défenseurs dans la box",
                            ylabel="Yards concédés (moy.)")
    ctx_path = out / "contexte_box.png"
    ax.figure.tight_layout()
    ax.figure.savefig(ctx_path, dpi=130)
    plt.close(ax.figure)
    print(f"[image] Contexte box -> {ctx_path}")

    # ------------------------------------------------------------------ E. Physique
    players = data_loader.load_players(data_dir)
    pff = data_loader.load_pff(data_dir)
    phys, disclaimer = physical.sacks_by_physique(pff, players)
    _print_table("E. PHYSIQUE — sacks par joueur (top 10)", phys.head(10))
    r, _ = physical.weight_sack_correlation(pff, players)
    print(f"\nCorrélation poids <-> sacks/100 snaps : r = {r}")
    print(f"  {disclaimer}")

    ax = plots.physique_scatter(
        phys[phys["snapsRush"] >= 30], disclaimer=disclaimer)
    phys_path = out / "physique_scatter.png"
    ax.figure.tight_layout()
    ax.figure.savefig(phys_path, dpi=130)
    plt.close(ax.figure)
    print(f"[image] Nuage physique -> {phys_path}")

    # ------------------------------------------------------------------ D. Tracking
    if play_ref is None:
        # Action-type par défaut : première action du premier match disponible.
        games = data_loader.list_tracking_games(data_dir)
        if games:
            gid = games[0]
            pid = int(plays[plays["gameId"] == gid]["playId"].iloc[0])
            play_ref = (gid, pid)

    if play_ref is not None:
        gid, pid = play_ref
        print(f"\nTracking de l'action gameId={gid}, playId={pid} "
              "(lecture filtrée, mémoire maîtrisée)...")
        track = data_loader.load_tracking_play(gid, pid, data_dir)
        if track.empty:
            print("  Aucune donnée de tracking pour cette action.")
        else:
            row = plays[(plays["gameId"] == gid) & (plays["playId"] == pid)]
            off_team = row["possessionTeam"].iloc[0] if not row.empty else None

            ax = plots.play_trajectories(track, offense_team=off_team)
            traj_path = out / "trajectoires.png"
            ax.figure.tight_layout()
            ax.figure.savefig(traj_path, dpi=130)
            plt.close(ax.figure)
            print(f"[image] Trajectoires -> {traj_path}")

            ax = plots.play_heatmap(track)
            heat_path = out / "carte_thermique.png"
            ax.figure.tight_layout()
            ax.figure.savefig(heat_path, dpi=130)
            plt.close(ax.figure)
            print(f"[image] Carte thermique -> {heat_path}")

            speeds = movement.peak_speed_per_player(track)
            _print_table("D. DÉPLACEMENTS — vitesse de pointe par joueur (top 5)",
                         speeds.head(5))

    print("\nTerminé. Images et tableaux dans :", out)


def main() -> None:
    p = argparse.ArgumentParser(description="Analyse de la défense NFL (Big Data Bowl).")
    p.add_argument("--data-dir", default=None,
                   help="Dossier des données (défaut: ../nfl-data/data ou $NFL_DATA_DIR).")
    p.add_argument("--play", nargs=2, type=int, metavar=("GAME_ID", "PLAY_ID"),
                   default=None, help="Action précise pour les visuels de tracking.")
    args = p.parse_args()
    play_ref = tuple(args.play) if args.play else None
    run(args.data_dir, play_ref)


if __name__ == "__main__":
    main()
