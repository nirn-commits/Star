"""経済：惑星の生産・国家財政・艦隊建造・企業の盛衰。"""

import math

from galaxy.content.planets import PLANET_TYPES
from galaxy.content.ideologies import IDEOLOGIES
from galaxy.content.corporations import SECTORS
from galaxy.narrative.voice import narrate, say
from galaxy.sim import careers


def planet_output(world, pl):
    f = world.faction(pl.owner)
    industry = f.tech.get("industry", 0) if f else 0
    res = (pl.minerals + pl.food + pl.energy) / 3
    return (1 + math.log10(pl.population + 1)) * pl.development * res * (1 + 0.06 * industry)


def monthly(world):
    rng = world.rng
    for f in world.alive_factions():
        income = sum(planet_output(world, world.planet(pid)) for pid in f.planets) * 0.35
        trade_partners = sum(1 for k, tr in world.treaties.items() if f.id in k and "trade" in tr)
        income *= 1 + 0.06 * trade_partners * IDEOLOGIES[f.ideology]["trade"] + 0.02 * trade_partners
        income += sum(c.value * 0.002 for c in world.corps.values() if c.alive and c.faction == f.id)
        if f.stability < 30:
            income *= 0.8
        upkeep = f.fleet * 0.012
        f.treasury += income - upkeep
        # 艦隊建造
        at_war = bool(world.wars_of(f.id))
        aggression = IDEOLOGIES[f.ideology]["aggression"]
        cap = income * (18 + 30 * aggression) * (1.6 if at_war else 1.0)
        if f.fleet < cap and f.treasury > 0:
            build = min(f.treasury * (0.25 if at_war else 0.1), (cap - f.fleet) * 0.06)
            f.treasury -= build * 0.6
            f.fleet += build
        elif f.fleet > cap * 1.3:
            f.fleet *= 0.995
        if f.treasury < -50 and rng.random() < 0.02:
            world.record("recession", narrate(world, "recession", faction=f.name), 2, factions=(f.id,))
            f.stability -= 5
    for pl in world.planets:
        _planet_growth(world, pl)
    for c in list(world.corps.values()):
        if c.alive:
            _corp(world, c)


def _planet_growth(world, pl):
    hab = PLANET_TYPES[pl.ptype]["habitability"]
    growth = 0.0006 * hab
    f = world.faction(pl.owner)
    if f and world.wars_of(f.id):
        growth -= 0.0003
    pl.population = max(0.05, pl.population * (1 + growth))
    dev_target = 0.4 + hab * 1.2 + (0.3 if f else -0.2)
    if f and f.capital == pl.id:
        dev_target += 0.5
    pl.development += (dev_target - pl.development) * 0.002
    pl.development = max(0.1, min(3.5, pl.development))


def _corp(world, c):
    rng = world.rng
    sec = SECTORS[c.sector]
    f = world.faction(c.faction)
    growth = 0.002 + rng.gauss(0, 0.018)
    if f:
        if world.wars_of(f.id):
            growth += (sec["war"] - 1) * 0.006
        trades = sum(1 for k, tr in world.treaties.items() if f.id in k and "trade" in tr)
        growth += trades * 0.0006 * sec["trade"]
        if f.ideology == "corporatism":
            growth += 0.002
    ceo = world.person(c.ceo)
    if ceo:
        growth += (ceo.stat("intellect") - 10) * 0.0005 + ceo.disposition("diligence") * 0.001
    c.value *= 1 + growth
    if c.ceo is None and careers.fill_top(world, "corporate", c.id) is None:
        _hire_outsider(world, c)
    if c.value > 300 and rng.random() < 0.004:
        _expand(world, c)
    if growth > 0.05 and c.value > 150 and rng.random() < 0.15:
        reason = rng.choice(["戦争特需によるものとみられる。" if sec["war"] > 1.2 else "新製品が大ヒットしている。",
                             "大型契約を相次いで獲得した。", "競合他社の不祥事が追い風となった。"])
        world.record("corp_boom", narrate(world, "corp_boom", org=c.name, reason=reason), 1, planet=c.hq)
    if c.value < 12:
        _bankrupt(world, c)
    elif c.value > 600 and rng.random() < 0.003:
        _acquire(world, c)


def _expand(world, c):
    cands = {n for b in c.branches for n in world.planet(b).lanes} - c.branches
    if not cands:
        return
    pid = world.rng.choice(sorted(cands))
    c.branches.add(pid)
    c.history.append((world.t, f"{world.plname(pid)}に支社を開設した。"))


def _bankrupt(world, c):
    c.alive = False
    c.closed_t = world.t
    years = (world.t - c.founded_t) // 12
    ceo = world.person(c.ceo)
    line = say(world, ceo, "bankrupt") if ceo else None
    world.record("corp_bankrupt", narrate(world, "corp_bankrupt", org=c.name, years=years), 2,
                 actors=(ceo.id,) if ceo else (), planet=c.hq, quote=line, speaker=ceo.id if ceo else None)
    for p in careers.members(world, "corporate", c.id):
        careers.clear_job(world, p, end_reason="会社の倒産", fill=False)
        p.wealth *= 0.5
    c.ceo = None


def _acquire(world, c):
    targets = [o for o in world.corps.values()
               if o.alive and o.id != c.id and o.faction == c.faction and o.value < c.value * 0.3]
    if not targets:
        return
    t = world.rng.choice(targets)
    c.value += t.value * 0.8
    c.branches |= t.branches
    t.alive = False
    t.closed_t = world.t
    world.record("corp_acquired", narrate(world, "corp_acquired", org=t.name, target_org=c.name), 2, planet=c.hq)
    for p in careers.members(world, "corporate", t.id):
        rank = min(p.job.rank, careers.top_rank("corporate") - 2)
        careers.clear_job(world, p, end_reason="買収", fill=False)
        careers.assign_job(world, p, "corporate", c.id, rank)
    t.ceo = None


def _hire_outsider(world, c):
    """社内に後継者がいなければ、外部から経営者を招く。"""
    from galaxy.content.species import SPECIES
    from galaxy.sim.life import create_person
    rng = world.rng
    pl = world.planet(c.hq)
    sp = SPECIES[pl.species]
    age = rng.uniform(sp["adult"] + 8, sp["lifespan"] * 0.55)
    p = create_person(world, pl.species, pl.id, pl.owner, world.t - int(age * 12), origin="外部招聘の経営者")
    careers.assign_job(world, p, "corporate", c.id, careers.top_rank("corporate"))
    p.fame = 15
    p.add_bio(world.t, f"{c.name}の社長として外部から招かれた。")
    world.record("ceo_hired", f"{c.name}は社外から{p.name}を新社長に迎えた。", 1, actors=(p.id,), planet=c.hq)
