"""Configuration: simulation numbers, colours and UI constants.

Every simulation value can be overridden by putting it in ``config.json`` next
to this file, e.g. ``{"start_foxes": 10, "rabbit_max_age": 120}``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")


@dataclass
class SimConfig:
    # --- world ---
    cols: int = 30
    rows: int = 20
    start_rabbits: int = 35
    start_foxes: int = 7
    ticks_per_second: float = 2.0  # at 1x speed (1 tick = 1 day)

    # --- grass ---
    grass_max: float = 100.0
    grass_regrow: float = 2.0       # per tick
    rabbit_eat_max: float = 20.0    # per feeding

    # --- rabbits ---
    rabbit_start_energy: float = 60.0
    rabbit_max_energy: float = 100.0
    rabbit_energy_loss: float = 3.0
    rabbit_energy_per_grass: float = 0.3
    rabbit_repro_threshold: float = 65.0
    rabbit_repro_prob: float = 0.15
    rabbit_repro_cost: float = 30.0
    rabbit_child_energy: float = 40.0
    rabbit_max_age: int = 100

    # --- foxes ---
    # NOTE: values below were tuned with tests/balance.py (see README, "Balancing").
    fox_start_energy: float = 65.0
    fox_max_energy: float = 120.0
    fox_energy_loss: float = 4.0
    fox_meal_energy: float = 50.0
    fox_detect_radius: float = 2.0
    fox_repro_threshold: float = 100.0
    fox_repro_prob: float = 0.07
    fox_repro_cost: float = 40.0
    fox_child_energy: float = 45.0
    fox_max_age: int = 200
    fox_hungry_below: float = 60.0  # a fox only hunts while its energy is below this
    fox_hunt_steps: int = 1         # cells a fox may cover per tick while chasing


def load_config(path: str = CONFIG_PATH) -> SimConfig:
    cfg = SimConfig()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return cfg
    names = {f.name: f for f in fields(SimConfig)}
    for key, value in data.items():
        if key in names:
            setattr(cfg, key, type(getattr(cfg, key))(value))
    return cfg


# ---------------------------------------------------------------- window/UI
WINDOW_W, WINDOW_H = 1280, 800
WORLD_AREA_W, WORLD_AREA_H = 960, 640        # main area above the graph
SIDEBAR_W = WINDOW_W - WORLD_AREA_W
GRAPH_H = WINDOW_H - WORLD_AREA_H
FPS = 60
HISTORY_VISIBLE = 300

CELL = 31                                    # pixels per logical cell
WORLD_OFFSET = (15, 8)                       # top-left of the meadow in the main area

# ---------------------------------------------------------------- palette
PANEL = (247, 241, 228)        # warm off-white
PANEL_DARK = (232, 223, 203)
PANEL_LINE = (205, 192, 167)
INK = (62, 54, 46)
INK_SOFT = (120, 108, 94)
BACKDROP = (204, 215, 186)
ACCENT = (93, 150, 82)
ACCENT_DARK = (68, 118, 60)
HIGHLIGHT = (255, 205, 96)

COL_GRASS = (88, 166, 72)
COL_RABBIT = (74, 134, 214)
COL_FOX = (232, 120, 40)
