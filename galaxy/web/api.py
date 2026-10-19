"""画面に渡すための JSON を組み立てる。

人物・国家・惑星・戦争は {"type", "id", "name"} の参照として渡し、
画面側でリンクとして描画できるようにしている。
"""

from galaxy.content.lore import PROLOGUE, RESONANCE_LORE, REGIONS, GALAXY_NAME
from galaxy.content.ideologies import IDEOLOGIES
from galaxy.content.governments import GOVERNMENTS
from galaxy.content.species import SPECIES
from galaxy.content.planets import PLANET_TYPES
from galaxy.content.technologies import TECH_FIELDS, tech_name
from galaxy.content.corporations import SECTORS
from galaxy.content.traits import TRAITS
from galaxy.content.events import WAR_CAUSES
from galaxy.model.entities import STAT_NAMES
from galaxy.narrative.chronicle import _cause
from galaxy.sim import careers

REGION_NAMES = {r["key"]: r["name"] for r in REGIONS}
HOT_KINDS = {"battle", "planet_captured", "revolution", "war_declared"}


# ---------------------------------------------------------------------- 参照
def pref(world, pid):
    p = world.person(pid)
    if p is None:
        return None
    return {"type": "person", "id": p.id, "name": p.name, "alive": p.alive}


def fref(world, fid):
    f = world.faction(fid)
    if f is None:
        return None
    return {"type": "faction", "id": f.id, "name": f.name, "alive": f.alive}


def plref(world, pid):
    if pid is None:
        return None
    pl = world.planet(pid)
    return {"type": "planet", "id": pl.id, "name": pl.name}


def wref(world, wid):
    w = world.wars.get(wid)
    return {"type": "war", "id": w.id, "name": w.name} if w else None


def _refs(items):
    return [r for r in items if r]


# ---------------------------------------------------------------------- 全体
def state(world):
    factions = sorted(world.alive_factions(), key=lambda f: -(len(f.planets) * 10 + f.fleet / 10))
    return {
        "galaxy": GALAXY_NAME,
        "date": world.date(),
        "t": world.t,
        "year": world.year,
        "seed": world.seed,
        "counts": {
            "planets": len(world.planets),
            "factions": len(factions),
            "persons": len(world.alive_persons()),
            "corps": sum(1 for c in world.corps.values() if c.alive),
            "wars": len(world.active_wars()),
            "log": len(world.log),
        },
        "factions": [faction_summary(world, f) for f in factions],
        "wars": [war_summary(world, w) for w in world.active_wars()],
        "hot": sorted({e.planet for e in world.log[-400:]
                       if e.kind in HOT_KINDS and e.planet is not None and world.t - e.t <= 4}),
    }


def faction_summary(world, f):
    leader = world.person(f.leader)
    return {
        "id": f.id, "name": f.name, "base": f.base_name, "alive": f.alive,
        "gov": GOVERNMENTS[f.gov]["name"], "ideology": IDEOLOGIES[f.ideology]["name"],
        "planets": len(f.planets), "fleet": round(f.fleet), "stability": round(f.stability),
        "capital": f.capital, "leader": pref(world, f.leader),
        "leader_title": careers.job_title(world, leader) if leader else "",
        "at_war": bool(world.wars_of(f.id)),
    }


def war_summary(world, w):
    return {
        "id": w.id, "name": w.name, "active": w.active,
        "start": world.year_of(w.start_t), "end": world.year_of(w.end_t) if w.end_t is not None else None,
        "score": round(w.score), "outcome": w.outcome,
        "attackers": _refs(fref(world, f) for f in sorted(w.attackers | {w.att_leader})),
        "defenders": _refs(fref(world, f) for f in sorted(w.defenders | {w.def_leader})),
        "cause": WAR_CAUSES.get(w.cause, w.cause),
    }


def galaxy_map(world):
    capitals = {f.capital: f.id for f in world.alive_factions()}
    planets = []
    lanes = set()
    for pl in world.planets:
        planets.append({
            "id": pl.id, "name": pl.name, "x": round(pl.x, 4), "y": round(pl.y, 4),
            "owner": pl.owner, "region": pl.region, "type": PLANET_TYPES[pl.ptype]["name"],
            "pop": round(pl.population, 1), "capital": pl.id in capitals,
            "unrest": round(pl.unrest), "features": pl.features,
        })
        for n in pl.lanes:
            lanes.add((min(pl.id, n), max(pl.id, n)))
    return {
        "planets": planets,
        "lanes": sorted(lanes),
        "regions": [{"name": r["name"], "radius": r["radius"]} for r in REGIONS],
    }


def prologue(world):
    return {
        "text": PROLOGUE.format(year=world.year_of(0)),
        "resonance": RESONANCE_LORE,
        "orgs": [{"name": o.name, "desc": o.desc} for o in world.orgs.values() if o.kind in ("order", "void")],
        "factions": [{
            **faction_summary(world, f), "legend": f.legend, "motto": f.motto,
        } for f in sorted(world.factions.values(), key=lambda f: -len(f.planets)) if f.founded_t < 0],
    }


def entry(world, i, e):
    refs = _refs([pref(world, a) for a in e.actors]
                 + [fref(world, f) for f in e.factions if f is not None]
                 + [plref(world, e.planet)]
                 + [pref(world, e.speaker) if e.speaker else None, pref(world, e.replier) if e.replier else None])
    return {
        "i": i, "t": e.t, "year": world.year_of(e.t), "month": e.t % 12 + 1, "kind": e.kind,
        "text": e.text, "imp": e.importance,
        "quote": e.quote, "speaker": pref(world, e.speaker) if e.speaker else None,
        "reply": e.reply, "replier": pref(world, e.replier) if e.replier else None,
        "refs": refs,
    }


def chronicle(world, since=0, min_imp=3, limit=400):
    out = []
    for i in range(len(world.log) - 1, max(since, 0) - 1, -1):
        e = world.log[i]
        if e.importance >= min_imp:
            out.append(entry(world, i, e))
            if len(out) >= limit:
                break
    out.reverse()
    return {"next": len(world.log), "entries": out}


# ---------------------------------------------------------------------- 詳細
def person(world, pid):
    p = world.person(pid)
    if p is None:
        return None
    sp = SPECIES[p.species]
    career = []
    for track, org, rank, start, end, reason in p.career_history:
        career.append({"from": world.year_of(start), "to": world.year_of(end),
                       "org": careers.org_name(world, track, org) or careers.CAREERS[track]["name"],
                       "title": careers.rank_name(world, track, org, rank, p.sex), "reason": reason})
    if p.job:
        career.append({"from": world.year_of(p.job.started), "to": None,
                       "org": careers.org_name(world, p.job.track, p.job.org_id) or careers.CAREERS[p.job.track]["name"],
                       "title": careers.job_title(world, p), "reason": ""})
    return {
        "type": "person", "id": p.id, "name": p.name, "alive": p.alive,
        "species": sp["name"], "species_desc": sp["desc"], "sex": p.sex, "age": p.age(world.t),
        "born": world.year_of(p.birth_t), "died": world.year_of(p.death_t) if p.death_t is not None else None,
        "death_cause": _cause(p.death_cause) if p.death_cause else None, "death_text": p.death_text,
        "origin": p.origin, "planet": plref(world, p.planet), "birth_planet": plref(world, p.birth_planet),
        "faction": fref(world, p.faction), "ideology": IDEOLOGIES[p.ideology]["name"],
        "job": careers.describe_job(world, p) if p.alive else "故人",
        "traits": [{"name": t, "desc": TRAITS[t]["desc"], "acquired": bool(TRAITS[t].get("acquired"))}
                   for t in p.traits],
        "stats": [{"key": k, "name": STAT_NAMES[k], "value": v} for k, v in p.stats.items()],
        "fame": round(p.fame), "wealth": round(p.wealth),
        "titles": list(dict.fromkeys(p.titles)),
        "family": {
            "parents": _refs(pref(world, x) for x in p.parents),
            "spouse": _refs([pref(world, p.spouse)]) if p.spouse else [],
            "former_spouses": _refs(pref(world, x) for x in dict.fromkeys(p.former_spouses)),
            "children": _refs(pref(world, x) for x in p.children),
            "mentor": _refs([pref(world, p.mentor)]) if p.mentor else [],
            "apprentices": _refs(pref(world, x) for x in p.apprentices),
            "rivals": _refs(pref(world, x) for x in sorted(p.rivals)),
        },
        "career": career,
        "bio": [{"date": world.date(t), "text": text} for t, text in p.bio],
        "quotes": [{"date": world.date(t), "text": q} for t, q in p.quotes],
    }


def faction(world, fid):
    f = world.faction(fid)
    if f is None:
        return None
    rel = sorted(((v, k) for k, v in f.relations.items() if world.faction(k) and world.faction(k).alive),
                 reverse=True)
    rulers = []
    for pid, start, end in f.rulers:
        p = world.person(pid)
        rulers.append({"person": pref(world, pid), "from": world.year_of(start),
                       "to": world.year_of(end) if end is not None else None,
                       "fate": _cause(p.death_cause) if p and not p.alive and p.death_cause else ""})
    return {
        "type": "faction", **faction_summary(world, f),
        "gov_desc": GOVERNMENTS[f.gov]["name"], "ideology_desc": IDEOLOGIES[f.ideology]["desc"],
        "motto": f.motto, "legend": f.legend, "species": SPECIES[f.main_species]["name"],
        "founded": world.year_of(f.founded_t), "fell": world.year_of(f.fall_t) if f.fall_t is not None else None,
        "treasury": round(f.treasury), "exhaustion": round(f.exhaustion),
        "capital_ref": plref(world, f.capital),
        "parent": fref(world, f.parent) if f.parent else None,
        "tech": [{"field": TECH_FIELDS[k]["name"], "level": v,
                  "latest": tech_name(k, v - 1) if v else "—"} for k, v in f.tech.items()],
        "allies": _refs(fref(world, a) for a in sorted(world.allies(f.id))) if f.alive else [],
        "trade": _refs(fref(world, next(iter(k - {f.id}))) for k, tr in world.treaties.items()
                       if f.id in k and "trade" in tr) if f.alive else [],
        "friends": [{"faction": fref(world, k), "value": round(v)} for v, k in rel[:4]],
        "enemies": [{"faction": fref(world, k), "value": round(v)} for v, k in rel[-4:][::-1]],
        "wars": [war_summary(world, w) for w in world.wars.values() if f.id in (w.attackers | w.defenders
                                                                                | {w.att_leader, w.def_leader})][-12:],
        "territory": [plref(world, p) for p in sorted(f.planets)],
        "rulers": rulers,
        "history": [{"date": world.date(t), "text": text} for t, text in f.history[-60:]],
    }


def planet(world, pid):
    if pid < 0 or pid >= len(world.planets):
        return None
    pl = world.planet(pid)
    people = sorted((p for p in world.alive_persons() if p.planet == pl.id), key=lambda p: -p.fame)
    corps = [c for c in world.corps.values() if c.alive and (c.hq == pl.id or pl.id in c.branches)]
    return {
        "type": "planet", "id": pl.id, "name": pl.name, "desc": pl.desc,
        "ptype": PLANET_TYPES[pl.ptype]["name"], "region": REGION_NAMES[pl.region],
        "owner": fref(world, pl.owner), "population": round(pl.population),
        "development": round(pl.development, 2), "species": SPECIES[pl.species]["name"],
        "culture": IDEOLOGIES[pl.culture]["name"], "unrest": round(pl.unrest), "defense": round(pl.defense),
        "lanes": [plref(world, n) for n in pl.lanes],
        "residents": [{**pref(world, p.id), "job": careers.describe_job(world, p), "age": p.age(world.t),
                       "species": SPECIES[p.species]["name"]} for p in people[:24]],
        "corps": [{"name": c.name, "sector": SECTORS[c.sector]["name"], "hq": c.hq == pl.id,
                   "ceo": pref(world, c.ceo) if c.ceo else None, "motto": c.motto} for c in corps],
        "history": [{"date": world.date(t), "text": text} for t, text in pl.history[-40:]],
    }


def war(world, wid):
    w = world.wars.get(wid)
    if w is None:
        return None
    return {
        "type": "war", **war_summary(world, w),
        "goal": plref(world, w.goal),
        "battles": [{"date": world.date(b["t"]), "name": b["name"], "planet": plref(world, b["planet"]),
                     "winner": fref(world, b["winner"]), "decisive": b["decisive"],
                     "commander": pref(world, b["w_cmd"]) if b["w_cmd"] else None} for b in w.battles],
        "captured": [{"date": world.date(t), "planet": plref(world, p), "from": fref(world, a),
                      "to": fref(world, b)} for t, p, a, b in w.captured],
        "fallen": _refs(pref(world, x) for x in w.fallen),
    }


def famous(world, n=40, alive_only=True):
    pool = [p for p in (world.alive_persons() if alive_only else world.persons.values())]
    pool.sort(key=lambda p: -p.fame)
    return [{**pref(world, p.id), "fame": round(p.fame), "species": SPECIES[p.species]["name"],
             "age": p.age(world.t), "job": careers.describe_job(world, p) if p.alive else "故人"}
            for p in pool[:n]]


def search(world, q, n=40):
    if not q:
        return []
    hits = [p for p in world.persons.values() if q in p.name]
    hits.sort(key=lambda p: (not p.alive, -p.fame))
    return [{**pref(world, p.id), "fame": round(p.fame), "species": SPECIES[p.species]["name"],
             "age": p.age(world.t), "job": careers.describe_job(world, p) if p.alive else "故人"}
            for p in hits[:n]]


def wars_list(world):
    ws = sorted(world.wars.values(), key=lambda w: (not w.active, -w.start_t))
    return [war_summary(world, w) for w in ws[:200]]
