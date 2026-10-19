"""就職・昇進・引退・転職。NPCもプレイヤーも同じ規則で出世する。"""

from galaxy.content.careers import CAREERS, BASE_INCOME, LABOR_JOBS, VOID_RANKS, cap_for
from galaxy.content.governments import leader_title
from galaxy.content.corporations import SECTORS, CORP_MOTTOS, CORP_PREFIX
from galaxy.content.species import SPECIES
from galaxy.minds import mind_of
from galaxy.narrative.voice import narrate, say, exchange
from galaxy.sim.life import adjust_opinion, effective_lifespan, is_adult, gain_trait


def top_rank(track):
    return len(CAREERS[track]["ranks"]) - 1


def notable_rank(track):
    return CAREERS[track]["notable"]


def rank_name(world, track, org_id, rank, sex=None):
    if track == "government" and rank == top_rank(track):
        f = world.faction(org_id)
        if f:
            return leader_title(f.gov, sex)
    if track == "order":
        org = world.orgs.get(org_id)
        if org and org.kind == "void":
            return VOID_RANKS[rank]
    return CAREERS[track]["ranks"][rank]


def org_name(world, track, org_id):
    kind = CAREERS[track]["org"]
    if kind == "faction":
        f = world.faction(org_id)
        if not f:
            return "亡国"
        suffix = {"military": "軍", "government": "政府", "academic": "国立学院"}[track]
        return f"{f.name}{suffix}"
    if kind == "corp":
        c = world.corps.get(org_id)
        return c.name if c else "消えた企業"
    if kind in ("order", "syndicate"):
        o = world.orgs.get(org_id)
        return o.name if o else "消えた組織"
    return ""


def job_title(world, person):
    j = person.job
    if j is None:
        return ""
    if j.track == "laborer":
        return j.detail
    return rank_name(world, j.track, j.org_id, j.rank, person.sex)


def describe_job(world, person):
    j = person.job
    if j is None:
        if person.retired:
            return "隠居"
        return "無職" if is_adult(world, person) else "子供"
    if j.track == "laborer":
        return j.detail
    org = org_name(world, j.track, j.org_id)
    title = job_title(world, person)
    return f"{org}の{title}" if org else title


def count(world, track, org_id, rank):
    return world.rank_count[(track, org_id, rank)]


def has_room(world, track, org_id, rank):
    cap = cap_for(track, rank)
    return cap is None or count(world, track, org_id, rank) < cap


# ---------------------------------------------------------------------- 職の付け外し
def assign_job(world, person, track, org_id, rank, detail="", end_reason="転職"):
    from galaxy.model.entities import Job
    if person.job is not None:
        clear_job(world, person, end_reason=end_reason)
    person.job = Job(track, org_id, rank, world.t, world.t, detail)
    person.retired = False
    world.rank_count[(track, org_id, rank)] += 1
    world.roster[(track, org_id)].add(person.id)
    _bind_top(world, person)


def set_rank(world, person, rank):
    j = person.job
    world.rank_count[(j.track, j.org_id, j.rank)] -= 1
    j.rank = rank
    j.since = world.t
    world.rank_count[(j.track, j.org_id, j.rank)] += 1
    _bind_top(world, person)


def _bind_top(world, person):
    """組織の頂点に就いたら、組織側の代表者を更新する。"""
    j = person.job
    if j.rank != top_rank(j.track):
        return
    if j.track == "corporate":
        c = world.corps.get(j.org_id)
        if c:
            c.ceo = person.id
    elif j.track in ("order", "underworld"):
        o = world.orgs.get(j.org_id)
        if o:
            o.leader = person.id


def clear_job(world, person, end_reason="", fill=True):
    j = person.job
    if j is None:
        return
    world.rank_count[(j.track, j.org_id, j.rank)] -= 1
    world.roster[(j.track, j.org_id)].discard(person.id)
    person.career_history.append((j.track, j.org_id, j.rank, j.started, world.t, end_reason))
    person.job = None
    was_top = j.rank == top_rank(j.track)
    if was_top:
        if j.track == "corporate":
            c = world.corps.get(j.org_id)
            if c and c.ceo == person.id:
                c.ceo = None
        elif j.track in ("order", "underworld"):
            o = world.orgs.get(j.org_id)
            if o and o.leader == person.id:
                o.leader = None
        if fill and j.track != "government":
            fill_top(world, j.track, j.org_id)


def members(world, track, org_id):
    return [world.persons[pid] for pid in sorted(world.roster.get((track, org_id), ()))]


def fill_top(world, track, org_id):
    """組織の長が空席になったとき、次席から後継者を選ぶ。"""
    if track in ("merchant", "arts", "explorer", "laborer"):
        return None
    top = top_rank(track)
    if count(world, track, org_id, top) > 0:
        return None
    cands = [p for p in members(world, track, org_id) if p.job.rank < top]
    if not cands:
        return None
    weights = CAREERS[track]["weights"]
    best = max(cands, key=lambda p: (p.job.rank, _merit_score(p, weights) + world.rng.random() * 3))
    old = rank_name(world, track, org_id, best.job.rank, best.sex)
    set_rank(world, best, top)
    title = rank_name(world, track, org_id, top, best.sex)
    org = org_name(world, track, org_id)
    line = say(world, best, "promotion_top", rank=title)
    world.record("promotion_top", narrate(world, "promotion_top", person=f"{old}{best.name}", org=org, rank=title),
                 3 if track in ("order", "underworld") else 2,
                 actors=(best.id,), planet=best.planet, quote=line, speaker=best.id)
    best.fame += 10
    return best


def _merit_score(person, weights):
    total = sum(weights.values())
    return sum(person.stat(k) * w for k, w in weights.items()) / total + person.merit * 0.15


# ---------------------------------------------------------------------- 就職
def career_options(world, person):
    rng = world.rng
    d = person.dispositions()
    s = person.stats
    opts = []
    f = world.faction(person.faction)
    if f is not None and f.alive:
        opts.append(("military", f.id, 1.0 + (s["martial"] + s["command"]) / 10 + d["boldness"] * 0.5
                     + (1.0 if f.ideology == "militarism" else 0)))
        opts.append(("government", f.id, 0.8 + s["diplomacy"] / 8 + d["ambition"] * 0.6))
        opts.append(("academic", f.id, 0.4 + s["learning"] / 8 + d["curiosity"] * 0.6))
    for c in world.corps.values():
        if c.alive and (person.planet in c.branches or c.hq == person.planet):
            opts.append(("corporate", c.id, 0.8 + s["intellect"] / 10 + d["greed"] * 0.4))
    if s["resonance"] >= 8:
        order = _light_order(world)
        void = _void_order(world)
        w = 2.0 + s["resonance"] / 3
        if order:
            opts.append(("order", order.id, w * (1.5 if d["compassion"] >= 0 else 0.7)))
        if void and (d["compassion"] < 0 or d["ambition"] > 1):
            opts.append(("order", void.id, w * 0.6))
    opts.append(("merchant", None, 0.5 + s["diplomacy"] / 12 + d["greed"] * 0.5))
    for o in world.orgs.values():
        if o.kind == "syndicate" and o.alive and _near(world, person.planet, o.seat, 3):
            opts.append(("underworld", o.id, 0.3 - d["honesty"] * 0.4 + d["greed"] * 0.2))
    opts.append(("arts", None, 0.2 + (1.2 if person.has("詩人気質") else 0) + d["sociability"] * 0.1))
    opts.append(("explorer", None, 0.15 + d["curiosity"] * 0.3 + d["boldness"] * 0.2))
    opts.append(("laborer", None, 3.0 - d["ambition"] * 0.5))
    if person.species == "mekan":
        opts = [(t, o, w * (1.6 if t in ("academic", "corporate") else 1)) for t, o, w in opts]
    return [o for o in opts if o[2] > 0]


def _light_order(world):
    return next((o for o in world.orgs.values() if o.kind == "order" and o.alive), None)


def _void_order(world):
    return next((o for o in world.orgs.values() if o.kind == "void" and o.alive), None)


def _near(world, a, b, hops):
    if a == b:
        return True
    frontier = {a}
    seen = {a}
    for _ in range(hops):
        nxt = set()
        for x in frontier:
            for y in world.planet(x).lanes:
                if y == b:
                    return True
                if y not in seen:
                    seen.add(y)
                    nxt.add(y)
        frontier = nxt
    return False


def start_career(world, person, quiet=False):
    opts = career_options(world, person)
    track, org_id, _ = mind_of(world, person).choose_career(world, person, opts)
    detail = world.rng.choice(LABOR_JOBS) if track == "laborer" else ""
    assign_job(world, person, track, org_id, 0, detail)
    org = org_name(world, track, org_id) or CAREERS[track]["name"]
    person.add_bio(world.t, f"{CAREERS[track]['name']}の道を歩み始めた（{describe_job(world, person)}）。")
    if quiet:
        return
    if track == "order":
        _assign_mentor(world, person)
    elif track not in ("laborer",) and world.rng.random() < 0.08:
        line = say(world, person, "career_start", org=org)
        person.add_quote(world.t, line)


def _assign_mentor(world, person):
    j = person.job
    cands = [m for m in members(world, "order", j.org_id) if m.job.rank >= 2 and len(m.apprentices) < 2]
    if not cands:
        return
    same = [m for m in cands if m.planet == person.planet]
    master = world.rng.choice(same or cands)
    person.mentor = master.id
    master.apprentices.append(person.id)
    adjust_opinion(person, master, 40)
    adjust_opinion(master, person, 30)
    a, b = exchange(world, "mentor_meet")
    org = world.orgs[j.org_id].name
    world.record("mentor", narrate(world, "mentor", person=person.name, target=master.name, org=org), 2,
                 actors=(person.id, master.id), planet=person.planet,
                 quote=a, speaker=master.id, reply=b, replier=person.id)


# ---------------------------------------------------------------------- 毎月の処理
def monthly(world):
    t = world.t
    for p in list(world.living):
        if not p.alive or (t - p.birth_t) % 12 != 0:
            continue
        # 誕生月に一年分の処理をまとめて行う
        _yearly_review(world, p)


def _yearly_review(world, p):
    if not is_adult(world, p):
        return
    life = effective_lifespan(world, p)
    age = p.age(world.t)
    if p.job is None:
        if not p.retired and age < life * 0.7:
            start_career(world, p)
        return
    _income(world, p)
    j = p.job
    # 元首は引退しない（選挙・死・政変でのみ退く）
    if j.track == "government" and j.rank == top_rank("government"):
        return
    retire_age = life * (0.62 if j.track == "military" else 0.72)
    if age > retire_age and mind_of(world, p).want_retire(world, p):
        _retire(world, p)
        return
    if j.track == "order":
        _order_life(world, p)
        if p.job is None:
            return
    _try_promotion(world, p)
    if p.job and p.job.track in ("corporate", "merchant") and p.job.rank >= 3 and p.wealth > 150:
        if world.rng.random() < 0.15 and mind_of(world, p).want_found_corp(world, p):
            found_corp(world, p)
    elif p.job and p.job.track == "laborer" and age < life * 0.4 and world.rng.random() < 0.12:
        if mind_of(world, p).want_career_change(world, p):
            old = p.job.detail
            clear_job(world, p, end_reason="転身")
            start_career(world, p, quiet=True)
            if p.job and p.job.track != "laborer":
                world.record("career_change", narrate(world, "career_change", person=p.name, old=old,
                                                      new=CAREERS[p.job.track]["name"]),
                             1, actors=(p.id,), planet=p.planet)


def _income(world, p):
    j = p.job
    base = BASE_INCOME[j.track] * (1 + j.rank * 0.6) * 12
    if j.track == "merchant":
        base *= world.rng.uniform(0.2, 2.2)
    if j.track == "underworld":
        base *= world.rng.uniform(0.3, 2.5)
    cost = 10 + (6 if p.has("強欲") else 0)
    p.wealth = max(0.0, p.wealth + base - cost)
    p.merit += 0.5 + p.disposition("diligence") * 0.4 + world.rng.random()


def _try_promotion(world, p):
    rng = world.rng
    j = p.job
    track = j.track
    top = top_rank(track)
    if j.rank >= top:
        return
    if track == "government" and j.rank + 1 == top:
        return  # 元首の座は継承でのみ
    weights = CAREERS[track]["weights"]
    score = (_merit_score(p, weights) + p.disposition("diligence") * 0.8
             + p.disposition("ambition") * 0.6 + (world.t - j.since) / 12 * 0.5 + rng.uniform(0, 7))
    if track == "merchant":
        score = p.wealth / 60 + rng.uniform(0, 4)
    elif track == "arts":
        score = p.fame / 6 + p.stat("diplomacy") / 3 + rng.uniform(0, 5)
    elif track == "explorer":
        score = p.fame / 5 + p.merit * 0.2 + rng.uniform(0, 5)
    threshold = 7 + j.rank * 1.7
    if score < threshold:
        return
    new_rank = j.rank + 1
    if not has_room(world, track, j.org_id, new_rank):
        # 席が埋まっている。若く野心ある者は燻る
        if new_rank >= notable_rank(track) and rng.random() < 0.15:
            holders = [m for m in members(world, track, j.org_id) if m.job.rank == new_rank]
            if holders:
                rival = rng.choice(holders)
                _make_rivals(world, p, rival)
        return
    set_rank(world, p, new_rank)
    title = rank_name(world, track, j.org_id, new_rank, p.sex)
    org = org_name(world, track, j.org_id) or CAREERS[track]["name"]
    p.fame += new_rank * 0.8
    if new_rank == top and CAREERS[track]["org"] == "none":
        # 組織に属さない職業の頂点は「称号」として語られる
        p.titles.append(title)
        line = say(world, p, "renown", rank=title)
        world.record("renown", narrate(world, "renown", person=p.name, rank=title,
                                       planet=world.plname(p.planet)), 2,
                     actors=(p.id,), planet=p.planet, quote=line, speaker=p.id)
    elif new_rank >= notable_rank(track):
        situation = "promotion_top" if new_rank == top else "promotion"
        line = say(world, p, situation, rank=title)
        importance = 3 if new_rank == top and track in ("military", "academic") else 2 if new_rank >= top - 1 else 1
        world.record(situation, narrate(world, situation, person=p.name, org=org, rank=title), importance,
                     actors=(p.id,), planet=p.planet, quote=line if importance >= 2 else None,
                     speaker=p.id, factions=(p.faction,) if p.faction else ())
        if importance < 2:
            p.add_quote(world.t, line)
    else:
        p.add_bio(world.t, f"{org}の{title}に昇進した。")


def _make_rivals(world, a, b):
    if b.id in a.rivals:
        return
    a.rivals.add(b.id)
    b.rivals.add(a.id)
    adjust_opinion(a, b, -30)
    adjust_opinion(b, a, -15)
    x, y = exchange(world, "rivalry")
    world.record("rivalry", narrate(world, "rivalry", person=a.name, target=b.name), 1,
                 actors=(a.id, b.id), planet=a.planet, quote=x, speaker=a.id, reply=y, replier=b.id)


def _retire(world, p):
    j = p.job
    title = job_title(world, p)
    org = org_name(world, j.track, j.org_id)
    notable = j.rank >= notable_rank(j.track)
    line = say(world, p, "retire")
    clear_job(world, p, end_reason="引退")
    p.retired = True
    if notable:
        world.record("retire", narrate(world, "retire", person=p.name, org=org or "職", rank=title), 1,
                     actors=(p.id,), planet=p.planet, quote=line, speaker=p.id)
    else:
        p.add_bio(world.t, "職を退き、静かな隠居生活に入った。")


def _order_life(world, p):
    """律士の修行と、虚ろな環への堕落。"""
    org = world.orgs.get(p.job.org_id)
    if org is None:
        return
    p.stats["resonance"] = min(25, p.stats["resonance"] + (1 if world.rng.random() < 0.4 else 0))
    if org.kind == "order" and world.rng.random() < 0.03 and mind_of(world, p).heed_void(world, p):
        void = _void_order(world)
        if void is None:
            return
        line = say(world, p, "fall_to_void")
        rank = min(p.job.rank, top_rank("order") - 1)
        assign_job(world, p, "order", void.id, rank)
        gain_trait(world, p, "堕ちた者")
        p.fame += 15
        world.record("fall_to_void", narrate(world, "fall_to_void", person=p.name), 3,
                     actors=(p.id,), planet=p.planet, quote=line, speaker=p.id)
        if p.mentor:
            m = world.person(p.mentor)
            if m and m.alive:
                adjust_opinion(m, p, -60)
                m.add_bio(world.t, f"弟子の{p.name}が虚環派に堕ちた。")
    elif org.kind == "void" and p.has("堕ちた者") and world.rng.random() < 0.01:
        order = _light_order(world)
        if order is None:
            return
        line = say(world, p, "redemption")
        assign_job(world, p, "order", order.id, 1)
        p.traits.remove("堕ちた者")
        world.record("redemption", f"虚環派の{p.name}が律院へと帰還した。堕ちた者が戻るのは数百年ぶりのことだという。",
                     3, actors=(p.id,), planet=p.planet, quote=line, speaker=p.id)


# ---------------------------------------------------------------------- 起業
def found_corp(world, p):
    from galaxy.model.entities import Corporation
    rng = world.rng
    planet = world.planet(p.planet)
    sector = rng.choice(list(SECTORS))
    name = _corp_name(world, sector, p)
    c = Corporation(id=world.new_id("corp"), name=name, sector=sector, hq=p.planet, faction=planet.owner,
                    founded_t=world.t, value=40 + p.wealth * 0.3, founder=p.id,
                    branches={p.planet}, motto=rng.choice(CORP_MOTTOS))
    world.corps[c.id] = c
    p.wealth *= 0.4
    old = describe_job(world, p)
    assign_job(world, p, "corporate", c.id, top_rank("corporate"))
    p.fame += 12
    line = say(world, p, "found_corp", org=name)
    world.record("corp_founded", narrate(world, "corp_founded", person=f"{old}だった{p.name}",
                                         planet=planet.name, org=name), 2,
                 actors=(p.id,), planet=p.planet, quote=line, speaker=p.id)
    return c


def _corp_name(world, sector, founder=None):
    rng = world.rng
    used = {c.name for c in world.corps.values()}
    for _ in range(20):
        if founder is not None and rng.random() < 0.4:
            prefix = founder.family
        else:
            prefix = rng.choice(CORP_PREFIX)
        name = prefix + rng.choice(SECTORS[sector]["suffixes"])
        if name not in used:
            return name
    return f"{rng.choice(CORP_PREFIX)}{rng.choice(SECTORS[sector]['suffixes'])}{len(used)}"


def adult_age(person):
    return SPECIES[person.species]["adult"]
