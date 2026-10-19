"""突発的な出来事：疫病・天災・海賊・遺跡・祭り・芸術・醜聞・預言・暗殺など。

ここで起きる事件が、国家や人物の運命に小さなひびを入れ、物語の種になる。
"""

from galaxy.content import events as ev
from galaxy.content.lore import ANCIENT_RELICS
from galaxy.minds import mind_of
from galaxy.narrative.voice import narrate, say
from galaxy.sim import careers, technology
from galaxy.sim.life import kill, gain_trait, adjust_opinion, is_adult


def monthly(world):
    rng = world.rng
    n = max(1, len(world.planets) // 40)
    for _ in range(n):
        handler = _pick(world)
        handler(world)


def _pick(world):
    table = [
        (_plague, 0.9), (_disaster, 0.9), (_pirates, 1.0), (_relic, 0.7), (_festival, 1.0),
        (_artwork, 1.2), (_scandal, 1.0), (_prophecy, 0.6), (_awakening, 0.7), (_anomaly, 0.4),
        (_exploration, 1.0), (_duel, 0.5), (_assassination, 0.5), (_crime, 0.8), (_refugees, 0.6),
        (_nothing, 6.0),
    ]
    total = sum(w for _, w in table)
    r = world.rng.random() * total
    for h, w in table:
        r -= w
        if r <= 0:
            return h
    return _nothing


def _nothing(world):
    pass


def _random_planet(world, owned=None):
    pls = world.planets
    if owned is True:
        pls = [p for p in pls if p.owner is not None]
    return world.rng.choice(pls) if pls else None


def _people_on(world, pid, adult=True):
    return [p for p in world.by_planet.get(pid, []) if p.alive and (not adult or is_adult(world, p))]


def _people_with(world, track, min_rank=0):
    return [p for p in world.living
            if p.alive and p.job and p.job.track == track and p.job.rank >= min_rank]


# ---------------------------------------------------------------------------
def _plague(world):
    rng = world.rng
    pl = _random_planet(world)
    plague = rng.choice(ev.PLAGUES)
    f = world.faction(pl.owner)
    med = f.tech.get("medicine", 0) if f else 0
    severity = max(0.02, rng.uniform(0.05, 0.25) - med * 0.02)
    pl.population *= 1 - severity * 0.3
    world.record("plague", narrate(world, "plague", planet=pl.name, plague=plague), 3 if severity > 0.15 else 2,
                 planet=pl.id, factions=(pl.owner,) if pl.owner else ())
    for p in _people_on(world, pl.id, adult=False):
        if p.species == "mekan" and plague != "回路錆病":
            continue
        if rng.random() < severity * 0.5 / max(0.4, p.health):
            kill(world, p, "plague", plague=plague)
    if f:
        f.stability -= severity * 20


def _disaster(world):
    rng = world.rng
    pl = _random_planet(world)
    disaster = rng.choice(ev.DISASTERS)
    pl.population *= rng.uniform(0.92, 0.99)
    pl.development = max(0.1, pl.development - rng.uniform(0.02, 0.15))
    world.record("disaster", narrate(world, "disaster", planet=pl.name, disaster=disaster), 2, planet=pl.id,
                 factions=(pl.owner,) if pl.owner else ())
    for p in _people_on(world, pl.id, adult=False):
        if rng.random() < 0.03:
            kill(world, p, "accident", accident=disaster)


def _pirates(world):
    rng = world.rng
    syndicates = [o for o in world.orgs.values() if o.kind == "syndicate" and o.alive]
    pirate_states = [f for f in world.alive_factions() if f.gov == "pirate"]
    if not syndicates and not pirate_states:
        return
    pl = _random_planet(world, owned=True)
    if pl is None:
        return
    org = rng.choice(syndicates).name if syndicates and rng.random() < 0.7 else (
        rng.choice(pirate_states).name if pirate_states else rng.choice(syndicates).name)
    loot = rng.choice(ev.LOOTS)
    f = world.faction(pl.owner)
    f.treasury -= rng.uniform(5, 25)
    world.record("pirate_raid", narrate(world, "pirate_raid", planet=pl.name, loot=loot, org=org), 2,
                 planet=pl.id, factions=(f.id,))


def _relic(world):
    rng = world.rng
    pls = [p for p in world.planets if "ruins" in p.features or p.region in ("outer", "rim")]
    if not pls:
        return
    pl = rng.choice(pls)
    finders = [p for p in _people_on(world, pl.id) if p.job and p.job.track in ("explorer", "academic", "order")]
    if not finders:
        finders = _people_with(world, "explorer")
    if not finders:
        return
    finder = rng.choice(finders)
    relic = rng.choice(ANCIENT_RELICS)
    finder.fame += 20
    finder.merit += 5
    finder.titles.append(f"{relic}の発見者")
    f = world.faction(finder.faction)
    field = technology.relic_boost(world, f, 80) if f else None
    line = say(world, finder, "discovery")
    text = narrate(world, "relic_found", person=finder.name, planet=pl.name, relic=relic)
    if field:
        text += f"{f.name}の{field}研究は大きく前進するだろう。"
    world.record("relic_found", text, 3, actors=(finder.id,), planet=pl.id,
                 factions=(f.id,) if f else (), quote=line, speaker=finder.id)


def _festival(world):
    rng = world.rng
    pl = _random_planet(world, owned=True)
    if pl is None:
        return
    f = world.faction(pl.owner)
    f.stability = min(100, f.stability + 2)
    pl.unrest = max(0, pl.unrest - 5)
    world.record("festival", narrate(world, "festival", planet=pl.name, festival=rng.choice(ev.FESTIVALS)), 1,
                 planet=pl.id, factions=(f.id,))


def _artwork(world):
    rng = world.rng
    artists = _people_with(world, "arts")
    if not artists:
        return
    a = rng.choice(artists)
    title = rng.choice(ev.WORK_TITLE_A) + rng.choice(ev.WORK_TITLE_B)
    work = rng.choice(ev.WORK_TYPES)
    quality = a.stat("diplomacy") + a.stat("learning") + rng.uniform(0, 15) + (8 if a.has("詩人気質") else 0)
    a.fame += quality / 3
    if quality > 30:
        a.titles.append(f"『{title}』の作者")
    line = say(world, a, "artwork")
    world.record("artwork", narrate(world, "artwork", person=a.name, work=work, title=title),
                 2 if quality > 28 else 1, actors=(a.id,), planet=a.planet, quote=line, speaker=a.id)


def _scandal(world):
    rng = world.rng
    cands = [p for p in world.living
             if p.alive and p.job and p.job.track in ("government", "corporate", "military")
             and p.job.rank >= 4]
    if not cands:
        return
    weights = [1 + max(0, -p.disposition("honesty")) * 2 + max(0, p.disposition("greed")) for p in cands]
    p = rng.choices(cands, weights)[0]
    scandal = rng.choice(ev.SCANDALS)
    p.fame = max(0, p.fame - 10)
    world.record("scandal", narrate(world, "scandal", person=f"{careers.describe_job(world, p)}の{p.name}",
                                    scandal=scandal), 2, actors=(p.id,), planet=p.planet,
                 factions=(p.faction,) if p.faction else ())
    f = world.faction(p.faction)
    is_leader = f is not None and f.leader == p.id
    if is_leader:
        f.stability -= 8
    elif rng.random() < 0.5:
        org = careers.org_name(world, p.job.track, p.job.org_id)
        careers.clear_job(world, p, end_reason=scandal)
        world.record("fired", narrate(world, "fired", person=p.name, reason=scandal, org=org), 1,
                     actors=(p.id,), planet=p.planet)


def _prophecy(world):
    rng = world.rng
    seers = [p for p in _people_with(world, "order") if p.stat("resonance") >= 12]
    if not seers:
        return
    s = rng.choice(seers)
    if rng.random() < 0.3:
        gain_trait(world, s, "預言者")
    s.fame += 5
    line = say(world, s, "prophecy")
    world.record("prophecy", narrate(world, "prophecy", person=s.name, planet=world.plname(s.planet)), 2,
                 actors=(s.id,), planet=s.planet, quote=line, speaker=s.id)


def _awakening(world):
    rng = world.rng
    pl = _random_planet(world)
    young = [p for p in _people_on(world, pl.id, adult=False) if p.stat("resonance") < 8
             and p.age(world.t) < 30 and p.species != "mekan"]
    if not young:
        return
    p = rng.choice(young)
    f = world.faction(p.faction)
    bonus = f.tech.get("resonance", 0) if f else 0
    p.stats["resonance"] = rng.randint(9, 15) + bonus
    world.record("resonance_awakening", narrate(world, "resonance_awakening", planet=pl.name, person=p.name), 2,
                 actors=(p.id,), planet=pl.id)
    if p.job and p.job.track not in ("order",) and is_adult(world, p) and rng.random() < 0.5:
        careers.clear_job(world, p, end_reason="共鳴の目覚め")
        order = careers._light_order(world)
        if order:
            careers.assign_job(world, p, "order", order.id, 0)
            careers._assign_mentor(world, p)


def _anomaly(world):
    rng = world.rng
    pls = [p for p in world.planets if p.region in ("outer", "rim")] or world.planets
    pl = rng.choice(pls)
    world.record("anomaly", narrate(world, "anomaly", planet=pl.name, anomaly=rng.choice(ev.ANOMALIES)), 2,
                 planet=pl.id)


def _exploration(world):
    rng = world.rng
    explorers = _people_with(world, "explorer")
    if not explorers:
        return
    e = rng.choice(explorers)
    risk = 0.12 - e.stat("command") * 0.004
    if rng.random() < risk:
        world.record("exploration_lost", narrate(world, "exploration_lost", person=e.name), 2,
                     actors=(e.id,), planet=e.planet)
        kill(world, e, "accident", importance=1, accident="未踏宙域での遭難")
        return
    e.fame += 6
    e.merit += 4
    f = world.faction(e.faction)
    if f:
        f.research["propulsion"] = f.research.get("propulsion", 0) + 20
    line = say(world, e, "discovery")
    world.record("exploration", narrate(world, "exploration", person=e.name, faction=f.name if f else "銀河",
                                        planet=world.plname(e.planet)), 1,
                 actors=(e.id,), planet=e.planet, quote=line, speaker=e.id)


def _duel(world):
    rng = world.rng
    pairs = [(p, world.person(r)) for p in world.living if p.alive for r in p.rivals]
    pairs = [(a, b) for a, b in pairs if b and b.alive and a.planet == b.planet
             and (a.disposition("boldness") > 0 or a.has("激情家"))]
    if not pairs:
        return
    a, b = rng.choice(pairs)
    sa = a.stat("martial") + a.stat("resonance") / 2 + rng.uniform(0, 10)
    sb = b.stat("martial") + b.stat("resonance") / 2 + rng.uniform(0, 10)
    winner, loser = (a, b) if sa > sb else (b, a)
    winner.fame += 8
    world.record("duel", narrate(world, "duel", person=a.name, target=b.name, planet=world.plname(a.planet),
                                 winner=winner.name), 2, actors=(a.id, b.id), planet=a.planet)
    if rng.random() < 0.3:
        kill(world, loser, "accident", accident=f"{winner.name}との決闘")
    else:
        gain_trait(world, loser, "傷痕")
        adjust_opinion(loser, winner, -20)


def _assassination(world):
    rng = world.rng
    leaders = [world.person(f.leader) for f in world.alive_factions() if f.leader]
    leaders = [p for p in leaders if p and p.alive]
    if not leaders:
        return
    target = rng.choice(leaders)
    f = world.faction(target.faction)
    plotters = [world.person(r) for r in target.rivals] + [
        p for p in world.living
        if p.alive and p.faction == target.faction and p.opinions.get(target.id, 0) < -40]
    plotters = [p for p in plotters if p and p.alive and p.disposition("honesty") < 0]
    if not plotters and f.stability > 30:
        return
    plotter = rng.choice(plotters) if plotters else None
    if plotter:
        plotter.add_quote(world.t, say(world, plotter, "assassination_plot"))
    if rng.random() < 0.35:
        kill(world, target, "assassinated", method=rng.choice(ev.ASSASSINATION_METHODS))
        if plotter:
            plotter.add_bio(world.t, f"{target.name}の暗殺に関与したと噂された。")
    else:
        world.record("assassination_failed", narrate(world, "assassination_failed", target=target.name,
                                                     planet=world.plname(target.planet)), 3,
                     actors=(target.id,), planet=target.planet, factions=(f.id,) if f else ())
        if plotter and rng.random() < 0.5:
            kill(world, plotter, "executed", importance=2, killer=target.name)


def _crime(world):
    rng = world.rng
    synds = [o for o in world.orgs.values() if o.kind == "syndicate" and o.alive]
    if not synds:
        return
    o = rng.choice(synds)
    boss = world.person(o.leader)
    pl = world.planet(o.seat)
    if rng.random() < 0.5 and pl.owner:
        f = world.faction(pl.owner)
        o.power *= 0.85
        world.record("smuggling_bust", narrate(world, "smuggling_bust", faction=f.name, org=o.name), 1,
                     planet=pl.id, factions=(f.id,))
    elif boss:
        o.power *= 1.1
        line = say(world, boss, "crime")
        world.record("crime_boss", narrate(world, "crime_boss", org=o.name, person=boss.name, planet=pl.name), 1,
                     actors=(boss.id,), planet=pl.id, quote=line, speaker=boss.id)


def _refugees(world):
    rng = world.rng
    wars = world.active_wars()
    if not wars:
        return
    w = rng.choice(wars)
    neutral = [p for p in world.planets if p.owner is not None and p.owner not in w.sides()]
    if not neutral:
        return
    pl = rng.choice(neutral)
    pl.population *= 1.01
    pl.unrest += 3
    world.record("refugees", narrate(world, "refugees", war=w.name, planet=pl.name), 1, planet=pl.id)
