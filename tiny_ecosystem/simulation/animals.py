"""Lightweight animal data objects (no Pygame, no drawing)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Animal:
    id: int
    x: int
    y: int
    energy: float
    age: int = 0
    status: str = "Wandering"
    px: int = -1          # position at the start of the last tick (for smooth drawing)
    py: int = -1
    alive: bool = True
    cooldown: int = 0     # ticks until this animal may breed again

    kind = "animal"

    def __post_init__(self) -> None:
        if self.px < 0:
            self.px, self.py = self.x, self.y


@dataclass
class Rabbit(Animal):
    kind = "rabbit"


@dataclass
class Fox(Animal):
    kind = "fox"
    chasing: int = -1     # id of the rabbit this fox is locked onto
    chase_ticks: int = 0
    rest: int = 0


@dataclass
class Decor:
    """Purely decorative item; never affects the simulation."""
    kind: str             # "rock" | "bush" | "flower"
    x: int
    y: int
    fx: float             # position inside the cell, 0..1
    fy: float
    variant: int
