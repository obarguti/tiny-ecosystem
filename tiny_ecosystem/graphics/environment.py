"""Terrain, grass, flowers, rocks and bushes - all drawn as flat-shaded polygons.

* The faceted ground is pre-rendered once per "grass bucket" (soil -> lush meadow);
  the visible ground is stitched together from those buckets and only the cells whose
  bucket changed are re-blitted.
* Grass tufts are tiny pre-rendered sprites (one per level / variant / sway frame).
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Sequence, Tuple

import pygame

from graphics.animals import mix, shade
from simulation.animals import Decor

Color = Tuple[int, int, int]

BUCKET_COLORS: List[Color] = [
    (150, 116, 72),    # bare soil
    (157, 134, 78),
    (160, 158, 86),    # dry olive
    (142, 168, 84),
    (128, 171, 80),    # meadow
    (114, 167, 78),
]
LEVEL_COLORS: List[Color] = [(176, 188, 92), (124, 194, 80), (90, 170, 72), (58, 144, 66)]
SWAY_FRAMES = 16
SWAY_FPS = 8
TUFT_W, TUFT_H = 24, 28


def grass_bucket(g: float) -> int:
    return min(5, int(g / 17.0))


def grass_level(g: float) -> int:
    """Visual level from the plan: 0-20 soil, 21-50 short, 51-80 medium, 81-100 tall."""
    if g <= 20:
        return 0
    if g <= 50:
        return 1
    if g <= 80:
        return 2
    return 3


class Environment:
    def __init__(self, cell: int, cols: int, rows: int, seed: int, decor: Sequence[Decor]) -> None:
        self.cell, self.cols, self.rows = cell, cols, rows
        self.size = (cols * cell, rows * cell)
        rng = random.Random(seed * 31 + 7)
        self.buckets = self._make_buckets(rng)
        self.ground = pygame.Surface(self.size)
        self.cell_bucket = [[-1] * cols for _ in range(rows)]
        self.cell_level = [[-1] * cols for _ in range(rows)]

        # per-cell tuft layout: 4 positions, a colour variant and a sway phase
        self.tufts: List[List[List[Tuple[float, float, int, int]]]] = []
        for y in range(rows):
            row = []
            for x in range(cols):
                spots = []
                for i in range(4):
                    qx, qy = (i % 2), (i // 2)
                    ox = (0.05 + 0.5 * qx + rng.uniform(0.08, 0.40)) * cell
                    oy = (0.22 + 0.5 * qy + rng.uniform(0.0, 0.40)) * cell
                    spots.append((ox, oy, rng.randrange(3), rng.randrange(SWAY_FRAMES)))
                spots.sort(key=lambda s: s[1])
                row.append(spots)
            self.tufts.append(row)

        self.decor = list(decor)
        self.flowers = [d for d in self.decor if d.kind == "flower"]
        self.flower_colors = [rng.choice([(255, 250, 240), (244, 150, 180), (255, 214, 90),
                                          (176, 150, 226), (255, 170, 110)]) for _ in self.flowers]
        self._tuft_cache: Dict[Tuple[int, int, int], pygame.Surface] = {}
        self.layer = pygame.Surface(self.size, pygame.SRCALPHA)
        self._layer_key = None
        self.decor_sprites: Dict[Tuple[str, int], pygame.Surface] = {}
        for kind in ("rock", "bush"):
            for v in range(4):
                self.decor_sprites[(kind, v)] = self._make_decor_sprite(kind, v, rng)

    # ------------------------------------------------------------ ground
    def _make_buckets(self, rng: random.Random) -> List[pygame.Surface]:
        c, cols, rows = self.cell, self.cols, self.rows
        # jittered vertex mesh -> faceted, continuous-looking ground
        verts = [[(x * c + (0 if x in (0, cols) else rng.uniform(-0.3, 0.3) * c),
                   y * c + (0 if y in (0, rows) else rng.uniform(-0.3, 0.3) * c))
                  for x in range(cols + 1)] for y in range(rows + 1)]
        tris: List[Tuple[List[Tuple[float, float]], float]] = []
        for y in range(rows):
            for x in range(cols):
                a, b, d, e = verts[y][x], verts[y][x + 1], verts[y + 1][x], verts[y + 1][x + 1]
                low = 1.0 + 0.045 * math.sin(x * 0.45 + 1.3) * math.cos(y * 0.55) \
                    + 0.03 * math.sin(x * 0.17 - y * 0.23)
                pair = ([a, b, d], [b, e, d]) if rng.random() < 0.5 else ([a, b, e], [a, e, d])
                for tri in pair:
                    tris.append((tri, low * rng.uniform(0.95, 1.05)))
        surfaces = []
        for col in BUCKET_COLORS:
            s = pygame.Surface(self.size)
            s.fill(col)
            for tri, f in tris:
                pygame.draw.polygon(s, shade(col, f), tri)
            surfaces.append(s)
        return surfaces

    def update_ground(self, grass: Sequence[Sequence[float]]) -> bool:
        """Refresh changed cells. Returns True if anything changed."""
        c = self.cell
        changed = False
        for y in range(self.rows):
            row, bk, lv = grass[y], self.cell_bucket[y], self.cell_level[y]
            for x in range(self.cols):
                g = row[x]
                b = grass_bucket(g)
                if b != bk[x]:
                    bk[x] = b
                    r = pygame.Rect(x * c, y * c, c, c)
                    self.ground.blit(self.buckets[b], r, r)
                    changed = True
                lvl = grass_level(g)
                if lvl != lv[x]:
                    lv[x] = lvl
                    changed = True
        return changed

    # ------------------------------------------------------------ tufts
    def tuft(self, level: int, variant: int, frame: int) -> pygame.Surface:
        key = (level, variant, frame)
        s = self._tuft_cache.get(key)
        if s is not None:
            return s
        s = pygame.Surface((TUFT_W, TUFT_H), pygame.SRCALPHA)
        rng = random.Random(level * 100 + variant)
        n = (2, 4, 5, 7)[level]
        height = (5.0, 9.5, 15.0, 21.0)[level]
        width = (2.4, 3.2, 3.8, 4.4)[level]
        base = LEVEL_COLORS[level]
        base = mix(base, (170, 190, 70), 0.22) if variant == 1 else \
            mix(base, (60, 150, 110), 0.2) if variant == 2 else base
        cx, by = TUFT_W / 2, TUFT_H - 2
        phase = 2 * math.pi * frame / SWAY_FRAMES
        order = sorted(range(n), key=lambda i: abs(i - (n - 1) / 2), reverse=True)
        blades = []
        for i in range(n):
            blades.append((rng.uniform(0.7, 1.0), rng.uniform(-1.0, 1.0)))
        for i in order:
            hf, lean0 = blades[i]
            h = height * hf
            off = i - (n - 1) / 2
            bx = cx + off * (width * 0.9)
            lean = off * 1.3 + lean0 * 1.2
            tipx = bx + lean + math.sin(phase + i * 0.5) * (0.5 + 0.13 * h)
            tipy = by - h
            col = shade(base, 0.9 + 0.1 * hf)
            pygame.draw.polygon(s, shade(col, 0.82), [(bx - width / 2, by), (bx, by), (tipx, tipy)])
            pygame.draw.polygon(s, shade(col, 1.12), [(bx, by), (bx + width / 2, by), (tipx, tipy)])
        self._tuft_cache[key] = s
        return s

    def grass_layer(self, grass: Sequence[Sequence[float]], t: float) -> pygame.Surface:
        sway = int(t * SWAY_FPS)
        dirty = self.update_ground(grass)
        key = sway
        if not dirty and key == self._layer_key:
            return self.layer
        self._layer_key = key
        layer, c = self.layer, self.cell
        layer.fill((0, 0, 0, 0))
        for y in range(self.rows):
            lv_row = self.cell_level[y]
            for x in range(self.cols):
                lvl = lv_row[x]
                cnt = (1, 2, 3, 3)[lvl]
                bx, by = x * c, y * c
                for ox, oy, var, ph in self.tufts[y][x][:cnt]:
                    sp = self.tuft(lvl, var, (sway + ph) % SWAY_FRAMES)
                    layer.blit(sp, (bx + ox - TUFT_W / 2, by + oy - TUFT_H + 3))
        # flowers only grow where grass is present
        for d, col in zip(self.flowers, self.flower_colors):
            if grass[d.y][d.x] > 30:
                self._draw_flower(layer, (d.x + d.fx) * c, (d.y + d.fy) * c, col, sway + d.x * 3 + d.y)
        return layer

    @staticmethod
    def _draw_flower(surf: pygame.Surface, x: float, y: float, col: Color, tick: int) -> None:
        lean = math.sin(tick * 2 * math.pi / SWAY_FRAMES) * 1.2
        hx, hy = x + lean, y - 9
        pygame.draw.polygon(surf, (60, 124, 58), [(x - 0.8, y), (x + 0.8, y), (hx + 0.5, hy), (hx - 0.5, hy)])
        pygame.draw.polygon(surf, (70, 140, 62), [(x, y - 3), (x + 4, y - 6), (x + 1, y - 2)])
        for i in range(5):
            a = i * 2 * math.pi / 5 + 0.3
            tip = (hx + math.cos(a) * 4.2, hy + math.sin(a) * 3.6)
            l = (hx + math.cos(a - 0.7) * 2, hy + math.sin(a - 0.7) * 2)
            r = (hx + math.cos(a + 0.7) * 2, hy + math.sin(a + 0.7) * 2)
            pygame.draw.polygon(surf, col if i % 2 else shade(col, 0.92), [l, tip, r])
        pygame.draw.polygon(surf, (250, 196, 60), [(hx - 1.4, hy), (hx, hy - 1.4), (hx + 1.4, hy), (hx, hy + 1.4)])

    # ------------------------------------------------------------ decor
    def _make_decor_sprite(self, kind: str, variant: int, rng: random.Random) -> pygame.Surface:
        r = random.Random(variant * 977 + (1 if kind == "rock" else 2))
        if kind == "rock":
            w, h = 38, 30
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (30, 40, 20, 60), (3, h - 11, w - 6, 9))
            sc = 0.8 + 0.12 * variant
            cx, base = w / 2, h - 6
            pts = [(-13, 0), (-15, -7), (-8, -15), (2, -17), (11, -12), (15, -4), (11, 1), (-4, 3)]
            pts = [(cx + px * sc + r.uniform(-1, 1), base + py * sc + r.uniform(-1, 1)) for px, py in pts]
            gray = (136, 144, 156)
            pygame.draw.polygon(s, shade(gray, 0.78), pts)
            top = [pts[1], pts[2], pts[3], pts[4], (cx + 1, base - 8 * sc)]
            pygame.draw.polygon(s, shade(gray, 1.12), top)
            pygame.draw.polygon(s, gray, [pts[4], pts[5], pts[6], pts[7], (cx + 1, base - 8 * sc)])
            pygame.draw.polygon(s, shade(gray, 0.62), [pts[0], pts[1], (cx + 1, base - 8 * sc), pts[7]])
            pygame.draw.polygon(s, shade(gray, 1.28), [pts[2], pts[3], (cx - 2, base - 11 * sc)])
            # a little moss
            pygame.draw.polygon(s, (104, 150, 82), [pts[0], pts[1], (pts[1][0] + 4, pts[1][1] + 3), (pts[0][0] + 3, pts[0][1] - 1)])
            return s
        w, h = 46, 36
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (30, 50, 20, 60), (3, h - 13, w - 6, 11))
        cx, base = w / 2, h - 6
        dark, mid, light = (44, 112, 62), (62, 140, 72), (96, 176, 88)
        lumps = [(-11, -7, 9), (10, -7, 9), (0, -12, 11), (-3, -4, 9)]
        for i, (lx, ly, lr) in enumerate(lumps):
            lr *= 0.88 + 0.07 * variant
            ring = []
            for k in range(7):
                a = k * 2 * math.pi / 7 + i
                ring.append((cx + lx + math.cos(a) * lr, base + ly + math.sin(a) * lr * 0.85))
            pygame.draw.polygon(s, dark if i % 2 == 0 else mid, ring)
            cxm, cym = cx + lx, base + ly
            pygame.draw.polygon(s, light if i % 2 == 0 else shade(light, 1.05),
                                [ring[5], ring[6], ring[0], (cxm, cym)])
            pygame.draw.polygon(s, shade(mid, 0.8), [ring[2], ring[3], ring[4], (cxm, cym)])
        if variant % 2 == 0:  # berries
            for bx, by in ((-9, -9), (6, -14), (11, -6), (-1, -4)):
                pygame.draw.circle(s, (214, 64, 74), (round(cx + bx), round(base + by)), 2)
        return s

    def decor_draw_list(self) -> List[Tuple[float, pygame.Surface, Tuple[float, float]]]:
        """(sort_y, sprite, topleft) in world pixels for rocks & bushes."""
        out = []
        c = self.cell
        for d in self.decor:
            if d.kind == "flower":
                continue
            spr = self.decor_sprites[(d.kind, d.variant)]
            gx, gy = (d.x + d.fx) * c, (d.y + d.fy) * c
            out.append((gy, spr, (gx - spr.get_width() / 2, gy - spr.get_height() + 6)))
        return out
