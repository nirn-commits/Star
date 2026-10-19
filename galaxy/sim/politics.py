"""国家の内政：継承・選挙・政変・独立運動・理念の変化・領土の移動。"""

from galaxy.content.governments import GOVERNMENTS, leader_title
from galaxy.content.ideologies import IDEOLOGIES, compatibility
from galaxy.content.careers import CAREERS
from galaxy.minds import mind_of
from galaxy.narrative.voice import narrate, say, exchange
from galaxy.sim import careers
from galaxy.sim.life import (create_person, kill, is_adult, gain_trait, relocate, adjust_opinion,
                             siblings)

GOV_TOP = careers.top_rank("government")


# ---------------------------------------------------------------------- 元首の交代
def close_reign(world, faction, pid):
    for i, (rid, start, end) in enumerate(faction.rulers):
        if rid == pid and end is None:
            faction.rulers[i] = (rid, start, world.t)


def install_leader(world, faction, person, kind, prev=None, share=None, quiet=False):
    """人物を元首に据える。"""
    old = world.person(faction.leader) if faction.leader else None
    if old is not None and old.id != person.id:
        close_reign(world, faction, old.id)
        if old.alive and old.job and old.job.track == "government" and old.job.org_id == faction.id:
            careers.set_rank(world, old, GOV_TOP - 1)
    if person.planet not in faction.planets:
        relocate(world, person, faction.capital)
    person.faction = faction.id
    j = person.job
    if not (j and j.track == "government" and j.org_id == faction.id and j.rank == GOV_TOP):
        careers.assign_job(world, person, "government", faction.id, GOV_TOP, end_reason="元首に就任")
    faction.leader = person.id
    faction.rulers.append((person.id, world.t, None))
    if GOVERNMENTS[faction.gov]["succession"] == "elective":
        faction.last_election_t = world.t
    title = leader_title(faction.gov, person.sex)
    person.titles.append(f"{faction.name}{title}")
    person.fame += 40
    if GOVERNMENTS[faction.gov]["succession"] == "hereditary" and faction.dynasty != person.family:
        if faction.dynasty and not quiet:
            world.record("new_dynasty", f"{faction.name}に新たな王朝「{person.family}朝」が開かれた。", 4,
                         actors=(person.id,), factions=(faction.id,), planet=faction.capital)
        faction.dynasty = person.family
    if quiet:
        return
    prev_name = prev.name if prev else "先代"
    if kind == "hereditary":
        text = narrate(world, "succession_hereditary", prev=prev_name, person=person.name,
                       faction=faction.name, title=title)
        line = say(world, person, "crowned", faction=faction.name)
        if prev and prev.id in person.parents and world.rng.random() < 0.5:
            line = say(world, person, "succession_heir") or line
    elif kind == "elective":
        text = narrate(world, "succession_elective", person=person.name, faction=faction.name,
                       title=title, share=share or world.rng.randint(38, 71))
        line = say(world, person, "elected")
    elif kind == "reelected":
        text = narrate(world, "election_reelected", person=person.name, faction=faction.name)
        line = say(world, person, "elected")
    else:
        text = narrate(world, "succession_other", prev=prev_name, person=person.name,
                       faction=faction.name, title=title)
        line = say(world, person, "crowned", faction=faction.name)
    world.record("succession", text, 4 if kind != "reelected" else 3, actors=(person.id,),
                 factions=(faction.id,), planet=faction.capital, quote=line, speaker=person.id)


def succession(world, faction, prev=None):
    """元首の座が空いたときに後継者を決める。"""
    if not faction.alive:
        return
    kind = GOVERNMENTS[faction.gov]["succession"]
    heir = None
    if kind == "hereditary":
        heir = _hereditary_heir(world, faction, prev)
        how = "hereditary"
    elif kind == "elective":
        heir, share = _hold_election(world, faction, exclude=prev)
        if heir:
            install_leader(world, faction, heir, "elective", prev, share)
            return
        how = "other"
    else:
        heir = _special_heir(world, faction, kind)
        how = "other"
    if heir is None:
        heir = _best_official(world, faction)
    if heir is None:
        heir = _spawn_leader(world, faction)
    install_leader(world, faction, heir, how, prev)


def _citizens(world, faction):
    return [p for p in world.living
            if p.alive and p.faction == faction.id and is_adult(world, p)]


def _hereditary_heir(world, faction, prev):
    if prev is None:
        return None
    adult = lambda p: p and p.alive and is_adult(world, p)
    kids = sorted((world.person(c) for c in prev.children), key=lambda p: p.birth_t if p else 0)
    for c in kids:
        if adult(c):
            return c
    if prev.spouse and adult(world.person(prev.spouse)):
        return world.person(prev.spouse)
    for sid in sorted(siblings(world, prev)):
        s = world.person(sid)
        if adult(s):
            return s
    kin = [p for p in _citizens(world, faction) if p.family == prev.family and p.species == prev.species]
    if kin:
        return max(kin, key=lambda p: p.fame)
    return None


def _special_heir(world, faction, kind):
    cits = _citizens(world, faction)
    if kind == "military":
        mil = [p for p in cits if p.job and p.job.track == "military" and p.job.org_id == faction.id]
        return max(mil, key=lambda p: (p.job.rank, p.stat("command")), default=None)
    if kind == "order":
        ords = [p for p in cits if p.job and p.job.track == "order"]
        return max(ords, key=lambda p: (p.job.rank, p.stat("resonance")), default=None)
    if kind == "corporate":
        ceos = [world.person(c.ceo) for c in world.corps.values()
                if c.alive and c.faction == faction.id and c.ceo]
        ceos = [p for p in ceos if p and p.alive]
        return max(ceos, key=lambda p: p.wealth, default=None)
    if kind == "strongest":
        fighters = [p for p in cits if p.job and p.job.track in ("military", "underworld")]
        return max(fighters, key=lambda p: p.stat("martial") + p.fame / 5 + world.rng.random() * 5, default=None)
    if kind == "hive":
        same = [p for p in cits if p.species == faction.main_species]
        return max(same, key=lambda p: world.t - p.birth_t, default=None)
    return None


def _best_official(world, faction):
    gov = [p for p in _citizens(world, faction) if p.job and p.job.track == "government"
           and p.job.org_id == faction.id]
    return max(gov, key=lambda p: (p.job.rank, p.stat("diplomacy")), default=None)


def _spawn_leader(world, faction):
    rng = world.rng
    from galaxy.content.species import SPECIES
    sp = SPECIES[faction.main_species]
    age = rng.uniform(sp["adult"] + 10, sp["adult"] + sp["lifespan"] * 0.4)
    p = create_person(world, faction.main_species, faction.capital, faction.id, world.t - int(age * 12),
                      origin="名門家の出")
    p.ideology = faction.ideology if rng.random() < 0.7 else p.ideology
    p.add_bio(world.t, f"混乱の中、{faction.name}の指導者として担ぎ出された。")
    return p


def _hold_election(world, faction, exclude=None):
    rng = world.rng
    gov = [p for p in _citizens(world, faction)
           if p.job and p.job.track == "government" and p.job.org_id == faction.id
           and p.job.rank >= GOV_TOP - 3 and (exclude is None or p.id != exclude.id)]
    if not gov:
        return None, None
    rng.shuffle(gov)
    cands = gov[:4]
    def votes(p):
        return (p.stat("diplomacy") * 2 + p.fame / 4 + (8 if p.ideology == faction.ideology else 0)
                + rng.uniform(0, 15) + (6 if p.has("美貌") else 0) + (5 if p.has("社交的") else 0))
    scored = sorted(((votes(p), p) for p in cands), key=lambda x: -x[0])
    total = sum(max(v, 1) for v, _ in scored)
    winner = scored[0][1]
    share = int(100 * max(scored[0][0], 1) / total)
    if len(scored) == 1:
        share = rng.randint(52, 78)  # 対立候補は名もなき泡沫候補だけだった
    for v, loser in scored[1:2]:
        line = say(world, loser, "election_lost")
        loser.add_quote(world.t, line)
        loser.add_bio(world.t, f"{faction.name}の元首選挙に敗れた。")
        adjust_opinion(loser, winner, -20)
    return winner, share


def _elections(world, faction):
    g = GOVERNMENTS[faction.gov]
    if g["succession"] != "elective" or not g["term"]:
        return
    if world.t - faction.last_election_t < g["term"] * 12:
        return
    faction.last_election_t = world.t
    incumbent = world.person(faction.leader)
    winner, share = _hold_election(world, faction, exclude=incumbent)
    if incumbent and incumbent.alive:
        # 現職は実績で票を得る
        inc_score = incumbent.stat("diplomacy") * 2 + faction.stability / 3 - faction.exhaustion / 3 + world.rng.uniform(0, 15)
        if winner is None or inc_score > winner.stat("diplomacy") * 2 + winner.fame / 4 + world.rng.uniform(0, 15):
            world.record("election", narrate(world, "election_reelected", person=incumbent.name,
                                             faction=faction.name), 2, actors=(incumbent.id,),
                         factions=(faction.id,), planet=faction.capital,
                         quote=say(world, incumbent, "elected"), speaker=incumbent.id)
            return
        line = say(world, incumbent, "election_lost")
        incumbent.add_quote(world.t, line)
    if winner:
        install_leader(world, faction, winner, "elective", incumbent, share)
        _maybe_shift_ideology(world, faction, winner, chance=0.5)


# ---------------------------------------------------------------------- 安定度・政変
def monthly(world):
    for f in world.alive_factions():
        if f.leader is None or not world.person(f.leader) or not world.person(f.leader).alive:
            f.leader = None
            succession(world, f)
        _stability(world, f)
        _elections(world, f)
        if f.stability < 35 and world.rng.random() < 0.008:
            _coup(world, f)
        leader = world.person(f.leader)
        if leader and leader.ideology != f.ideology and world.rng.random() < 0.004:
            _maybe_shift_ideology(world, f, leader, chance=1.0)
    dist = {f.id: _hops_from(world, f.capital) for f in world.alive_factions()}
    for pl in world.planets:
        _planet_unrest(world, pl, dist.get(pl.owner, {}))
    if world.t % 3 == 0:
        _colonize(world)
    if world.t % 6 == 0:
        _unification(world)


def _stability(world, f):
    g = GOVERNMENTS[f.gov]
    leader = world.person(f.leader)
    target = g["stability"]
    if leader:
        target += (leader.stat("diplomacy") + leader.stat("command")) / 4 - 5
        if leader.has("残忍"):
            target -= 5
        if leader.has("慈悲深い") or leader.has("誠実"):
            target += 4
    target -= f.exhaustion * 0.4
    # 広すぎる国は統治が行き届かない
    target -= max(0, len(f.planets) - 10) * 1.0
    if f.treasury < 0:
        target -= 15
    unrest = sum(world.planet(pid).unrest for pid in f.planets) / max(1, len(f.planets))
    target -= unrest * 0.3
    f.stability += (target - f.stability) * 0.05 + world.rng.uniform(-1.2, 1.2)
    f.stability = max(0.0, min(100.0, f.stability))
    if not world.active_wars() or not world.wars_of(f.id):
        f.exhaustion = max(0.0, f.exhaustion - 0.5)
    if f.stability < 20 and world.rng.random() < 0.02:
        world.record("stability_crisis", narrate(world, "stability_crisis", faction=f.name,
                                                 planet=world.plname(f.capital)), 2,
                     factions=(f.id,), planet=f.capital)


def _coup(world, f):
    rng = world.rng
    leader = world.person(f.leader)
    if leader is None:
        return
    plotters = [p for p in _citizens(world, f)
                if p.job and p.job.org_id == f.id and p.id != leader.id
                and ((p.job.track == "military" and p.job.rank >= 8)
                     or (p.job.track == "government" and p.job.rank >= GOV_TOP - 2))]
    plotters = [p for p in plotters if mind_of(world, p).plot_coup(world, p, f)]
    if not plotters:
        return
    plotter = max(plotters, key=lambda p: p.stat("command") + p.stat("intellect"))
    power = plotter.stat("command") + plotter.stat("intellect") / 2 + rng.uniform(0, 15)
    resist = leader.stat("command") / 2 + f.stability / 3 + rng.uniform(0, 15)
    a, b = exchange(world, "conspiracy")
    world.record("conspiracy", f"{f.name}の{careers.job_title(world, plotter)}{plotter.name}が、密かに同志を集めている。",
                 1, actors=(plotter.id,), factions=(f.id,), planet=plotter.planet,
                 quote=a, speaker=plotter.id, reply=b, replier=None)
    if power > resist:
        line = say(world, plotter, "coup", target=leader.name)
        world.record("coup", narrate(world, "coup", faction=f.name, person=plotter.name, target=leader.name), 5,
                     actors=(plotter.id, leader.id), factions=(f.id,), planet=f.capital,
                     quote=line, speaker=plotter.id)
        leader.add_quote(world.t, say(world, leader, "deposed"))
        close_reign(world, f, leader.id)
        f.leader = None
        if rng.random() < 0.45:
            kill(world, leader, "executed", importance=4, killer=plotter.name)
        else:
            careers.clear_job(world, leader, end_reason="政変で失脚")
            _exile(world, leader, f)
        install_leader(world, f, plotter, "coup", leader, quiet=True)
        f.stability = max(f.stability, 30)  # 新体制にはしばしの猶予が与えられる
        if plotter.job and rng.random() < 0.5 and f.gov not in ("junta",):
            if GOVERNMENTS[f.gov]["succession"] != "hereditary" or rng.random() < 0.5:
                change_government(world, f, "junta")
        _maybe_shift_ideology(world, f, plotter, chance=0.7)
    else:
        world.record("coup_failed", narrate(world, "coup_failed", faction=f.name, person=plotter.name), 3,
                     actors=(plotter.id,), factions=(f.id,), planet=f.capital)
        if rng.random() < 0.6:
            kill(world, plotter, "executed", importance=3, killer=leader.name)
        else:
            careers.clear_job(world, plotter, end_reason="反逆罪で投獄")
            plotter.fame += 10


def _exile(world, person, faction):
    others = [pl for pl in world.planets if pl.owner not in (None, faction.id)]
    if not others:
        return
    dest = world.rng.choice(others)
    relocate(world, person, dest.id)
    gain_trait(world, person, "亡命者")
    line = say(world, person, "exile")
    world.record("exile", narrate(world, "exile", person=person.name, planet=dest.name), 2,
                 actors=(person.id,), planet=dest.id, quote=line, speaker=person.id)


def _maybe_shift_ideology(world, f, person, chance):
    if person.ideology == f.ideology or world.rng.random() > chance:
        return
    old = IDEOLOGIES[f.ideology]["name"]
    f.ideology = person.ideology
    f.motto = world.rng.choice(IDEOLOGIES[f.ideology]["slogans"])
    new = IDEOLOGIES[f.ideology]["name"]
    world.record("ideology_shift", narrate(world, "ideology_shift", faction=f.name, old=old, new=new,
                                           person=person.name), 4,
                 actors=(person.id,), factions=(f.id,), planet=f.capital)
    govs = IDEOLOGIES[f.ideology]["govs"]
    if f.gov not in govs and world.rng.random() < 0.5:
        change_government(world, f, world.rng.choice(govs))


def change_government(world, f, new_gov):
    if new_gov == f.gov:
        return
    from galaxy.content.governments import GOVERNMENTS as G
    old_name = G[f.gov]["name"]
    old_full = f.name
    f.gov = new_gov
    f.name = f.base_name + world.rng.choice(G[new_gov]["suffixes"])
    if G[new_gov]["succession"] == "elective":
        f.last_election_t = world.t
    world.record("gov_change", narrate(world, "gov_change", faction=old_full, old=old_name,
                                       new=G[new_gov]["name"], new_name=f.name), 4,
                 factions=(f.id,), planet=f.capital)


# ---------------------------------------------------------------------- 独立運動
def _hops_from(world, start):
    dist = {start: 0}
    frontier = [start]
    while frontier:
        nxt = []
        for a in frontier:
            for b in world.planet(a).lanes:
                if b not in dist:
                    dist[b] = dist[a] + 1
                    nxt.append(b)
        frontier = nxt
    return dist


def _planet_unrest(world, pl, dist):
    if pl.owner is None:
        pl.unrest = max(0.0, pl.unrest - 1)
        return
    f = world.faction(pl.owner)
    target = 0.0
    if pl.culture != f.ideology:
        target += (1 - compatibility(pl.culture, f.ideology)) * 12
    if pl.species != f.main_species:
        target += 8 if f.ideology != "purity" else 30
    if pl.conquered_t is not None and world.t - pl.conquered_t < 240:
        target += 25 * (1 - (world.t - pl.conquered_t) / 240)
    target += (50 - f.stability) * 0.3
    target += max(0, dist.get(pl.id, 0) - 3) * 2.0
    if pl.id == f.capital:
        target *= 0.3
    pl.unrest += (target - pl.unrest) * 0.04 + world.rng.uniform(-0.5, 0.5)
    pl.unrest = max(0.0, min(100.0, pl.unrest))
    # 文化はゆっくりと支配者の理念に染まっていく
    if world.rng.random() < 0.0015:
        pl.culture = f.ideology
    crowd = len(world.factions_alive_cache) / max(1, len(world.planets) / 6)
    if (pl.unrest > 50 and pl.id != f.capital and len(f.planets) > 3
            and world.rng.random() < 0.0015 * (1 + (pl.unrest - 50) / 15) / max(0.5, crowd)):
        revolt(world, pl)


def revolt(world, pl):
    rng = world.rng
    from galaxy.sim import diplomacy
    old = world.faction(pl.owner)
    locals_ = [p for p in world.by_planet.get(pl.id, []) if p.alive and is_adult(world, p)]
    if locals_:
        leader = max(locals_, key=lambda p: p.disposition("ambition") + p.disposition("boldness")
                     + p.stat("command") / 5 + rng.random() * 2)
    else:
        leader = _spawn_leader_at(world, pl)
    ideology = leader.ideology if leader.ideology != old.ideology else pl.culture
    if ideology == old.ideology:
        ideology = rng.choice(["liberation", "republic", "freetrade", "purity"])
    nf = found_faction(world, pl, ideology, leader, parent=old)
    line = say(world, leader, "revolution", faction=old.name, planet=pl.name)
    world.record("revolution", narrate(world, "revolution", planet=pl.name, faction=old.name,
                                       new_faction=nf.name, person=leader.name), 5,
                 actors=(leader.id,), factions=(old.id, nf.id), planet=pl.id, quote=line, speaker=leader.id)
    # 不満を抱える近隣の星々も合流する。大国が揺らいでいるほど大きな塊が離れる
    limit = 1 + int(max(0, 45 - old.stability) / 10) + len(old.planets) // 12
    frontier = [pl.id]
    joined = 0
    while frontier and joined < limit:
        cur = frontier.pop(0)
        for nid in world.planet(cur).lanes:
            n = world.planet(nid)
            if (n.owner == old.id and n.unrest > 25 and n.id != old.capital and joined < limit
                    and rng.random() < 0.7):
                transfer_planet(world, n.id, nf.id, reason="合流")
                frontier.append(n.id)
                joined += 1
    pl.unrest = 0
    nf.stability = 55
    share = min(0.6, 0.1 + 1.2 * len(nf.planets) / max(1, len(old.planets) + len(nf.planets)))
    nf.fleet = old.fleet * share
    old.fleet -= nf.fleet * 0.8
    nf.treasury = old.treasury * share * 0.5
    world.record("defection", f"{old.name}の艦隊の一部が離反し、{nf.name}に合流した。", 3,
                 factions=(old.id, nf.id), planet=pl.id)
    w = diplomacy.declare_war(world, old, nf, "independence", goal=pl.id)
    # 旧宗主国を憎む国々が独立派を支援する（多くても二か国まで）
    supporters = 0
    for g in sorted(world.alive_factions(), key=lambda x: x.relations.get(old.id, 0)):
        if supporters >= 2:
            break
        if g.id in (old.id, nf.id) or g.id in w.sides():
            continue
        if g.relations.get(old.id, 0) < -30 and old.id in world.neighbors.get(g.id, set()) and rng.random() < 0.5:
            w.defenders.add(g.id)
            supporters += 1
            nf.relations[g.id] = 50
            g.relations[nf.id] = 40
            world.record("war_joined", f"{g.name}は{nf.name}の独立を支持し、{w.name}に参戦した。", 3,
                         factions=(g.id, nf.id, old.id))


def _spawn_leader_at(world, pl):
    from galaxy.content.species import SPECIES
    sp = SPECIES[pl.species]
    age = world.rng.uniform(sp["adult"] + 5, sp["adult"] + sp["lifespan"] * 0.3)
    return create_person(world, pl.species, pl.id, pl.owner, world.t - int(age * 12), origin="反乱の指導者")


def found_faction(world, capital_planet, ideology, leader, parent=None):
    from galaxy.model.entities import Faction
    from galaxy.content.technologies import TECH_KEYS
    rng = world.rng
    govs = IDEOLOGIES[ideology]["govs"]
    gov = rng.choice(govs)
    base = capital_planet.name.replace(" ", "")
    if rng.random() < 0.4:
        base = rng.choice(["新", "自由", "真", "第二", "辺境"]) + base
    nf = Faction(id=world.new_id("faction"), name=base + rng.choice(GOVERNMENTS[gov]["suffixes"]),
                 base_name=base, gov=gov, ideology=ideology, capital=capital_planet.id,
                 founded_t=world.t, main_species=capital_planet.species,
                 motto=rng.choice(IDEOLOGIES[ideology]["slogans"]), parent=parent.id if parent else None)
    nf.tech = dict(parent.tech) if parent else {k: 0 for k in TECH_KEYS}
    nf.research = {k: 0.0 for k in TECH_KEYS}
    nf.treasury = 40
    nf.last_election_t = world.t
    world.factions[nf.id] = nf
    if parent:
        nf.relations[parent.id] = -60
        parent.relations[nf.id] = -60
        nf.legend = f"{parent.name}の圧政に抗い、{capital_planet.name}の民が立ち上がったことで生まれた国。"
    transfer_planet(world, capital_planet.id, nf.id, reason="独立")
    if leader.job:
        careers.clear_job(world, leader, end_reason="独立運動の指導者となる")
    install_leader(world, nf, leader, "founder", quiet=True)
    leader.titles.append(f"{nf.name}の建国者")
    return nf


# ---------------------------------------------------------------------- 領土
def transfer_planet(world, planet_id, new_owner, reason=""):
    pl = world.planet(planet_id)
    old_id = pl.owner
    if old_id == new_owner:
        return
    old = world.faction(old_id)
    new = world.faction(new_owner)
    pl.owner = new_owner
    if old:
        old.planets.discard(planet_id)
    if new:
        new.planets.add(planet_id)
    if reason in ("征服", "割譲"):
        pl.conquered_t = world.t
        pl.unrest = min(100, pl.unrest + 30)
    pl.defense = 10 + pl.development * 10
    # 住民の処遇
    for p in [p for p in world.living if p.alive and p.planet == planet_id]:
        loyal_job = (p.job and p.job.org_id == old_id
                     and p.job.track in ("military", "government", "academic"))
        if loyal_job and old and old.alive and old.planets and old.id != new_owner:
            relocate(world, p, old.capital if old.capital in old.planets else next(iter(old.planets)))
        else:
            if loyal_job:
                careers.clear_job(world, p, end_reason="祖国の喪失")
            p.faction = new_owner
    if old and old.alive:
        if not old.planets:
            fall_faction(world, old, conqueror=new, last_planet=pl, peaceful=(reason == "合流"))
        elif old.capital == planet_id:
            newcap = max(old.planets, key=lambda i: world.planet(i).population)
            old.capital = newcap
            world.record("capital_moved", f"{old.name}は首都を{world.plname(newcap)}へ移した。", 3,
                         factions=(old.id,), planet=newcap)


def fall_faction(world, f, conqueror=None, last_planet=None, peaceful=False):
    f.alive = False
    f.fall_t = world.t
    years = (world.t - f.founded_t) // 12
    if peaceful:
        world.record("faction_merged", f"{f.name}は{years}年の歴史を閉じ、{conqueror.name}の一部となった。", 3,
                     factions=(f.id, conqueror.id))
        conqueror = None
    else:
        world.record("faction_fall", narrate(world, "faction_fall", faction=f.name, years=years,
                                             planet=last_planet.name if last_planet else "最後の星"), 5,
                     factions=(f.id,), planet=last_planet.id if last_planet else None)
    leader = world.person(f.leader)
    close_reign(world, f, f.leader)
    f.leader = None
    for key in [k for k in world.treaties if f.id in k]:
        del world.treaties[key]
    for w in world.active_wars():
        w.attackers.discard(f.id)
        w.defenders.discard(f.id)
    # 旧臣たちの行く末
    for p in [p for p in world.living if p.alive and p.job and p.job.org_id == f.id
              and p.job.track in ("military", "government", "academic")]:
        careers.clear_job(world, p, end_reason="祖国の滅亡")
        gain_trait(world, p, "亡命者")
    for p in world.living:
        if p.alive and p.faction == f.id:
            p.faction = world.planet(p.planet).owner
    if leader and leader.alive:
        if conqueror and world.rng.random() < 0.4:
            kill(world, leader, "executed", importance=4, killer=conqueror.name)
        else:
            _exile(world, leader, f)
    for c in world.corps.values():
        if c.faction == f.id:
            c.faction = world.planet(c.hq).owner


def _colonize(world):
    """国家が隣接する無主の惑星へ植民する。"""
    rng = world.rng
    for pl in world.planets:
        if pl.owner is not None:
            continue
        claimants = {world.planet(n).owner for n in pl.lanes} - {None}
        claimants = [world.faction(c) for c in claimants if world.faction(c).alive]
        if not claimants:
            continue
        f = rng.choice(claimants)
        if f.treasury < 60 or rng.random() > 0.03:
            continue
        f.treasury -= 40
        transfer_planet(world, pl.id, f.id, reason="植民")
        world.record("colonize", narrate(world, "colonize", faction=f.name, planet=pl.name), 2,
                     factions=(f.id,), planet=pl.id)


def _unification(world):
    """弱小国が、理念を同じくする大国の庇護を求めて自ら併合を受け入れる。"""
    rng = world.rng
    factions = world.alive_factions()
    crowd = len(factions) / max(1, len(world.planets) / 6)
    for f in factions:
        if len(f.planets) > 2 or world.wars_of(f.id) or rng.random() > 0.04 * crowd:
            continue
        cands = []
        for gid in world.neighbors.get(f.id, ()):
            g = world.faction(gid)
            if not g.alive or len(g.planets) <= len(f.planets) * 2:
                continue
            rel = f.relations.get(gid, 0)
            if rel > 20 and compatibility(f.ideology, g.ideology) > 0.2:
                cands.append((rel + rng.uniform(0, 20), g))
        if not cands:
            continue
        _, g = max(cands, key=lambda x: x[0])
        leader = world.person(f.leader)
        text = (f"{f.name}は{g.name}への合流を決議した。"
                f"{len(f.planets)}つの星系が平和裡に{g.name}の一部となった。")
        world.record("unification", text, 4, actors=(leader.id,) if leader else (),
                     factions=(f.id, g.id), planet=f.capital)
        if leader:
            careers.clear_job(world, leader, end_reason="国家の合流")
            leader.titles.append(f"{f.name}最後の{leader_title(f.gov, leader.sex)}")
            leader.fame += 10
        f.leader = None
        close_reign(world, f, leader.id if leader else None)
        for pid in sorted(f.planets):
            transfer_planet(world, pid, g.id, reason="合流")
