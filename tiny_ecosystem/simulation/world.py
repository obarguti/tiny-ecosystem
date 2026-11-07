"""World state: grid, animals, seeded RNG and population history."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config import SimConfig
from simulation.animals import Animal, Decor, Fox, Rabbit

NEIGHBOURS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


@dataclass
class Params:
    """Student-adjustable knobs (1.0 = default). Changes apply immediately."""
    rabbit_repro: float = 1.0   # multiplies rabbit birth probability
    fox_repro: float = 1.0      # multiplies fox birth probability
    grass_growth: float = 1.0   # multiplies grass regrowth
    fox_hunger: float = 1.0     # multiplies fox energy loss


@dataclass
class Stat:
    day: int
    rabbits: int
    foxes: int
    grass_pct: float            # 0..100, average grass fullness
    eaten: int = 0              # rabbits eaten by foxes this tick
    starved: int = 0            # animals that starved this tick
    old: int = 0                # animals that died of old age this tick
    born_r: int = 0
    born_f: int = 0


class World:
    def __init__(self, cfg: SimConfig, seed: Optional[int] = None,
                 rabbits: Optional[int] = None, foxes: Optional[int] = None,
                 params: Optional[Params] = None, grass_scale: float = 1.0,
                 record_events: bool = True, grass_level: float = 1.0) -> None:
        self.cfg = cfg
        self.seed = seed if seed is not None else random.randrange(1, 1_000_000)
        self.rng = random.Random(self.seed)
        self.params = params if params is not None else Params()
        self.grass_scale = grass_scale          # scenario modifier (e.g. drought)
        self.record_events = record_events

        self.cols, self.rows = cfg.cols, cfg.rows
        self.day = 0
        self.next_id = 1
        self.rabbits: List[Rabbit] = []
        self.foxes: List[Fox] = []
        self.occ: Dict[Tuple[int, int], Animal] = {}
        self.events: List[tuple] = []
        self.history: List[Stat] = []

        # Most cells start at least partly grown.
        self.grass: List[List[float]] = [
            [(self.rng.uniform(45, 100) if self.rng.random() < 0.9 else self.rng.uniform(10, 45)) * grass_level
             for _ in range(self.cols)] for _ in range(self.rows)]

        cells = [(x, y) for y in range(self.rows) for x in range(self.cols)]
        self.rng.shuffle(cells)
        n_r = cfg.start_rabbits if rabbits is None else rabbits
        n_f = cfg.start_foxes if foxes is None else foxes
        for _ in range(n_r):
            if cells:
                x, y = cells.pop()
                self.spawn("rabbit", x, y)
        for _ in range(n_f):
            if cells:
                x, y = cells.pop()
                self.spawn("fox", x, y)

        # Decorations use their own RNG so they never disturb the simulation.
        self.decor: List[Decor] = self._make_decor(random.Random(self.seed * 7919 + 13))
        self.record_stats()

    # ------------------------------------------------------------ helpers
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    def is_free(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and (x, y) not in self.occ

    def animal_at(self, x: int, y: int) -> Optional[Animal]:
        return self.occ.get((x, y))

    def find_animal(self, animal_id: int) -> Optional[Animal]:
        for a in self.rabbits:
            if a.id == animal_id:
                return a
        for a in self.foxes:
            if a.id == animal_id:
                return a
        return None

    def emit(self, *event) -> None:
        if self.record_events:
            self.events.append(event)

    def pop_events(self) -> List[tuple]:
        ev, self.events = self.events, []
        return ev

    # ------------------------------------------------------------ mutation
    def spawn(self, kind: str, x: int, y: int, energy: Optional[float] = None) -> Optional[Animal]:
        if not self.is_free(x, y):
            return None
        c = self.cfg
        if kind == "rabbit":
            a: Animal = Rabbit(self.next_id, x, y, c.rabbit_start_energy if energy is None else energy)
            self.rabbits.append(a)  # type: ignore[arg-type]
        else:
            a = Fox(self.next_id, x, y, c.fox_start_energy if energy is None else energy)
            self.foxes.append(a)  # type: ignore[arg-type]
        self.next_id += 1
        self.occ[(x, y)] = a
        return a

    def move(self, a: Animal, nx: int, ny: int) -> None:
        del self.occ[(a.x, a.y)]
        a.x, a.y = nx, ny
        self.occ[(nx, ny)] = a

    def remove(self, a: Animal, cause: str) -> None:
        if not a.alive:
            return
        a.alive = False
        self.occ.pop((a.x, a.y), None)
        (self.rabbits if a.kind == "rabbit" else self.foxes).remove(a)  # type: ignore[arg-type]
        self.emit("die", a.kind, a.id, a.x, a.y, cause)

    def free_neighbour(self, x: int, y: int, radius: int = 2) -> Optional[Tuple[int, int]]:
        """A random free cell near (x, y), widening the search up to ``radius``."""
        for r in range(1, radius + 1):
            options = [(x + dx, y + dy)
                       for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                       if max(abs(dx), abs(dy)) == r and self.is_free(x + dx, y + dy)]
            if options:
                return self.rng.choice(options)
        return None

    def add_grass(self, x: int, y: int, amount: float) -> None:
        if self.in_bounds(x, y):
            self.grass[y][x] = min(self.cfg.grass_max, self.grass[y][x] + amount)

    # ------------------------------------------------------------ stats
    def grass_pct(self) -> float:
        total = sum(sum(row) for row in self.grass)
        return 100.0 * total / (self.cols * self.rows * self.cfg.grass_max)

    def record_stats(self, **counters: int) -> None:
        self.history.append(Stat(self.day, len(self.rabbits), len(self.foxes),
                                 self.grass_pct(), **counters))
        if len(self.history) > 4000:
            del self.history[:1000]

    # ------------------------------------------------------------ decor
    def _make_decor(self, rng: random.Random) -> List[Decor]:
        items: List[Decor] = []
        cells = [(x, y) for y in range(self.rows) for x in range(self.cols)]
        rng.shuffle(cells)
        n_rocks, n_bush, n_flower = 11, 8, 46
        for kind, n in (("rock", n_rocks), ("bush", n_bush), ("flower", n_flower)):
            for _ in range(n):
                x, y = cells.pop()
                items.append(Decor(kind, x, y, rng.uniform(0.25, 0.75), rng.uniform(0.35, 0.85),
                                   rng.randrange(4)))
        return items
