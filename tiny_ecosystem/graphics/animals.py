"""Procedural low-poly rabbits and foxes.

Shapes are defined once as point lists in a small "model space" (feet at the
origin, +x = facing direction, -y = up). Each frame they are scaled, flipped
and nudged by animation parameters. Nothing here touches simulation state.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Sequence, Tuple

import pygame

Pt = Tuple[float, float]
Color = Tuple[int, int, int]


def shade(c: Color, f: float) -> Color:
    """Multiply brightness (f<1 darker, f>1 lighter)."""
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))))


def mix(a: Color, b: Color, t: float) -> Color:
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def _rot(pts: Iterable[Pt], pivot: Pt, ang: float) -> List[Pt]:
    c, s = math.cos(ang), math.sin(ang)
    px, py = pivot
    return [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in pts]


def _shift(pts: Iterable[Pt], dx: float, dy: float) -> List[Pt]:
    return [(x + dx, y + dy) for x, y in pts]


class _Painter:
    """Draws model-space polygons onto a surface with scale / flip / squash."""

    def __init__(self, surf: pygame.Surface, ox: float, oy: float, k: float, facing: int,
                 sx: float = 1.0, sy: float = 1.0) -> None:
        self.s, self.ox, self.oy, self.k, self.f, self.sx, self.sy = surf, ox, oy, k, facing, sx, sy

    def tf(self, pts: Sequence[Pt]) -> List[Pt]:
        return [(self.ox + self.f * x * self.k * self.sx, self.oy + y * self.k * self.sy)
                for x, y in pts]

    def poly(self, pts: Sequence[Pt], color: Color) -> None:
        pygame.draw.polygon(self.s, color, self.tf(pts))

    def dot(self, x: float, y: float, r: float, color: Color) -> None:
        (px, py), = self.tf([(x, y)])
        pygame.draw.circle(self.s, color, (round(px), round(py)), max(1, round(r * self.k)))


# ------------------------------------------------------------------ rabbit
RABBIT_FUR = [(236, 218, 184), (222, 196, 158), (206, 178, 140), (242, 232, 210)]
_EYE = (46, 36, 34)
_PINK = (232, 168, 158)

_R_BODY = [(-12, -4), (-13, -10), (-9, -16), (-2, -18), (5, -16), (9, -11), (9, -5), (5, -1), (-6, -1)]
_R_BELLY = [(-12, -4), (9, -5), (5, -1), (-6, -1)]
_R_BACK = [(-9, -16), (-2, -18), (5, -16), (1, -12), (-6, -12)]
_R_HAUNCH = [(-12, -4), (-13, -10), (-8, -13), (-3, -10), (-3, -3), (-8, -1)]
_R_TAIL = [(-13, -9), (-17, -11), (-16, -6), (-13, -5)]
_R_HEAD = [(4, -17), (10, -18), (15, -14), (15, -9), (10, -6), (4, -9)]
_R_CHEEK = [(10, -6), (15, -9), (15, -14), (11, -11)]
_R_NOSE = [(14, -12), (17, -11), (14, -9)]
_R_EAR_FAR = [(3, -17), (1, -26), (4, -27), (7, -18)]
_R_EAR_NEAR = [(6, -17), (5, -28), (8, -29), (11, -18)]
_R_EAR_IN = [(7, -18), (6.5, -26), (8, -27), (10, -19)]
_R_FOOT_B = [(-9, -1), (-2, -1), (-1, 1), (-11, 1)]
_R_FOOT_F = [(3, -2), (8, -2), (10, 0.5), (3, 0.5)]


def draw_rabbit(surf: pygame.Surface, x: float, y: float, k: float, facing: int, t: float,
                hop: float = 0.0, squash: float = 0.0, head_down: float = 0.0,
                tint: int = 0, ear_flop: float = 0.0) -> None:
    """(x, y) is the ground point under the rabbit. hop = lift in px. squash -1..1.
    ``t`` is an animation phase in radians (periodic with 2*pi)."""
    fur = RABBIT_FUR[tint % len(RABBIT_FUR)]
    dark, light = shade(fur, 0.84), shade(fur, 1.08)
    p = _Painter(surf, x, y - hop, k, facing, 1.0 + 0.16 * squash, 1.0 - 0.18 * squash)
    breathe = math.sin(t) * 0.35
    hd = head_down
    # feet first (behind body)
    p.poly(_R_FOOT_B, shade(fur, 0.7))
    # tail + body
    p.poly(_R_TAIL, (250, 246, 238))
    p.poly(_R_BODY, fur)
    p.poly(_R_BELLY, dark)
    p.poly(_R_BACK, light)
    p.poly(_R_HAUNCH, shade(fur, 0.93))
    # head group (dips when eating, ears wiggle / flop)
    hdx, hdy = 2.0 * hd, 5.5 * hd + breathe * 0.5
    wig = math.sin(t + 1.3) * 0.05 + ear_flop
    head = _shift(_R_HEAD, hdx, hdy)
    pivot = (6 + hdx, -17 + hdy)
    p.poly(_rot(_shift(_R_EAR_FAR, hdx, hdy), pivot, -wig - 0.1 - 0.5 * hd), shade(fur, 0.78))
    p.poly(head, light)
    p.poly(_shift(_R_CHEEK, hdx, hdy), fur)
    p.poly(_rot(_shift(_R_EAR_NEAR, hdx, hdy), pivot, wig - 0.5 * hd), fur)
    p.poly(_rot(_shift(_R_EAR_IN, hdx, hdy), pivot, wig - 0.5 * hd), _PINK)
    p.poly(_shift(_R_NOSE, hdx, hdy), _PINK)
    p.dot(11 + hdx, -13.5 + hdy, 1.5, _EYE)
    p.poly(_R_FOOT_F, shade(fur, 0.7))


# --------------------------------------------------------------------- fox
FOX_ORANGE = (219, 104, 44)
FOX_RUST = (172, 70, 36)
FOX_CREAM = (248, 238, 222)
FOX_DARK = (52, 40, 38)

_F_BODY = [(-13, -10), (-7, -17), (6, -18), (13, -13), (13, -7), (8, -5), (-8, -5)]
_F_BACK = [(-7, -17), (6, -18), (13, -13), (2, -13), (-8, -12)]
_F_BELLY = [(-6, -7), (8, -8), (11, -6), (8, -4.5), (-8, -4.5)]
_F_CHEST = [(7, -13), (13, -13), (13, -7), (8, -5), (6, -8)]
_F_HEAD = [(11, -19), (17, -21), (27, -14.5), (27, -13), (17, -8), (11, -9)]
_F_MUZZLE = [(17, -13), (27, -13.5), (27, -13), (21, -8.5), (17, -8)]
_F_CHEEK = [(11, -12), (18, -13), (19, -8), (12, -8)]
_F_NOSE = [(25.5, -15.5), (28, -14), (25.5, -12.5)]
_F_EAR_NEAR = [(14, -20), (15, -30), (20, -21)]
_F_EAR_FAR = [(10, -19), (9, -28), (14, -21)]
_F_EAR_IN = [(15, -22), (15.5, -27.5), (18, -22)]
_F_TAIL = [(-12, -12), (-19, -18), (-28, -16), (-32, -10), (-27, -5.5), (-14, -7)]
_F_TAIL_LIGHT = [(-12, -12), (-19, -18), (-28, -16), (-17, -11)]
_F_TAIL_TIP = [(-27, -5.5), (-32, -10), (-28, -16), (-25, -14), (-24, -8)]


def draw_fox(surf: pygame.Surface, x: float, y: float, k: float, facing: int, t: float,
             stride: float = 0.0, speed: float = 0.0, hunting: bool = False,
             tint: int = 0, bob: float = 0.0) -> None:
    """stride = leg phase in radians, speed 0..1 how much the legs swing."""
    body = FOX_ORANGE if tint % 2 == 0 else (226, 116, 52)
    rust = shade(body, 0.8)
    p = _Painter(surf, x, y - bob, k, facing)
    sway = math.sin(t * (3 if hunting else 1)) * (0.14 if hunting else 0.2)
    # tail (behind)
    tail_pivot = (-12.0, -11.0)
    tail = lambda pts: _rot(pts, tail_pivot, sway + (0.15 if hunting else -0.05))
    p.poly(tail(_F_TAIL), body)
    p.poly(tail(_F_TAIL_LIGHT), shade(body, 1.1))
    p.poly(tail(_F_TAIL_TIP), FOX_CREAM)
    # far legs
    legs = [(-8.0, 0.0, True), (7.0, math.pi, True), (-4.0, math.pi, False), (10.0, 0.0, False)]
    for hx, ph, far in legs:
        if far:
            _fox_leg(p, hx, stride + ph, speed, rust, shade(FOX_DARK, 0.9))
    p.poly(_F_BODY, body)
    p.poly(_F_BACK, shade(body, 1.1))
    p.poly(_F_BELLY, FOX_CREAM)
    p.poly(_F_CHEST, FOX_CREAM)
    for hx, ph, far in legs:
        if not far:
            _fox_leg(p, hx, stride + ph, speed, body, FOX_DARK)
    # head (slight bob; lowered when hunting)
    hx_, hy_ = (1.5, 1.5) if hunting else (0.0, 0.0)
    hy_ += math.sin(t * 2) * 0.5
    p.poly(_shift(_F_EAR_FAR, hx_, hy_), rust)
    p.poly(_shift(_F_HEAD, hx_, hy_), body)
    p.poly(_shift(_F_CHEEK, hx_, hy_), FOX_CREAM)
    p.poly(_shift(_F_MUZZLE, hx_, hy_), FOX_CREAM)
    p.poly(_shift(_F_EAR_NEAR, hx_, hy_), body)
    p.poly(_shift(_F_EAR_IN, hx_, hy_), FOX_DARK)
    p.poly(_shift(_F_NOSE, hx_, hy_), FOX_DARK)
    p.dot(20 + hx_, -15 + hy_, 1.4, FOX_DARK)


def _fox_leg(p: _Painter, hx: float, phase: float, speed: float, col: Color, foot: Color) -> None:
    swing = math.sin(phase) * 4.5 * speed
    lift = max(0.0, math.cos(phase)) * 3.0 * speed
    fx, fy = hx + swing, -lift
    p.poly([(hx - 1.8, -8), (hx + 1.8, -8), (fx + 1.5, fy - 2), (fx - 1.5, fy - 2)], col)
    p.poly([(fx - 1.8, fy - 2.5), (fx + 3.2, fy - 2.5), (fx + 3.2, fy), (fx - 1.8, fy)], foot)


# ----------------------------------------------------------------- shadows
_shadow_cache: Dict[Tuple[int, int], pygame.Surface] = {}


def shadow_sprite(w: int, h: int) -> pygame.Surface:
    """A soft elliptical ground shadow (cached)."""
    key = (w, h)
    s = _shadow_cache.get(key)
    if s is None:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = 5
        for i in range(steps):
            f = 1 - i / steps
            r = pygame.Rect(0, 0, int(w * f), int(h * f))
            r.center = (w // 2, h // 2)
            pygame.draw.ellipse(s, (30, 50, 20, 20 + i * 5), r)
        _shadow_cache[key] = s
    return s


def draw_heart(surf: pygame.Surface, x: float, y: float, size: float, color: Color = (236, 90, 120)) -> None:
    r = size / 2
    pygame.draw.circle(surf, color, (round(x - r * 0.9), round(y - r * 0.5)), max(1, round(r)))
    pygame.draw.circle(surf, color, (round(x + r * 0.9), round(y - r * 0.5)), max(1, round(r)))
    pygame.draw.polygon(surf, color, [(x - r * 1.85, y - r * 0.2), (x + r * 1.85, y - r * 0.2), (x, y + r * 1.9)])
