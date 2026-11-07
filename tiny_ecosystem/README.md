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
| **Why?** (H) | plain-language explanation of recent changes |
| **Sliders** | Rabbit Babies, Fox Babies, Grass Growth, Fox Hunger. They apply instantly |
| **Setup** (S) | choose starting rabbits, foxes and grass; presets; live preview |
| **Challenges** (C) | three little experiments with progress, success/failure and instant retry |

The graph shows the last 300 days: rabbits (blue, left scale), foxes (orange, right scale) and grass
(green, % of meadow). F12 saves a screenshot. Right-click returns to Inspect.

## Layout

```
main.py                 app loop, input, glue
config.py               all numbers (override any SimConfig field in config.json)
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

## Balancing notes (please read)

The plan's starting values were treated as hypotheses and tested with `tests/balance.py`. With them
unchanged, foxes wiped out the rabbits (and then themselves) in most seeds. Changes made:

* Foxes only **hunt while hungry** (`fox_hungry_below = 60` energy) and see **2 cells** (plan: 4).
* Fox meal 50 energy, fox reproduction needs 100 energy, fox max age 200.
* Rabbits reproduce at 65 energy with 15% chance.

Result over 20 seeds x 1000 days: rabbits survive in 20/20, both species in 19/20 (foxes die out in
1). Populations follow visible boom-and-bust cycles (about 100 days long): rabbits swing roughly
40-280, foxes climb slowly, and grass collapses at each rabbit peak. Extinction is not prevented and
is still possible, especially if you push the sliders hard. Peaks are crowded; that is the overgrazing
lesson, but you can soften it with fewer rabbit babies.

## Known issues / not done

* Grass colour changes in whole-cell steps, so overgrazed patches look slightly blocky.
* No sound (the plan says only if it clearly helps).
* Tested headlessly and by screenshot review; it has not been played by hand on a real display, and
  the 60 FPS target was only measured headlessly (about 3-6 ms/frame).
