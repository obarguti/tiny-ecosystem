"""Ecosystem rules. Pure Python: no Pygame, no drawing.

Update order of one tick:

 1. Regenerate grass; cooldowns tick down.
 2. Rabbits move. A rabbit that is being chased (or has a fox right next to it) FLEES:
    it picks the free cell farthest from the fox and does not eat that tick.
 3. Other rabbits drift towards greener cells; conflicts resolve first-come-first-served
    in a seeded-random order, so two animals never share a cell.
 4. Calm rabbits eat grass at their new cell.
 5. Foxes: a hungry fox looks for rabbits inside its VISION radius. When it spots one it
    LOCKS ON and sprints after it (``fox_hunt_steps`` cells per tick). Reaching the rabbit
    eats it. A chase that fails after ``fox_chase_max`` ticks ends in a short rest.
    The "Fox Hunger" slider scales the vision radius.
 6. Energy is spent and animals age.
 7. Dead animals are removed.
 8. Reproduction: both partners must be adult, well-fed and off cooldown, and close to
    each other. Both then start a cooldown.
 9. Population statistics are recorded.
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

    # 1. grass regrows, timers tick
    regrow = cfg.grass_regrow * p.grass_growth * w.grass_scale
    gmax = cfg.grass_max
    for row in w.grass:
        for x in range(w.cols):
            if row[x] < gmax:
                row[x] = min(gmax, row[x] + regrow)
    for a in w.rabbits + w.foxes:
        a.px, a.py = a.x, a.y
        a.status = "Wandering"
        if a.cooldown > 0:
            a.cooldown -= 1

    # 2-3. rabbits move (flee or forage)
    locked = {f.chasing for f in w.foxes if f.chasing >= 0}
    rabbits = list(w.rabbits)
    rng.shuffle(rabbits)
    for r in rabbits:
        _move_rabbit(w, r, locked)

    # 4. calm rabbits eat
    for r in rabbits:
        if r.status == "Fleeing":
            continue
        eaten = min(cfg.rabbit_eat_max, w.grass[r.y][r.x])
        if eaten > 0:
            w.grass[r.y][r.x] -= eaten
            r.energy = min(cfg.rabbit_max_energy, r.energy + eaten * cfg.rabbit_energy_per_grass)
            r.status = "Eating"
            w.emit("eat", r.x, r.y)

    # 5. foxes hunt
    foxes = list(w.foxes)
    rng.shuffle(foxes)
    for f in foxes:
        _move_fox(w, f, counters)

    # 6. energy and age
    for a in w.rabbits + w.foxes:
        if a.kind == "rabbit":
            a.energy -= cfg.rabbit_energy_loss
        else:
            a.energy -= cfg.fox_energy_loss + (cfg.fox_chase_energy if a.status == "Hunting" else 0.0)
        a.age += 1

    # 7. deaths
    for a in list(w.rabbits) + list(w.foxes):
        max_age = cfg.rabbit_max_age if a.kind == "rabbit" else cfg.fox_max_age
        if a.energy <= 0:
            counters["starved"] += 1
            w.remove(a, "starved")
        elif a.age > max_age:
            counters["old"] += 1
            w.remove(a, "old")

    # 8. reproduction
    for a in _shuffled(w, w.rabbits + w.foxes):
        if a.alive:
            _maybe_reproduce(w, a, counters)

    for a in w.rabbits + w.foxes:
        if a.status != "Reproducing" and a.energy < STARVING_BELOW:
            a.status = "Starving"

    # 9. statistics
    w.record_stats(**counters)


# ----------------------------------------------------------------- helpers
def _shuffled(w: World, items: List[Animal]) -> List[Animal]:
    items = list(items)
    w.rng.shuffle(items)
    return items


def _d2(a: Animal, b: Animal) -> int:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def vision(w: World) -> float:
    """Fox vision radius in cells; the Fox Hunger slider scales it."""
    return w.cfg.fox_detect_radius * w.params.fox_hunger


def _move_rabbit(w: World, r: Rabbit, locked: set) -> None:
    flee2 = w.cfg.rabbit_flee_radius ** 2
    threats = [f for f in w.foxes if f.chasing == r.id or _d2(f, r) <= flee2]
    best: Optional[Tuple[float, int, int]] = None
    for dx, dy in [(0, 0)] + NEIGHBOURS:
        nx, ny = r.x + dx, r.y + dy
        if not w.in_bounds(nx, ny):
            continue
        if (dx, dy) != (0, 0) and (nx, ny) in w.occ:
            continue
        if threats:
            # run: maximise distance from the nearest threatening fox
            dist = min((nx - f.x) ** 2 + (ny - f.y) ** 2 for f in threats)
            score = dist * 10 + w.rng.uniform(0, 4) + w.grass[ny][nx] * 0.02
        else:
            # prefer greener cells, but add noise so movement stays lively
            score = w.grass[ny][nx] + w.rng.uniform(0, 55) - (12 if (dx, dy) == (0, 0) else 0)
        if best is None or score > best[0]:
            best = (score, nx, ny)
    if best and (best[1], best[2]) != (r.x, r.y):
        w.move(r, best[1], best[2])
        r.status = "Searching for food"
    if threats:
        r.status = "Fleeing"


def _find_rabbit(w: World, rabbit_id: int) -> Optional[Rabbit]:
    if rabbit_id < 0:
        return None
    a = w.find_animal(rabbit_id)
    return a if a is not None and a.kind == "rabbit" and a.alive else None


def _move_fox(w: World, f: Fox, counters: dict) -> None:
    cfg = w.cfg
    if f.rest > 0:                       # catching its breath after a failed chase
        f.rest -= 1
        f.chasing, f.chase_ticks = -1, 0
        f.status = "Resting"
        return

    target: Optional[Rabbit] = None
    if f.energy < cfg.fox_hungry_below:  # well-fed foxes don't bother hunting
        v = vision(w)
        cur = _find_rabbit(w, f.chasing)
        if cur is not None and _d2(f, cur) <= (v * 1.5) ** 2:
            target = cur                 # keep the lock while it stays roughly in sight
        else:
            best_d = v * v + 1
            for r in w.rabbits:
                d = _d2(f, r)
                if d <= v * v and d < best_d:
                    target, best_d = r, d

    if target is None:
        f.chasing, f.chase_ticks = -1, 0
        f.status = "Wandering"
        options = [(f.x + dx, f.y + dy) for dx, dy in NEIGHBOURS if w.is_free(f.x + dx, f.y + dy)]
        if options and w.rng.random() < 0.8:
            nx, ny = w.rng.choice(options)
            w.move(f, nx, ny)
        return

    f.chasing = target.id
    f.status = "Hunting"
    f.chase_ticks += 1
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
    if f.chase_ticks >= cfg.fox_chase_max:   # the rabbit got away: give up and rest
        f.rest = cfg.fox_rest_ticks
        f.chasing, f.chase_ticks = -1, 0


def _eat_rabbit(w: World, f: Fox, r: Rabbit, counters: dict) -> None:
    w.remove(r, "eaten")
    w.move(f, r.x, r.y)
    f.energy = min(w.cfg.fox_max_energy, f.energy + w.cfg.fox_meal_energy)
    f.status = "Eating"
    f.chasing, f.chase_ticks = -1, 0
    counters["eaten"] += 1
    w.emit("hunt", f.x, f.y)


def _eligible(w: World, a: Animal) -> bool:
    c = w.cfg
    if not a.alive or a.cooldown > 0:
        return False
    if a.kind == "rabbit":
        return a.age >= c.rabbit_repro_min_age and a.energy >= c.rabbit_repro_threshold
    return a.age >= c.fox_repro_min_age and a.energy >= c.fox_repro_threshold


def _maybe_reproduce(w: World, a: Animal, counters: dict) -> None:
    cfg, p = w.cfg, w.params
    if not _eligible(w, a):
        return
    if a.kind == "rabbit":
        prob, radius, same, cd = (cfg.rabbit_repro_prob * p.rabbit_repro, cfg.rabbit_mate_radius,
                                  w.rabbits, cfg.rabbit_repro_cooldown)
    else:
        prob, radius, same, cd = (cfg.fox_repro_prob * p.fox_repro, cfg.fox_mate_radius,
                                  w.foxes, cfg.fox_repro_cooldown)
    mates = [o for o in same if o is not a and _d2(a, o) <= radius * radius and _eligible(w, o)]
    if not mates or w.rng.random() >= prob:
        return
    spot = w.free_neighbour(a.x, a.y)
    if spot is None:
        return
    mate = min(mates, key=lambda o: _d2(a, o))
    a.cooldown = mate.cooldown = cd
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
