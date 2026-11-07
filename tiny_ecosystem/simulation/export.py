"""Export a run as one simple CSV, and replay it to prove it is reproducible.

The file is plain CSV. Everything needed to reproduce the run sits in ``# key = value`` comment
lines at the top, followed by the daily time series:

    import pandas as pd
    df = pd.read_csv("run.csv", comment="#")          # Excel / Sheets: just open it; delete the # lines if needed

Reproduce and verify:   python tests/replay.py run.csv
"""
from __future__ import annotations

import csv
import io
import os
import re
from dataclasses import asdict, fields
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config import SimConfig
from simulation import rules
from simulation.world import Params, World

FORMAT_VERSION = 1
COLUMNS = ["day", "rabbits", "foxes", "grass_pct", "eaten_by_foxes", "starved", "old_age",
           "born_rabbits", "born_foxes", "rabbit_repro", "fox_repro", "grass_growth", "fox_hunger"]


def build_csv(world: World, challenge=None, now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    out = io.StringIO()

    def put(key: str, value) -> None:
        out.write("# %s = %s\n" % (key, value))

    out.write("# Tiny Ecosystem export\n")
    out.write("# Open in Excel/Sheets, or pandas: pd.read_csv(path, comment='#')\n")
    out.write("# Reproduce and check:  python tests/replay.py <this file>\n")
    out.write("#\n# --- run ---\n")
    put("format_version", FORMAT_VERSION)
    put("exported", now.strftime("%Y-%m-%d %H:%M:%S"))
    put("seed", world.seed)
    put("mode", ("challenge %d: %s" % (challenge.id, challenge.title)) if challenge else "sandbox")
    put("start_rabbits", world.start_rabbits)
    put("start_foxes", world.start_foxes)
    put("start_grass_level", world.start_grass_level)
    put("grass_scale", world.grass_scale)
    put("days_simulated", world.day)
    p = world.params
    put("sliders_at_export", "rabbit_repro=%g fox_repro=%g grass_growth=%g fox_hunger=%g (the per-day values are columns below)"
        % (p.rabbit_repro, p.fox_repro, p.grass_growth, p.fox_hunger))
    out.write("#\n# --- simulation settings (SimConfig) ---\n")
    for k, v in asdict(world.cfg).items():
        put("cfg." + k, repr(v))
    out.write("#\n# --- player actions: day,tool,x,y,dragging,target_id (applied before the next day) ---\n")
    for iv in world.interventions:
        put("action", ",".join(str(v) for v in iv))
    out.write("#\n")
    w = csv.writer(out, lineterminator="\n")
    w.writerow(COLUMNS)
    for s in world.history:
        w.writerow([s.day, s.rabbits, s.foxes, "%.4f" % s.grass_pct, s.eaten, s.starved, s.old,
                    s.born_r, s.born_f, "%g" % s.rabbit_repro, "%g" % s.fox_repro,
                    "%g" % s.grass_growth, "%g" % s.fox_hunger])
    return out.getvalue()


def write_export(world: World, folder: str, challenge=None) -> str:
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(folder, "tiny_ecosystem_seed%d_day%d_%s.csv" % (world.seed, world.day, stamp))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(build_csv(world, challenge))
    return path


# ----------------------------------------------------------------- replay
def parse(text: str) -> Tuple[Dict[str, str], List[tuple], List[dict]]:
    meta: Dict[str, str] = {}
    actions: List[tuple] = []
    body: List[str] = []
    for line in text.splitlines():
        m = re.match(r"^# (\S+) = (.*)$", line)
        if m:
            if m.group(1) == "action":
                actions.append(tuple(int(v) if re.fullmatch(r"-?\d+", v) else v for v in m.group(2).split(",")))
            else:
                meta[m.group(1)] = m.group(2)
        elif line and not line.startswith("#"):
            body.append(line)
    rows = list(csv.DictReader(body))
    return meta, actions, rows


def replay(text: str) -> Tuple[World, List[dict]]:
    """Rebuild the run from an export: same settings, seed, slider values and player actions."""
    meta, actions, rows = parse(text)
    cfg = SimConfig()
    for f in fields(SimConfig):
        raw = meta.get("cfg." + f.name)
        if raw is not None:
            setattr(cfg, f.name, type(getattr(cfg, f.name))(eval(raw, {}, {})))
    world = World(cfg, seed=int(meta["seed"]), rabbits=int(meta["start_rabbits"]), foxes=int(meta["start_foxes"]),
                  grass_scale=float(meta["grass_scale"]), grass_level=float(meta["start_grass_level"]),
                  record_events=False)
    by_day: Dict[int, List[tuple]] = {}
    for a in actions:
        by_day.setdefault(int(a[0]), []).append(a)
    last = int(rows[-1]["day"]) if rows else 0
    params = {int(r["day"]): r for r in rows}
    for d in range(0, last):
        for _, tool, x, y, dragging, target in by_day.get(d, []):
            world.apply_tool(tool, x, y, bool(dragging), None if target < 0 else target)
        r = params.get(d + 1)
        if r is not None:
            world.params = Params(float(r["rabbit_repro"]), float(r["fox_repro"]),
                                  float(r["grass_growth"]), float(r["fox_hunger"]))
        rules.step(world)
    return world, rows


def verify(text: str) -> Optional[str]:
    """Replay an export. Returns None if the replay matches every row, else a description of the first difference."""
    world, rows = replay(text)
    mine = {s.day: s for s in world.history}
    for r in rows:
        s = mine.get(int(r["day"]))
        got = (s.rabbits, s.foxes, "%.4f" % s.grass_pct) if s else None
        want = (int(r["rabbits"]), int(r["foxes"]), r["grass_pct"])
        if got != want:
            return "day %s: file has %s, replay produced %s" % (r["day"], want, got)
    return None
