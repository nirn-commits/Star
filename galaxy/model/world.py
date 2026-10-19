"""世界の状態を保持するコンテナ。

すべての実体の登録簿・暦・年代記・条約を持つ。シミュレーションの各システムは
World を受け取って状態を書き換える。
"""

import random
from collections import defaultdict

from galaxy.content.lore import ERA_NAME, START_YEAR
from galaxy.model.entities import Entry


class World:
    def __init__(self, seed=0):
        self.seed = seed
        self.rng = random.Random(seed)
        self.t = 0  # 経過月数（0 = 残光暦 START_YEAR 年 1月）
        self.persons = {}
        self.living = []  # 生存者（死者は月初めに取り除かれる）
        self.planets = []
        self.factions = {}
        self.corps = {}
        self.orgs = {}
        self.wars = {}
        self.log = []
        self.treaties = {}  # {frozenset({a, b}): {"alliance": t, "trade": t, "truce": 期限}}
        self._next = defaultdict(int)
        # 階級ごとの在職者数 {(track, org_id, rank): 人数}
        self.rank_count = defaultdict(int)
        # 組織ごとの在籍者 {(track, org_id): {人物ID}}
        self.roster = defaultdict(set)
        # 毎月再計算されるキャッシュ
        self.by_planet = defaultdict(list)
        self.neighbors = defaultdict(set)
        self.factions_alive_cache = []
        self.war_count = 0
        self.war_names = defaultdict(int)

    # ------------------------------------------------------------------ ID
    def new_id(self, kind):
        self._next[kind] += 1
        return self._next[kind]

    # ------------------------------------------------------------------ 暦
    @property
    def year(self):
        return START_YEAR + self.t // 12

    @property
    def month(self):
        return self.t % 12 + 1

    def date(self, t=None):
        t = self.t if t is None else t
        return f"{ERA_NAME}{START_YEAR + t // 12}年{t % 12 + 1}月"

    def year_of(self, t):
        return START_YEAR + t // 12

    # ------------------------------------------------------------------ 検索
    def add_person(self, p):
        self.persons[p.id] = p
        self.living.append(p)

    def person(self, pid):
        return self.persons.get(pid)

    def planet(self, pid):
        return self.planets[pid]

    def faction(self, fid):
        return self.factions.get(fid)

    def alive_persons(self):
        return [p for p in self.living if p.alive]

    def alive_factions(self):
        return [f for f in self.factions.values() if f.alive]

    def active_wars(self):
        return [w for w in self.wars.values() if w.active]

    def pname(self, pid):
        p = self.persons.get(pid)
        return p.name if p else "名もなき者"

    def fname(self, fid):
        f = self.factions.get(fid)
        return f.name if f else "無所属"

    def plname(self, pid):
        return self.planets[pid].name if pid is not None else "どこか"

    # ------------------------------------------------------------------ 年代記
    def record(self, kind, text, importance=1, actors=(), planet=None, factions=(),
               quote=None, speaker=None, reply=None, replier=None, bio=True):
        e = Entry(self.t, kind, text, importance, tuple(actors), planet, tuple(factions),
                  quote, speaker, reply, replier)
        self.log.append(e)
        if bio:
            for pid in actors:
                p = self.persons.get(pid)
                if p is not None:
                    p.add_bio(self.t, text)
        if quote and speaker is not None:
            p = self.persons.get(speaker)
            if p is not None:
                p.add_quote(self.t, quote)
        if reply and replier is not None:
            p = self.persons.get(replier)
            if p is not None:
                p.add_quote(self.t, reply)
        if importance >= 3:
            for fid in factions:
                f = self.factions.get(fid)
                if f is not None:
                    f.history.append((self.t, text))
            if planet is not None:
                self.planets[planet].history.append((self.t, text))
        return e

    # ------------------------------------------------------------------ 条約
    def treaty(self, a, b):
        return self.treaties.setdefault(frozenset((a, b)), {})

    def has_treaty(self, a, b, kind):
        tr = self.treaties.get(frozenset((a, b)))
        if not tr or kind not in tr:
            return False
        if kind == "truce":
            return tr["truce"] > self.t
        return True

    def drop_treaty(self, a, b, kind):
        tr = self.treaties.get(frozenset((a, b)))
        if tr:
            tr.pop(kind, None)

    def allies(self, fid):
        out = set()
        for key, tr in self.treaties.items():
            if fid in key and "alliance" in tr:
                out |= set(key) - {fid}
        return {a for a in out if self.factions[a].alive}

    def at_war(self, a, b):
        for w in self.wars.values():
            if w.active and ((a in w.attackers and b in w.defenders) or
                             (a in w.defenders and b in w.attackers)):
                return w
        return None

    def wars_of(self, fid):
        return [w for w in self.wars.values() if w.active and fid in w.sides()]

    # ------------------------------------------------------------------ キャッシュ
    def rebuild_caches(self):
        self.factions_alive_cache = [f for f in self.factions.values() if f.alive]
        self.living = [p for p in self.living if p.alive]
        self.by_planet = defaultdict(list)
        for p in self.living:
            self.by_planet[p.planet].append(p)
        self.neighbors = defaultdict(set)
        for pl in self.planets:
            if pl.owner is None:
                continue
            for other in pl.lanes:
                o = self.planets[other].owner
                if o is not None and o != pl.owner:
                    self.neighbors[pl.owner].add(o)
