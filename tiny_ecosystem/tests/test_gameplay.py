import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SimConfig
from gameplay.challenges import CHALLENGES, ChallengeRun
from gameplay.explain import explain
from simulation import rules
from simulation.world import Params, World


def play(ch, **p):
    w = World(SimConfig(), seed=ch.seed, rabbits=ch.rabbits, foxes=ch.foxes,
              params=Params(**p), grass_scale=ch.grass_scale, record_events=False)
    run = ChallengeRun(ch)
    while run.status == "running":
        rules.step(w)
        run.update(w)
    return run


def test_three_challenges_exist_and_fail_by_default():
    assert len(CHALLENGES) == 3
    for ch in CHALLENGES:
        run = play(ch)
        assert run.status == "lost", ch.title      # the default settings should need adjusting


def test_each_challenge_can_be_won_with_sensible_tweaks():
    tweaks = [dict(fox_hunger=0.5), dict(fox_hunger=0.5, fox_repro=0.3), dict(rabbit_repro=1.5), dict(grass_growth=2.0),
              dict(fox_repro=0.0, fox_hunger=0.7), dict(rabbit_repro=1.5, grass_growth=1.5, fox_hunger=0.7)]
    for ch in CHALLENGES:
        outcomes = [play(ch, **t).status for t in tweaks]
        assert "won" in outcomes, (ch.title, outcomes)


def test_challenge_progress_and_status():
    ch = CHALLENGES[1]
    w = World(SimConfig(), seed=2, record_events=False)
    run = ChallengeRun(ch)
    run.update(w)
    assert run.days == 1 and run.status == "running"
    for a in list(w.rabbits):
        w.remove(a, "removed")
    run.update(w)
    assert run.status == "lost" and run.reason


def test_explain_returns_short_messages():
    w = World(SimConfig(), seed=4, record_events=False)
    assert explain(w)
    for _ in range(60):
        rules.step(w)
    msgs = explain(w)
    assert 1 <= len(msgs) <= 3 and all(isinstance(m, str) and m for m in msgs)
