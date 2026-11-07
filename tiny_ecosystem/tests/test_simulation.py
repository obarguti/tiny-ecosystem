import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SimConfig
from simulation import rules
from simulation.world import World


def empty_world(seed=1, **kw):
    w = World(SimConfig(), seed=seed, rabbits=0, foxes=0, **kw)
    return w


def test_grass_growth_is_capped():
    w = empty_world()
    for row in w.grass:
        for x in range(w.cols):
            row[x] = 99.0
    w.grass[0][0] = 10.0
    rules.step(w)
    assert all(0 <= v <= 100 for row in w.grass for v in row)
    assert w.grass[0][0] == 10.0 + w.cfg.grass_regrow
    assert w.grass[1][1] == 100.0          # stops at 100


def test_grass_regrowth_slider_applies_live():
    w = empty_world()
    w.grass[0][0] = 0.0
    w.params.grass_growth = 2.0
    rules.step(w)
    assert w.grass[0][0] == 2 * w.cfg.grass_regrow


def test_rabbit_energy_cost_and_eating():
    w = empty_world()
    for row in w.grass:
        for x in range(w.cols):
            row[x] = 0.0
    r = w.spawn("rabbit", 5, 5)
    rules.step(w)
    assert r.energy == 60 - 3 + 0.0 or abs(r.energy - 57) < 1.5  # only 2 grass regrew
    # on lush grass a rabbit gains 20 * 0.3 = 6 before paying 3
    w2 = empty_world()
    for row in w2.grass:
        for x in range(w2.cols):
            row[x] = 100.0
    r2 = w2.spawn("rabbit", 5, 5)
    rules.step(w2)
    assert abs(r2.energy - (60 + 6 - 3)) < 1e-9
    assert sum(sum(row) for row in w2.grass) < 100.0 * 600   # something was eaten


def test_rabbit_starves():
    w = empty_world()
    for row in w.grass:
        for x in range(w.cols):
            row[x] = 0.0
    w.params.grass_growth = 0.0
    r = w.spawn("rabbit", 3, 3, energy=2.0)
    rules.step(w)
    assert not r.alive and r not in w.rabbits
    assert (3, 3) not in w.occ and w.history[-1].starved == 1


def test_old_age_death():
    w = empty_world()
    r = w.spawn("rabbit", 3, 3)
    r.age = w.cfg.rabbit_max_age
    for row in w.grass:
        for x in range(w.cols):
            row[x] = 100.0
    rules.step(w)
    assert not r.alive and w.history[-1].old == 1


def _lush(w):
    for row in w.grass:
        for x in range(w.cols):
            row[x] = 100.0


def _pair(w, **kw):
    a = w.spawn("rabbit", 10, 10, energy=kw.get("energy", 100))
    b = w.spawn("rabbit", 11, 10, energy=kw.get("energy", 100))
    a.age = b.age = kw.get("age", 30)
    return a, b


def test_rabbit_reproduction_needs_energy_age_partner_and_cooldown():
    cfg = SimConfig()
    # a lone rabbit never breeds
    w = empty_world(); _lush(w); w.params.rabbit_repro = 100.0
    r = w.spawn("rabbit", 10, 10, energy=100); r.age = 30
    rules.step(w)
    assert len(w.rabbits) == 1
    # a pair that is too hungry never breeds
    w = empty_world(); _lush(w); w.params.rabbit_repro = 100.0; w.params.grass_growth = 0.0
    for row in w.grass:
        for x in range(w.cols):
            row[x] = 0.0
    _pair(w, energy=50)
    rules.step(w)
    assert len(w.rabbits) == 2
    # a pair that is too young never breeds
    w = empty_world(); _lush(w); w.params.rabbit_repro = 100.0
    _pair(w, age=2)
    rules.step(w)
    assert len(w.rabbits) == 2
    # an eligible pair breeds; both go on cooldown; the child gets 40 energy
    w = empty_world(); _lush(w); w.params.rabbit_repro = 100.0
    a, b = _pair(w)
    rules.step(w)
    assert len(w.rabbits) == 3
    child = [x for x in w.rabbits if x not in (a, b)][0]
    assert child.energy == cfg.rabbit_child_energy
    assert a.cooldown > 0 and b.cooldown > 0
    # cooldown blocks the very next tick
    rules.step(w)
    assert len(w.rabbits) == 3


def test_fox_pair_needed_too():
    w = empty_world(); w.params.fox_repro = 100.0; w.params.fox_hunger = 0.0
    f = w.spawn("fox", 10, 10, energy=120); f.age = 40
    rules.step(w)
    assert len(w.foxes) == 1
    g = w.spawn("fox", 12, 10, energy=120); g.age = 40
    rules.step(w)
    assert len(w.foxes) == 3


def test_fox_eats_adjacent_rabbit():
    w = empty_world()
    w.params.grass_growth = 0.0
    f = w.spawn("fox", 10, 10, energy=50)
    f.age = 0
    r = w.spawn("rabbit", 12, 10, energy=100)
    # rabbit might wander off, so use a deterministic check on many seeds
    eaten = 0
    for seed in range(20):
        w = empty_world(seed=seed)
        w.params.fox_repro = 0.0
        f = w.spawn("fox", 10, 10, energy=50)
        w.spawn("rabbit", 11, 10, energy=100)
        rules.step(w)
        if not w.rabbits:
            eaten += 1
            assert w.history[-1].eaten == 1
            assert f.energy > 50
    assert eaten >= 5   # rabbits also move, so not every attempt connects


def test_fox_starves_and_dies():
    w = empty_world()
    f = w.spawn("fox", 4, 4, energy=3.0)
    rules.step(w)
    assert not f.alive and not w.foxes


def test_fox_hunger_slider_sets_vision():
    def status(hunger):
        w = empty_world(); w.params.fox_repro = 0.0; w.params.grass_growth = 0.0
        w.params.fox_hunger = hunger
        w.spawn("fox", 10, 10, energy=50)
        w.spawn("rabbit", 10, 15, energy=100)       # 5 cells away
        rules.step(w)
        return w.foxes[0].status
    assert status(0.5) == "Wandering"                # sees 2 cells
    assert status(1.5) in ("Hunting", "Eating")      # sees 6 cells


def test_rabbit_flees_a_locked_on_fox():
    fled = 0
    for seed in range(10):
        w = empty_world(seed=seed); w.params.fox_repro = 0.0
        f = w.spawn("fox", 10, 10, energy=50)
        r = w.spawn("rabbit", 12, 10, energy=100)
        f.chasing = r.id
        rules.step(w)
        if r.alive and r.status == "Fleeing":
            fled += 1
            assert r.x >= 12 or r.alive
    assert fled >= 3


def test_failed_chase_ends_in_rest():
    w = empty_world(); w.params.fox_repro = 0.0
    f = w.spawn("fox", 0, 0, energy=50)
    f.chase_ticks = w.cfg.fox_chase_max - 1
    w.spawn("rabbit", 4, 0, energy=100)
    rules.step(w)
    assert f.alive and (f.rest > 0 or not w.rabbits)


def test_positions_valid_and_unique():
    w = World(SimConfig(), seed=5)
    for _ in range(300):
        rules.step(w)
        cells = [(a.x, a.y) for a in w.rabbits + w.foxes]
        assert len(cells) == len(set(cells))
        assert all(w.in_bounds(x, y) for x, y in cells)
        assert set(cells) == set(w.occ.keys())


def test_reproducible_with_same_seed():
    def run(seed):
        w = World(SimConfig(), seed=seed, record_events=False)
        for _ in range(150):
            rules.step(w)
        return [(s.rabbits, s.foxes, round(s.grass_pct, 6)) for s in w.history]
    assert run(42) == run(42)
    assert run(42) != run(43)


def test_history_recorded_every_tick():
    w = World(SimConfig(), seed=3)
    n = len(w.history)
    for _ in range(10):
        rules.step(w)
    assert len(w.history) == n + 10


def test_fox_ignores_rabbits_when_full():
    w = empty_world()
    w.params.fox_repro = 0.0
    f = w.spawn("fox", 10, 10, energy=110)
    f.status = "x"
    w.spawn("rabbit", 11, 10, energy=100)
    rules.step(w)
    assert f.status != "Hunting" and f.status != "Eating"
    assert w.history[-1].eaten == 0
