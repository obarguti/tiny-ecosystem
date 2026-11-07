"""Population graph drawn with plain Pygame lines (last 300 ticks)."""
from __future__ import annotations

from typing import Sequence, Tuple

import pygame

import config as C
from simulation.world import Stat


def _nice_max(v: float) -> int:
    for step in (10, 20, 40, 60, 100, 150, 200, 300, 400, 600):
        if v <= step:
            return step
    return int(v / 100 + 1) * 100


def draw_graph(surf: pygame.Surface, rect: pygame.Rect, history: Sequence[Stat], fonts) -> None:
    pygame.draw.rect(surf, C.PANEL, rect)
    pygame.draw.line(surf, C.PANEL_LINE, rect.topleft, rect.topright, 2)
    small, label = fonts.get(12), fonts.get(13, True)

    # plot area (room for left/right axis labels, title row and day labels)
    plot = pygame.Rect(rect.x + 44, rect.y + 34, rect.w - 44 - 52, rect.h - 34 - 24)
    data = list(history[-C.HISTORY_VISIBLE:])

    # title + legend
    surf.blit(label.render("Population over time", True, C.INK), (rect.x + 16, rect.y + 9))
    lx = rect.x + 200
    for name, col in (("Rabbits (left scale)", C.COL_RABBIT), ("Foxes (right scale)", C.COL_FOX),
                      ("Grass (% of meadow)", C.COL_GRASS)):
        pygame.draw.rect(surf, col, (lx, rect.y + 13, 14, 6), border_radius=3)
        t = small.render(name, True, C.INK_SOFT)
        surf.blit(t, (lx + 20, rect.y + 9))
        lx += 20 + t.get_width() + 22

    pygame.draw.rect(surf, (255, 252, 244), plot, border_radius=4)
    max_r = _nice_max(max([s.rabbits for s in data] + [5]) * 1.1)
    max_f = _nice_max(max([s.foxes for s in data] + [3]) * 1.25) if max([s.foxes for s in data] + [0]) > 8 else \
        max(5, int(max([s.foxes for s in data] + [3]) * 1.3) + 1)

    for i in range(5):
        y = plot.bottom - i * plot.h / 4
        pygame.draw.line(surf, (228, 220, 202), (plot.x, y), (plot.right, y), 1)
        r_txt = small.render(str(int(max_r * i / 4)), True, C.COL_RABBIT)
        f_txt = small.render(str(int(round(max_f * i / 4))), True, (196, 96, 30))
        surf.blit(r_txt, (plot.x - 6 - r_txt.get_width(), y - 7))
        surf.blit(f_txt, (plot.right + 6, y - 7))

    if len(data) >= 2:
        n = C.HISTORY_VISIBLE
        dx = plot.w / (n - 1)
        x0 = plot.x

        def pts(vals, vmax):
            return [(x0 + i * dx, plot.bottom - min(1.0, v / vmax) * plot.h) for i, v in enumerate(vals)]

        gp = pts([s.grass_pct for s in data], 100.0)
        fill = pygame.Surface(plot.size, pygame.SRCALPHA)
        poly = [(x - plot.x, y - plot.y) for x, y in gp] + [(gp[-1][0] - plot.x, plot.h), (gp[0][0] - plot.x, plot.h)]
        pygame.draw.polygon(fill, (*C.COL_GRASS, 40), poly)
        surf.blit(fill, plot.topleft)
        pygame.draw.lines(surf, C.COL_GRASS, False, gp, 2)
        pygame.draw.lines(surf, C.COL_RABBIT, False, pts([s.rabbits for s in data], max_r), 3)
        fp = pts([s.foxes for s in data], max_f)
        pygame.draw.lines(surf, C.COL_FOX, False, fp, 3)
        # current-value dots
        for p, col in ((gp[-1], C.COL_GRASS), (pts([data[-1].rabbits], max_r)[0], C.COL_RABBIT), (fp[-1], C.COL_FOX)):
            pygame.draw.circle(surf, col, (round(x0 + (len(data) - 1) * dx), round(p[1])), 4)
        d0, d1 = data[0].day, data[-1].day
        surf.blit(small.render("Day %d" % d0, True, C.INK_SOFT), (plot.x, plot.bottom + 5))
        t = small.render("Day %d" % d1, True, C.INK_SOFT)
        surf.blit(t, (plot.right - t.get_width(), plot.bottom + 5))
    else:
        t = small.render("Press Play to start the story of your meadow...", True, C.INK_SOFT)
        surf.blit(t, (plot.centerx - t.get_width() // 2, plot.centery - 8))
