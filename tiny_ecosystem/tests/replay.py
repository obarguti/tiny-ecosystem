"""Reproduce an exported run and check it matches.

    python tests/replay.py exports/tiny_ecosystem_seed123_day200_20261107-120000.csv
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation.export import verify

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    problem = verify(open(sys.argv[1], encoding="utf-8").read())
    print("REPRODUCED: every day matches." if problem is None else "MISMATCH: " + problem)
    sys.exit(0 if problem is None else 1)
