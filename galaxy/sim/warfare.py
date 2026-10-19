"""戦争：会戦・惑星の攻略・提督の生死・講和。"""

from galaxy.minds import mind_of
from galaxy.narrative.voice import narrate, say, exchange
from galaxy.sim import careers, politics
from galaxy.sim.life import kill, gain_trait, adjust_opinion

BATTLE_STYLES = ["{p}の戦い", "{p}軌道会戦", "{p}星域会戦", "{p}包囲戦", "{p}沖海戦", "{p}降下作戦"]


def monthly(world):
    for pl in world.planets:
        cap = max_defense(world, pl)
        if pl.defense < cap:
            pl.defense = min(cap, pl.defense + cap * 0.04)
    for w in list(world.active_wars()):
        _cleanup(world, w)
        if not w.active:
            continue
        for fid in w.sides():
            f = world.faction(fid)
            f.exhaustion = min(100.0, f.exhaustion + 0.45)
        if world.rng.random() < 0.6:
            _battle(world, w)
            _cleanup(world, w)
        if w.active:
            _check_peace(world, w)


def _cleanup(world, w):
    w.attackers = {a for a in w.attackers if world.faction(a).alive}
    w.defenders = {d for d in w.defenders if world.faction(d).alive}
    if not w.attackers or not w.defenders:
        winner = "att" if w.attackers else "def"
        _end_war(world, w, winner, annihilation=True)


def side_fleet(world, fids):
    total = 0.0
    for fid in fids:
        f = world.faction(fid)
        total += f.fleet / max(1, len(world.wars_of(fid)))
    return total


def _tech_mult(f):
    t = f.tech
    return 1 + 0.09 * t.get("weapons", 0) + 0.06 * t.get("shields", 0) + 0.04 * t.get("propulsion", 0)


def _commander(world, fids):
    pool = [p for fid in sorted(fids) for p in careers.members(world, "military", fid)]
    cands = [p for p in pool if p.job.rank >= 5] or pool
    if not cands:
        return None
    cands.sort(key=lambda p: -(p.job.rank * 3 + p.stat("command") + world.rng.random() * 6))
    return cands[0]


def _front(world, w, offense):
    """攻勢側が狙う惑星を選ぶ。"""
    rng = world.rng
    own = w.attackers if offense == "att" else w.defenders
    enemy = w.defenders if offense == "att" else w.attackers
    border = []
    for fid in enemy:
        for pid in world.faction(fid).planets:
            if any(world.planet(n).owner in own for n in world.planet(pid).lanes):
                border.append(pid)
    if offense == "att" and w.goal in border and rng.random() < 0.5:
        return w.goal
    if border:
        return rng.choice(border)
    pool = [pid for fid in enemy for pid in world.faction(fid).planets]
    return rng.choice(pool) if pool else None


def _battle(world, w):
    rng = world.rng
    att_power = side_fleet(world, w.attackers)
    def_power = side_fleet(world, w.defenders)
    momentum = 0.5 + w.score / 400
    offense = "att" if rng.random() < (att_power / max(1, att_power + def_power)) * 0.6 + momentum * 0.4 else "def"
    target = _front(world, w, offense)
    if target is None:
        return
    planet = world.planet(target)
    off_side = w.attackers if offense == "att" else w.defenders
    def_side = w.defenders if offense == "att" else w.attackers
    off_fac = _lead_faction(world, off_side, target, attacking=True)
    def_fac = world.faction(planet.owner)
    off_cmd = _commander(world, off_side)
    def_cmd = _commander(world, def_side)
    off_commit = side_fleet(world, off_side) * rng.uniform(0.2, 0.5)
    def_commit = side_fleet(world, def_side) * rng.uniform(0.2, 0.5)
    off_eff = off_commit * _tech_mult(off_fac) * _cmd_mult(off_cmd) * rng.uniform(0.7, 1.3)
    fort = 1.25 if "fortress" in planet.features else 1.0
    if def_fac and len(def_fac.planets) == 1:
        fort *= 1.6  # 最後の星を守る者は死に物狂いで戦う
    if def_fac and planet.id == def_fac.capital:
        fort *= 1.2
    def_eff = (def_commit + planet.defense) * _tech_mult(def_fac) * _cmd_mult(def_cmd) * rng.uniform(0.7, 1.3) * fort
    off_wins = off_eff > def_eff
    margin = abs(off_eff - def_eff) / max(1.0, off_eff + def_eff)
    w_side, l_side = (off_side, def_side) if off_wins else (def_side, off_side)
    w_cmd, l_cmd = (off_cmd, def_cmd) if off_wins else (def_cmd, off_cmd)
    w_fac, l_fac = (off_fac, def_fac) if off_wins else (def_fac, off_fac)
    w_loss = (off_commit if off_wins else def_commit) * (0.08 + (1 - margin) * 0.15)
    l_loss = (def_commit if off_wins else off_commit) * (0.2 + margin * 0.5)
    _apply_losses(world, w_side, w_loss)
    _apply_losses(world, l_side, l_loss)

    # 戦いの名前
    prior = sum(1 for b in w.battles if b["planet"] == target)
    name = rng.choice(BATTLE_STYLES).format(p=planet.name)
    if prior:
        name = f"第{prior + 1}次{name}"
    swing = 6 + margin * 25
    w.score += swing if (w_side is w.attackers) else -swing
    w.score = max(-100.0, min(100.0, w.score))
    decisive = margin > 0.45 and (off_commit + def_commit) > 60 and rng.random() < 0.4
    w.battles.append({"t": world.t, "name": name, "planet": target, "winner": w_fac.id,
                      "loser": l_fac.id, "decisive": decisive,
                      "w_cmd": w_cmd.id if w_cmd else None, "l_cmd": l_cmd.id if l_cmd else None})

    # 提督の運命
    actors = tuple(c.id for c in (w_cmd, l_cmd) if c)
    pre = say(world, off_cmd, "battle_before", planet=planet.name) if off_cmd else None
    if w_cmd:
        w_cmd.merit += 4 + margin * 10
        w_cmd.fame += 4 + margin * 20 + (25 if decisive else 0)
        if decisive and rng.random() < 0.5:
            gain_trait(world, w_cmd, "英雄")
    if decisive:
        text = narrate(world, "battle_decisive", battle=name, winner=w_fac.name, loser=l_fac.name,
                       commander=w_cmd.name if w_cmd else "無名の艦長")
        after = say(world, w_cmd, "battle_victory", planet=planet.name, enemy=l_fac.name) if w_cmd else None
        world.record("battle", text, 4, actors=actors, planet=target, factions=(w_fac.id, l_fac.id),
                     quote=after, speaker=w_cmd.id if w_cmd else None)
    else:
        text = narrate(world, "battle", battle=name, winner=w_fac.name, loser=l_fac.name, planet=planet.name,
                       losses=max(1, int(l_loss)))
        world.record("battle", text, 2, actors=actors, planet=target, factions=(w_fac.id, l_fac.id),
                     quote=pre, speaker=off_cmd.id if (pre and off_cmd) else None)
    if l_cmd:
        if rng.random() < 0.06 + margin * 0.15:
            w.fallen.append(l_cmd.id)
            kill(world, l_cmd, "battle", importance=3 if l_cmd.fame > 20 else 2, battle=name)
        else:
            l_cmd.add_quote(world.t, say(world, l_cmd, "battle_defeat", enemy=w_fac.name))
            if rng.random() < 0.25:
                gain_trait(world, l_cmd, rng.choice(["傷痕", "隻眼", "復讐者"]))
            if w_cmd:
                adjust_opinion(l_cmd, w_cmd, -15)
    if w_cmd and rng.random() < 0.03:
        w.fallen.append(w_cmd.id)
        kill(world, w_cmd, "battle", importance=3, battle=name)
    _soldier_casualties(world, l_side, name, 0.03 + margin * 0.05)

    # 惑星の攻略
    if off_wins:
        planet.defense -= off_commit * (0.15 + margin * 0.6)
        if planet.defense <= 0 or (margin > 0.5 and rng.random() < 0.25):
            _capture(world, w, planet, off_fac, def_fac, off_cmd)
    else:
        planet.defense = min(planet.defense + 5, max_defense(world, planet))


def max_defense(world, planet):
    f = world.faction(planet.owner)
    shields = f.tech.get("shields", 0) if f else 0
    return 20 + planet.development * 15 + shields * 6 + (25 if "fortress" in planet.features else 0)


def _lead_faction(world, side, target, attacking):
    """攻撃を担う国（目標惑星に隣接する国を優先）。"""
    for n in world.planet(target).lanes:
        o = world.planet(n).owner
        if o in side:
            return world.faction(o)
    return world.faction(max(side, key=lambda f: world.faction(f).fleet))


def _cmd_mult(cmd):
    if cmd is None:
        return 0.85
    bonus = (cmd.stat("command") - 10) * 0.03 + (cmd.stat("martial") - 10) * 0.01
    if cmd.has("英雄"):
        bonus += 0.08
    if cmd.job and cmd.job.track == "order":
        bonus += cmd.stat("resonance") * 0.01
    return max(0.6, 1 + bonus)


def _apply_losses(world, side, loss):
    total = sum(world.faction(f).fleet for f in side) or 1
    for fid in side:
        f = world.faction(fid)
        f.fleet = max(1.0, f.fleet - loss * f.fleet / total)
        f.exhaustion = min(100.0, f.exhaustion + loss / max(5.0, f.fleet) * 4)


def _soldier_casualties(world, side, battle_name, chance):
    """名もなき兵士だけでなく、記録された若い軍人たちも戦場で散る。"""
    for p in [p for fid in sorted(side) for p in careers.members(world, "military", fid) if p.job.rank < 5]:
        if world.rng.random() < chance * 0.25:
            kill(world, p, "battle", importance=1, battle=battle_name)


def _capture(world, w, planet, winner, loser, cmd):
    old_owner = planet.owner
    line = say(world, cmd, "planet_captured", planet=planet.name) if cmd else None
    world.record("planet_captured", narrate(world, "planet_captured", planet=planet.name, winner=winner.name,
                                            loser=loser.name if loser else "旧支配者"), 4,
                 actors=(cmd.id,) if cmd else (), planet=planet.id,
                 factions=(winner.id, loser.id) if loser else (winner.id,),
                 quote=line, speaker=cmd.id if cmd else None)
    if loser and loser.alive:
        ll = world.person(loser.leader)
        if ll:
            ll.add_quote(world.t, say(world, ll, "planet_lost", planet=planet.name))
        loser.grievances[winner.id] = loser.grievances.get(winner.id, 0) + 10
    swing = 12 + (20 if loser and planet.id == loser.capital else 0)
    politics.transfer_planet(world, planet.id, winner.id, reason="征服")
    w.captured.append((world.t, planet.id, old_owner, winner.id))
    w.score += swing if winner.id in w.attackers else -swing
    w.score = max(-100.0, min(100.0, w.score))
    if cmd:
        cmd.fame += 10
        cmd.merit += 5


def _check_peace(world, w):
    rng = world.rng
    att = world.faction(w.att_leader) if world.faction(w.att_leader).alive else world.faction(next(iter(w.attackers)))
    de = world.faction(w.def_leader) if world.faction(w.def_leader).alive else world.faction(next(iter(w.defenders)))
    months = world.t - w.start_t
    if months < 4:
        return
    goal_taken = w.goal is not None and world.planet(w.goal).owner in w.attackers
    gains = sum(1 for c in w.captured if c[3] in w.attackers)
    # 征服した星が増えるほど、攻め手も矛を収めたくなる
    att.exhaustion = min(100.0, att.exhaustion + gains * 0.05)
    if w.score > 55 or (w.score > 25 and (de.exhaustion > 55 or goal_taken)):
        loser_leader = world.person(de.leader)
        if mind_of(world, loser_leader).accept_peace(world, loser_leader, de, w, False) or w.score > 85 or goal_taken:
            _end_war(world, w, "att")
    elif w.score < -55 or (w.score < -30 and att.exhaustion > 55):
        loser_leader = world.person(att.leader)
        if mind_of(world, loser_leader).accept_peace(world, loser_leader, att, w, False) or w.score < -85:
            _end_war(world, w, "def")
    elif w.cause == "independence" and months > 18 and w.score < 30 and rng.random() < 0.08:
        _end_war(world, w, "def")  # 独立を認めざるを得ない
    elif (att.exhaustion > 65 and de.exhaustion > 45) or months > 10 * 12:
        if rng.random() < 0.15:
            _end_war(world, w, None)


def _end_war(world, w, winner, annihilation=False):
    rng = world.rng
    w.end_t = world.t
    years = max(1, (w.end_t - w.start_t) // 12)
    if winner is None:
        text = narrate(world, "peace_white", war=w.name, faction=world.fname(w.att_leader),
                       enemy=world.fname(w.def_leader))
        w.outcome = "痛み分け"
        win_side, lose_side = w.attackers, w.defenders
    else:
        win_side = w.attackers if winner == "att" else w.defenders
        lose_side = w.defenders if winner == "att" else w.attackers
        wl = w.att_leader if winner == "att" else w.def_leader
        ll = w.def_leader if winner == "att" else w.att_leader
        wf, lf = world.faction(wl), world.faction(ll)
        terms = []
        if not annihilation and lf.alive:
            ceded = _cede(world, w, wf, lf, winner)
            if ceded:
                terms.append(f"{ceded}を割譲した")
            rep = max(0.0, lf.treasury * 0.4)
            if rep > 5:
                lf.treasury -= rep
                wf.treasury += rep
                terms.append(f"{int(rep)}億クレジットの賠償金を支払った")
            if w.cause == "independence" and winner == "def":
                terms.append("独立を承認した")
        if annihilation:
            text = narrate(world, "peace_annihilation", war=w.name, winner=wf.name, loser=lf.name)
        else:
            if not terms:
                terms.append("屈辱的な講和を受け入れた")
            text = narrate(world, "peace_victory", war=w.name, winner=wf.name, loser=lf.name,
                           terms="、".join(terms))
        w.outcome = f"{wf.name}の勝利"
        for fid in lose_side:
            f = world.faction(fid)
            for e in win_side:
                f.grievances[e] = f.grievances.get(e, 0) + 25
    months = w.end_t - w.start_t
    if months < 12:
        text += f"（わずか{max(1, months)}か月の戦争であった）"
    else:
        text += f"（{years}年に及ぶ戦争であった）"
    quote = speaker = reply = replier = None
    if winner is None:
        sp = world.person(world.faction(w.att_leader).leader) if world.faction(w.att_leader).alive else None
        if sp:
            quote, speaker = say(world, sp, "peace"), sp.id
    else:
        wl = world.faction(w.att_leader if winner == "att" else w.def_leader)
        lf = world.faction(w.def_leader if winner == "att" else w.att_leader)
        win_p = world.person(wl.leader) if wl.alive else None
        lose_p = world.person(lf.leader) if lf.alive else None
        if lose_p and win_p and rng.random() < 0.35:
            quote, reply = exchange(world, "negotiation")
            speaker, replier = lose_p.id, win_p.id
        elif lose_p:
            quote, speaker = say(world, lose_p, "surrender"), lose_p.id
            if win_p:
                reply, replier = say(world, win_p, "victory_peace", enemy=lf.name), win_p.id
        elif win_p:
            quote, speaker = say(world, win_p, "victory_peace", enemy=lf.name), win_p.id
    world.record("peace", text, 5, factions=tuple(w.sides()), planet=w.goal,
                 quote=quote, speaker=speaker, reply=reply, replier=replier, bio=False)
    for a in w.attackers:
        for d in w.defenders:
            if world.faction(a).alive and world.faction(d).alive:
                world.treaty(a, d)["truce"] = world.t + 12 * rng.randint(8, 15)
    for fid in w.sides():
        f = world.faction(fid)
        leader = world.person(f.leader)
        if leader:
            leader.add_bio(world.t, f"{w.name}が終結した（{w.outcome}）。")


def _cede(world, w, wf, lf, winner):
    """敗戦国から戦勝国へ惑星を割譲させる。"""
    if w.cause == "independence" and winner == "def":
        return None
    cands = []
    if w.goal is not None and world.planet(w.goal).owner == lf.id:
        cands.append(w.goal)
    border = [pid for pid in lf.planets if pid != lf.capital
              and any(world.planet(n).owner == wf.id for n in world.planet(pid).lanes)]
    cands += border
    cands = [c for c in dict.fromkeys(cands) if c != lf.capital]
    if not cands or len(lf.planets) <= 1:
        return None
    pid = cands[0]
    politics.transfer_planet(world, pid, wf.id, reason="割譲")
    w.captured.append((world.t, pid, lf.id, wf.id))
    return world.plname(pid)
