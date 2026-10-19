"""人物の誕生・死亡・移住など、人生の基本操作。"""

from galaxy.content.species import SPECIES
from galaxy.content.traits import TRAITS, INNATE_TRAITS, conflicts
from galaxy.content.ideologies import IDEOLOGY_KEYS, SPECIES_IDEOLOGY_BIAS
from galaxy.content.names import gen_given, gen_family
from galaxy.content.events import ORIGINS
from galaxy.model.entities import Person, STATS
from galaxy.narrative.voice import narrate, say


def weighted_choice(rng, weights):
    """{キー: 重み} から1つ選ぶ。"""
    items = [(k, w) for k, w in weights.items() if w > 0]
    total = sum(w for _, w in items)
    r = rng.random() * total
    for k, w in items:
        r -= w
        if r <= 0:
            return k
    return items[-1][0]


def roll_traits(rng, species, inherited=()):
    bias = SPECIES[species]["trait_bias"]
    pool = {t: bias.get(t, 1.0) * (0.08 if TRAITS[t].get("rare") else 1.0) for t in INNATE_TRAITS}
    for t in inherited:
        if t in pool:
            pool[t] *= 3.0
    chosen = []
    count = rng.choice((2, 3, 3, 3, 4))
    for _ in range(20):
        if len(chosen) >= count:
            break
        t = weighted_choice(rng, pool)
        if t in chosen or any(conflicts(t, c) for c in chosen):
            pool[t] = 0
            continue
        chosen.append(t)
        pool[t] = 0
    return chosen


def roll_stats(rng, species, traits, parents=()):
    bias = SPECIES[species]["stat_bias"]
    stats = {}
    for s in STATS:
        if s == "resonance":
            # 共鳴の才は稀にしか現れない
            base = rng.randint(9, 18) if rng.random() < 0.04 else rng.randint(0, 3)
        else:
            base = rng.randint(3, 14)
        if parents:
            inherit = sum(p.stats.get(s, 0) for p in parents) / len(parents)
            if s == "resonance" and inherit >= 8 and rng.random() < 0.35:
                base = max(base, rng.randint(8, 16))
            else:
                base = round(base * 0.6 + inherit * 0.4)
        base += bias.get(s, 0)
        for t in traits:
            base += TRAITS[t].get("stats", {}).get(s, 0)
        stats[s] = max(0, min(25, base))
    return stats


def roll_ideology(rng, species, culture=None, parents=()):
    weights = {k: 1.0 for k in IDEOLOGY_KEYS}
    weights["voidism"] = 0.15
    weights["collectivism"] = 0.2
    for k, w in SPECIES_IDEOLOGY_BIAS.get(species, {}).items():
        weights[k] *= w
    if culture:
        weights[culture] += 6.0
    for p in parents:
        weights[p.ideology] += 4.0
    return weighted_choice(rng, weights)


def create_person(world, species, planet_id, faction_id, birth_t, sex=None, family=None,
                  parents=(), origin=None):
    rng = world.rng
    sp = SPECIES[species]
    sex = sex or rng.choice(sp["sexes"])
    parent_objs = [world.person(pid) for pid in parents if world.person(pid)]
    inherited = [t for p in parent_objs for t in p.traits if not TRAITS[t].get("acquired")]
    traits = roll_traits(rng, species, inherited)
    stats = roll_stats(rng, species, traits, parent_objs)
    planet = world.planet(planet_id)
    ideology = roll_ideology(rng, species, planet.culture, parent_objs)
    health = 1.0 + sum(TRAITS[t].get("health", 0) for t in traits)
    p = Person(
        id=world.new_id("person"),
        given=gen_given(rng, sp["names"], sex),
        family=family or gen_family(rng, sp["names"]),
        species=species,
        sex=sex,
        birth_t=birth_t,
        birth_planet=planet_id,
        planet=planet_id,
        faction=faction_id,
        traits=traits,
        stats=stats,
        ideology=ideology,
        origin=origin or rng.choice(ORIGINS),
        health=health,
        parents=tuple(parents),
    )
    world.add_person(p)
    return p


def effective_lifespan(world, person):
    base = SPECIES[person.species]["lifespan"]
    f = world.faction(person.faction)
    if f is not None:
        base *= 1.0 + 0.035 * f.tech.get("medicine", 0)
    return base


def is_adult(world, person):
    return person.age(world.t) >= SPECIES[person.species]["adult"]


def gain_trait(world, person, trait):
    if trait in person.traits:
        return False
    person.traits = [t for t in person.traits if not conflicts(t, trait)] + [trait]
    for s, v in TRAITS[trait].get("stats", {}).items():
        person.stats[s] = min(25, person.stats.get(s, 0) + v)
    person.health += TRAITS[trait].get("health", 0)
    return True


def adjust_opinion(a, b, delta):
    if a is None or b is None or a.id == b.id:
        return
    v = a.opinions.get(b.id, 0) + delta
    a.opinions[b.id] = max(-100, min(100, v))
    if len(a.opinions) > 30:
        # 最も印象の薄い相手を忘れる
        weakest = min(a.opinions, key=lambda k: abs(a.opinions[k]))
        del a.opinions[weakest]


def relocate(world, person, planet_id):
    person.planet = planet_id
    owner = world.planet(planet_id).owner
    if owner is not None:
        person.faction = owner


def siblings(world, person):
    out = set()
    for pid in person.parents:
        par = world.person(pid)
        if par:
            out.update(par.children)
    out.discard(person.id)
    return out


def kill(world, person, cause, importance=None, **ctx):
    """人物を死亡させる。職・婚姻・地位の後始末もここで行う。

    cause: natural / illness / accident / battle / assassinated / executed / plague
    """
    if not person.alive:
        return
    from galaxy.sim import careers, politics  # 循環参照を避けるため遅延 import

    t = world.t
    person.alive = False
    person.death_t = t
    person.death_cause = cause
    age = person.age(t)
    was_leader = None
    for f in world.factions.values():
        if f.alive and f.leader == person.id:
            was_leader = f
    rank_title = careers.job_title(world, person) if person.job else None

    # 遺言
    if cause == "battle":
        words = say(world, person, "death_in_battle", faction=world.fname(person.faction))
    elif cause == "executed":
        words = say(world, person, "executed", enemy=ctx.get("killer", "敵"))
    elif cause == "plague":
        words = say(world, person, "plague_victim")
    else:
        spouse_name = world.pname(person.former_spouses[-1]) if person.former_spouses else ""
        words = say(world, person, "last_words", spouse=spouse_name)

    text = narrate(world, f"death_{cause}", person=_label(world, person, rank_title),
                   planet=world.plname(person.planet), age=age, **ctx)
    person.death_text = text
    if importance is None:
        importance = 1
        if person.fame > 30 or (person.job and person.job.rank >= careers.notable_rank(person.job.track)):
            importance = 2
        if person.fame > 80:
            importance = 3
        if was_leader:
            importance = 4
    show_quote = importance >= 2 and words
    world.record(f"death_{cause}", text, importance, actors=(person.id,), planet=person.planet,
                 factions=(person.faction,) if person.faction else (),
                 quote=words if show_quote else None, speaker=person.id if show_quote else None)

    if person.job:
        careers.clear_job(world, person, end_reason="死去")

    # 配偶者を未亡人に
    if person.spouse is not None:
        sp = world.person(person.spouse)
        if sp and sp.alive:
            sp.spouse = None
            sp.former_spouses.append(person.id)
            gain_trait(world, sp, "未亡人")
            if importance >= 2:
                line = say(world, sp, "widowed", spouse=person.given)
                sp.add_quote(t, line)
            sp.add_bio(t, f"伴侶{person.name}に先立たれた。")
        person.former_spouses.append(person.spouse)
        person.spouse = None

    # 子への影響
    for cid in person.children:
        c = world.person(cid)
        if c and c.alive:
            c.add_bio(t, f"親である{person.name}が亡くなった。")
            if cause in ("assassinated", "executed", "battle") and world.rng.random() < 0.3:
                gain_trait(world, c, "復讐者")

    # 弟子への影響
    for aid in person.apprentices:
        a = world.person(aid)
        if a and a.alive:
            a.add_bio(t, f"師である{person.name}が亡くなった。")

    if was_leader:
        was_leader.leader = None
        politics.close_reign(world, was_leader, person.id)
        politics.succession(world, was_leader, prev=person)


def _label(world, person, rank_title):
    if rank_title:
        return f"{rank_title}{person.name}"
    return person.name
