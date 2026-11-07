# Tiny Ecosystem

A low-poly meadow where rabbits eat grass and foxes eat rabbits. Add animals, change the rules with
sliders, and watch the populations rise and fall. Built with Python + Pygame CE; every animal, plant
and rock is drawn from polygons (no art files).

## Run

```bash
python -m pip install -r requirements.txt     # pygame-ce + pytest
python main.py                                 # play
python main.py --seed 7 --no-intro             # a specific world, skip the welcome screen
python main.py --challenge 2                   # jump straight into a challenge
python main.py --screenshot shot.png --days 60 --seed 3 --select 5   # headless snapshot
```

## How to play

| Do this | To get this |
|---|---|
| **Play / Pause** (Space) | start or stop time |
| **Step** (N) | advance one day |
| **Restart** (R) / **New** (G) | same world again / brand-new world |
| **Speed** slider (+ / -) | 0.1x to 8x in 11 steps |
| **Tools** (1-5) | Inspect, Add Rabbits, Add Foxes, Add Grass, Remove. Click or drag on the meadow |
| **Inspect** | click an animal for age, energy and what it is doing |
| **Reset** (rules header) | puts the four rule sliders back to normal; double-click one slider to reset just it |
| **Help** (H) | explains what has been happening (hunting, fleeing, grazing, pairs) and how the rules work |
| **Sliders** | Rabbit Babies, Fox Babies, Grass Growth, Fox Hunger (= how far foxes can see). They apply instantly |
| **Setup** (S) | choose starting rabbits, foxes and grass; presets; live preview |
| **Challenges** (C) | three little experiments with progress, success/failure and instant retry |

The graph shows the last 300 days: rabbits (blue, left scale), foxes (orange, right scale) and grass
(green, % of meadow). F12 saves a screenshot. Right-click returns to Inspect.

**The sandbox ends** when there are no rabbits, no foxes and the grass has grown back to 100%.
Challenges have their own win/lose rules.

## Layout

```
main.py                 app loop, input, glue
config.py               loads the numbers; defaults.json holds them, config.json overrides
simulation/             world.py, animals.py, rules.py    <- no Pygame in here
graphics/               renderer.py, animals.py, environment.py
ui/                     interface.py, graph.py
gameplay/               challenges.py, explain.py
tests/                  test_simulation.py, test_gameplay.py, balance.py, smoke_ui.py
```

Simulation and drawing are separate: the world ticks at a fixed rate (2 days/second at 1x) and the
renderer interpolates animals between cells at 60 FPS. The same seed and settings always give the
same history.

## Tests

```bash
python -m pytest tests          # rules, determinism, challenges
python tests/balance.py 20 1000 # 20 seeds x 1000 days: extinction + population statistics
python tests/smoke_ui.py        # drives the real UI headlessly (clicks, sliders, challenge flow)
```

## How the animals behave

* **Foxes hunt by sight.** A hungry fox (energy below 90) that sees a rabbit inside its vision radius
  *locks on* and sprints after it (2 cells per tick). The **Fox Hunger** slider scales that vision radius
  (2 to 6 cells). A chase that fails after 3 ticks ends in a short rest, so rabbits can get away.
* **Rabbits flee.** A rabbit that a fox has locked onto, or that has a fox within 2-3 cells, runs to the
  free cell farthest from the fox (a red "!" shows it) and does not eat while running.
* **Breeding needs a pair.** Both animals must be adult (rabbits 10 days, foxes 20), well fed
  (65 / 100 energy), close to each other (3 / 5 cells), and off cooldown (8 / 25 days). Then there is a
  chance of a baby, and both partners start their cooldown. A lone animal never breeds.

## Balancing notes

All values live in `defaults.json` (load order: built-in, `defaults.json`, `config.json`); test changes
with `python tests/balance.py 20 1000 key=value`.

* **Rabbits forage.** A rabbit below 80 energy heads for the best grass within 4 cells (and stays put on a
  cell with 30+ grass); a well-fed rabbit just ambles about. Grass regrows 1.5 per tick, so grazed
  patches really do go bare.
* Over 20 seeds x 1000 days: grass averages about 50%, rabbit peaks are around 160, rabbits die out in
  about 13 runs and the foxes in every run (usually by day 250-600).
* **A stable, permanent three-way balance was NOT achieved.** Several bounded searches (fox energy and
  breeding, rabbit mating range, grass regrowth and nutrition, bush hiding spots) hit the same wall: in
  this small, well-mixed world the foxes overshoot, eat the last rabbits and then starve. A real fix
  needs a new mechanism (e.g. fox territories or a population cap), not another number.

## Known issues / not done

* Grass colour changes in whole-cell steps, so overgrazed patches look slightly blocky.
* No sound (the plan says only if it clearly helps).
* Tested headlessly and by screenshot review; it has not been played by hand on a real display, and
  the 60 FPS target was only measured headlessly (about 3-6 ms/frame).
