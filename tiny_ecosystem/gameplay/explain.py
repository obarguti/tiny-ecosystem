"""Rule-based 'Why?' messages from recent population statistics (no AI involved)."""
from __future__ import annotations

from typing import List

from simulation.world import World

WINDOW = 12


def explain(world: World) -> List[str]:
    h = world.history
    if len(h) < 4:
        return ["Press Play and watch for a few days. I'll explain what changes!"]
    recent = h[-WINDOW:]
    before = h[-2 * WINDOW:-WINDOW] or h[:1]
    r_now, r_then = recent[-1].rabbits, before[-1].rabbits
    f_now, f_then = recent[-1].foxes, before[-1].foxes
    g_now, g_then = recent[-1].grass_pct, before[-1].grass_pct
    eaten = sum(s.eaten for s in recent)
    starved = sum(s.starved for s in recent)
    born_r = sum(s.born_r for s in recent)
    born_f = sum(s.born_f for s in recent)

    msgs: List[str] = []
    if r_now == 0:
        return ["There are no rabbits left. Foxes will go hungry, and the grass will grow back."]
    if f_now == 0:
        msgs.append("There are no foxes, so nothing keeps the rabbits in check.")

    r_delta, g_delta, f_delta = r_now - r_then, g_now - g_then, f_now - f_then
    r_drop = r_delta < -max(2, 0.08 * r_then)
    r_rise = r_delta > max(2, 0.08 * max(r_then, 1))

    if r_drop and eaten >= 3:
        msgs.append("More foxes are eating rabbits: %d were caught recently." % eaten)
    if (r_drop or starved >= 3) and g_now < 40:
        msgs.append("Rabbit numbers have fallen because food is scarce.")
    elif starved >= 3:
        msgs.append("Some rabbits are starving because they can't find enough grass nearby.")
    if g_delta > 3 and r_drop:
        msgs.append("Grass is recovering because fewer rabbits are eating it.")
    elif g_delta > 3:
        msgs.append("The grass is growing back faster than it is eaten.")
    if g_delta < -3 and r_rise:
        msgs.append("Rabbits are multiplying and eating lots of grass.")
    elif g_delta < -3:
        msgs.append("The grass is shrinking: too many animals are eating it.")
    if r_rise and g_now >= 40 and not r_drop:
        msgs.append("Rabbit numbers are rising because there is plenty of grass.")
    if f_delta < -1 and r_now < 25:
        msgs.append("Foxes are going hungry because there are fewer rabbits to catch.")
    elif f_delta > 1 and born_f:
        msgs.append("Foxes had babies because they ate well.")
    elif born_r >= 4 and not msgs:
        msgs.append("Well-fed rabbits are having babies.")
    if not msgs:
        msgs.append("Things look fairly balanced right now. Try adding some foxes!")
    return msgs[:3]
