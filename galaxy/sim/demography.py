"""人口動態：老化・死亡・結婚・出産・新たな人物の台頭。"""

import math

from galaxy.content.species import SPECIES
from galaxy.minds import mind_of
from galaxy.narrative.voice import narrate, say, exchange
from galaxy.sim.life import (create_person, kill, effective_lifespan, is_adult, adjust_opinion,
                             siblings)


def target_notables(planet):
    """惑星ごとに追跡する「名のある人物」の目安人数。"""
    return int(max(4, min(26, 3 + math.log10(planet.population + 1) * 5 * planet.development ** 0.3)))


def monthly(world):
    rng = world.rng
    t = world.t
    for p in list(world.living):
        if not p.alive:
            continue
        _mortality(world, p)
    # 結婚と出産は惑星単位で処理する
    for planet_id, people in list(world.by_planet.items()):
        alive = [p for p in people if p.alive]
        if not alive:
            continue
        crowd = len(alive) / (target_notables(world.planet(planet_id)) * 1.6)
        singles = [p for p in alive if p.spouse is None and _marriageable(world, p)]
        if len(singles) >= 2:
            for p in singles:
                if p.spouse is None and rng.random() < 0.012 * (1 + p.disposition("sociability") * 0.3):
                    _seek_spouse(world, p, singles)
        for p in alive:
            if p.spouse is not None and _is_mother(p):
                _maybe_birth(world, p, crowd)
    if t % 12 == 6:
        _replenish(world)


def _mortality(world, p):
    life = effective_lifespan(world, p)
    x = (world.t - p.birth_t) / 12 / life
    annual = 0.002 + 0.35 * math.exp(8 * (x - 1))
    if x < 0.05:
        annual += 0.004
    annual /= max(0.3, p.health)
    monthly_p = min(0.6, annual / 12)
    if world.rng.random() < monthly_p:
        if x > 0.7:
            cause = "natural"
        else:
            cause = world.rng.choice(("illness", "illness", "accident"))
        if cause == "accident":
            from galaxy.content.events import ACCIDENTS
            kill(world, p, cause, accident=world.rng.choice(ACCIDENTS))
        else:
            kill(world, p, cause)


def _marriageable(world, p):
    sp = SPECIES[p.species]
    if not sp["can_marry"] or not is_adult(world, p):
        return False
    return p.age(world.t) < sp["lifespan"] * 0.75


def _compatible(world, a, b):
    if a.id == b.id or a.sex == b.sex:
        return False
    if not SPECIES[b.species]["can_marry"]:
        return False
    if b.id in a.parents or a.id in b.parents or b.id in siblings(world, a):
        return False
    if a.id in b.former_spouses:
        return False
    la = SPECIES[a.species]["lifespan"]
    return abs(a.age(world.t) - b.age(world.t)) < max(6, la * 0.22)


def _seek_spouse(world, p, singles):
    rng = world.rng
    cands = [c for c in singles if c.spouse is None and _compatible(world, p, c)]
    if not cands:
        return
    def appeal(c):
        v = p.opinions.get(c.id, 0) + rng.uniform(0, 40)
        if c.species == p.species:
            v += 40
        if c.ideology == p.ideology:
            v += 10
        if c.has("美貌"):
            v += 15
        return v
    partner = max(cands, key=appeal)
    if partner.species != p.species and rng.random() < 0.7:
        return
    if not (mind_of(world, p).accept_marriage(world, p, partner)
            and mind_of(world, partner).accept_marriage(world, partner, p)):
        adjust_opinion(p, partner, 5)
        return
    marry(world, p, partner)


def marry(world, a, b):
    rng = world.rng
    a.spouse = b.id
    b.spouse = a.id
    adjust_opinion(a, b, 50)
    adjust_opinion(b, a, 50)
    planet = world.planet(a.planet)
    fa, fb = world.faction(a.faction), world.faction(b.faction)
    royal = any(f and f.leader in _family_ids(world, x) for f in (fa, fb) for x in (a, b))
    fame = a.fame + b.fame
    importance = 1
    if fame > 40:
        importance = 2
    if royal:
        importance = 3
    if fa and fb and fa.id != fb.id and royal:
        text = narrate(world, "marriage_political", person=a.name, target=b.name, faction=fa.name,
                       target_faction=fb.name)
        fa.relations[fb.id] = fa.relations.get(fb.id, 0) + 20
        fb.relations[fa.id] = fb.relations.get(fa.id, 0) + 20
    else:
        text = narrate(world, "marriage", person=a.name, target=b.name, planet=planet.name,
                       guests=rng.randint(20, 3000))
    if importance >= 2 and rng.random() < 0.5:
        q, r = exchange(world, "proposal")
        world.record("marriage", text, importance, actors=(a.id, b.id), planet=a.planet,
                     factions=tuple(f.id for f in (fa, fb) if f), quote=q, speaker=a.id, reply=r, replier=b.id)
    else:
        line = say(world, a, "marriage", spouse=b.given)
        world.record("marriage", text, importance, actors=(a.id, b.id), planet=a.planet,
                     factions=tuple(f.id for f in (fa, fb) if f),
                     quote=line if importance >= 2 else None, speaker=a.id)
        if importance < 2:
            a.add_quote(world.t, line)
    # 夫婦は同じ国に住む（身分の高い方に合わせる）
    if a.faction != b.faction:
        if (b.job and b.job.rank >= 3) and not (a.job and a.job.rank >= 3):
            a.planet, a.faction = b.planet, b.faction
        else:
            b.planet, b.faction = a.planet, a.faction


def _family_ids(world, p):
    return {p.id, *p.parents}


def _is_mother(p):
    return p.sex in ("女", "雌", "繁体")


def _maybe_birth(world, mother, crowd):
    rng = world.rng
    sp = SPECIES[mother.species]
    if sp["fertility"] <= 0:
        return
    age = mother.age(world.t)
    if age > sp["lifespan"] * 0.55:
        return
    father = world.person(mother.spouse)
    if father is None or not father.alive:
        return
    n = len(mother.children)
    chance = 0.011 * sp["fertility"] / (1 + n * 0.6)
    if crowd > 1:
        chance /= crowd ** 3
    if father.species != mother.species:
        chance *= 0.3
    if rng.random() >= chance:
        return
    species = mother.species if rng.random() < 0.5 else father.species
    family = father.family if rng.random() < 0.8 else mother.family
    if SPECIES[species]["names"] != SPECIES[father.species]["names"]:
        family = mother.family
    child = create_person(world, species, mother.planet, mother.faction, world.t, family=family,
                          parents=(father.id, mother.id), origin="名家の子" if father.fame > 30 else "")
    mother.children.append(child.id)
    father.children.append(child.id)
    adjust_opinion(child, mother, 40)
    adjust_opinion(child, father, 40)
    planet = world.planet(mother.planet)
    parents = f"{father.name}と{mother.name}"
    text = narrate(world, "birth_notable", parents=parents, person=child.name, planet=planet.name)
    leader_child = any(f.leader in (father.id, mother.id) for f in world.factions.values() if f.alive)
    importance = 3 if leader_child else 2 if (father.fame + mother.fame) > 60 else 0
    speaker = rng.choice((father, mother))
    line = say(world, speaker, "birth", child=child.given)
    if importance:
        world.record("birth", text, importance, actors=(father.id, mother.id), planet=mother.planet,
                     quote=line, speaker=speaker.id, bio=False)
    father.add_bio(world.t, f"子の{child.name}が生まれた。")
    mother.add_bio(world.t, f"子の{child.name}が生まれた。")
    child.add_bio(world.t, f"{planet.name}で、{parents}の子として生まれた。")


def _replenish(world):
    """名のある人物が少ない惑星に、新たに頭角を現した人物を登場させる。"""
    from galaxy.sim.careers import start_career
    rng = world.rng
    for planet in world.planets:
        people = [p for p in world.by_planet.get(planet.id, []) if p.alive]
        adults = [p for p in people if is_adult(world, p)]
        need = target_notables(planet) - len(adults)
        if need <= 0:
            continue
        for _ in range(min(need, 2)):
            species = planet.species if rng.random() < 0.75 else rng.choice(list(SPECIES))
            sp = SPECIES[species]
            age = rng.uniform(sp["adult"], sp["adult"] + sp["lifespan"] * 0.25)
            p = create_person(world, species, planet.id, planet.owner, world.t - int(age * 12))
            p.add_bio(world.t, f"{planet.name}の{p.origin}として、歴史の表舞台に現れた。")
            start_career(world, p, quiet=True)
            world.by_planet[planet.id].append(p)
            if rng.random() < 0.05:
                world.record("coming_of_age", narrate(world, "coming_of_age", planet=planet.name,
                                                      origin=p.origin, person=p.name),
                             1, actors=(p.id,), planet=planet.id, bio=False)
