"""年代記・人物伝・国家史などの読み物を組み立てる。"""

from galaxy.content.lore import PROLOGUE, START_YEAR, GALAXY_NAME, REGIONS, RESONANCE_LORE
from galaxy.content.ideologies import IDEOLOGIES
from galaxy.content.governments import GOVERNMENTS
from galaxy.content.species import SPECIES
from galaxy.content.planets import PLANET_TYPES
from galaxy.content.technologies import TECH_FIELDS, tech_name
from galaxy.content.corporations import SECTORS
from galaxy.content.traits import TRAITS
from galaxy.content.events import WAR_CAUSES
from galaxy.model.entities import STAT_NAMES
from galaxy.sim import careers

STARS = {1: "・", 2: "◇", 3: "◆", 4: "★", 5: "✦"}
REGION_NAMES = {r["key"]: r["name"] for r in REGIONS}


def format_entry(world, e, quotes=True):
    head = f"{STARS.get(e.importance, '・')} {e.t % 12 + 1:>2}月 {e.text}"
    lines = [head]
    if quotes and e.quote:
        lines.append(f"        {world.pname(e.speaker) if e.speaker else '？'}「{e.quote}」")
    if quotes and e.reply:
        lines.append(f"        {world.pname(e.replier) if e.replier else '傍らの者'}「{e.reply}」")
    return "\n".join(lines)


def prologue(world):
    out = [PROLOGUE.format(year=world.year), ""]
    out.append(f"――{GALAXY_NAME}の諸勢力――")
    for f in sorted(world.alive_factions(), key=lambda f: -len(f.planets)):
        leader = world.person(f.leader)
        title = careers.job_title(world, leader) if leader else "空位"
        out.append(f"\n【{f.name}】 {GOVERNMENTS[f.gov]['name']}／{IDEOLOGIES[f.ideology]['name']}"
                   f"／首都{world.plname(f.capital)}／{len(f.planets)}星系")
        out.append(f"  {f.legend}")
        out.append(f"  国是「{f.motto}」 {title} {leader.name if leader else ''}")
    orgs = [o for o in world.orgs.values() if o.kind in ("order", "void")]
    out.append("\n――星々の間に響くもの――")
    out.append(RESONANCE_LORE)
    for o in orgs:
        out.append(f"・{o.name}：{o.desc}")
    return "\n".join(out)


def year_chronicle(world, year, min_importance=3, quotes=True):
    start = (year - START_YEAR) * 12
    entries = [e for e in world.log if start <= e.t < start + 12 and e.importance >= min_importance]
    out = [f"\n━━━━━━━━━━ 残光暦{year}年 ━━━━━━━━━━"]
    if not entries:
        out.append("  銀河は静かな一年を過ごした。")
    for e in entries:
        out.append(format_entry(world, e, quotes))
    return "\n".join(out)


def year_stats(world, year):
    start = (year - START_YEAR) * 12
    es = [e for e in world.log if start <= e.t < start + 12]
    births = sum(1 for p in world.persons.values() if start <= p.birth_t < start + 12)
    deaths = sum(1 for e in es if e.kind.startswith("death_"))
    battles = sum(1 for e in es if e.kind == "battle")
    marriages = sum(1 for e in es if e.kind == "marriage")
    return f"  （この年：記録された死{deaths}件／婚礼{marriages}件／会戦{battles}回／記録された誕生{births}件）"


def _years(world, t0, t1=None):
    t1 = world.t if t1 is None else t1
    return world.year_of(t0), world.year_of(t1)


def biography(world, pid):
    p = world.person(pid)
    if p is None:
        return "その人物は記録にない。"
    sp = SPECIES[p.species]
    born = world.year_of(p.birth_t)
    out = [f"\n＝＝＝ 人物伝：{p.name} ＝＝＝"]
    if p.alive:
        out.append(f"{sp['name']}・{p.sex}　残光暦{born}年生まれ（{p.age(world.t)}歳）　{world.plname(p.planet)}在住")
    else:
        out.append(f"{sp['name']}・{p.sex}　残光暦{born}年〜{world.year_of(p.death_t)}年（享年{p.age(world.t)}）")
    out.append(f"出自：{p.origin or '不明'}　所属：{world.fname(p.faction)}　理念：{IDEOLOGIES[p.ideology]['name']}")
    out.append(f"現在：{careers.describe_job(world, p) if p.alive else '故人'}")
    out.append("性格：" + "、".join(f"{t}（{TRAITS[t]['desc']}）" for t in p.traits))
    out.append("能力：" + "　".join(f"{STAT_NAMES[k]}{v}" for k, v in p.stats.items()))
    out.append(f"名声：{p.fame:.0f}　資産：{p.wealth:.0f}")
    if p.titles:
        out.append("称号：" + "、".join(dict.fromkeys(p.titles)))
    fam = []
    if p.parents:
        fam.append("親：" + "、".join(_pref(world, x) for x in p.parents))
    if p.spouse:
        fam.append("伴侶：" + _pref(world, p.spouse))
    if p.former_spouses:
        fam.append("先立った伴侶：" + "、".join(_pref(world, x) for x in dict.fromkeys(p.former_spouses)))
    if p.children:
        fam.append("子：" + "、".join(_pref(world, x) for x in p.children))
    if p.mentor:
        fam.append("師：" + _pref(world, p.mentor))
    if p.apprentices:
        fam.append("弟子：" + "、".join(_pref(world, x) for x in p.apprentices))
    if p.rivals:
        fam.append("宿敵：" + "、".join(_pref(world, x) for x in sorted(p.rivals)))
    if fam:
        out.append("\n― 縁 ―")
        out.extend("  " + x for x in fam)
    if p.career_history or p.job:
        out.append("\n― 経歴 ―")
        for track, org, rank, start, end, reason in p.career_history:
            title = careers.rank_name(world, track, org, rank, p.sex)
            org_n = careers.org_name(world, track, org)
            out.append(f"  {world.year_of(start)}〜{world.year_of(end)}年　{org_n}　最終階級：{title}"
                       + (f"（{reason}）" if reason else ""))
        if p.job:
            out.append(f"  {world.year_of(p.job.started)}年〜　{careers.describe_job(world, p)}")
    out.append("\n― 生涯 ―")
    for t, text in p.bio:
        out.append(f"  {world.year_of(t)}年{t % 12 + 1}月　{text}")
    if p.quotes:
        out.append("\n― 語録 ―")
        for t, q in p.quotes[-12:]:
            out.append(f"  「{q}」（{world.year_of(t)}年）")
    if not p.alive:
        out.append(f"\n― 最期 ―\n  {p.death_text}")
    return "\n".join(out)


def _pref(world, pid):
    q = world.person(pid)
    if q is None:
        return "？"
    mark = "" if q.alive else "†"
    return f"{q.name}{mark}[{q.id}]"


def faction_report(world, fid):
    f = world.faction(fid)
    if f is None:
        return "その国家は記録にない。"
    out = [f"\n＝＝＝ 国家史：{f.name} ＝＝＝"]
    out.append(f"政体：{GOVERNMENTS[f.gov]['name']}　国是：{IDEOLOGIES[f.ideology]['name']}"
               f"（{IDEOLOGIES[f.ideology]['desc']}）")
    out.append(f"建国：残光暦{world.year_of(f.founded_t)}年" + ("" if f.alive else f"　滅亡：{world.year_of(f.fall_t)}年"))
    out.append(f"標語：「{f.motto}」　主要種族：{SPECIES[f.main_species]['name']}")
    if f.legend:
        out.append(f"建国神話：{f.legend}")
    if f.alive:
        out.append(f"首都：{world.plname(f.capital)}　領土：{len(f.planets)}星系　"
                   f"安定度：{f.stability:.0f}　戦争疲弊：{f.exhaustion:.0f}　国庫：{f.treasury:.0f}　艦隊：{f.fleet:.0f}")
        out.append("技術：" + "　".join(f"{TECH_FIELDS[k]['name']}{v}" for k, v in f.tech.items()))
        allies = [world.fname(a) for a in world.allies(f.id)]
        if allies:
            out.append("同盟国：" + "、".join(allies))
        rel = sorted(((v, k) for k, v in f.relations.items() if world.faction(k).alive), reverse=True)
        if rel:
            out.append("最も友好的：" + "、".join(f"{world.fname(k)}({v:+.0f})" for v, k in rel[:3]))
            out.append("最も敵対的：" + "、".join(f"{world.fname(k)}({v:+.0f})" for v, k in rel[-3:]))
        wars = world.wars_of(f.id)
        if wars:
            out.append("交戦中：" + "、".join(w.name for w in wars))
        out.append("領土：" + "、".join(world.plname(p) for p in sorted(f.planets)))
    out.append("\n― 歴代の元首 ―")
    for pid, start, end in f.rulers:
        p = world.person(pid)
        span = f"{world.year_of(start)}〜{world.year_of(end) if end is not None else ''}"
        out.append(f"  {span}年　{_pref(world, pid)}" + (f"（{p.death_cause and _cause(p.death_cause)}）" if p and not p.alive else ""))
    if f.history:
        out.append("\n― 歩み ―")
        for t, text in f.history[-40:]:
            out.append(f"  {world.year_of(t)}年　{text}")
    return "\n".join(out)


def _cause(c):
    return {"natural": "老衰", "illness": "病死", "accident": "事故死", "battle": "戦死",
            "assassinated": "暗殺", "executed": "処刑", "plague": "疫病"}.get(c, c)


def planet_report(world, pid):
    try:
        pl = world.planet(pid)
    except IndexError:
        return "その星は星図にない。"
    out = [f"\n＝＝＝ 惑星：{pl.name} ＝＝＝"]
    out.append(f"{PLANET_TYPES[pl.ptype]['name']}／{REGION_NAMES[pl.region]}　支配：{world.fname(pl.owner)}")
    out.append(pl.desc)
    out.append(f"人口：{pl.population:,.0f}百万　発展度：{pl.development:.2f}　主要種族：{SPECIES[pl.species]['name']}"
               f"　住民の理念：{IDEOLOGIES[pl.culture]['name']}　不穏度：{pl.unrest:.0f}")
    out.append("航路：" + "、".join(f"{world.plname(n)}[{n}]" for n in pl.lanes))
    people = sorted([p for p in world.persons.values() if p.alive and p.planet == pl.id], key=lambda p: -p.fame)
    if people:
        out.append("\n― 名のある住人 ―")
        for p in people[:15]:
            out.append(f"  [{p.id}] {p.name}（{SPECIES[p.species]['name']}・{p.age(world.t)}歳）{careers.describe_job(world, p)}")
    corps = [c for c in world.corps.values() if c.alive and (c.hq == pl.id or pl.id in c.branches)]
    if corps:
        out.append("\n― 企業 ―")
        for c in corps:
            out.append(f"  {c.name}（{SECTORS[c.sector]['name']}）" + ("本社" if c.hq == pl.id else "支社"))
    if pl.history:
        out.append("\n― この星の歴史 ―")
        for t, text in pl.history[-20:]:
            out.append(f"  {world.year_of(t)}年　{text}")
    return "\n".join(out)


def war_report(world, wid):
    w = world.wars.get(wid)
    if w is None:
        return "その戦争は記録にない。"
    out = [f"\n＝＝＝ 戦史：{w.name} ＝＝＝"]
    span = f"{world.year_of(w.start_t)}年〜" + (f"{world.year_of(w.end_t)}年" if w.end_t is not None else "継続中")
    out.append(f"{span}　原因：{WAR_CAUSES.get(w.cause, w.cause)}　戦況：{w.score:+.0f}")
    out.append("攻撃側：" + "、".join(world.fname(f) for f in w.attackers | {w.att_leader}))
    out.append("防衛側：" + "、".join(world.fname(f) for f in w.defenders | {w.def_leader}))
    if w.outcome:
        out.append(f"結末：{w.outcome}")
    if w.battles:
        out.append("\n― 主な会戦 ―")
        for b in w.battles[-25:]:
            mark = "★" if b["decisive"] else "・"
            cmd = f"（指揮：{world.pname(b['w_cmd'])}）" if b["w_cmd"] else ""
            out.append(f"  {mark}{world.year_of(b['t'])}年{b['t'] % 12 + 1}月 {b['name']}：{world.fname(b['winner'])}の勝利{cmd}")
    if w.captured:
        out.append("\n― 領土の変化 ―")
        for t, pid, old, new in w.captured:
            out.append(f"  {world.year_of(t)}年　{world.plname(pid)}：{world.fname(old)} → {world.fname(new)}")
    if w.fallen:
        out.append("\n― 散った者たち ―")
        out.append("  " + "、".join(_pref(world, x) for x in w.fallen))
    return "\n".join(out)


def overview(world):
    out = [f"\n＝＝＝ {GALAXY_NAME}の現状（{world.date()}） ＝＝＝"]
    alive = world.alive_persons()
    out.append(f"惑星{len(world.planets)}　国家{len(world.alive_factions())}　記録された人物{len(alive)}名"
               f"　企業{sum(1 for c in world.corps.values() if c.alive)}社　進行中の戦争{len(world.active_wars())}")
    out.append("\n― 列強 ―")
    for f in sorted(world.alive_factions(), key=lambda f: -(len(f.planets) * 10 + f.fleet / 10))[:20]:
        leader = world.person(f.leader)
        out.append(f"  [{f.id:>2}] {f.name}（{GOVERNMENTS[f.gov]['name']}・{IDEOLOGIES[f.ideology]['name']}）"
                   f" {len(f.planets)}星系　艦隊{f.fleet:.0f}　元首：{leader.name if leader else '空位'}")
    wars = world.active_wars()
    if wars:
        out.append("\n― 進行中の戦争 ―")
        for w in wars:
            out.append(f"  [{w.id}] {w.name}（{world.year_of(w.start_t)}年〜）戦況{w.score:+.0f}")
    return "\n".join(out)


def famous(world, n=20, alive_only=True):
    pool = [p for p in world.persons.values() if p.alive or not alive_only]
    pool.sort(key=lambda p: -p.fame)
    out = ["\n＝＝＝ 銀河の著名人 ＝＝＝"]
    for p in pool[:n]:
        mark = "" if p.alive else "†"
        out.append(f"  [{p.id:>5}] {p.name}{mark}（{SPECIES[p.species]['name']}・{p.age(world.t)}歳）"
                   f"名声{p.fame:.0f}　{careers.describe_job(world, p) if p.alive else '故人'}")
    return "\n".join(out)


def tech_report(world):
    out = ["\n＝＝＝ 技術の最前線 ＝＝＝"]
    for k, field in TECH_FIELDS.items():
        best = max(world.alive_factions(), key=lambda f: f.tech.get(k, 0), default=None)
        if best:
            lv = best.tech.get(k, 0)
            latest = tech_name(k, lv - 1) if lv else "未開拓"
            out.append(f"  {field['name']}：{best.name}（第{lv}段階「{latest}」）")
    return "\n".join(out)
