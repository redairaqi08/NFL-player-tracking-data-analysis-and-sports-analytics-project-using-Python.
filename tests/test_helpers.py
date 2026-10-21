"""
Tests légers sans dépendance externe (pas besoin de pandas) : valident la
logique pure du module config et des conversions de data_loader.

Lancer :  python tests/test_helpers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nfl_defense import config


def test_rusher_buckets():
    assert config.rusher_bucket(2) == config.RUSHER_BUCKETS[3]
    assert config.rusher_bucket(3) == config.RUSHER_BUCKETS[3]
    assert config.rusher_bucket(4) == config.RUSHER_BUCKETS[4]
    assert config.rusher_bucket(5) == config.RUSHER_BUCKETS[5]
    assert config.rusher_bucket(6) == config.RUSHER_BUCKETS[6]
    assert config.rusher_bucket(8) == config.RUSHER_BUCKETS[6]


def test_height_conversion():
    # data_loader importe pandas ; si absent, on ignore ce test (environnement minimal).
    try:
        from nfl_defense.data_loader import _height_to_inches
    except ModuleNotFoundError as e:
        print(f"SKIP test_height_conversion (dépendance absente: {e.name})")
        return
    assert _height_to_inches("6-4") == 76
    assert _height_to_inches("5-11") == 71
    import math
    assert math.isnan(_height_to_inches("bad"))
    assert math.isnan(_height_to_inches(None))


def test_pass_result_labels():
    assert config.PASS_RESULT_LABELS["S"] == "Sack"
    assert config.PASS_RESULT_LABELS["C"] == "Passe réussie"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
                passed += 1
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {name}: {e}")
                raise
    print(f"\n{passed} tests OK")


def test_verdict_components():
    # verdict.py importe pandas ; skip si absent.
    try:
        from nfl_defense.analysis import verdict
    except ModuleNotFoundError as e:
        print(f"SKIP test_verdict_components (dépendance absente: {e.name})")
        return

    # Un sack doit donner la meilleure composante résultat.
    s_sack, _ = verdict._result_component("S", None)
    s_big, _ = verdict._result_component("C", 25)
    assert s_sack > s_big, "un sack doit mieux noter qu'une grosse réception"

    # Peu de yards concédés > beaucoup de yards concédés.
    s_short, _ = verdict._result_component("C", 3)
    s_long, _ = verdict._result_component("C", 20)
    assert s_short > s_long

    # Pression : sack > hit > hurry > rien.
    s1, _ = verdict._pressure_component(True, False, False, 4)
    s2, _ = verdict._pressure_component(False, False, True, 4)
    s3, _ = verdict._pressure_component(False, False, False, 4)
    assert s1 > s2 > s3

    # Vitesse : plus c'est rapide, plus la composante est haute.
    fast, _ = verdict._speed_component(8.0)
    slow, _ = verdict._speed_component(3.0)
    assert fast > slow

    # Étiquettes cohérentes avec la note.
    assert verdict._label(90)[0] == "Excellente défense"
    assert verdict._label(10)[0] == "Mauvaise défense"