# Project Plan: Tiny Ecosystem
## A Low-Poly Wildlife Simulation Game for Students

### 1. Project Objective

Build a visually appealing, interactive ecosystem simulation where rabbits, foxes, and grass coexist according to simple biological rules.

The game should feel like a miniature living world.

It should combine:
- The emergent behavior of Conway's Game of Life.
- The visual charm of a low-poly nature game.
- The interactivity of a simple sandbox.
- The educational value of experimenting with ecosystems.

**Primary audience:** Students approximately 9–14 years old.

**Core design principles:**
1. Simple rules producing interesting behavior.
2. Attractive graphics are essential, not optional.
3. Minimal controls and an intuitive interface.
4. Visual explanations instead of complicated numbers.
5. Easy to understand, modify, and extend.
6. Prioritize a polished small game over a complicated unfinished one.

The goal is a complete playable desktop application, not a technology demo.

---

## 2. Technology Stack

Use:

- **Python 3.12+**
- **Pygame CE** for graphics, animation, input, and window management.
- Python standard library for simulation logic, randomness, and data storage.
- JSON for configuration and saved presets.
- Pytest for basic simulation tests.

Install with:

```bash
python -m pip install pygame-ce pytest
```

Avoid:
- Unity, Unreal, Godot, or other game engines.
- OpenGL or complex 3D rendering.
- External physics engines.
- Complicated UI frameworks.
- Network services, accounts, or databases.

### Graphics approach

Use **procedurally drawn 2D polygons** with a stylized, low-poly appearance.

The visual style should create the illusion of a miniature 3D world using:

- Polygonal animal bodies.
- Faceted grass and vegetation.
- Soft ground shadows.
- Flat-shaded colors.
- Layered shapes and simple highlights.
- Smooth movement between positions.
- Small squash, bounce, and idle animations.

Use Pygame's polygon drawing functions. No external art assets should be required for the first version.

Do not attempt to create an actual 3D environment.

---

## 3. Visual Design

### Overall appearance

Create a colorful, inviting miniature meadow.

Visual inspiration:
- Low-poly dioramas.
- Polygonal animal figurines.
- Stylized nature illustrations.
- Minimalist strategy games.

The environment should feel lively and slightly playful without looking excessively childish.

### Camera

Use a fixed, slightly elevated, top-down 2D view.

The world should have a subtle pseudo-isometric appearance, but movement and simulation calculations should use a standard rectangular grid.

**Important:** Separate simulation coordinates from rendering coordinates.

Animals should move smoothly between logical cells. The grid should not be visibly drawn during normal gameplay.

### Color palette

Use a consistent, restrained palette:

| Element | Suggested color |
|---|---|
| Grassland | Light olive and meadow green |
| Fresh grass | Bright green |
| Tall grass | Deep green |
| Rabbits | Cream, beige, and light brown |
| Foxes | Burnt orange, rust, and white |
| Rocks | Cool gray |
| Soil | Warm brown |
| Water (future) | Muted blue |
| UI panels | Warm off-white |

Use subtle color variations to prevent the landscape from appearing repetitive.

### Animals

**Rabbits**

Draw each rabbit using approximately 8–15 polygons:
- Rounded polygonal body.
- Smaller head.
- Two long ears.
- Short tail.
- Tiny dark eyes.
- Small feet.

Animation:
- Gentle idle movement.
- Two-frame hopping motion.
- Body compression before moving.
- Small bounce upon landing.
- Head lowered when eating.

**Foxes**

Draw each fox using approximately 10–18 polygons:
- Orange, angular body.
- Pointed face.
- Triangular ears.
- Bushy tail with a white tip.
- Dark feet and nose.

Animation:
- Smooth walking or trotting.
- Tail swaying.
- Slight head movement.
- Faster motion when pursuing rabbits.

**Important:** Animals should remain recognizable at small sizes. Prioritize silhouettes over detail.

### Environment

Build the terrain with polygonal grass clumps, subtle ground variation, and occasional decorations.

Include:
- Short and tall grass.
- Small flowers.
- Decorative rocks.
- Occasional bushes.
- Small ground shadows.

These objects should not interfere with simulation rules unless explicitly implemented as interactive elements.

### Rendering performance

Pre-render static terrain to a Pygame surface.

Cache animal polygon shapes when practical.

Use simple transforms and animation offsets instead of reconstructing complicated geometry every frame.

Target 60 FPS on an ordinary laptop.

---

## 4. World Structure

Use a logical grid of **30 columns × 20 rows**.

Each cell stores:
- Grass amount: integer from 0 to 100.
- Terrain type: grassland initially.
- Optional decorative elements.

Animals are separate objects occupying grid positions.

This allows:
- Multiple kinds of entities to interact.
- Smooth visual movement.
- Easier simulation rules.
- Future expansion.

The grid should define the simulation, but the world should appear as a continuous landscape.

### Initial environment

Default starting configuration:

- 30 × 20 world.
- 35 rabbits.
- 7 foxes.
- Randomly distributed grass.
- Most grass cells at least partially grown.
- Some decorative rocks and flowers.

All values should be adjustable through a configuration file.

Avoid making the world too crowded.

---

## 5. Simulation Rules

Keep the first implementation limited to five fundamental animal mechanics:

**Movement, Eating, Energy, Reproduction, and Death.**

Grass regrowth is an additional environmental mechanic.

### 5.1 Time

The simulation advances in discrete ticks.

Suggested default:
- 1 tick = 1 simulated day.
- 2 ticks per real-world second.
- Rendering continues at 60 FPS independently.

Support simulation speed adjustment from 0.5× to 8×.

The simulation must produce repeatable results when using the same random seed and settings.

### 5.2 Grass

Each cell contains a grass amount from 0 to 100.

Rules:
- Grass regenerates by 2 units per tick.
- A rabbit can consume up to 20 units per feeding action.
- Grass growth stops at 100.

Grass should visually change with its amount:

| Grass amount | Appearance |
|---|---|
| 0–20 | Mostly soil and tiny shoots |
| 21–50 | Short grass |
| 51–80 | Medium grass |
| 81–100 | Tall lush grass |

This creates visible feedback when rabbits overgraze.

### 5.3 Rabbits

Suggested starting attributes:

| Attribute | Value |
|---|---|
| Starting energy | 60 |
| Maximum energy | 100 |
| Energy loss per tick | 3 |
| Energy gained per grass unit | 0.3 |
| Reproduction threshold | 75 |
| Reproduction probability | 12% per eligible tick |
| Maximum age | 100 ticks |

Rules:
1. Rabbits prefer neighboring cells containing more grass.
2. Randomness should influence movement.
3. Rabbits consume grass at their destination.
4. Every tick costs energy.
5. Rabbits with sufficient energy may reproduce.
6. Reproduction costs the parent 30 energy.
7. Offspring begin with 40 energy.
8. Rabbits die if their energy reaches zero or they exceed maximum age.

Newborn rabbits appear in nearby available positions.

Only one animal should occupy a cell at the end of a tick.

### 5.4 Foxes

Suggested attributes:

| Attribute | Value |
|---|---|
| Starting energy | 65 |
| Maximum energy | 120 |
| Energy loss per tick | 4 |
| Energy gained from eating rabbit | 55 |
| Hunting detection radius | 4 cells |
| Reproduction threshold | 90 |
| Reproduction probability | 7% per eligible tick |
| Maximum age | 140 ticks |

Rules:
1. Foxes search for rabbits within their detection radius.
2. If a rabbit is detected, move toward it.
3. Otherwise, wander randomly.
4. If a fox reaches a rabbit's position, the rabbit is eaten.
5. The fox gains energy from the meal.
6. Foxes lose energy every tick.
7. Foxes can reproduce when sufficiently energized.
8. Reproduction costs the parent 40 energy.
9. Foxes die from starvation or old age.

For simplicity, hunting is deterministic when a fox reaches a rabbit.

Do not implement complicated pursuit or combat algorithms.

### 5.5 Rule execution order

Each simulation tick should:

1. Regenerate grass.
2. Determine rabbit movement.
3. Resolve rabbit movement conflicts.
4. Allow rabbits to eat grass.
5. Determine fox movement and hunting.
6. Resolve hunts and movement conflicts.
7. Apply energy consumption and aging.
8. Remove dead animals.
9. Process eligible reproduction.
10. Record population statistics.

Use a stable, documented update order so results remain understandable.

Randomize animal processing order using the simulation's seeded random-number generator.

Avoid modifying a collection while iterating through it.

### 5.6 Balancing

The starting values are hypotheses, not guaranteed to produce stable populations.

Before finalizing the simulation, automatically test at least 20 random seeds over 1,000 ticks each.

Measure:
- Rabbit extinction rate.
- Fox extinction rate.
- Average population sizes.
- Frequency of excessive population growth.
- Population oscillations.

Adjust the parameters to produce understandable predator-prey cycles across a useful range of starting configurations.

Do not artificially prevent extinction. Extinction should remain a possible educational outcome.

---

## 6. User Interface

Create a clean UI around the living world.

### Recommended screen layout

Target initial resolution: **1280 × 800**.

**Main area:**
- Approximately 75% of the screen width.
- Large, animated ecosystem.
- Minimal visual clutter.

**Right sidebar:**
- Current day.
- Rabbit population.
- Fox population.
- Grass abundance.
- Simulation controls.
- Adjustable parameters.

**Bottom area:**
- Population graph.

### Controls

Implement:
- Play / Pause.
- Step Forward (one tick).
- Restart World.
- Generate New World.
- Simulation Speed.
- Add Rabbits.
- Add Foxes.
- Add Grass.
- Remove Animals.

The user should be able to click on the world to place entities.

The active placement tool should be visually highlighted.

### Parameters

Include only four adjustable parameters initially:

1. Rabbit reproduction rate.
2. Fox reproduction rate.
3. Grass regrowth speed.
4. Fox energy consumption.

Use simple sliders labeled with student-friendly descriptions.

For example:

"Fox Hunger: Low — High"

Show numerical values in a small tooltip or secondary label.

Parameter changes should take effect during the running simulation without requiring a restart.

### Population graph

Display an evolving line chart:
- Green: Total grass abundance.
- Blue: Rabbit population.
- Orange: Fox population.

Use a dedicated scale for grass or normalize it so grass does not hide population changes.

The graph should update every simulation tick, not every rendering frame.

Keep the last 300 ticks visible.

Implement the graph directly with Pygame line drawing.

Do not add a plotting library unless necessary.

---

## 7. Interactivity and Feedback

Make the world responsive and visually satisfying.

### Animal inspection

When the user clicks an animal, display a compact information panel.

Example:

**Rabbit #23**

- Age: 14 days
- Energy: 72 / 100
- Status: Searching for food

Possible statuses:
- Wandering
- Searching for food
- Eating
- Hunting
- Fleeing (future feature)
- Reproducing
- Starving

Use readable labels and simple icons.

### Visual events

Add lightweight effects:
- Small particles when grass is eaten.
- Brief hearts when animals reproduce.
- A subtle fade-out when animals die.
- Gentle camera-independent animation for plants.

Avoid excessive particle effects, loud sounds, or distracting screen movements.

### Educational explanations

Include a small optional "Why?" information panel explaining recent changes.

Examples:
- "More foxes are eating rabbits."
- "Rabbit numbers have fallen because food is scarce."
- "Grass is recovering because fewer rabbits are eating it."

Generate these messages using simple rule-based comparisons between recent population statistics.

Do not use AI-generated explanations or external APIs.

---

## 8. Student Challenges

Create three introductory challenges.

### Challenge 1: Balance the Meadow

**Goal:** Keep at least 10 rabbits and 2 foxes alive for 200 simulated days.

The student may adjust reproduction rates and grass growth before beginning.

### Challenge 2: The Drought

**Scenario:** Grass regrowth is reduced to half its normal rate.

**Goal:** Keep the rabbit population alive for 150 days.

### Challenge 3: Too Many Foxes

**Scenario:** A large fox population has entered the ecosystem.

**Goal:** Prevent rabbit extinction by modifying the environment or adding rabbits.

All challenges should:
- Start with a predefined world and random seed.
- Show the objective clearly.
- Track progress.
- Display success or failure.
- Allow immediate retries.

Challenges should be educational experiments, not difficult strategy puzzles.

Do not require students to complete challenges to access the sandbox.

---

## 9. Recommended Python Architecture

Use a modular but deliberately small project structure.

```text
tiny_ecosystem/
│
├── main.py
├── config.py
│
├── simulation/
│   ├── world.py
│   ├── animals.py
│   └── rules.py
│
├── graphics/
│   ├── renderer.py
│   ├── animals.py
│   └── environment.py
│
├── ui/
│   ├── interface.py
│   └── graph.py
│
├── gameplay/
│   └── challenges.py
│
├── tests/
│   └── test_simulation.py
│
├── requirements.txt
└── README.md
```

### Responsibilities

**main.py**

Initialize Pygame, manage the application loop, handle events, and coordinate simulation with rendering.

**config.py**

Store world dimensions, simulation parameters, colors, and UI constants.

**simulation/world.py**

Store the grid, animals, random generator, world state, and population history.

**simulation/animals.py**

Define lightweight Rabbit and Fox data objects.

**simulation/rules.py**

Implement movement, feeding, predation, reproduction, aging, and death.

**graphics/renderer.py**

Draw the world and animals. Implement camera positioning and animation interpolation.

**graphics/animals.py**

Contain procedural polygon drawing functions for rabbits and foxes.

**graphics/environment.py**

Draw terrain, grass, decorative rocks, flowers, and bushes.

**ui/interface.py**

Draw buttons, sliders, panels, status indicators, and inspection information.

**ui/graph.py**

Render population-history graphs.

**gameplay/challenges.py**

Define challenge conditions and evaluate progress.

### Architectural requirements

Simulation logic must not depend on Pygame.

Rendering must not modify simulation state.

Use a fixed simulation timestep and smooth visual interpolation.

Store visual animation state separately from logical entity state.

Use Python dataclasses where appropriate.

Avoid large inheritance hierarchies, plugin systems, event buses, and premature abstraction.

---

## 10. Implementation Roadmap

**IMPORTANT: Do not implement everything at once. Build a sequence of working, visually inspectable prototypes.**

### Phase 1 — Visual Prototype

Build this phase before implementing ecosystem rules.

Create a running Pygame application displaying:

- A beautiful polygonal meadow.
- 10 randomly positioned rabbits.
- 3 foxes.
- Grass clumps, flowers, and rocks.
- Simple idle animations.
- A fixed elevated camera.

Implement:
- Polygonal animal drawing.
- Faceted vegetation.
- Ground shadows.
- Basic color variations.
- Proper draw order.

No reproduction, hunting, or energy systems yet.

**Required deliverable:** A playable visual prototype that can be opened and inspected.

**Preview checkpoint 1:** Capture a screenshot and review:
- Are the animals recognizable?
- Do the graphics feel cohesive?
- Is the world visually attractive?
- Are the animals large enough to see?
- Is the scene pleasant rather than cluttered?

Do not proceed until the art direction is satisfactory.

### Phase 2 — Animation Prototype

Implement:
- Rabbit hopping.
- Fox walking.
- Smooth movement between cells.
- Grass sway.
- Basic idle animations.
- Animal direction changes.

Use a basic random walk, without biological rules.

**Preview checkpoint 2:** Observe the simulation running for at least 30 seconds.

Check:
- Movement smoothness.
- Animation quality.
- Overlapping sprites.
- Frame rate.
- Whether motion looks natural.

Do not continue until movement feels convincing.

### Phase 3 — Ecosystem Simulation

Implement:
- Grass growth.
- Rabbit eating and energy.
- Rabbit reproduction.
- Fox hunting and feeding.
- Fox reproduction.
- Starvation.
- Aging and death.
- Population statistics.

Make all rules run independently of rendering.

Create automated tests for:
- Correct grass growth limits.
- Energy consumption.
- Reproduction conditions.
- Predation.
- Death.
- Valid grid positions.
- Reproducibility with fixed seeds.

**Preview checkpoint 3:** Run multiple simulations and tune the starting parameters.

### Phase 4 — User Interface

Implement:
- Start/Pause.
- Step Forward.
- Restart.
- Speed adjustment.
- Population counters.
- Population graph.
- Placement tools.
- Parameter sliders.
- Animal inspection.

**Preview checkpoint 4:** Verify that all actions work and that the UI remains readable without overwhelming the environment.

### Phase 5 — Educational Features

Implement:
- Three challenges.
- Challenge selection.
- Progress and outcome screens.
- Basic ecological explanations.
- Brief introductory instructions.

Keep all educational text concise and accessible.

### Phase 6 — Final Polish

Add:
- More attractive vegetation.
- Better character animations.
- Subtle particles.
- Interface transitions.
- Helpful tooltips.
- Seed-based world regeneration.
- Keyboard shortcuts.
- Sound effects only if they genuinely improve the experience.

Avoid introducing new simulation mechanics at this stage.

---

## 11. Explicit Instructions for the Coding LLM

Follow these requirements:

1. **Start with Phase 1 only.** Do not write the entire game immediately.
2. Create real, runnable Python files rather than pseudocode.
3. Use simple, maintainable implementations.
4. Explain how to run each milestone.
5. Keep the project working after every phase.
6. Prefer custom Pygame polygons over downloaded graphics.
7. Do not introduce external dependencies unless essential.
8. Make the world aesthetically appealing from the earliest prototype.
9. Separate simulation rules from rendering and UI.
10. Use deterministic randomness for reproducible experiments.
11. Use interpolation for animation but discrete ticks for simulation.
12. Include automated tests for the simulation rules.
13. Preserve existing functionality when adding features.
14. Do not implement unrequested features or overengineer the architecture.
15. Keep the main world visible and dominant at all times.

After each phase, provide:
- A summary of implemented functionality.
- The files created or modified.
- Exact instructions to launch the prototype.
- Any known issues.
- A short visual or functional review checklist.

If screenshot inspection or graphical preview tools are available, use them at each graphical checkpoint.

If unavailable, provide an easy way to run the prototype locally and describe what should be inspected manually.

**Do not claim that the graphics have been visually verified unless an actual rendered preview was inspected.**

---

## 12. Definition of Done

The project is complete when:

- The game runs locally with a simple Python command.
- The world has a cohesive, attractive low-poly appearance.
- Rabbits and foxes move with smooth animations.
- Grass visibly grows and gets eaten.
- Rabbits and foxes interact through clear ecological rules.
- Populations change over time.
- Students can modify the ecosystem.
- Population graphs reflect the actual simulation.
- All three student challenges work.
- The UI is understandable without reading a manual.
- The game operates smoothly on ordinary laptop hardware.
- Core simulation tests pass.

### Final Guiding Principle

**Make the world visually charming, the rules scientifically intuitive, and the interactions immediately understandable.**

The experience should make a student curious enough to ask:

*"What would happen if I added five more foxes?"*

And then immediately let them find out.