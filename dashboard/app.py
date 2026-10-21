"""
Dashboard à filtres — relie les 3 axes (tactique / performance / déplacements).

Lancer :
    streamlit run dashboard/app.py

On filtre un contexte (équipe, down, formation, nb de rushers) et on voit d'un
coup : la tactique choisie, le résultat (yards/sacks), et le mouvement sur le
terrain (tracking d'une action du filtre courant).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

# Rendre le package importable quand on lance via `streamlit run`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nfl_defense import config, data_loader                        # noqa: E402
from nfl_defense.analysis import coverage, pressure, movement, verdict  # noqa: E402
from nfl_defense.viz import plots, animation                       # noqa: E402

st.set_page_config(page_title="Défense NFL — Big Data Bowl", layout="wide")


@st.cache_data(show_spinner="Chargement des actions...")
def _load_plays(data_dir: str | None):
    return data_loader.build_play_table(data_dir)


@st.cache_data(show_spinner="Chargement du tracking de l'action...")
def _load_track(game_id: int, play_id: int, data_dir: str | None):
    return data_loader.load_tracking_play(game_id, play_id, data_dir)


@st.cache_data(show_spinner="Chargement du scouting (rôles, sacks)...")
def _load_pff(data_dir: str | None):
    return data_loader.load_pff(data_dir)


@st.cache_data(show_spinner="Chargement des joueurs...")
def _load_players(data_dir: str | None):
    return data_loader.load_players(data_dir)


def main() -> None:
    st.title("🏈 Quelle défense arrête le mieux l'attaque, et dans quel contexte ?")
    st.caption("Tactique (pression × couverture) · Performance (sacks, yards) · "
               "Déplacements (tracking). Données : NFL Big Data Bowl.")

    # --- Source de données ---
    data_dir_input = st.sidebar.text_input(
        "Dossier des données (vide = défaut)", value="")
    data_dir = data_dir_input or None
    try:
        plays = _load_plays(data_dir)
    except FileNotFoundError as e:
        st.error(f"Données introuvables : {e}\n\n"
                 "Renseigne le chemin du dossier `data/` dans la barre latérale.")
        st.stop()

    # --- Filtres de contexte ---
    st.sidebar.header("Filtres de contexte")
    teams = sorted(plays["defensiveTeam"].dropna().unique())
    team = st.sidebar.selectbox("Défense", ["Toutes"] + list(teams))
    down = st.sidebar.selectbox("Down", ["Tous", 1, 2, 3, 4])
    formations = sorted(plays["offenseFormation"].dropna().unique())
    formation = st.sidebar.selectbox("Formation offensive", ["Toutes"] + list(formations))
    buckets = sorted(plays["rusherBucket"].dropna().unique())
    bucket = st.sidebar.selectbox("Pression (rushers)", ["Toutes"] + list(buckets))

    df = plays.copy()
    if team != "Toutes":
        df = df[df["defensiveTeam"] == team]
    if down != "Tous":
        df = df[df["down"] == down]
    if formation != "Toutes":
        df = df[df["offenseFormation"] == formation]
    if bucket != "Toutes":
        df = df[df["rusherBucket"] == bucket]

    if df.empty:
        st.warning("Aucune action pour ce filtre.")
        st.stop()

    # --- Axe PERFORMANCE : indicateurs clés ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Actions", f"{len(df):,}")
    c2.metric("Yards concédés (moy.)", f"{df['playResult'].mean():.2f}")
    c3.metric("Taux de sack", f"{df['isSack'].mean() * 100:.1f} %")
    c4.metric("Taux de complétion", f"{df['isComplete'].mean() * 100:.1f} %")

    # --- Axe TACTIQUE : matrice + pression ---
    left, right = st.columns(2)
    with left:
        st.subheader("Matrice tactique (pression × couverture)")
        matrix = coverage.tactical_matrix(df, value="playResult")
        if matrix.size:
            fig, ax = plt.subplots(figsize=(9, 4))
            plots.tactical_matrix_heatmap(matrix, ax=ax, title="Yards concédés")
            fig.tight_layout()
            st.pyplot(fig)
        else:
            st.info("Pas assez de données pour la matrice sur ce filtre.")
    with right:
        st.subheader("Effet de la pression")
        st.dataframe(pressure.pressure_summary(df), use_container_width=True)

    # --- Axe DÉPLACEMENTS : animation + données clés + verdict d'une action ---
    st.markdown("---")
    st.header("🎬 Analyse d'une action (animation, données, verdict)")
    sample = df[["gameId", "playId", "playDescription"]].head(50)
    labels = {
        f"{r.gameId} · {r.playId} · {str(r.playDescription)[:70]}": (r.gameId, r.playId)
        for r in sample.itertuples()
    }
    choice = st.selectbox("Choisir une action", list(labels.keys()))
    gid, pid = labels[choice]

    track = _load_track(int(gid), int(pid), data_dir)
    row = df[(df["gameId"] == gid) & (df["playId"] == pid)]

    if track.empty:
        st.info("Pas de tracking pour cette action (fichier de match absent ?).")
    elif row.empty:
        st.info("Action introuvable dans la sélection.")
    else:
        play_row = row.iloc[0]
        off_team = play_row.get("possessionTeam")
        pff = _load_pff(data_dir)
        players = _load_players(data_dir)

        # ---- VERDICT : bonne ou mauvaise défense sur cette action ? ----
        v = verdict.play_verdict(play_row, play_tracking=track, pff=pff)
        st.subheader(f"{v['emoji']} Verdict défense : {v['label']} "
                     f"— {v['note_sur_100']}/100")
        st.progress(min(int(v["note_sur_100"]), 100))
        st.markdown("**Pourquoi ?**")
        for reason in v["raisons"]:
            st.markdown(f"- {reason}")

        # ---- Animation image par image (slider) ----
        st.subheader("Animation — déplacements image par image")
        frames = sorted(track["frameId"].unique())
        events = movement.frame_events(track)
        # Repère l'évènement 'ball_snap' comme point de départ par défaut.
        default_frame = next((f for f, e in events.items() if e == "ball_snap"),
                             frames[0])
        show_trails = st.checkbox("Afficher les trainées", value=True)
        frame_id = st.slider("Image (frame)", int(frames[0]), int(frames[-1]),
                             int(default_frame))
        if frame_id in events:
            st.caption(f"⏱️ Évènement à cette image : **{events[frame_id]}**")

        fig, ax = plt.subplots(figsize=(13, 6))
        animation.draw_frame(
            track, frame_id, ax=ax, offense_team=off_team,
            pff=pff, game_id=int(gid), play_id=int(pid),
            show_trails=show_trails, event_label=events.get(frame_id),
        )
        fig.tight_layout()
        st.pyplot(fig)

        # ---- Données clés par joueur ----
        st.subheader("📊 Données clés par joueur (vitesse, accélération, distance)")
        stats = movement.player_stats_for_play(
            track, pff=pff, players=players,
            game_id=int(gid), play_id=int(pid),
        )
        if not stats.empty:
            cols = ["displayName", "officialPosition", "team", "pff_role",
                    "vitessePointe", "vitesseMoyenne", "accelMax", "distanceTotale"]
            cols = [c for c in cols if c in stats.columns]
            st.dataframe(
                stats[cols].rename(columns={
                    "displayName": "Joueur", "officialPosition": "Poste",
                    "team": "Équipe", "pff_role": "Rôle",
                    "vitessePointe": "V. pointe (yd/s)",
                    "vitesseMoyenne": "V. moyenne (yd/s)",
                    "accelMax": "Accél. max (yd/s²)",
                    "distanceTotale": "Distance (yd)",
                }),
                use_container_width=True, height=380,
            )

        # ---- Vues statiques complémentaires ----
        st.subheader("Vues d'ensemble de l'action")
        t1, t2 = st.columns(2)
        with t1:
            fig, ax = plt.subplots(figsize=(8, 4.2))
            plots.play_trajectories(track, ax=ax, offense_team=off_team)
            fig.tight_layout()
            st.pyplot(fig)
        with t2:
            fig, ax = plt.subplots(figsize=(8, 4.2))
            plots.play_heatmap(track, ax=ax)
            fig.tight_layout()
            st.pyplot(fig)


if __name__ == "__main__":
    main()
