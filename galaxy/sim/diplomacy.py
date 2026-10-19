"""外交：国家間の感情・同盟・通商協定・宣戦布告。"""

from galaxy.content.ideologies import IDEOLOGIES, compatibility
from galaxy.content.events import WAR_CAUSES
from galaxy.minds import mind_of
from galaxy.model.entities import War
from galaxy.narrative.voice import narrate, say


def contacts(world, f):
    out = set(world.neighbors.get(f.id, set()))
    for key, tr in world.treaties.items():
        if f.id in key and tr:
            out |= set(key)
    for w in world.wars_of(f.id):
        out |= w.enemies_of(f.id)
    out.discard(f.id)
    return {c for c in out if world.factions[c].alive}


def monthly(world):
    rng = world.rng
    factions = world.alive_factions()
    for f in factions:
        for oid in contacts(world, f):
            _drift(world, f, world.factions[oid])
    for f in factions:
        if rng.random() < 0.2:
            _act(world, f)
    if rng.random() < 0.15 and factions:
        _incident(world, rng.choice(factions))


def _target_opinion(world, f, g):
    v = compatibility(f.ideology, g.ideology) * 30
    if world.has_treaty(f.id, g.id, "trade"):
        v += 15
    if world.has_treaty(f.id, g.id, "alliance"):
        v += 30
    if g.id in world.neighbors.get(f.id, set()):
        v -= 12 + IDEOLOGIES[f.ideology]["aggression"] * 10
    if world.at_war(f.id, g.id):
        v -= 60
    v -= f.grievances.get(g.id, 0)
    # 共通の敵
    for w in world.wars_of(g.id):
        if f.id not in w.sides() and w.enemies_of(g.id) & {e for e in world.factions if f.relations.get(e, 0) < -30}:
            v += 15
    feared = {e for e, r in f.relations.items() if r < -30}
    if feared & {e for e, r in g.relations.items() if r < -30}:
        v += 12
    # 強大すぎる隣国は脅威とみなされる
    avg = sum(len(x.planets) for x in world.alive_factions()) / max(1, len(world.alive_factions()))
    if len(g.planets) > avg * 1.8 and g.id in world.neighbors.get(f.id, set()):
        v -= 10 + (len(g.planets) / avg) * 4
    if f.main_species != g.main_species and f.ideology == "purity":
        v -= 30
    leader = world.person(f.leader)
    if leader:
        v += (leader.stat("diplomacy") - 10) * 0.8
    return v


def _drift(world, f, g):
    cur = f.relations.get(g.id, 0.0)
    target = _target_opinion(world, f, g)
    cur += (target - cur) * 0.04 + world.rng.uniform(-1.5, 1.5)
    f.relations[g.id] = max(-100.0, min(100.0, cur))
    if g.id in f.grievances:
        f.grievances[g.id] *= 0.995
        if f.grievances[g.id] < 1:
            del f.grievances[g.id]


def strength(world, fid, with_allies=True):
    f = world.faction(fid)
    s = f.fleet
    if with_allies:
        for a in world.allies(fid):
            s += world.faction(a).fleet * 0.5
    return s


def _act(world, f):
    rng = world.rng
    leader = world.person(f.leader)
    for oid in sorted(contacts(world, f)):
        g = world.factions[oid]
        rel = f.relations.get(g.id, 0)
        rel_back = g.relations.get(f.id, 0)
        at_war = world.at_war(f.id, g.id)
        if at_war:
            continue
        # 通商協定
        if (not world.has_treaty(f.id, g.id, "trade") and rel > 5 and rel_back > 0
                and rng.random() < (IDEOLOGIES[f.ideology]["trade"] + IDEOLOGIES[g.ideology]["trade"]) * 0.05):
            world.treaty(f.id, g.id)["trade"] = world.t
            gl = world.person(g.leader)
            line = say(world, leader, "trade_pact") if leader else None
            world.record("trade_pact", narrate(world, "trade_pact", faction=f.name, target_faction=g.name), 2,
                         actors=tuple(x.id for x in (leader, gl) if x), factions=(f.id, g.id),
                         quote=line, speaker=leader.id if leader else None, bio=False)
            continue
        if world.has_treaty(f.id, g.id, "trade") and rel < -20 and rng.random() < 0.1:
            world.drop_treaty(f.id, g.id, "trade")
            world.record("trade_broken", narrate(world, "trade_broken", faction=f.name, target_faction=g.name), 2,
                         factions=(f.id, g.id))
        # 同盟
        if (not world.has_treaty(f.id, g.id, "alliance") and rel > 45 and rel_back > 40
                and len(world.allies(f.id)) < 3 and rng.random() < 0.08
                and mind_of(world, leader).consider_alliance(world, leader, f, g)):
            world.treaty(f.id, g.id)["alliance"] = world.t
            gl = world.person(g.leader)
            line = say(world, leader, "alliance", target=g.name) if leader else None
            world.record("alliance", narrate(world, "alliance", faction=f.name, target_faction=g.name,
                                             planet=world.plname(f.capital)), 3,
                         actors=tuple(x.id for x in (leader, gl) if x), factions=(f.id, g.id),
                         planet=f.capital, quote=line, speaker=leader.id if leader else None)
            continue
        if world.has_treaty(f.id, g.id, "alliance") and rel < 5 and rng.random() < 0.1:
            world.drop_treaty(f.id, g.id, "alliance")
            f.grievances[g.id] = g.grievances.get(f.id, 0) + 5
            g.grievances[f.id] = g.grievances.get(f.id, 0) + 15
            world.record("alliance_broken", narrate(world, "alliance_broken", faction=f.name, target_faction=g.name),
                         3, factions=(f.id, g.id))
            continue
        # 宣戦布告
        if (rel < -25 and g.id in world.neighbors.get(f.id, set())
                and not world.has_treaty(f.id, g.id, "truce")
                and not world.has_treaty(f.id, g.id, "alliance")
                and not any(w.att_leader == f.id for w in world.wars_of(f.id))
                and f.stability > 25 and f.exhaustion < 35):
            odds = strength(world, f.id) / max(1.0, strength(world, g.id))
            if odds > 0.8 and mind_of(world, leader).consider_war(world, leader, f, g, odds):
                cause = _war_cause(world, f, g)
                goal = _war_goal(world, f, g)
                declare_war(world, f, g, cause, goal)
                return


def _war_cause(world, f, g):
    if f.grievances.get(g.id, 0) > 20:
        return "revenge"
    if f.ideology in ("voidism", "harmonist") and g.ideology != f.ideology:
        return "holy"
    if compatibility(f.ideology, g.ideology) < -0.3:
        return "ideology"
    return world.rng.choice(("territory", "resources", "conquest"))


def _war_goal(world, f, g):
    border = [pid for pid in g.planets
              if any(world.planet(n).owner == f.id for n in world.planet(pid).lanes)]
    pool = border or list(g.planets)
    return max(pool, key=lambda pid: world.planet(pid).population * world.rng.random())


def _war_name(world, f, g, cause, goal):
    rng = world.rng
    if cause == "independence":
        base = f"{world.plname(goal)}独立戦争"
    else:
        style = rng.random()
        if style < 0.35 and goal is not None:
            base = f"{world.plname(goal)}戦争"
        elif style < 0.6:
            base = f"{f.base_name}・{g.base_name}戦争"
        elif style < 0.75 and goal is not None:
            base = f"{world.plname(goal)}紛争"
        elif style < 0.88:
            base = f"{g.base_name}{rng.choice(['遠征', '侵攻', '討伐戦'])}"
        else:
            base = rng.choice(["星焔戦争", "鉄の冬戦争", "灰色の戦争", "千日戦争", "航路戦争",
                               "残光戦争", "沈黙の戦争", "血の潮戦争", "冠の戦争", "裂けた星図戦争"])
    world.war_names[base] += 1
    n = world.war_names[base]
    if n > 1:
        return f"第{n}次{base}"
    return base


def declare_war(world, f, g, cause, goal=None):
    w = War(id=world.new_id("war"), name=_war_name(world, f, g, cause, goal), attackers={f.id},
            defenders={g.id}, att_leader=f.id, def_leader=g.id, cause=cause, goal=goal, start_t=world.t)
    world.wars[w.id] = w
    world.drop_treaty(f.id, g.id, "trade")
    world.drop_treaty(f.id, g.id, "alliance")
    f.relations[g.id] = min(f.relations.get(g.id, 0), -50)
    g.relations[f.id] = min(g.relations.get(f.id, 0), -60)
    leader, defender = world.person(f.leader), world.person(g.leader)
    line = say(world, leader, "declare_war", enemy=g.name) if leader else None
    world.record("war_declared", narrate(world, "war_declared", faction=f.name, enemy=g.name, war=w.name,
                                         cause=WAR_CAUSES[cause]), 5,
                 actors=tuple(x.id for x in (leader, defender) if x), factions=(f.id, g.id),
                 planet=goal, quote=line, speaker=leader.id if leader else None, bio=False)
    if leader:
        leader.add_bio(world.t, f"{g.name}に宣戦布告した（{w.name}）。")
    if defender:
        reply = say(world, defender, "defend_war", enemy=f.name)
        defender.add_bio(world.t, f"{f.name}の侵攻を受けた（{w.name}）。")
        world.record("war_response", f"{g.name}の{_title(world, defender)}{defender.name}は徹底抗戦を宣言した。", 3,
                     actors=(defender.id,), factions=(g.id,), quote=reply, speaker=defender.id, bio=False)
    _call_allies(world, w, g, "def")
    _call_allies(world, w, f, "att")
    return w


def _title(world, person):
    from galaxy.sim.careers import job_title
    return job_title(world, person)


def _call_allies(world, w, f, side):
    for aid in sorted(world.allies(f.id)):
        if aid in w.sides():
            continue
        ally = world.faction(aid)
        leader = world.person(ally.leader)
        chance_ok = side == "def" or world.rng.random() < 0.5
        if chance_ok and mind_of(world, leader).honor_alliance(world, leader, ally, f, w):
            (w.defenders if side == "def" else w.attackers).add(aid)
            world.record("war_joined", narrate(world, "war_joined", faction=ally.name, ally=f.name, war=w.name), 3,
                         factions=(aid, f.id))
        else:
            world.drop_treaty(aid, f.id, "alliance")
            f.grievances[aid] = f.grievances.get(aid, 0) + 30
            world.record("alliance_betrayed", f"{ally.name}は同盟国{f.name}の参戦要請を拒否した。同盟は破棄された。", 3,
                         factions=(aid, f.id))


def _incident(world, f):
    rng = world.rng
    cs = sorted(world.neighbors.get(f.id, set()))
    if not cs:
        return
    g = world.factions[rng.choice(cs)]
    if not g.alive or world.at_war(f.id, g.id):
        return
    border = [pid for pid in f.planets if any(world.planet(n).owner == g.id for n in world.planet(pid).lanes)]
    planet = rng.choice(border) if border else f.capital
    delta = rng.uniform(8, 20)
    f.relations[g.id] = f.relations.get(g.id, 0) - delta
    g.relations[f.id] = g.relations.get(f.id, 0) - delta
    f.grievances[g.id] = f.grievances.get(g.id, 0) + delta / 3
    world.record("border_incident", narrate(world, "border_incident", faction=f.name, target_faction=g.name,
                                            planet=world.plname(planet)), 2,
                 factions=(f.id, g.id), planet=planet)
