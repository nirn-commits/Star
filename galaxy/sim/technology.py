"""技術革新：研究点の蓄積とブレイクスルー、発明者の栄誉。"""

from galaxy.content.technologies import TECH_FIELDS, TECH_KEYS, tech_name
from galaxy.content.ideologies import IDEOLOGIES
from galaxy.narrative.voice import narrate, say

FIELD_BIAS = {
    "militarism": {"weapons": 2.0, "shields": 1.5},
    "imperial": {"weapons": 1.3, "propulsion": 1.3},
    "corporatism": {"industry": 2.0, "propulsion": 1.3},
    "freetrade": {"propulsion": 1.8, "industry": 1.4},
    "harmonist": {"resonance": 2.5, "medicine": 1.3},
    "voidism": {"resonance": 2.5, "weapons": 1.5},
    "pacifism": {"medicine": 2.0, "industry": 1.3},
    "republic": {"medicine": 1.3, "industry": 1.3},
    "collectivism": {"industry": 1.6, "medicine": 1.4},
    "purity": {"weapons": 1.5, "medicine": 1.3},
    "liberation": {"propulsion": 1.6},
}


def cost(level):
    return 90 * (1.55 ** level)


def monthly(world):
    academics = {}
    for p in world.living:
        if p.alive and p.job and p.job.track == "academic":
            academics.setdefault(p.job.org_id, []).append(p)
    for f in world.alive_factions():
        staff = academics.get(f.id, [])
        points = (sum(p.stat("learning") * (1 + p.job.rank * 0.2) for p in staff) / 25
                  + sum(world.planet(pid).development for pid in f.planets) * 0.15)
        points *= 0.5 + IDEOLOGIES[f.ideology]["research"]
        bias = FIELD_BIAS.get(f.ideology, {})
        at_war = bool(world.wars_of(f.id))
        weights = {}
        for k in TECH_KEYS:
            w = bias.get(k, 1.0)
            if at_war and k in ("weapons", "shields"):
                w *= 1.6
            weights[k] = w
        total = sum(weights.values())
        for k in TECH_KEYS:
            gain = points * weights[k] / total
            # 交易相手からの技術拡散
            for key, tr in world.treaties.items():
                if f.id in key and "trade" in tr:
                    other = world.faction(next(iter(key - {f.id})))
                    if other and other.tech.get(k, 0) > f.tech.get(k, 0):
                        gain *= 1.15
            f.research[k] = f.research.get(k, 0.0) + gain
            level = f.tech.get(k, 0)
            if f.research[k] >= cost(level):
                f.research[k] -= cost(level)
                _breakthrough(world, f, k, staff)


def _breakthrough(world, f, field, staff):
    level = f.tech.get(field, 0)
    f.tech[field] = level + 1
    name = tech_name(field, level)
    fname = TECH_FIELDS[field]["name"]
    inventor = None
    if staff:
        inventor = max(staff, key=lambda p: p.stat("learning") + p.stat("intellect") / 2 + world.rng.random() * 8)
    if inventor:
        inventor.fame += 15 + level * 3
        inventor.merit += 8
        inventor.titles.append(f"「{name}」の開発者")
        line = say(world, inventor, "invention")
        world.record("tech", narrate(world, "tech", faction=f.name, person=inventor.name, tech=name, field=fname),
                     3 if level < 3 else 4, actors=(inventor.id,), factions=(f.id,), planet=inventor.planet,
                     quote=line, speaker=inventor.id)
    else:
        world.record("tech", narrate(world, "tech_nobody", faction=f.name, tech=name), 3, factions=(f.id,))
    # 効果
    if field == "shields":
        for pid in f.planets:
            world.planet(pid).defense += 5
    elif field == "industry":
        for pid in f.planets:
            world.planet(pid).development = min(3.5, world.planet(pid).development + 0.05)


def relic_boost(world, f, amount):
    field = world.rng.choice(TECH_KEYS)
    f.research[field] = f.research.get(field, 0.0) + amount
    return TECH_FIELDS[field]["name"]

