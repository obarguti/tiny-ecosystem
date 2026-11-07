"""Headless UI smoke test: drives the real Game object with synthetic input."""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
import config as C
from main import Game

pygame.init()
screen = pygame.display.set_mode((C.WINDOW_W, C.WINDOW_H))
g = Game(screen, C.load_config())
E = pygame.event.Event

def click(pos):
    g.handle_event(E(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    g.handle_event(E(pygame.MOUSEBUTTONUP, pos=pos, button=1))
    g.apply_ui_actions()

def frames(n, dt=1/60):
    for _ in range(n):
        g.update(dt); g.draw()

def btn(bid):
    b = [b for b in g.ui.buttons if b.id == bid][0]
    return b.rect.center

g.open_modal("intro"); frames(5)
click(g.ui.modal_buttons[0][1].center); assert g.modal is None and g.playing
frames(130)                       # ~2 sim days at 1x
assert g.world.day >= 3, g.world.day
click(btn("play")); assert not g.playing
d = g.world.day; click(btn("step")); assert g.world.day == d + 1
r0 = len(g.world.rabbits)
click(btn("tool_rabbit")); assert g.tool == "rabbit"
for x in range(100, 400, 31):
    g.handle_event(E(pygame.MOUSEBUTTONDOWN if x == 100 else pygame.MOUSEMOTION, pos=(x + 15, 200), button=1, buttons=(1,0,0), rel=(0,0)))
g.handle_event(E(pygame.MOUSEBUTTONUP, pos=(400, 200), button=1)); frames(3)
assert len(g.world.rabbits) > r0, (len(g.world.rabbits), r0)
click(btn("tool_fox")); f0 = len(g.world.foxes); click((300, 300)); assert len(g.world.foxes) == f0 + 1
click(btn("tool_grass")); click((300, 300)); frames(2)
click(btn("tool_remove")); n = len(g.world.rabbits + g.world.foxes)
a = g.world.foxes[-1]; px, py = g.renderer.feet(a); click((int(px + 15), int(py + 8 - 11))); assert len(g.world.rabbits + g.world.foxes) == n - 1
click(btn("tool_inspect")); a = g.world.rabbits[0]; px, py = g.renderer.feet(a)
click((int(px + 15), int(py + 8 - 11))); assert g.selected is not None; frames(3)
# sliders
sl = g.ui.sliders["fox_hunger"]
click((sl.rect.right - 2, sl.rect.centery)); assert g.params.fox_hunger > 1.4, g.params
click((sl.rect.x + sl.rect.w // 2, sl.rect.centery))
g.params.fox_repro = 1.7; g.params.grass_growth = 0.4; g.params.fox_hunger = 1.4
click(btn("reset_rules")); assert (g.params.fox_repro, g.params.grass_growth, g.params.fox_hunger, g.params.rabbit_repro) == (1, 1, 1, 1), g.params
click((sl.rect.right - 2, sl.rect.centery)); assert g.params.fox_hunger > 1.4
click((sl.rect.right - 2, sl.rect.centery)); assert g.params.fox_hunger == 1.0   # double-click resets one slider
sp = g.ui.sliders["speed"]; click((sp.rect.right - 1, sp.rect.centery)); assert g.speed == 8.0
click(btn("play")); frames(120); assert g.world.day > d + 5
click(btn("help")); click(btn("help")); frames(2)
click(btn("export")); assert os.path.exists(g.last_export), g.last_export
from simulation.export import verify
assert verify(open(g.last_export, encoding="utf-8").read()) is None
os.remove(g.last_export)
click(btn("restart")); assert g.world.day == 0 and not g.playing
click(btn("new")); frames(2); assert not g.playing and g.world.day == 0
# challenges
click(btn("menu")); frames(5)
c1 = [r for b, r in g.ui.modal_buttons if b == "c1"][0]; click(c1.center)
assert g.challenge is not None and not g.playing and g.run is not None
click(btn("play")); g.speed = 8.0
for _ in range(3000):
    g.update(1/30)
    if g.modal == "outcome": break
g.draw(); print("challenge outcome:", g.run.status, "day", g.world.day)
assert g.modal == "outcome"; frames(10)
for b, r in g.ui.modal_buttons:
    if b == "retry": click(r.center); break
assert g.modal is None and g.world.day == 0
# keyboard
for k in (pygame.K_SPACE, pygame.K_n, pygame.K_h, pygame.K_2, pygame.K_ESCAPE, pygame.K_PLUS, pygame.K_MINUS, pygame.K_r, pygame.K_g):
    g.handle_event(E(pygame.KEYDOWN, key=k)); frames(2)
# performance with a crowded world
g.new_world(seed=1); g.speed = 4.0; g.playing = True
t = time.time(); n = 0
while g.world.day < 120:
    g.update(1/60); g.draw(); n += 1
print("avg frame ms (incl. sim at 4x): %.1f, rabbits %d" % ((time.time() - t) / n * 1000, len(g.world.rabbits)))
print("SMOKE OK")
