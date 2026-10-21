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
