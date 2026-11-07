"""Tiny Ecosystem - a low-poly wildlife simulation for students.

Run:  python main.py            (play)
      python main.py --screenshot out.png --days 60 --seed 3     (headless snapshot)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import List, Optional

import pygame

import config as C
from gameplay.challenges import CHALLENGES, Challenge, ChallengeRun
from gameplay.explain import explain
from graphics.renderer import Renderer
from simulation import rules
from simulation.export import write_export
from simulation.world import Params, World
from ui.interface import PRESETS, SPEEDS, TOOLS, Interface


class Game:
    def __init__(self, screen: pygame.Surface, cfg: C.SimConfig) -> None:
        self.screen = screen
        self.cfg = cfg
        self.renderer = Renderer()
        self.ui = Interface()
        self.params = Params()
        self.playing = False
        self.speed = 1.0
        self.tool = "inspect"
        self.selected: Optional[int] = None
        self.show_why = False
        self.toast = None                   # (message, show-until time)
        self.ended = False                  # sandbox run finished (nothing left to simulate)
        self.why: List[str] = []
        self.modal: Optional[str] = None
        self.modal_t = 0.0
        self.challenge: Optional[Challenge] = None
        self.run: Optional[ChallengeRun] = None
        self.spec = {"rabbits": cfg.start_rabbits, "foxes": cfg.start_foxes, "grass": 1.0}
        self.acc = 0.0
        self.painting = False
        self.last_paint_cell = None
        self.running = True
        self.world: World = None  # type: ignore[assignment]
        self.new_world()

    # ------------------------------------------------------------ world management
    def new_world(self, seed: Optional[int] = None, challenge: Optional[Challenge] = None) -> None:
        self.challenge = challenge
        if challenge is not None:
            self.params = Params()
            self.world = World(self.cfg, seed=challenge.seed, rabbits=challenge.rabbits, foxes=challenge.foxes,
                               params=self.params, grass_scale=challenge.grass_scale)
            self.run = ChallengeRun(challenge)
        else:
            self.run = None
            self.world = World(self.cfg, seed=seed, rabbits=self.spec["rabbits"], foxes=self.spec["foxes"],
                               params=self.params, grass_level=self.spec["grass"])
        self.renderer.set_world(self.world)
        self.selected = None
        self.ended = False
        self.acc = 0.0
        self.refresh_why()

    def restart(self) -> None:
        w = self.world
        self.new_world(seed=w.seed, challenge=self.challenge)
        self.playing = False                    # start paused so you can step from day 1

    def refresh_why(self) -> None:
        self.why = explain(self.world)

    def selected_animal(self):
        if self.selected is None:
            return None
        a = self.world.find_animal(self.selected)
        if a is None:
            self.selected = None
        return a

    # ------------------------------------------------------------ simulation
    def step_once(self) -> None:
        if self.ended:
            return
        rules.step(self.world)
        self.renderer.note_tick(self.world)
        w = self.world
        if self.run is None and not w.rabbits and not w.foxes and w.grass_pct() >= 99.999:
            self.ended = True                   # no rabbits, no foxes, and the grass grew unchecked
            self.playing = False
            self.open_modal("end")
        if self.run is not None and self.run.status == "running":
            self.run.update(self.world)
            if self.run.status != "running":
                self.playing = False
                self.open_modal("outcome")
        if self.world.day % 4 == 0:
            self.refresh_why()

    def update(self, dt: float) -> None:
        self.ui.now += dt
        if self.modal:
            self.modal_t += dt * 4
        interval = 1.0 / (self.cfg.ticks_per_second * self.speed)
        self.renderer.move_dur = min(0.45, interval * 0.92)
        if self.playing and not self.modal:
            self.acc += dt
            steps = 0
            while self.acc >= interval and steps < 6:
                self.acc -= interval
                self.step_once()
                steps += 1
                if self.modal or not self.playing:
                    break
            self.acc = min(self.acc, interval)
        self.renderer.update(dt)

    def export(self) -> None:
        path = write_export(self.world, os.path.join(C.HERE, "exports"), self.challenge)
        print("exported", path)
        self.toast = ("Saved exports/" + os.path.basename(path), self.ui.now + 6.0)
        self.last_export = path

    def open_modal(self, name: str) -> None:
        self.modal, self.modal_t = name, 0.0

    # ------------------------------------------------------------ actions
    def set_tool(self, tool: str) -> None:
        self.tool = tool
        if tool != "inspect":
            self.selected = None

    def do_button(self, bid: str) -> None:
        if bid in ("play", "step") and self.ended:
            self.open_modal("end")
        elif bid == "play":
            self.playing = not self.playing
        elif bid == "step":
            self.playing = False
            self.renderer.move_dur = 0.4
            self.step_once()
        elif bid == "restart":
            self.restart()
        elif bid == "new":
            self.new_world(challenge=None)
            self.playing = False
        elif bid.startswith("tool_"):
            self.set_tool(bid[5:])
        elif bid == "help":
            self.show_why = not self.show_why
            self.refresh_why()
        elif bid == "export":
            self.export()
        elif bid == "reset_rules":
            for k, v in vars(Params()).items():
                setattr(self.params, k, v)
        elif bid == "menu":
            self.open_modal("menu")
        elif bid == "guide":
            self.open_modal("intro")
        elif bid == "setup":
            self.playing = False
            if self.challenge is not None:
                self.new_world(challenge=None)
            self.open_modal("setup")

    def do_modal(self, bid: str) -> None:
        if self.modal == "setup":
            if bid == "start":
                self.modal = None
                self.playing = True
            elif bid == "dice":
                self.new_world()
            elif bid == "reset":
                self.spec = {"rabbits": self.cfg.start_rabbits, "foxes": self.cfg.start_foxes, "grass": 1.0}
                self.new_world(seed=self.world.seed)
            elif bid.startswith("p_"):
                for pid, _, r, f, g in PRESETS:
                    if bid[2:] == pid:
                        self.spec = {"rabbits": r, "foxes": f, "grass": g}
                self.new_world(seed=self.world.seed)
            return
        if self.modal == "intro" and bid == "start":
            self.modal = None
            self.playing = True
        elif bid == "menu":
            self.open_modal("menu")
        elif bid == "close":
            self.modal = None
        elif bid == "end_new":
            self.modal = None
            self.new_world(challenge=None)
            self.playing = False
        elif bid == "end_restart":
            self.modal = None
            self.restart()
        elif bid == "freeplay":
            self.modal = None
            if self.run is not None and self.run.status != "running":
                self.run = None                # keep this world, but as a sandbox
                self.challenge = None
            elif self.challenge is not None:
                self.new_world(challenge=None)
            self.playing = True
        elif bid.startswith("c") and bid[1:].isdigit():
            ch = CHALLENGES[int(bid[1:]) - 1]
            self.modal = None
            self.new_world(challenge=ch)
            self.playing = False                # let the student tweak the sliders first
        elif bid == "retry":
            self.modal = None
            self.restart()
            self.playing = False

    def apply_ui_actions(self) -> None:
        for act in self.ui.take_actions():
            if act[0] == "button":
                self.do_button(act[1])
            elif act[0] == "speed":
                self.speed = act[1]
            elif act[0] == "param":
                setattr(self.params, act[1], act[2])
            elif act[0] == "setup":
                self.spec[act[1]] = act[2]
                self.new_world(seed=self.world.seed)
            elif act[0] == "modal":
                self.do_modal(act[1])

    # ------------------------------------------------------------ world interaction
    def world_click(self, pos, dragging: bool = False) -> None:
        cell = self.renderer.cell_at(pos)
        if cell is None:
            return
        w = self.world
        if self.tool == "inspect":
            if not dragging:
                a = self.renderer.pick_animal(w, pos)
                self.selected = a.id if a else None
            return
        if dragging and cell == self.last_paint_cell:
            return
        self.last_paint_cell = cell
        x, y = cell
        if self.tool in ("rabbit", "fox"):
            a = w.apply_tool(self.tool, x, y, dragging)
            if a is not None:
                self.renderer.vis_pop_in(a)
        elif self.tool == "grass":
            w.apply_tool("grass", x, y)
            self.renderer.particles_grass(x, y)
        elif self.tool == "remove":
            a = self.renderer.pick_animal(w, pos) or w.animal_at(x, y)
            w.apply_tool("remove", x, y, False, a.id if a is not None else None)
            if a is not None:
                self.renderer.flush_events(w)

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
            return
        if ev.type == pygame.KEYDOWN:
            self.handle_key(ev)
            return
        consumed = self.ui.handle_event(ev, self)
        self.apply_ui_actions()
        if consumed or self.modal:
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.painting = True
            self.last_paint_cell = None
            self.world_click(ev.pos)
        elif ev.type == pygame.MOUSEMOTION and self.painting and self.tool in ("rabbit", "fox", "grass"):
            self.world_click(ev.pos, dragging=True)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.painting = False
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self.set_tool("inspect")

    def handle_key(self, ev: pygame.event.Event) -> None:
        k = ev.key
        if self.modal:
            if k == pygame.K_ESCAPE and self.modal != "outcome":
                self.modal = None
            elif k in (pygame.K_RETURN, pygame.K_SPACE) and self.modal == "intro":
                self.do_modal("start")
            return
        if k == pygame.K_SPACE:
            self.do_button("play")
        elif k in (pygame.K_n, pygame.K_RIGHT, pygame.K_PERIOD):
            self.do_button("step")
        elif k == pygame.K_r:
            self.do_button("restart")
        elif k == pygame.K_g:
            self.do_button("new")
        elif k == pygame.K_h:
            self.do_button("help")
        elif k == pygame.K_c:
            self.do_button("menu")
        elif k == pygame.K_i:
            self.do_button("guide")
        elif k == pygame.K_s:
            self.do_button("setup")
        elif k == pygame.K_e:
            self.do_button("export")
        elif k == pygame.K_ESCAPE:
            self.set_tool("inspect")
            self.selected = None
        elif pygame.K_1 <= k <= pygame.K_5:
            self.set_tool(TOOLS[k - pygame.K_1][0])
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed = SPEEDS[min(len(SPEEDS) - 1, SPEEDS.index(self.speed) + 1)]
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed = SPEEDS[max(0, SPEEDS.index(self.speed) - 1)]
        elif k == pygame.K_F12:
            path = time.strftime("screenshot_%Y%m%d_%H%M%S.png")
            pygame.image.save(self.screen, path)

    # ------------------------------------------------------------ drawing
    def draw(self) -> None:
        mouse = pygame.mouse.get_pos()
        hover = self.renderer.cell_at(mouse) if (not self.modal and mouse[0] < C.WORLD_AREA_W
                                                  and mouse[1] < C.WORLD_AREA_H) else None
        self.renderer.draw(self.screen, self.world, self.selected, hover, self.tool)
        self.ui.draw_world_overlays(self.screen, self)
        self.ui.draw_graph(self.screen, self, mouse)
        self.ui.draw_sidebar(self.screen, self, mouse)
        self.ui.draw_modal(self.screen, self, mouse)
        self.ui.draw_tooltip(self.screen, self, mouse)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tiny Ecosystem")
    ap.add_argument("--seed", type=int, default=None, help="world seed")
    ap.add_argument("--screenshot", metavar="PNG", help="run headless, save a screenshot and exit")
    ap.add_argument("--days", type=int, default=0, help="days to simulate before the screenshot")
    ap.add_argument("--no-intro", action="store_true", help="skip the welcome screen")
    ap.add_argument("--challenge", type=int, choices=[1, 2, 3], help="start a challenge")
    ap.add_argument("--modal", choices=["intro", "menu", "outcome", "setup"], help="(screenshot) show a dialog")
    ap.add_argument("--tool", choices=[t[0] for t in TOOLS], help="(screenshot) active tool")
    ap.add_argument("--select", type=int, default=None, help="(screenshot) select the animal with this id")
    args = ap.parse_args(argv)

    if args.screenshot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_caption("Tiny Ecosystem")
    flags = pygame.SCALED | pygame.RESIZABLE if not args.screenshot else 0
    screen = pygame.display.set_mode((C.WINDOW_W, C.WINDOW_H), flags)
    clock = pygame.time.Clock()
    game = Game(screen, C.load_config())
    if args.seed is not None:
        game.new_world(seed=args.seed)
    if args.challenge:
        game.new_world(challenge=CHALLENGES[args.challenge - 1])
    if not args.no_intro and not args.screenshot and not args.challenge:
        game.open_modal("intro")
    else:
        game.playing = bool(args.screenshot) is False and not args.challenge

    if args.screenshot:
        for _ in range(args.days):
            game.step_once()
            game.renderer.update(0.12)
        if args.tool:
            game.set_tool(args.tool)
        if args.select is not None:
            game.selected = args.select
        game.show_why = True
        game.refresh_why()
        if args.modal:
            game.open_modal(args.modal)
            game.modal_t = 5
        for _ in range(12):
            game.renderer.update(1 / 30)
        game.draw()
        pygame.image.save(screen, args.screenshot)
        print("saved", args.screenshot)
        return 0

    while game.running:
        dt = min(clock.tick(C.FPS) / 1000.0, 0.05)
        for ev in pygame.event.get():
            game.handle_event(ev)
        game.apply_ui_actions()
        game.update(dt)
        game.draw()
        pygame.display.flip()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
