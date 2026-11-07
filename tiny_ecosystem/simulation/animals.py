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
    chasing: int = -1     # id of the rabbit being chased (for the renderer)


@dataclass
class Decor:
    """Purely decorative item; never affects the simulation."""
    kind: str             # "rock" | "bush" | "flower"
    x: int
    y: int
    fx: float             # position inside the cell, 0..1
    fy: float
    variant: int
