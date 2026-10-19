"""銀河の生成：星々、航路、国家、企業、組織、そして最初の人々。"""

import math

from galaxy.content.lore import REGIONS, ANCIENT_EVENTS
from galaxy.content.planets import (PLANET_TYPES, PLANET_FEATURES, NAME_PREFIX, NAME_MID, NAME_SUFFIX,
                                    NAME_DECOR, CORE_RELIC_PLANET)
from galaxy.content.species import SPECIES, SPECIES_WEIGHTS
from galaxy.content.ideologies import IDEOLOGIES, compatibility
from galaxy.content.governments import GOVERNMENTS
from galaxy.content.technologies import TECH_KEYS
from galaxy.content.corporations import SECTORS, CORP_MOTTOS
from galaxy.content.careers import cap_for
from galaxy.model.entities import Planet, Faction, Corporation, Organization
from galaxy.model.world import World
from galaxy.sim import careers, politics, demography
from galaxy.sim.life import create_person, roll_ideology, weighted_choice, is_adult

REGION_TYPE_WEIGHTS = {
    "core": {"ecumenopolis": 4, "temperate": 3, "ocean": 2, "desert": 1, "jungle": 1, "barren": 1},
    "inner": {"temperate": 3, "ocean": 2, "desert": 2, "jungle": 2, "ecumenopolis": 1, "ice": 1, "gas_moon": 1, "volcanic": 1},
    "mid": {"desert": 2, "jungle": 2, "ice": 2, "volcanic": 2, "barren": 2, "gas_moon": 2, "temperate": 2, "ocean": 1, "toxic": 1, "asteroid": 1},
    "outer": {"barren": 3, "ice": 2, "volcanic": 2, "toxic": 2, "asteroid": 2, "desert": 2, "gas_moon": 2, "jungle": 1},
    "rim": {"barren": 3, "toxic": 2, "asteroid": 2, "ice": 2, "volcanic": 1, "jungle": 1},
}
REGION_DEV = {"core": (1.4, 2.6), "inner": (1.0, 2.0), "mid": (0.6, 1.4), "outer": (0.3, 0.9), "rim": (0.15, 0.6)}
REGION_POP = {"core": (2.5, 4.5), "inner": (2.0, 3.8), "mid": (1.2, 3.0), "outer": (0.5, 2.3), "rim": (0.0, 1.5)}


def generate(seed=1, n_planets=120, n_factions=None):
    world = World(seed)
    rng = world.rng
    _make_planets(world, n_planets)
    _make_lanes(world)
    _make_factions(world, n_factions or max(4, n_planets // 7))
    _make_orgs(world)
    _make_corps(world)
    _populate(world)
    world.rebuild_caches()
    for f in world.alive_factions():
        if f.leader is None:
            politics.succession(world, f)
    for c in world.corps.values():
        if c.ceo is None:
            _staff_top(world, "corporate", c.id, c.hq)
    for o in world.orgs.values():
        if o.leader is None:
            _staff_top(world, "order" if o.kind in ("order", "void") else "underworld", o.id, o.seat)
    world.log.clear()
    for p in world.persons.values():
        p.bio = [(t, b) for t, b in p.bio if t >= 0] or p.bio
    return world


# ---------------------------------------------------------------------- 惑星
def _planet_name(world, used):
    rng = world.rng
    for _ in range(100):
        name = rng.choice(NAME_PREFIX) + rng.choice(NAME_MID) + rng.choice(NAME_SUFFIX)
        decor = rng.choice(NAME_DECOR)
        if decor == "新":
            name = "新" + name
        else:
            name += decor
        if name not in used:
            used.add(name)
            return name
    name = f"星系{len(used)}"
    used.add(name)
    return name


def _region_of(r):
    for reg in REGIONS:
        if r <= reg["radius"]:
            return reg["key"]
    return "rim"


def _make_planets(world, n):
    rng = world.rng
    min_d = 0.11 * math.sqrt(120 / n)
    pts = [(0.0, 0.0)]
    tries = 0
    while len(pts) < n and tries < n * 400:
        tries += 1
        r = math.sqrt(rng.random())
        theta = rng.random() * 2 * math.pi
        # 渦状腕の濃淡をつける
        arm = math.cos(2 * theta - r * 5.0)
        if rng.random() > 0.55 + 0.45 * arm:
            continue
        x, y = r * math.cos(theta), r * math.sin(theta)
        if all((x - a) ** 2 + (y - b) ** 2 >= min_d ** 2 for a, b in pts):
            pts.append((x, y))
    used = {CORE_RELIC_PLANET}
    for i, (x, y) in enumerate(pts):
        r = math.hypot(x, y)
        region = _region_of(r)
        if i == 0:
            name, ptype = CORE_RELIC_PLANET, "ecumenopolis"
        else:
            name = _planet_name(world, used)
            ptype = weighted_choice(rng, REGION_TYPE_WEIGHTS[region])
        pt = PLANET_TYPES[ptype]
        sp_weights = {}
        for s, w in SPECIES_WEIGHTS.items():
            sp_weights[s] = w * (3.0 if ptype in SPECIES[s]["homeworld_types"] else 0.6)
        species = weighted_choice(rng, sp_weights)
        lo, hi = REGION_POP[region]
        pop = 10 ** rng.uniform(lo, hi) * pt["habitability"]
        dlo, dhi = REGION_DEV[region]
        pl = Planet(id=i, name=name, ptype=ptype, region=region, x=x, y=y, population=pop,
                    development=rng.uniform(dlo, dhi), minerals=pt["minerals"] * rng.uniform(0.7, 1.3),
                    food=pt["food"] * rng.uniform(0.7, 1.3), energy=pt["energy"] * rng.uniform(0.7, 1.3),
                    species=species, culture="republic")
        world.planets.append(pl)
        pl.culture = roll_ideology(rng, species)
        feats = []
        if i == 0:
            feats = ["ruins", "battlefield"]
        else:
            for key, _ in PLANET_FEATURES:
                chance = 0.06
                if key == "ruins" and region in ("core", "rim"):
                    chance = 0.2
                if rng.random() < chance:
                    feats.append(key)
        pl.features = feats[:2]
        desc = rng.choice(pt["descs"])
        for key, text in PLANET_FEATURES:
            if key in pl.features:
                desc += text
        if i == 0:
            desc = ("旧アウラ帝政の帝都。大寂滅の炎に焼かれた都市殻が、いまも星を覆っている。"
                    "廃墟の奥深くには、誰も近づかない玉座の間があるという。")
        pl.desc = desc
        pl.defense = 10 + pl.development * 10 + (25 if "fortress" in pl.features else 0)


def _make_lanes(world):
    pls = world.planets
    n = len(pls)
    d = lambda a, b: math.hypot(pls[a].x - pls[b].x, pls[a].y - pls[b].y)
    # 最小全域木で全ての星をつなぐ（プリム法）
    in_tree = {0}
    best = {i: (d(0, i), 0) for i in range(1, n)}
    edges = set()
    while best:
        i = min(best, key=lambda k: best[k][0])
        _, j = best.pop(i)
        edges.add((min(i, j), max(i, j)))
        in_tree.add(i)
        for k in best:
            dk = d(i, k)
            if dk < best[k][0]:
                best[k] = (dk, i)
    # 近い星同士に追加の航路
    for i in range(n):
        near = sorted((d(i, j), j) for j in range(n) if j != i)[:3]
        for dist, j in near:
            if dist < 0.26 * math.sqrt(120 / n) and world.rng.random() < 0.6:
                edges.add((min(i, j), max(i, j)))
    for a, b in edges:
        pls[a].lanes.append(b)
        pls[b].lanes.append(a)


# ---------------------------------------------------------------------- 国家
def _make_factions(world, count):
    rng = world.rng
    pls = world.planets
    cands = [p for p in pls if p.region != "rim"]
    capitals = []
    first = max(cands, key=lambda p: p.population * rng.random())
    capitals.append(first)
    while len(capitals) < count and len(capitals) < len(cands):
        def score(p):
            md = min(math.hypot(p.x - c.x, p.y - c.y) for c in capitals)
            return md * (0.6 + rng.random()) * (1 + math.log10(p.population + 1) * 0.1)
        nxt = max((p for p in cands if p not in capitals), key=score)
        capitals.append(nxt)
    # 領土の拡大
    owner = {}
    sizes = {}
    frontier = {}
    for idx, cap in enumerate(capitals):
        owner[cap.id] = idx
        sizes[idx] = rng.randint(2, 11)
        frontier[idx] = [cap.id]
    target = int(len(pls) * 0.75)
    grew = True
    while len(owner) < target and grew:
        grew = False
        for idx in rng.sample(range(len(capitals)), len(capitals)):
            mine = sum(1 for v in owner.values() if v == idx)
            if mine >= sizes[idx]:
                continue
            opts = [n for pid in frontier[idx] for n in pls[pid].lanes if n not in owner]
            if not opts:
                continue
            pick = rng.choice(opts)
            owner[pick] = idx
            frontier[idx].append(pick)
            grew = True
    for idx, cap in enumerate(capitals):
        species = cap.species
        ideology = cap.culture
        if species == "ketari" and rng.random() < 0.7:
            ideology = "collectivism"
        govs = IDEOLOGIES[ideology]["govs"]
        gov = "hive" if (species == "ketari" and ideology == "collectivism") else rng.choice(govs)
        if cap.region == "outer" and rng.random() < 0.25:
            gov, ideology = "pirate", "liberation"
        base = cap.name.split("・")[0].split(" ")[0]
        f = Faction(id=world.new_id("faction"), name=base + rng.choice(GOVERNMENTS[gov]["suffixes"]),
                    base_name=base, gov=gov, ideology=ideology, capital=cap.id,
                    founded_t=-12 * rng.randint(30, 1800), main_species=species,
                    motto=rng.choice(IDEOLOGIES[ideology]["slogans"]))
        f.legend = rng.choice(ANCIENT_EVENTS).format(a=f.name)
        core_bonus = {"core": 2, "inner": 1}.get(cap.region, 0)
        f.tech = {k: max(0, rng.randint(0, 2) + core_bonus - (1 if rng.random() < 0.4 else 0)) for k in TECH_KEYS}
        f.research = {k: rng.uniform(0, 50) for k in TECH_KEYS}
        f.last_election_t = -rng.randint(0, 60)
        f.stability = GOVERNMENTS[gov]["stability"] + rng.uniform(-10, 10)
        world.factions[f.id] = f
        for pid, o in owner.items():
            if o == idx:
                f.planets.add(pid)
                pls[pid].owner = f.id
        # 首都の文化は国家の理念に合わせる
        cap.culture = ideology
    from galaxy.sim.economy import planet_output
    facs = list(world.factions.values())
    for f in facs:
        income = sum(planet_output(world, pls[pid]) for pid in f.planets) * 0.35
        f.fleet = income * (10 + 20 * IDEOLOGIES[f.ideology]["aggression"]) * rng.uniform(0.6, 1.2)
        f.treasury = income * rng.uniform(5, 20)
        for g in facs:
            if g.id != f.id:
                f.relations[g.id] = compatibility(f.ideology, g.ideology) * 30 + rng.uniform(-20, 20)
    world.rebuild_caches()
    # 初期の条約
    for f in facs:
        for gid in world.neighbors.get(f.id, ()):
            g = world.factions[gid]
            if f.id < gid:
                if f.relations[gid] > 15 and rng.random() < 0.5:
                    world.treaty(f.id, gid)["trade"] = 0
                if f.relations[gid] > 30 and rng.random() < 0.4:
                    world.treaty(f.id, gid)["alliance"] = 0
                if f.relations[gid] < -15 and rng.random() < 0.6:
                    f.grievances[gid] = rng.uniform(5, 30)
                    g.grievances[f.id] = rng.uniform(5, 30)


# ---------------------------------------------------------------------- 組織
def _make_orgs(world):
    rng = world.rng
    pls = world.planets
    shrines = [p for p in pls if "shrine" in p.features] or [p for p in pls if p.region in ("inner", "mid")]
    seat = rng.choice(shrines)
    if "shrine" not in seat.features:
        seat.features.append("shrine")
    o = Organization(id=world.new_id("org"), kind="order", name="ハルモニア律院", seat=seat.id,
                     founded_t=-12 * 2900,
                     desc="共鳴者を導き、銀河の調和を守る古き組織。本院は" + seat.name + "にある。")
    world.orgs[o.id] = o
    void_seats = [p for p in pls if p.region in ("rim", "outer")] or pls
    vs = rng.choice(void_seats)
    v = Organization(id=world.new_id("org"), kind="void", name="虚環派", seat=vs.id, founded_t=-12 * 1200,
                     power=25, desc="律院が封じた禁忌の技を求める影の結社。拠点は" + vs.name + "に隠されているという。")
    world.orgs[v.id] = v
    synd_names = ["黒潮会", "赤鱗団", "灰色の手", "星屑シンジケート", "無名の兄弟団", "鉄錨組", "夜鳴き商会",
                  "裂け目の徒", "金眼一家", "三日月同盟"]
    rng.shuffle(synd_names)
    outer = [p for p in pls if p.region in ("mid", "outer")] or pls
    for i in range(max(2, len(pls) // 35)):
        base = rng.choice([p for p in outer if "market" in p.features] or outer)
        s = Organization(id=world.new_id("org"), kind="syndicate", name=synd_names[i % len(synd_names)],
                         seat=base.id, founded_t=-12 * rng.randint(10, 300), power=rng.uniform(20, 60),
                         desc=f"{base.name}を根城とする犯罪組織。")
        world.orgs[s.id] = s


def _make_corps(world):
    rng = world.rng
    owned = [p for p in world.planets if p.owner is not None]
    for _ in range(max(4, len(world.planets) // 4)):
        hq = max(rng.sample(owned, min(3, len(owned))), key=lambda p: p.development)
        if hq.minerals > 1.2:
            sector = rng.choice(["mining", "shipbuilding", "arms", "mining"])
        elif hq.food > 1.2:
            sector = rng.choice(["agri", "medical", "transport"])
        else:
            sector = rng.choice(list(SECTORS))
        c = Corporation(id=world.new_id("corp"), name=careers._corp_name(world, sector), sector=sector,
                        hq=hq.id, faction=hq.owner, founded_t=-12 * rng.randint(5, 400),
                        value=rng.uniform(60, 500), branches={hq.id}, motto=rng.choice(CORP_MOTTOS))
        for n in hq.lanes:
            if rng.random() < 0.4:
                c.branches.add(n)
        world.corps[c.id] = c


# ---------------------------------------------------------------------- 人々
def _populate(world):
    rng = world.rng
    for pl in world.planets:
        n = demography.target_notables(pl)
        for _ in range(n):
            species = pl.species if rng.random() < 0.8 else rng.choice(list(SPECIES))
            sp = SPECIES[species]
            age = rng.uniform(sp["adult"], sp["lifespan"] * 0.85)
            create_person(world, species, pl.id, pl.owner, -int(age * 12))
    world.rebuild_caches()
    # 婚姻と子供
    for pl in world.planets:
        singles = [p for p in world.by_planet[pl.id] if p.spouse is None and demography._marriageable(world, p)]
        rng.shuffle(singles)
        for p in singles:
            if p.spouse is not None or rng.random() > 0.55:
                continue
            for q in singles:
                if q.spouse is None and q.species == p.species and demography._compatible(world, p, q):
                    p.spouse, q.spouse = q.id, p.id
                    p.opinions[q.id] = q.opinions[p.id] = 60
                    _initial_children(world, p, q)
                    break
    # 職業の初期化
    adults = [p for p in world.persons.values() if is_adult(world, p)]
    rng.shuffle(adults)
    for p in adults:
        careers.start_career(world, p, quiet=True)
        _warm_rank(world, p)
    for p in world.persons.values():
        p.bio = [(0, f"{world.plname(p.birth_planet)}で生まれた。")]
        if p.job:
            p.bio.append((0, f"物語の始まりの時点で、{careers.describe_job(world, p)}であった。"))
        p.wealth = rng.uniform(5, 60) * (1 + (p.job.rank if p.job else 0))
        p.fame = (p.job.rank * 2 if p.job else 0) + rng.uniform(0, 5)
    # 元首
    for f in world.factions.values():
        cits = [p for p in world.persons.values() if p.faction == f.id and is_adult(world, p)
                and p.age(0) > SPECIES[p.species]["adult"] + 5]
        if not cits:
            continue
        cap_people = [p for p in cits if p.planet == f.capital] or cits
        leader = max(cap_people, key=lambda p: p.stat("diplomacy") + p.stat("command")
                     + p.disposition("ambition") * 3 + rng.random() * 8
                     + (10 if p.job and p.job.track == "government" else 0))
        if rng.random() < 0.7:
            leader.ideology = f.ideology
        politics.install_leader(world, f, leader, "initial", quiet=True)
        f.rulers[-1] = (leader.id, -12 * rng.randint(0, 20), None)


def _initial_children(world, a, b):
    rng = world.rng
    mother = a if a.sex in ("女", "雌", "繁体") else b
    father = b if mother is a else a
    sp = SPECIES[mother.species]
    if sp["fertility"] <= 0:
        return
    span = (0 - mother.birth_t) / 12 - sp["adult"]
    if span <= 1:
        return
    for _ in range(rng.choice((0, 1, 1, 2, 2, 3))):
        offset = rng.uniform(0, min(span, sp["lifespan"] * 0.35))
        birth_t = mother.birth_t + int((sp["adult"] + offset) * 12)
        if birth_t >= 0:
            continue
        child = create_person(world, mother.species, mother.planet, mother.faction, birth_t,
                              family=father.family, parents=(father.id, mother.id))
        mother.children.append(child.id)
        father.children.append(child.id)
        world.by_planet[mother.planet].append(child)


def _warm_rank(world, p):
    """物語開始時点で、年齢に応じた地位を与える。"""
    rng = world.rng
    j = p.job
    if j is None:
        return
    years = p.age(0) - SPECIES[p.species]["adult"]
    speed = rng.uniform(3, 9) * SPECIES[p.species]["lifespan"] / 82
    rank = min(int(years / speed), careers.top_rank(j.track))
    if j.track == "government":
        rank = min(rank, careers.top_rank("government") - 1)
    while rank > 0 and not careers.has_room(world, j.track, j.org_id, rank):
        rank -= 1
    if rank:
        careers.set_rank(world, p, rank)


def _staff_top(world, track, org_id, planet_id):
    if careers.fill_top(world, track, org_id):
        return
    rng = world.rng
    pl = world.planet(planet_id)
    sp = SPECIES[pl.species]
    age = rng.uniform(sp["adult"] + 10, sp["lifespan"] * 0.6)
    p = create_person(world, pl.species, pl.id, pl.owner, world.t - int(age * 12))
    if track == "order":
        p.stats["resonance"] = rng.randint(16, 22)
    careers.assign_job(world, p, track, org_id, careers.top_rank(track))
    p.fame = 30
    p.bio = [(0, f"物語の始まりの時点で、{careers.describe_job(world, p)}であった。")]
    world.log.clear()
