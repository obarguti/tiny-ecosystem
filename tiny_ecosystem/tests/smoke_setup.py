import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame, config as C
from main import Game
pygame.init(); screen = pygame.display.set_mode((C.WINDOW_W, C.WINDOW_H))
g = Game(screen, C.load_config()); E = pygame.event.Event
def click(pos):
    g.handle_event(E(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)); g.handle_event(E(pygame.MOUSEBUTTONUP, pos=pos, button=1)); g.apply_ui_actions()
g.do_button("setup"); g.update(0.01); g.draw()
sl = g.ui.modal_sliders["s_foxes"]; click((sl.rect.right, sl.rect.centery)); g.draw()
assert len(g.world.foxes) == 30, len(g.world.foxes)
click([r for b, r in g.ui.modal_buttons if b == "p_bunnyboom"][0].center); assert (len(g.world.rabbits), len(g.world.foxes)) == (80, 3)
click([r for b, r in g.ui.modal_buttons if b == "start"][0].center); assert g.modal is None and g.playing
g.restart(); assert len(g.world.rabbits) == 80          # restart keeps the setup
sp = g.ui.sliders["speed"]; click((sp.rect.x, sp.rect.centery)); assert g.speed == 0.1
print("SETUP OK")
