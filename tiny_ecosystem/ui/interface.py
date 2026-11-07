"""Buttons, sliders, panels, overlays and modal dialogs.

The interface never changes the simulation. It reads the ``game`` object and
queues *actions* (tuples) that ``main.Game`` carries out.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

import config as C
from gameplay.challenges import CHALLENGES
from graphics import animals as art
from ui.graph import draw_graph

SPEEDS = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

PRESETS = [
    ("balanced", "Balanced", 35, 7, 1.0),
    ("foxparty", "Fox Party", 25, 20, 1.0),
    ("bunnyboom", "Bunny Boom", 80, 3, 1.0),
    ("sparse", "Sparse Meadow", 40, 5, 0.3),
]

PARAMS = [
    # attribute, title, low label, high label, min, max
    ("rabbit_repro", "Rabbit Babies", "Few", "Many", 0.0, 2.0),
    ("fox_repro", "Fox Babies", "Few", "Many", 0.0, 2.0),
    ("grass_growth", "Grass Growth", "Slow", "Fast", 0.25, 2.0),
    ("fox_hunger", "Fox Hunger", "Low", "High", 0.5, 1.5),
]

TOOLS = [
    ("inspect", "Inspect", "Click an animal to see how it is doing.", "1"),
    ("rabbit", "Add Rabbits", "Click or drag on the meadow to add rabbits.", "2"),
    ("fox", "Add Foxes", "Click or drag on the meadow to add foxes.", "3"),
    ("grass", "Add Grass", "Click or drag to make grass grow.", "4"),
    ("remove", "Remove", "Click an animal to remove it from the meadow.", "5"),
]

STATUS_COLORS = {
    "Eating": (110, 180, 80), "Hunting": (222, 90, 60), "Searching for food": (230, 180, 60),
    "Wandering": (150, 150, 160), "Reproducing": (236, 90, 120), "Starving": (176, 70, 50),
}


class Fonts:
    def __init__(self) -> None:
        self.cache: Dict[Tuple[int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        k = (size, bold)
        f = self.cache.get(k)
        if f is None:
            f = pygame.font.SysFont("segoeui,tahoma,arial,helvetica", size, bold=bold)
            self.cache[k] = f
        return f


def wrap(text: str, font: pygame.font.Font, width: int) -> List[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if font.size(trial)[0] <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class Button:
    def __init__(self, bid: str, rect: pygame.Rect, label: str, tip: str = "", icon=None) -> None:
        self.id, self.rect, self.label, self.tip, self.icon = bid, rect, label, tip, icon


class Slider:
    def __init__(self, sid: str, rect: pygame.Rect, vmin: float, vmax: float, steps=None, integer=False) -> None:
        self.id, self.rect, self.vmin, self.vmax, self.steps, self.integer = sid, rect, vmin, vmax, steps, integer
        self.value = vmin

    def frac(self) -> float:
        if self.steps:
            return self.steps.index(self.value) / (len(self.steps) - 1) if self.value in self.steps else 0.5
        return (self.value - self.vmin) / (self.vmax - self.vmin)

    def from_x(self, x: int) -> float:
        f = max(0.0, min(1.0, (x - self.rect.x) / self.rect.w))
        if self.steps:
            return self.steps[round(f * (len(self.steps) - 1))]
        v = self.vmin + f * (self.vmax - self.vmin)
        if self.integer:
            return int(round(v))
        if abs(v - 1.0) < 0.05:
            v = 1.0                      # snap to the default
        return round(v, 2)


class Interface:
    def __init__(self) -> None:
        self.fonts = Fonts()
        self.actions: List[tuple] = []
        self.pressed: Optional[str] = None
        self.hover_id: Optional[str] = None
        self.hover_since = 0.0
        self.dragging: Optional[Slider] = None
        self.modal_buttons: List[Tuple[str, pygame.Rect]] = []
        self.modal_sliders: Dict[str, Slider] = {}
        self.now = 0.0
        self.icons = self._make_icons()

        x0 = C.WORLD_AREA_W + 16
        w = C.SIDEBAR_W - 32
        self.x0, self.w = x0, w
        bw = (w - 3 * 8) // 4
        self.buttons: List[Button] = [
            Button("play", pygame.Rect(x0, 176, bw, 40), "Play", "Start or pause time (Space)"),
            Button("step", pygame.Rect(x0 + (bw + 8), 176, bw, 40), "Step", "Advance a single day (N)"),
            Button("restart", pygame.Rect(x0 + 2 * (bw + 8), 176, bw, 40), "Restart",
                   "Start this same world again (R)"),
            Button("new", pygame.Rect(x0 + 3 * (bw + 8), 176, bw, 40), "New", "Make a brand new world (G)"),
        ]
        tw = (w - 8) // 2
        for i, (tid, label, tip, key) in enumerate(TOOLS):
            r = pygame.Rect(x0 + (i % 2) * (tw + 8), 316 + (i // 2) * 40, tw, 34)
            self.buttons.append(Button("tool_" + tid, r, label, tip + "  (" + key + ")", icon=tid))
        self.buttons.append(Button("why", pygame.Rect(x0 + (tw + 8), 396, tw, 34), "Why?",
                                   "Explain what has been changing lately (H)"))
        b3 = (w - 16) // 3
        for i, (bid, label, tip) in enumerate((("setup", "Setup", "Choose how many animals to start with (S)"),
                                               ("menu", "Challenges", "Try a science experiment (C)"),
                                               ("help", "Help", "Show the instructions again (I)"))):
            self.buttons.append(Button(bid, pygame.Rect(x0 + i * (b3 + 8), 714, b3, 40), label, tip))
        self.sliders: Dict[str, Slider] = {"speed": Slider("speed", pygame.Rect(x0 + 4, 252, w - 8, 12), 0.5, 8.0, SPEEDS)}
        for i, (pid, title, lo, hi, vmin, vmax) in enumerate(PARAMS):
            self.sliders[pid] = Slider(pid, pygame.Rect(x0 + 4, 474 + i * 58 + 18, w - 8, 12), vmin, vmax)

    # ------------------------------------------------------------ icons
    def _make_icons(self) -> Dict[str, pygame.Surface]:
        icons = {}
        s = pygame.Surface((34, 28), pygame.SRCALPHA)
        art.draw_rabbit(s, 18, 25, 0.78, 1, 0.0)
        icons["rabbit"] = s
        s = pygame.Surface((38, 28), pygame.SRCALPHA)
        art.draw_fox(s, 22, 25, 0.58, 1, 0.0)
        icons["fox"] = s
        s = pygame.Surface((26, 28), pygame.SRCALPHA)
        for i, (bx, h) in enumerate(((6, 14), (12, 22), (18, 16))):
            pygame.draw.polygon(s, (70, 150, 66), [(bx - 3, 26), (bx, 26), (bx + (i - 1) * 2, 26 - h)])
            pygame.draw.polygon(s, (120, 200, 84), [(bx, 26), (bx + 3, 26), (bx + (i - 1) * 2, 26 - h)])
        icons["grass"] = s
        s = pygame.Surface((26, 28), pygame.SRCALPHA)
        pygame.draw.polygon(s, (60, 54, 46), [(7, 3), (7, 22), (12, 17), (16, 25), (19, 23), (15, 16), (21, 15)])
        pygame.draw.polygon(s, (255, 252, 244), [(9, 8), (9, 17), (12, 14), (17, 14)])
        icons["inspect"] = s
        s = pygame.Surface((26, 28), pygame.SRCALPHA)
        pygame.draw.polygon(s, (200, 70, 60), [(6, 7), (10, 5), (21, 20), (17, 23)])
        pygame.draw.polygon(s, (200, 70, 60), [(21, 7), (17, 5), (6, 20), (10, 23)])
        icons["remove"] = s
        return icons

    # ------------------------------------------------------------ events
    def handle_event(self, ev: pygame.event.Event, game) -> bool:
        """Returns True if the interface consumed the event."""
        if game.modal:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for sl in self.modal_sliders.values():
                    if sl.rect.inflate(16, 22).collidepoint(ev.pos):
                        self.dragging = sl
                        self._set_slider(sl, ev.pos[0])
                        return True
            if ev.type == pygame.MOUSEMOTION and self.dragging:
                self._set_slider(self.dragging, ev.pos[0])
                return True
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                if self.dragging:
                    self.dragging = None
                    return True
                for bid, rect in self.modal_buttons:
                    if rect.collidepoint(ev.pos):
                        self.actions.append(("modal", bid))
                        return True
            return ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if ev.pos[0] < C.WORLD_AREA_W and ev.pos[1] < C.WORLD_AREA_H:
                return False
            for sid, sl in self.sliders.items():
                if sl.rect.inflate(16, 22).collidepoint(ev.pos):
                    self.dragging = sl
                    self._set_slider(sl, ev.pos[0])
                    return True
            for b in self.buttons:
                if b.rect.collidepoint(ev.pos):
                    self.pressed = b.id
                    return True
            return ev.pos[0] >= C.WORLD_AREA_W or ev.pos[1] >= C.WORLD_AREA_H
        if ev.type == pygame.MOUSEMOTION and self.dragging:
            self._set_slider(self.dragging, ev.pos[0])
            return True
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            consumed = False
            if self.dragging:
                self.dragging = None
                consumed = True
            if self.pressed:
                for b in self.buttons:
                    if b.id == self.pressed and b.rect.collidepoint(ev.pos):
                        self.actions.append(("button", b.id))
                self.pressed = None
                consumed = True
            return consumed
        return False

    def _set_slider(self, sl: Slider, x: int) -> None:
        v = sl.from_x(x)
        sl.value = v
        if sl.id == "speed":
            self.actions.append(("speed", v))
        elif sl.id.startswith("s_"):
            self.actions.append(("setup", sl.id[2:], v))
        else:
            self.actions.append(("param", sl.id, v))

    def take_actions(self) -> List[tuple]:
        a, self.actions = self.actions, []
        return a

    # ------------------------------------------------------------ drawing helpers
    def text(self, surf, s, size, color, pos, bold=False, anchor="topleft"):
        img = self.fonts.get(size, bold).render(s, True, color)
        r = img.get_rect(**{anchor: pos})
        surf.blit(img, r)
        return r

    def panel(self, surf, rect, fill=C.PANEL, border=C.PANEL_LINE, radius=10, shadow=True):
        if shadow:
            pygame.draw.rect(surf, (0, 0, 0, 0) if False else (176, 168, 146), rect.move(0, 3), border_radius=radius)
        pygame.draw.rect(surf, fill, rect, border_radius=radius)
        pygame.draw.rect(surf, border, rect, 1, border_radius=radius)

    def _draw_button(self, surf, b: Button, active=False, mouse=(0, 0), label=None, accent=False):
        hover = b.rect.collidepoint(mouse)
        down = self.pressed == b.id
        r = b.rect.move(0, 2 if down else 0)
        base = C.ACCENT if (active or accent) else (255, 250, 238) if hover else C.PANEL_DARK
        pygame.draw.rect(surf, art.shade(base, 0.8), r.move(0, 3 if not down else 1), border_radius=9)
        pygame.draw.rect(surf, base, r, border_radius=9)
        if active:
            pygame.draw.rect(surf, C.HIGHLIGHT, r, 3, border_radius=9)
        col = (255, 255, 255) if (active or accent) else C.INK
        txt = label or b.label
        font = self.fonts.get(14, True)
        icon = self.icons.get(b.icon) if b.icon else None
        tw = font.size(txt)[0] + (30 if icon else 0)
        x = r.centerx - tw // 2
        if icon:
            ic = icon
            if ic.get_height() > 26:
                ic = pygame.transform.smoothscale(ic, (ic.get_width() * 26 // ic.get_height(), 26))
            surf.blit(ic, (x, r.centery - ic.get_height() // 2))
            x += 30
        surf.blit(font.render(txt, True, col), (x, r.centery - font.get_height() // 2))

    # ------------------------------------------------------------ sidebar
    def draw_sidebar(self, surf: pygame.Surface, game, mouse) -> None:
        sb = pygame.Rect(C.WORLD_AREA_W, 0, C.SIDEBAR_W, C.WINDOW_H)
        pygame.draw.rect(surf, C.PANEL, sb)
        pygame.draw.line(surf, C.PANEL_LINE, sb.topleft, sb.bottomleft, 2)
        x0, w = self.x0, self.w
        world = game.world

        self.text(surf, "Tiny Ecosystem", 26, C.INK, (x0, 12), bold=True)
        self.text(surf, "Day %d   ·   world #%d" % (world.day, world.seed), 14, C.INK_SOFT, (x0, 48))

        # live counters
        rows = [("Rabbits", str(len(world.rabbits)), C.COL_RABBIT, "rabbit"),
                ("Foxes", str(len(world.foxes)), C.COL_FOX, "fox"),
                ("Grass", "%d%%" % round(world.grass_pct()), C.COL_GRASS, "grass")]
        for i, (name, val, col, icon) in enumerate(rows):
            y = 74 + i * 33
            self.panel(surf, pygame.Rect(x0, y, w, 29), fill=(255, 252, 244), radius=8, shadow=False)
            ic = self.icons[icon]
            surf.blit(pygame.transform.smoothscale(ic, (ic.get_width() * 22 // ic.get_height(), 22)), (x0 + 8, y + 4))
            self.text(surf, name, 15, C.INK, (x0 + 52, y + 5), bold=True)
            if name == "Grass":
                bar = pygame.Rect(x0 + 112, y + 9, 110, 11)
                pygame.draw.rect(surf, (226, 220, 202), bar, border_radius=5)
                pygame.draw.rect(surf, col, (bar.x, bar.y, max(4, int(bar.w * world.grass_pct() / 100)), bar.h),
                                 border_radius=5)
            self.text(surf, val, 18, col if name != "Foxes" else (200, 96, 30), (x0 + w - 10, y + 4), bold=True,
                      anchor="topright")

        # controls
        for b in self.buttons[:4]:
            if b.id == "play":
                self._draw_button(surf, b, mouse=mouse, label="Pause" if game.playing else "Play",
                                  accent=not game.playing)
            else:
                self._draw_button(surf, b, mouse=mouse)

        # speed
        sp = self.sliders["speed"]
        sp.value = game.speed
        self.text(surf, "Speed", 14, C.INK, (x0, 232), bold=True)
        self.text(surf, ("%gx" % game.speed), 14, C.ACCENT_DARK, (x0 + w, 232), bold=True, anchor="topright")
        self._draw_slider(surf, sp, ticks=True)

        # tools
        self.text(surf, "Tools", 14, C.INK, (x0, 292), bold=True)
        for b in self.buttons[4:9]:
            self._draw_button(surf, b, active=(game.tool == b.id[5:]), mouse=mouse)
        why = self.buttons[9]
        self._draw_button(surf, why, active=game.show_why, mouse=mouse)

        # parameters
        self.text(surf, "Change the rules", 14, C.INK, (x0, 446), bold=True)
        self.text(surf, "(changes apply right away)", 12, C.INK_SOFT, (x0 + w, 448), anchor="topright")
        for i, (pid, title, lo, hi, vmin, vmax) in enumerate(PARAMS):
            y = 474 + i * 58
            sl = self.sliders[pid]
            sl.value = getattr(game.params, pid)
            self.text(surf, title, 14, C.INK, (x0, y), bold=True)
            self.text(surf, "×%.2f" % sl.value if sl.value != 1.0 else "normal", 12, C.INK_SOFT, (x0 + w, y + 2),
                      anchor="topright")
            self._draw_slider(surf, sl)
            self.text(surf, lo, 12, C.INK_SOFT, (x0 + 2, y + 36))
            self.text(surf, hi, 12, C.INK_SOFT, (x0 + w - 2, y + 36), anchor="topright")

        for b in self.buttons[10:]:
            self._draw_button(surf, b, mouse=mouse)
        self.text(surf, "Space: play/pause   N: step   H: why", 12, C.INK_SOFT, (x0 + w // 2, 770), anchor="midtop")

    def _draw_slider(self, surf, sl: Slider, ticks=False) -> None:
        r = sl.rect
        track = pygame.Rect(r.x, r.centery - 4, r.w, 8)
        pygame.draw.rect(surf, (214, 205, 184), track, border_radius=4)
        kx = r.x + int(sl.frac() * r.w)
        pygame.draw.rect(surf, C.ACCENT, (track.x, track.y, kx - track.x, track.h), border_radius=4)
        if ticks and sl.steps:
            for i, v in enumerate(sl.steps):
                tx = r.x + int(i / (len(sl.steps) - 1) * r.w)
                pygame.draw.line(surf, C.PANEL_LINE, (tx, r.centery + 7), (tx, r.centery + 11), 2)
        else:
            dx = r.x + int(((1.0 - sl.vmin) / (sl.vmax - sl.vmin)) * r.w)
            pygame.draw.line(surf, C.INK_SOFT, (dx, r.centery + 6), (dx, r.centery + 11), 1)
        down = self.dragging is sl
        pygame.draw.circle(surf, art.shade(C.ACCENT_DARK, 0.7), (kx, r.centery + 2), 11 if down else 10)
        pygame.draw.circle(surf, (255, 252, 244), (kx, r.centery), 11 if down else 10)
        pygame.draw.circle(surf, C.ACCENT_DARK, (kx, r.centery), 11 if down else 10, 3)

    # ------------------------------------------------------------ world overlays
    def draw_world_overlays(self, surf: pygame.Surface, game) -> None:
        world = game.world
        # challenge banner
        run = game.run
        if run is not None:
            ch = run.challenge
            rect = pygame.Rect(0, 0, 640, 74)
            rect.midtop = (C.WORLD_AREA_W // 2, 16)
            self.panel(surf, rect, fill=(*C.PANEL,), radius=12)
            self.text(surf, "Challenge %d: %s" % (ch.id, ch.title), 16, C.INK, (rect.x + 16, rect.y + 8), bold=True)
            self.text(surf, ch.goal, 13, C.INK_SOFT, (rect.x + 16, rect.y + 30))
            bar = pygame.Rect(rect.x + 16, rect.y + 54, rect.w - 280, 10)
            pygame.draw.rect(surf, (226, 220, 202), bar, border_radius=5)
            pygame.draw.rect(surf, C.ACCENT, (bar.x, bar.y, max(6, int(bar.w * run.progress)), bar.h), border_radius=5)
            self.text(surf, run.status_line(world), 12, C.INK, (bar.right + 12, rect.y + 50))

        # tool hint
        if game.tool != "inspect" and not game.modal:
            tip = [t for t in TOOLS if t[0] == game.tool][0][2]
            font = self.fonts.get(14, True)
            img = font.render(tip, True, (255, 255, 255))
            rect = img.get_rect()
            rect.inflate_ip(28, 14)
            rect.midbottom = (C.WORLD_AREA_W // 2, C.WORLD_AREA_H - 18)
            pygame.draw.rect(surf, (62, 54, 46), rect, border_radius=16)
            surf.blit(img, img.get_rect(center=rect.center))

        # "Why?" card
        if game.show_why:
            f = self.fonts.get(13)
            blocks = [wrap(m, f, 252) for m in game.why]
            height = 44 + sum(len(b) * 17 + 8 for b in blocks)
            rect = pygame.Rect(0, 0, 300, height)
            rect.topright = (C.WORLD_AREA_W - 24, 18 if run is None else 100)
            self.panel(surf, rect, radius=12)
            self.text(surf, "Why is this happening?", 15, C.INK, (rect.x + 14, rect.y + 10), bold=True)
            y = rect.y + 38
            for lines in blocks:
                pygame.draw.circle(surf, C.ACCENT, (rect.x + 20, y + 8), 4)
                for ln in lines:
                    surf.blit(f.render(ln, True, C.INK), (rect.x + 32, y))
                    y += 17
                y += 8

        # inspector card
        a = game.selected_animal()
        if a is not None:
            self._draw_inspector(surf, game, a)

    def _draw_inspector(self, surf, game, a) -> None:
        cfg = game.world.cfg
        fx, fy = game.renderer.feet(a)
        ax, ay = fx + game.renderer.ox, fy + game.renderer.oy
        rect = pygame.Rect(0, 0, 204, 98)
        rect.topleft = (ax + 30, ay - 78)
        if rect.right > C.WORLD_AREA_W - 8:
            rect.right = ax - 30
        rect.clamp_ip(pygame.Rect(8, 8, C.WORLD_AREA_W - 16, C.WORLD_AREA_H - 16))
        self.panel(surf, rect, radius=10)
        name = "Rabbit" if a.kind == "rabbit" else "Fox"
        col = C.COL_RABBIT if a.kind == "rabbit" else (200, 96, 30)
        self.text(surf, "%s #%d" % (name, a.id), 16, col, (rect.x + 12, rect.y + 8), bold=True)
        mx = cfg.rabbit_max_age if a.kind == "rabbit" else cfg.fox_max_age
        self.text(surf, "Age: %d days" % a.age, 13, C.INK, (rect.x + 12, rect.y + 32))
        maxe = cfg.rabbit_max_energy if a.kind == "rabbit" else cfg.fox_max_energy
        self.text(surf, "Energy: %d / %d" % (max(0, round(a.energy)), maxe), 13, C.INK, (rect.x + 12, rect.y + 50))
        bar = pygame.Rect(rect.x + 120, rect.y + 54, 72, 8)
        pygame.draw.rect(surf, (226, 220, 202), bar, border_radius=4)
        frac = max(0.0, min(1.0, a.energy / maxe))
        pygame.draw.rect(surf, (110, 180, 80) if frac > 0.3 else (214, 90, 60), (bar.x, bar.y, max(3, int(bar.w * frac)), bar.h),
                         border_radius=4)
        sc = STATUS_COLORS.get(a.status, (150, 150, 160))
        if a.status == "Reproducing":
            art.draw_heart(surf, rect.x + 20, rect.y + 79, 7, sc)
        elif a.status == "Hunting":
            pygame.draw.polygon(surf, sc, [(rect.x + 14, rect.y + 79), (rect.x + 26, rect.y + 73), (rect.x + 26, rect.y + 85)])
        else:
            pygame.draw.circle(surf, sc, (rect.x + 20, rect.y + 79), 6)
        self.text(surf, a.status, 13, C.INK, (rect.x + 34, rect.y + 71), bold=True)

    # ------------------------------------------------------------ graph
    def draw_graph(self, surf, game) -> None:
        draw_graph(surf, pygame.Rect(0, C.WORLD_AREA_H, C.WORLD_AREA_W, C.GRAPH_H), game.world.history, self.fonts)

    # ------------------------------------------------------------ tooltip
    def draw_tooltip(self, surf, game, mouse) -> None:
        hit = None
        if not game.modal:
            for b in self.buttons:
                if b.rect.collidepoint(mouse):
                    hit = (b.id, b.tip)
            for pid, title, lo, hi, vmin, vmax in PARAMS:
                sl = self.sliders[pid]
                if sl.rect.inflate(16, 24).collidepoint(mouse):
                    hit = (pid, "%s: %s to %s. Now ×%.2f (1.00 = normal)" % (title, lo.lower(), hi.lower(), sl.value))
            if self.sliders["speed"].rect.inflate(16, 24).collidepoint(mouse):
                hit = ("speed", "How fast days pass (+ / - keys)")
        if hit is None or hit[0] != self.hover_id:
            self.hover_id = hit[0] if hit else None
            self.hover_since = self.now
        if hit and hit[1] and self.now - self.hover_since > 0.45:
            f = self.fonts.get(13)
            lines = wrap(hit[1], f, 240)
            w = max(f.size(l)[0] for l in lines) + 20
            h = len(lines) * 17 + 12
            r = pygame.Rect(mouse[0] - w - 8, mouse[1] + 14, w, h)
            if r.left < 6:
                r.left = 6
            if r.bottom > C.WINDOW_H - 4:
                r.bottom = mouse[1] - 8
            pygame.draw.rect(surf, (62, 54, 46), r, border_radius=8)
            for i, l in enumerate(lines):
                surf.blit(f.render(l, True, (255, 250, 238)), (r.x + 10, r.y + 6 + i * 17))

    # ------------------------------------------------------------ modals
    def draw_modal(self, surf: pygame.Surface, game, mouse) -> None:
        self.modal_buttons = []
        self.modal_sliders = {}
        if not game.modal:
            return
        t = min(1.0, game.modal_t)
        ease = 1 - (1 - t) ** 3
        dim = pygame.Surface((C.WINDOW_W, C.WINDOW_H), pygame.SRCALPHA)
        dim.fill((40, 34, 28, int(130 * ease)))
        surf.blit(dim, (0, 0))
        layer = pygame.Surface((C.WINDOW_W, C.WINDOW_H), pygame.SRCALPHA)
        if game.modal == "intro":
            self._modal_intro(layer, game, mouse)
        elif game.modal == "menu":
            self._modal_menu(layer, game, mouse)
        elif game.modal == "outcome":
            self._modal_outcome(layer, game, mouse)
        elif game.modal == "setup":
            self._modal_setup(layer, game, mouse)
        layer.set_alpha(int(255 * ease))
        surf.blit(layer, (0, int((1 - ease) * 24)))

    def _modal_button(self, surf, bid, rect, label, mouse, accent=False):
        b = Button("m_" + bid, rect, label)
        self._draw_button(surf, b, mouse=mouse, accent=accent)
        self.modal_buttons.append((bid, rect))

    def _modal_frame(self, surf, w, h, title, title_color=C.INK):
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (C.WINDOW_W // 2 - 40, C.WINDOW_H // 2 - 10)
        self.panel(surf, rect, radius=16)
        self.text(surf, title, 28, title_color, (rect.centerx, rect.y + 22), bold=True, anchor="midtop")
        return rect

    def _modal_intro(self, surf, game, mouse) -> None:
        rect = self._modal_frame(surf, 640, 470, "Welcome to Tiny Ecosystem!")
        lines = [
            ("Rabbits eat grass.  Foxes eat rabbits.", True),
            ("Everybody needs energy to stay alive and have babies.", False),
            ("", False),
            ("Press Play and watch the meadow come alive.", False),
            ("Click an animal to see how it is doing.", False),
            ("Use the tools to add animals or grass to the meadow.", False),
            ("Use the sliders to change the rules of nature.", False),
            ("", False),
            ("Then ask: what would happen if I added five more foxes?", True),
        ]
        y = rect.y + 80
        for s, bold in lines:
            if s:
                self.text(surf, s, 18, C.INK if bold else C.INK_SOFT, (rect.centerx, y), bold=bold, anchor="midtop")
            y += 30
        # little mascots
        spr = pygame.Surface((90, 70), pygame.SRCALPHA)
        art.draw_rabbit(spr, 40, 60, 1.7, 1, 0.0)
        surf.blit(spr, (rect.x + 36, rect.y + 6))
        spr = pygame.Surface((120, 70), pygame.SRCALPHA)
        art.draw_fox(spr, 60, 60, 1.4, -1, 0.0)
        surf.blit(spr, (rect.right - 150, rect.y + 6))
        self._modal_button(surf, "start", pygame.Rect(rect.centerx - 230, rect.bottom - 70, 220, 46), "Let's go!", mouse, True)
        self._modal_button(surf, "menu", pygame.Rect(rect.centerx + 10, rect.bottom - 70, 220, 46), "Challenges", mouse)

    def _modal_menu(self, surf, game, mouse) -> None:
        rect = self._modal_frame(surf, 700, 560, "Challenges")
        self.text(surf, "Little experiments to try. The sandbox is always free to play.", 15, C.INK_SOFT,
                  (rect.centerx, rect.y + 62), anchor="midtop")
        for i, ch in enumerate(CHALLENGES):
            card = pygame.Rect(rect.x + 28, rect.y + 96 + i * 104, rect.w - 56, 94)
            self.panel(surf, card, fill=(255, 252, 244), radius=12, shadow=False)
            self.text(surf, "%d. %s" % (ch.id, ch.title), 18, C.INK, (card.x + 16, card.y + 10), bold=True)
            self.text(surf, ch.scenario, 13, C.INK_SOFT, (card.x + 16, card.y + 36))
            self.text(surf, "Goal: " + ch.goal, 13, C.INK, (card.x + 16, card.y + 58), bold=True)
            self._modal_button(surf, "c%d" % ch.id, pygame.Rect(card.right - 116, card.y + 24, 100, 40), "Start", mouse, True)
        self._modal_button(surf, "freeplay", pygame.Rect(rect.centerx - 230, rect.bottom - 64, 220, 44), "Free play (sandbox)", mouse)
        self._modal_button(surf, "close", pygame.Rect(rect.centerx + 10, rect.bottom - 64, 220, 44), "Back", mouse)

    def _modal_outcome(self, surf, game, mouse) -> None:
        run = game.run
        won = run.status == "won"
        rect = self._modal_frame(surf, 600, 360, "Challenge complete!" if won else "Not this time...",
                                 C.ACCENT_DARK if won else (176, 80, 50))
        ch = run.challenge
        self.text(surf, ch.title, 18, C.INK, (rect.centerx, rect.y + 72), bold=True, anchor="midtop")
        if won:
            msg = "You kept the meadow alive for %d days. Nicely balanced!" % ch.days
        else:
            msg = "%s It happened on day %d." % (run.reason, game.world.day)
        y = rect.y + 112
        f = self.fonts.get(17)
        for ln in wrap(msg, f, rect.w - 80):
            surf.blit(f.render(ln, True, C.INK), f.render(ln, True, C.INK).get_rect(midtop=(rect.centerx, y)))
            y += 26
        if not won:
            y += 8
            f = self.fonts.get(14)
            for ln in wrap("Hint: " + ch.hint, f, rect.w - 80):
                surf.blit(f.render(ln, True, C.INK_SOFT), f.render(ln, True, C.INK_SOFT).get_rect(midtop=(rect.centerx, y)))
                y += 20
        self._modal_button(surf, "retry", pygame.Rect(rect.centerx - 270, rect.bottom - 70, 170, 46), "Try again", mouse, True)
        self._modal_button(surf, "menu", pygame.Rect(rect.centerx - 85, rect.bottom - 70, 170, 46), "Challenges", mouse)
        self._modal_button(surf, "freeplay", pygame.Rect(rect.centerx + 100, rect.bottom - 70, 170, 46), "Keep playing", mouse)

    def _modal_setup(self, surf, game, mouse) -> None:
        rect = self._modal_frame(surf, 640, 520, "Set up your meadow")
        self.text(surf, "Move the sliders and watch the meadow change behind this window.", 15, C.INK_SOFT,
                  (rect.centerx, rect.y + 62), anchor="midtop")
        pw = (rect.w - 56 - 3 * 8) // 4
        for i, (pid, label, r, f, g) in enumerate(PRESETS):
            self._modal_button(surf, "p_" + pid, pygame.Rect(rect.x + 28 + i * (pw + 8), rect.y + 96, pw, 38), label, mouse)
        spec = game.spec
        rows = [("rabbits", "Rabbits at the start", 0, 100, True, str(spec["rabbits"]), "None", "Lots"),
                ("foxes", "Foxes at the start", 0, 30, True, str(spec["foxes"]), "None", "Lots"),
                ("grass", "Grass at the start", 0.1, 1.0, False, "%d%%" % round(spec["grass"] * 100), "Sparse", "Lush")]
        for i, (sid, title, lo, hi, integer, shown, lot, hit) in enumerate(rows):
            y = rect.y + 160 + i * 74
            sl = Slider("s_" + sid, pygame.Rect(rect.x + 36, y + 32, rect.w - 72, 12), lo, hi, integer=integer)
            sl.value = spec[sid]
            self.modal_sliders[sl.id] = sl
            self.text(surf, title, 16, C.INK, (rect.x + 36, y), bold=True)
            self.text(surf, shown, 18, C.ACCENT_DARK, (rect.right - 36, y), bold=True, anchor="topright")
            self._draw_slider(surf, sl)
            self.text(surf, lot, 12, C.INK_SOFT, (rect.x + 36, y + 48))
            self.text(surf, hit, 12, C.INK_SOFT, (rect.right - 36, y + 48), anchor="topright")
        y = rect.y + 384
        self.text(surf, "World #%d" % game.world.seed, 15, C.INK, (rect.x + 36, y + 11), bold=True)
        self._modal_button(surf, "dice", pygame.Rect(rect.x + 150, y, 200, 38), "Roll a new world", mouse)
        self._modal_button(surf, "reset", pygame.Rect(rect.centerx - 230, rect.bottom - 70, 220, 46), "Reset to defaults", mouse)
        self._modal_button(surf, "start", pygame.Rect(rect.centerx + 10, rect.bottom - 70, 220, 46), "Start!", mouse, True)
