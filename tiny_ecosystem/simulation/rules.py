"""Ecosystem rules. Pure Python: no Pygame, no drawing.

Update order of one tick (documented in plan.md section 5.5):

 1. Regenerate grass.
 2. Rabbits choose a move (processed in seeded-random order).
 3. Conflicts resolve first-come-first-served: a cell claimed earlier in the
    shuffled order is taken, so two animals never share a cell.
 4. Rabbits eat grass at their new cell.
 5. Foxes look for rabbits in their detection radius and move / hunt.
 6. A fox that steps onto a rabbit eats it (deterministic).
 7. Energy is spent and animals age.
 8. Dead animals are removed.
 9. Eligible animals reproduce (new animals appear next to their parent).
10. Population statistics are recorded.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from simulation.animals import Animal, Fox, Rabbit
from simulation.world import NEIGHBOURS, World

STARVING_BELOW = 25.0


def step(w: World) -> None:
    cfg, p, rng = w.cfg, w.params, w.rng
    w.day += 1
    counters = dict(eaten=0, starved=0, old=0, born_r=0, born_f=0)

    # 1. grass regrows
    regrow = cfg.grass_regrow * p.grass_growth * w.grass_scale
    gmax = cfg.grass_max
    for row in w.grass:
        for x in range(w.cols):
            if row[x] < gmax:
                row[x] = min(gmax, row[x] + regrow)

    for a in w.rabbits + w.foxes:
        a.px, a.py = a.x, a.y
        a.status = "Wandering"

    # 2-3. rabbits move
    rabbits = list(w.rabbits)
    rng.shuffle(rabbits)
    for r in rabbits:
        _move_rabbit(w, r)

    # 4. rabbits eat
    for r in rabbits:
        eaten = min(cfg.rabbit_eat_max, w.grass[r.y][r.x])
        if eaten > 0:
            w.grass[r.y][r.x] -= eaten
            r.energy = min(cfg.rabbit_max_energy, r.energy + eaten * cfg.rabbit_energy_per_grass)
            r.status = "Eating"
            w.emit("eat", r.x, r.y)

    # 5-6. foxes hunt
    foxes = list(w.foxes)
    rng.shuffle(foxes)
    for f in foxes:
        _move_fox(w, f, counters)

    # 7. energy and age
    fox_loss = cfg.fox_energy_loss * p.fox_hunger
    for a in w.rabbits + w.foxes:
        a.energy -= cfg.rabbit_energy_loss if a.kind == "rabbit" else fox_loss
        a.age += 1

    # 8. deaths
    for a in list(w.rabbits) + list(w.foxes):
        max_age = cfg.rabbit_max_age if a.kind == "rabbit" else cfg.fox_max_age
        if a.energy <= 0:
            counters["starved"] += 1
            w.remove(a, "starved")
        elif a.age > max_age:
            counters["old"] += 1
            w.remove(a, "old")

    # 9. reproduction
    for a in _shuffled(w, w.rabbits + w.foxes):
        if a.alive:
            _maybe_reproduce(w, a, counters)

    for a in w.rabbits + w.foxes:
        if a.status != "Reproducing":
            a.status = _status(cfg, a)

    # 10. statistics
    w.record_stats(**counters)


# ----------------------------------------------------------------- helpers
def _shuffled(w: World, items: List[Animal]) -> List[Animal]:
    items = list(items)
    w.rng.shuffle(items)
    return items


def _move_rabbit(w: World, r: Rabbit) -> None:
    best: Optional[Tuple[float, int, int]] = None
    for dx, dy in [(0, 0)] + NEIGHBOURS:
        nx, ny = r.x + dx, r.y + dy
        if not w.in_bounds(nx, ny):
            continue
        if (dx, dy) != (0, 0) and (nx, ny) in w.occ:
            continue
        # prefer greener cells, but add noise so movement stays lively
        score = w.grass[ny][nx] + w.rng.uniform(0, 55) - (12 if (dx, dy) == (0, 0) else 0)
        if best is None or score > best[0]:
            best = (score, nx, ny)
    if best and (best[1], best[2]) != (r.x, r.y):
        w.move(r, best[1], best[2])
        r.status = "Searching for food"


def _move_fox(w: World, f: Fox, counters: dict) -> None:
    cfg = w.cfg
    target = _nearest_rabbit(w, f) if f.energy < cfg.fox_hungry_below else None
    f.chasing = target.id if target else -1
    if target is None:
        f.status = "Wandering"
        options = [(f.x + dx, f.y + dy) for dx, dy in NEIGHBOURS if w.is_free(f.x + dx, f.y + dy)]
        if options and w.rng.random() < 0.8:
            nx, ny = w.rng.choice(options)
            w.move(f, nx, ny)
        return

    f.status = "Hunting"
    for _ in range(cfg.fox_hunt_steps):
        dx = (target.x > f.x) - (target.x < f.x)
        dy = (target.y > f.y) - (target.y < f.y)
        tries = [(dx, dy)]
        if dx and dy:
            tries += [(dx, 0), (0, dy)] if w.rng.random() < 0.5 else [(0, dy), (dx, 0)]
        moved = False
        for tx, ty in tries:
            nx, ny = f.x + tx, f.y + ty
            occupant = w.animal_at(nx, ny)
            if occupant is not None and occupant.kind == "rabbit":
                _eat_rabbit(w, f, occupant, counters)
                return
            if occupant is None and w.in_bounds(nx, ny):
                w.move(f, nx, ny)
                moved = True
                break
        if not moved:
            break


def _eat_rabbit(w: World, f: Fox, r: Rabbit, counters: dict) -> None:
    w.remove(r, "eaten")
    w.move(f, r.x, r.y)
    f.energy = min(w.cfg.fox_max_energy, f.energy + w.cfg.fox_meal_energy)
    f.status = "Eating"
    f.chasing = -1
    counters["eaten"] += 1
    w.emit("hunt", f.x, f.y)


def _nearest_rabbit(w: World, f: Fox) -> Optional[Rabbit]:
    r2 = w.cfg.fox_detect_radius ** 2
    best, best_d = None, r2 + 1
    for r in w.rabbits:
        d = (r.x - f.x) ** 2 + (r.y - f.y) ** 2
        if d <= r2 and d < best_d:
            best, best_d = r, d
    return best


def _maybe_reproduce(w: World, a: Animal, counters: dict) -> None:
    cfg, p = w.cfg, w.params
    if a.kind == "rabbit":
        ok = a.energy >= cfg.rabbit_repro_threshold
        prob = cfg.rabbit_repro_prob * p.rabbit_repro
    else:
        ok = a.energy >= cfg.fox_repro_threshold
        prob = cfg.fox_repro_prob * p.fox_repro
    if not ok or w.rng.random() >= prob:
        return
    spot = w.free_neighbour(a.x, a.y)
    if spot is None:
        return
    if a.kind == "rabbit":
        a.energy -= cfg.rabbit_repro_cost
        child = w.spawn("rabbit", *spot, energy=cfg.rabbit_child_energy)
        counters["born_r"] += 1
    else:
        a.energy -= cfg.fox_repro_cost
        child = w.spawn("fox", *spot, energy=cfg.fox_child_energy)
        counters["born_f"] += 1
    a.status = "Reproducing"
    w.emit("born", a.kind, child.id, spot[0], spot[1], a.x, a.y)


def _status(cfg, a: Animal) -> str:
    if a.energy < STARVING_BELOW:
        return "Starving"
    if a.status == "Searching for food" and a.energy >= 70:
        return "Wandering"
    return a.status
