"""Balance check: run many seeds and report extinction / population statistics.

    python tests/balance.py [seeds=20] [ticks=1000]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import load_config
from simulation import rules
from simulation.world import World


def run(seeds=20, ticks=1000, rabbits=None, foxes=None, verbose=True, **overrides):
    cfg = load_config()
    for k, v in overrides.items():
        setattr(cfg, k, type(getattr(cfg, k))(v))
    rows = []
    for seed in range(1, seeds + 1):
        w = World(cfg, seed=seed, rabbits=rabbits, foxes=foxes, record_events=False)
        r_ext = f_ext = None
        for _ in range(ticks):
            rules.step(w)
            if r_ext is None and not w.rabbits:
                r_ext = w.day
            if f_ext is None and not w.foxes:
                f_ext = w.day
            if r_ext and f_ext:
                break
        h = w.history
        rs = [s.rabbits for s in h]
        fs = [s.foxes for s in h]
        rows.append((seed, r_ext, f_ext, sum(rs) / len(rs), sum(fs) / len(fs), max(rs), max(fs),
                     sum(s.grass_pct for s in h) / len(h)))
        if verbose:
            print("seed %2d  rabbit-ext %-5s fox-ext %-5s  avg R %6.1f F %5.1f  max R %3d F %3d  grass %4.1f%%"
                  % (seed, r_ext, f_ext, rows[-1][3], rows[-1][4], rows[-1][5], rows[-1][6], rows[-1][7]))
    n = len(rows)
    print("-- rabbit extinction %d/%d, fox extinction %d/%d (of those, foxes only after rabbits: %d)"
          % (sum(1 for r in rows if r[1]), n, sum(1 for r in rows if r[2]), n,
             sum(1 for r in rows if r[2] and r[1] and r[2] >= r[1])))
    print("-- mean pop R %.1f F %.1f, mean max R %.0f F %.0f, mean grass %.0f%%"
          % (sum(r[3] for r in rows) / n, sum(r[4] for r in rows) / n,
             sum(r[5] for r in rows) / n, sum(r[6] for r in rows) / n, sum(r[7] for r in rows) / n))
    return rows


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if "=" not in x]
    ov = dict(x.split("=") for x in sys.argv[1:] if "=" in x)
    run(int(a[0]) if a else 20, int(a[1]) if len(a) > 1 else 1000, verbose="quiet" not in ov,
        **{k: v for k, v in ov.items() if k != "quiet"})
