"""Rule-based Help messages from recent population statistics (no AI involved)."""
from __future__ import annotations

from typing import List

from simulation.world import World

WINDOW = 12


def explain(world: World) -> List[str]:
    h = world.history
    if len(h) < 4:
        return ["Press Step or Play and watch for a few days. I'll explain what changes!"]
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

    fleeing = sum(1 for r in world.rabbits if r.status == "Fleeing")
    hunting = sum(1 for f in world.foxes if f.status == "Hunting")
    resting = sum(1 for f in world.foxes if f.status == "Resting")
    hungry_r = sum(1 for r in world.rabbits if r.energy < world.cfg.rabbit_hungry_below)
    sight = world.cfg.fox_detect_radius * world.params.fox_hunger

    r_delta, g_delta, f_delta = r_now - r_then, g_now - g_then, f_now - f_then
    r_drop = r_delta < -max(2, 0.08 * r_then)
    r_rise = r_delta > max(2, 0.08 * max(r_then, 1))

    if hunting and fleeing:
        msgs.append("%d fox%s locked onto a rabbit and %d rabbit%s running away. "
                    "Fleeing rabbits can't eat." % (hunting, "es are" if hunting > 1 else " is",
                                                   fleeing, "s are" if fleeing > 1 else " is"))
    elif hunting:
        msgs.append("Hungry foxes can see rabbits within %.0f cells, so they are chasing them." % sight)
    elif resting and f_now:
        msgs.append("Some foxes gave up a chase and are resting before they hunt again.")
    if r_drop and eaten >= 3:
        msgs.append("More foxes are eating rabbits: %d were caught recently." % eaten)
    if (r_drop or starved >= 3) and g_now < 40:
        msgs.append("Rabbit numbers have fallen because the grass was grazed down and food is scarce.")
    elif starved >= 3:
        msgs.append("Some rabbits are starving because they can't find enough grass nearby.")
    elif hungry_r >= 0.5 * r_now and r_now >= 6 and g_now < 60:
        msgs.append("Many rabbits are hungry and searching for greener grass.")
    if g_delta > 3 and r_drop:
        msgs.append("Grass is recovering because fewer rabbits are grazing it.")
    elif g_delta > 3:
        msgs.append("The grass is growing back faster than it is eaten.")
    if g_delta < -3 and r_rise:
        msgs.append("Rabbits are multiplying and grazing lots of grass.")
    elif g_delta < -3:
        msgs.append("The grass is shrinking: too many animals are eating it.")
    if r_rise and g_now >= 40 and not r_drop:
        msgs.append("Rabbit numbers are rising because there is plenty of grass.")
    if r_now < 6 and not born_r:
        msgs.append("With so few rabbits it is hard to find a partner. Babies need two grown-up, well-fed rabbits close together.")
    if f_now == 1 and not born_f:
        msgs.append("A lone fox can't have cubs. Foxes need a grown-up, well-fed partner nearby.")
    elif f_delta < -1 and r_now < 25:
        msgs.append("Foxes are going hungry because there are fewer rabbits to catch.")
    elif f_delta > 1 and born_f:
        msgs.append("Foxes had cubs because they ate well and had partners nearby.")
    elif born_r >= 4 and not msgs:
        msgs.append("Well-fed rabbit pairs are having babies.")
    if not msgs:
        msgs.append("Things look fairly balanced right now. Try adding some foxes!")
    return msgs[:3]
