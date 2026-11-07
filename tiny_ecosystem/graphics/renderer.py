"""Draws the living world. Reads simulation state, never modifies it.

Logical animals live on grid cells; here each one gets a small *visual* record
(facing, stride, spawn time...) and is drawn at a position interpolated between
its previous and current cell.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame

import config as C
from graphics import animals as art
from graphics.environment import Environment
from simulation.animals import Animal
from simulation.world import World

N_FRAMES = 8                      # idle animation frames in sprite cache
RABBIT_K, FOX_K = 1.2, 0.92      # model-space -> pixels


@dataclass
class Vis:
    facing: int = 1
    moved: bool = False
    stride: float = 0.0
    speed: float = 0.0
    born_t: float = -99.0
    tint: int = 0


@dataclass
class Particle:
    kind: str
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: Tuple[int, int, int]
    size: float


@dataclass
class Ghost:
    kind: str
    x: float
    y: float
    facing: int
    tint: int
    t0: float
    cause: str


def _smooth(a: float) -> float:
    a = max(0.0, min(1.0, a))
    return a * a * (3 - 2 * a)


class Renderer:
    def __init__(self) -> None:
        self.cell = C.CELL
        self.ox, self.oy = C.WORLD_OFFSET
        self.time = 0.0
        self.since_tick = 99.0
        self.move_dur = 0.4
        self.env: Optional[Environment] = None
        self.env_seed = None
        self.vis: Dict[int, Vis] = {}
        self.particles: List[Particle] = []
        self.ghosts: List[Ghost] = []
        self.sprites: Dict[tuple, pygame.Surface] = {}
        self.rng = random.Random(1234)
        self.view: Optional[pygame.Surface] = None
        self.backdrop: Optional[pygame.Surface] = None
        self.vignette: Optional[pygame.Surface] = None

    # ------------------------------------------------------------ setup
    def set_world(self, world: World) -> None:
        if self.env is None or self.env_seed != world.seed:
            self.env = Environment(self.cell, world.cols, world.rows, world.seed, world.decor)
            self.env_seed = world.seed
        self.world_w, self.world_h = world.cols * self.cell, world.rows * self.cell
        self.view = pygame.Surface((self.world_w, self.world_h))
        self.vis.clear()
        self.particles.clear()
        self.ghosts.clear()
        self.since_tick = 99.0
        if self.backdrop is None:
            self.backdrop = self._make_backdrop()
            self.vignette = self._make_vignette()
        for a in world.rabbits + world.foxes:
            self._vis(a)

    def _make_backdrop(self) -> pygame.Surface:
        s = pygame.Surface((C.WORLD_AREA_W, C.WORLD_AREA_H))
        s.fill(C.BACKDROP)
        rng = random.Random(5)
        for _ in range(60):  # faint facets so the backdrop isn't flat
            x, y = rng.randrange(C.WORLD_AREA_W), rng.randrange(C.WORLD_AREA_H)
            r = rng.randrange(30, 90)
            pts = [(x + math.cos(a) * r, y + math.sin(a) * r * 0.7) for a in (0.2, 2.3, 4.4)]
            pygame.draw.polygon(s, art.shade(C.BACKDROP, rng.uniform(0.97, 1.03)), pts)
        w, h = self.world_w, self.world_h
        ox, oy = self.ox, self.oy
        # soft drop shadow + soil slab: the meadow looks like a little diorama
        sh = pygame.Surface((w + 40, h + 40), pygame.SRCALPHA)
        for i in range(8):
            pygame.draw.rect(sh, (40, 60, 30, 14), (i * 2, i * 2 + 6, w + 40 - i * 4, h + 40 - i * 4 - 6),
                             border_radius=14)
        s.blit(sh, (ox - 20, oy - 14))
        slab = 11
        soil = (122, 88, 58)
        pygame.draw.rect(s, soil, (ox, oy + h - 4, w, slab + 4))
        x = ox
        i = 0
        while x < ox + w:
            nx = min(ox + w, x + 34)
            pygame.draw.polygon(s, art.shade(soil, 0.88 if i % 2 else 1.06),
                                [(x, oy + h - 4), (nx, oy + h - 4), (nx, oy + h + slab), (x, oy + h + slab)])
            pygame.draw.polygon(s, art.shade(soil, 0.78),
                                [(x, oy + h + slab), (nx, oy + h + slab), ((x + nx) / 2, oy + h + slab - 4)])
            x, i = nx, i + 1
        return s

    def _make_vignette(self) -> pygame.Surface:
        small = pygame.Surface((24, 16), pygame.SRCALPHA)
        for y in range(16):
            for x in range(24):
                dx, dy = (x - 11.5) / 12.0, (y - 7.5) / 8.0
                d = min(1.0, math.hypot(dx, dy) / 1.25)
                small.set_at((x, y), (20, 40, 10, int(max(0.0, d - 0.55) * 120)))
        return pygame.transform.smoothscale(small, (self.world_w, self.world_h))

    def _vis(self, a: Animal) -> Vis:
        v = self.vis.get(a.id)
        if v is None:
            v = self.vis[a.id] = Vis(tint=a.id % 4, facing=1 if a.id % 2 else -1)
        return v

    # ------------------------------------------------------------ events
    def vis_pop_in(self, a: Animal) -> None:
        self.vis[a.id] = Vis(tint=a.id % 4, facing=1 if a.id % 2 else -1, born_t=self.time)
        px, py = self._cell_px(a.x, a.y)
        self.particles.append(Particle("heart", px, py - 26, 0, -18, 0.9, 0.9, (255, 214, 96), 5))

    def particles_grass(self, x: int, y: int) -> None:
        px, py = self._cell_px(x, y)
        for _ in range(8):
            self.particles.append(Particle(
                "speck", px + self.rng.uniform(-24, 24), py - 6, self.rng.uniform(-10, 10),
                self.rng.uniform(-50, -25), 0.6, 0.6, self.rng.choice([(120, 200, 80), (170, 220, 96)]), 2.4))

    def flush_events(self, world: World) -> None:
        for ev in world.pop_events():
            self._on_event(ev, world)

    def note_tick(self, world: World) -> None:
        """Call right after each simulation step."""
        self.since_tick = 0.0
        for a in world.rabbits + world.foxes:
            v = self._vis(a)
            v.moved = (a.x, a.y) != (a.px, a.py)
            if a.x > a.px:
                v.facing = 1
            elif a.x < a.px:
                v.facing = -1
        self.flush_events(world)

    def _cell_px(self, x: float, y: float) -> Tuple[float, float]:
        c = self.cell
        return (x + 0.5) * c, (y + 0.85) * c

    def _on_event(self, ev: tuple, world: World) -> None:
        kind = ev[0]
        c = self.cell
        if kind == "eat":
            px, py = self._cell_px(ev[1], ev[2])
            for _ in range(3):
                self.particles.append(Particle(
                    "speck", px + self.rng.uniform(-6, 10), py - 8, self.rng.uniform(-14, 14),
                    self.rng.uniform(-38, -18), 0.55, 0.55,
                    self.rng.choice([(120, 200, 80), (160, 214, 96), (84, 160, 66)]), self.rng.uniform(1.6, 2.6)))
        elif kind == "hunt":
            px, py = self._cell_px(ev[1], ev[2])
            for _ in range(7):
                a = self.rng.uniform(0, 2 * math.pi)
                self.particles.append(Particle(
                    "speck", px, py - 10, math.cos(a) * 34, math.sin(a) * 22 - 14, 0.45, 0.45,
                    self.rng.choice([(250, 238, 220), (236, 190, 150)]), self.rng.uniform(2, 3.2)))
        elif kind == "born":
            _, akind, child_id, cx, cy, parent_x, parent_y = ev
            px, py = self._cell_px(parent_x, parent_y)
            self.particles.append(Particle("heart", px, py - 30, 0, -22, 1.0, 1.0, (236, 90, 120), 6))
            self.vis[child_id] = Vis(tint=child_id % 4, facing=1 if child_id % 2 else -1, born_t=self.time)
        elif kind == "die":
            _, akind, aid, x, y, cause = ev
            v = self.vis.pop(aid, None)
            px, py = self._cell_px(x, y)
            # fade where it was last seen on screen
            self.ghosts.append(Ghost(akind, px, py, v.facing if v else 1, v.tint if v else 0,
                                     self.time, cause))
            if cause == "starved":
                self.particles.append(Particle("heart", px, py - 24, 0, -14, 1.0, 1.0, (160, 160, 170), 4))

    # ------------------------------------------------------------ update
    def update(self, dt: float) -> None:
        self.time += dt
        self.since_tick += dt
        for p in self.particles:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.kind == "speck":
                p.vy += 90 * dt
        self.particles = [p for p in self.particles if p.life > 0]
        self.ghosts = [g for g in self.ghosts if self.time - g.t0 < 0.8]

    # ------------------------------------------------------------ helpers
    def cell_at(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        x, y = pos[0] - self.ox, pos[1] - self.oy
        if 0 <= x < self.world_w and 0 <= y < self.world_h:
            return int(x // self.cell), int(y // self.cell)
        return None

    def _alpha(self) -> float:
        return _smooth(self.since_tick / max(0.05, self.move_dur))

    def feet(self, a: Animal) -> Tuple[float, float]:
        """Interpolated ground position in world pixels."""
        v = self.vis.get(a.id)
        t = self._alpha()
        if v is not None and v.moved and a.kind == "rabbit":
            t = _smooth((self.since_tick / max(0.05, self.move_dur) - 0.12) / 0.76)
        x0, y0 = self._cell_px(a.px, a.py)
        x1, y1 = self._cell_px(a.x, a.y)
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t

    def pick_animal(self, world: World, pos: Tuple[int, int]) -> Optional[Animal]:
        mx, my = pos[0] - self.ox, pos[1] - self.oy
        best, best_d = None, 22.0 ** 2
        for a in world.rabbits + world.foxes:
            fx, fy = self.feet(a)
            d = (fx - mx) ** 2 + ((fy - 11) - my) ** 2
            if d < best_d:
                best, best_d = a, d
        return best

    # ------------------------------------------------------------ sprites
    def _rabbit_sprite(self, tint: int, facing: int, lift: int, squash: float, head: float,
                       frame: int, k: float) -> pygame.Surface:
        key = ("r", tint, facing, lift, squash, head, frame, k)
        s = self.sprites.get(key)
        if s is None:
            s = pygame.Surface((72, 76), pygame.SRCALPHA)
            art.draw_rabbit(s, 36, 58, k, facing, 2 * math.pi * frame / N_FRAMES, lift, squash, head, tint)
            self._store(key, s)
        return s

    def _fox_sprite(self, tint: int, facing: int, stride_q: int, speed: float, hunting: bool,
                    bob: int, frame: int, k: float) -> pygame.Surface:
        key = ("f", tint, facing, stride_q, speed, hunting, bob, frame, k)
        s = self.sprites.get(key)
        if s is None:
            s = pygame.Surface((110, 70), pygame.SRCALPHA)
            art.draw_fox(s, 55, 52, k, facing, 2 * math.pi * frame / N_FRAMES, 2 * math.pi * stride_q / 12,
                         speed, hunting, tint, bob)
            self._store(key, s)
        return s

    def _store(self, key: tuple, s: pygame.Surface) -> None:
        if len(self.sprites) > 6000:
            self.sprites.clear()
        self.sprites[key] = s

    def _animal_sprite(self, a: Animal, dt: float = 0.0) -> Tuple[pygame.Surface, Tuple[int, int], float, float]:
        """-> sprite, anchor offset (feet in sprite), lift, scale"""
        v = self._vis(a)
        sc = 1.0
        age_in = self.time - v.born_t
        if age_in < 0.5:
            sc = 0.35 + 0.65 * (1 - (1 - age_in / 0.5) ** 3) * (1.0 + 0.12 * math.sin(age_in * 14))
        sc = round(sc * 20) / 20
        raw = self.since_tick / max(0.05, self.move_dur)
        if a.kind == "rabbit":
            k = RABBIT_K * sc
            frame = int(((self.time + a.id * 0.37) / 2.4) * N_FRAMES) % N_FRAMES
            lift, squash, head = 0, 0.0, 0.0
            if v.moved and raw < 1.0:
                if raw < 0.14:
                    squash = raw / 0.14
                elif raw < 0.88:
                    u = (raw - 0.14) / 0.74
                    lift = math.sin(math.pi * u) * 10.0
                    squash = -0.45 * math.sin(math.pi * u)
                else:
                    squash = 0.7 * (1 - (raw - 0.88) / 0.12)
                    if a.status == "Eating":
                        head = 0.5
            elif a.status == "Eating":
                head = 0.55 + 0.45 * math.sin(self.time * 7 + a.id) ** 2
            lift_i = int(round(lift))
            sq = round(squash * 4) / 4
            hd = round(head * 3) / 3
            spr = self._rabbit_sprite(v.tint, v.facing, lift_i, sq, hd, frame, round(k, 2))
            return spr, (36, 58), lift_i, sc
        # fox
        k = FOX_K * sc
        hunting = a.status == "Hunting"
        moving = v.moved and raw < 1.0
        target = (1.0 if hunting else 0.6) if moving else 0.0
        v.speed += (target - v.speed) * min(1.0, 0.25)
        v.stride += (0.34 if hunting else 0.22) * (1 if moving else 0.0) + (0.04 if not moving else 0)
        stride_q = int(v.stride / (2 * math.pi) * 12) % 12
        sp_q = 0.0 if v.speed < 0.15 else (0.5 if v.speed < 0.75 else 1.0)
        frame = int(((self.time + a.id * 0.31) / (1.6 if not hunting else 1.6)) * N_FRAMES) % N_FRAMES
        bob = 1 if (sp_q > 0 and stride_q % 6 in (1, 2, 3)) else 0
        spr = self._fox_sprite(v.tint, v.facing, stride_q, sp_q, hunting, bob, frame, round(k, 2))
        return spr, (55, 52), 0, sc

    # ------------------------------------------------------------ drawing
    def draw(self, screen: pygame.Surface, world: World, selected: Optional[int] = None,
             hover: Optional[Tuple[int, int]] = None, tool: str = "inspect") -> None:
        assert self.env is not None and self.view is not None and self.backdrop is not None
        view = self.view
        env = self.env
        screen.blit(self.backdrop, (0, 0))

        layer = env.grass_layer(world.grass, self.time)
        view.blit(env.ground, (0, 0))
        view.blit(layer, (0, 0))

        # hover highlight for placement tools
        if hover is not None and tool != "inspect":
            hx, hy = hover
            c = self.cell
            col = {"rabbit": (255, 255, 255), "fox": (255, 170, 80), "grass": (120, 230, 100),
                   "remove": (240, 90, 80)}.get(tool, (255, 255, 255))
            ov = pygame.Surface((c, c), pygame.SRCALPHA)
            ov.fill((*col, 70))
            pygame.draw.rect(ov, (*col, 200), ov.get_rect(), 2, border_radius=5)
            view.blit(ov, (hx * c, hy * c))

        # collect drawables, sorted by ground y so nearer things overlap farther ones
        items: List[tuple] = [(y, 0, spr, pos) for y, spr, pos in env.decor_draw_list()]
        for a in world.rabbits:
            items.append((self.feet(a)[1], 1, a))
        for a in world.foxes:
            items.append((self.feet(a)[1], 1, a))
        items.sort(key=lambda it: it[0])

        # shadows first (they lie on the ground, below every body)
        for it in items:
            if it[1] == 1:
                a = it[2]
                fx, fy = self.feet(a)
                if a.kind == "rabbit":
                    w, h = 30, 10
                else:
                    w, h = 46, 12
                view.blit(art.shadow_sprite(w, h), (fx - w / 2 + (1 if a.kind == "fox" else 0), fy - h / 2 + 1))
        for g in self.ghosts:
            pass
        sel = None
        for it in items:
            if it[1] == 0:
                view.blit(it[2], it[3])
                continue
            a = it[2]
            fx, fy = self.feet(a)
            spr, (ax, ay), lift, sc = self._animal_sprite(a)
            if selected == a.id:
                sel = (fx, fy)
                pygame.draw.ellipse(view, C.HIGHLIGHT, (fx - 20, fy - 6, 40, 14), 2)
            view.blit(spr, (fx - ax, fy - ay))
            if a.status == "Fleeing":
                ex, ey = fx + 2, fy - 50 - lift
                pygame.draw.polygon(view, (230, 70, 50), [(ex - 2, ey - 9), (ex + 2, ey - 9), (ex + 1, ey - 2), (ex - 1, ey - 2)])
                pygame.draw.rect(view, (230, 70, 50), (ex - 1, ey, 3, 3))

        for g in self.ghosts:
            age = (self.time - g.t0) / 0.8
            spr = (self._rabbit_sprite(g.tint, g.facing, 0, 0.0, 0.0, 0, RABBIT_K) if g.kind == "rabbit"
                   else self._fox_sprite(g.tint, g.facing, 0, 0.0, False, 0, 0, FOX_K)).copy()
            spr.set_alpha(int(255 * (1 - age) ** 1.5))
            ax, ay = (36, 58) if g.kind == "rabbit" else (55, 52)
            rise = age * 8
            view.blit(spr, (g.x - ax, g.y - ay - rise))

        for p in self.particles:
            f = max(0.0, p.life / p.max_life)
            if p.kind == "heart":
                art.draw_heart(view, p.x, p.y, p.size * (0.7 + 0.3 * f), p.color)
            else:
                r = max(1, int(p.size * (0.4 + 0.6 * f)))
                pygame.draw.polygon(view, p.color, [(p.x, p.y - r), (p.x + r, p.y), (p.x, p.y + r), (p.x - r, p.y)])

        view.blit(self.vignette, (0, 0))
        screen.blit(view, (self.ox, self.oy))
        if sel is not None:
            # little bobbing marker above the selected animal
            bx = self.ox + sel[0]
            by = self.oy + sel[1] - 52 + math.sin(self.time * 5) * 2
            pygame.draw.polygon(screen, C.HIGHLIGHT, [(bx - 6, by - 7), (bx + 6, by - 7), (bx, by + 1)])
            pygame.draw.polygon(screen, C.INK, [(bx - 6, by - 7), (bx + 6, by - 7), (bx, by + 1)], 1)
