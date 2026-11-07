"""Three introductory challenges. Pure logic (no Pygame)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from simulation.world import World


@dataclass(frozen=True)
class Challenge:
    id: int
    title: str
    scenario: str          # what is different about this world
    goal: str              # one-line objective
    seed: int
    rabbits: int
    foxes: int
    grass_scale: float     # 1.0 = normal regrowth
    days: int              # days to survive
    min_rabbits: int       # must stay at or above this many
    min_foxes: int
    hint: str


CHALLENGES: List[Challenge] = [
    Challenge(1, "Balance the Meadow",
              "Lots of foxes already live here. Adjust the sliders before you press Play.",
              "Keep at least 10 rabbits and 2 foxes alive for 200 days.",
              seed=1, rabbits=25, foxes=14, grass_scale=1.0, days=200, min_rabbits=10, min_foxes=2,
              hint="Too many foxes empties the meadow of rabbits. Too few babies lets populations crash."),
    Challenge(2, "The Drought",
              "Grass grows back at half the normal speed.",
              "Keep the rabbits alive for 150 days.",
              seed=1, rabbits=40, foxes=14, grass_scale=0.5, days=150, min_rabbits=1, min_foxes=0,
              hint="Hungry rabbits cannot find food. Fewer mouths, or fewer foxes, may help."),
    Challenge(3, "Too Many Foxes",
              "A large group of foxes has moved in!",
              "Stop the rabbits from dying out for 150 days.",
              seed=1, rabbits=15, foxes=35, grass_scale=1.0, days=150, min_rabbits=1, min_foxes=0,
              hint="Try adding rabbits, helping the grass grow, or making foxes less hungry."),
]


class ChallengeRun:
    """Tracks progress of one attempt. Call ``update`` after every simulation tick."""

    def __init__(self, challenge: Challenge) -> None:
        self.challenge = challenge
        self.status = "running"      # running | won | lost
        self.days = 0
        self.reason = ""

    @property
    def progress(self) -> float:
        return min(1.0, self.days / self.challenge.days)

    def update(self, world: World) -> None:
        if self.status != "running":
            return
        ch = self.challenge
        r, f = len(world.rabbits), len(world.foxes)
        if r < ch.min_rabbits:
            self.status = "lost"
            self.reason = ("All the rabbits are gone." if ch.min_rabbits == 1
                           else "There are fewer than %d rabbits." % ch.min_rabbits)
        elif f < ch.min_foxes:
            self.status = "lost"
            self.reason = "There are fewer than %d foxes." % ch.min_foxes
        else:
            self.days += 1
            if self.days >= ch.days:
                self.status = "won"

    def status_line(self, world: World) -> str:
        ch = self.challenge
        parts = ["Day %d / %d" % (self.days, ch.days), "Rabbits %d" % len(world.rabbits)]
        if ch.min_foxes:
            parts.append("Foxes %d" % len(world.foxes))
        return "  ·  ".join(parts)
