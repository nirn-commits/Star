"""シミュレーションに登場する全ての実体（データクラス）。

人物（Person）はNPCもプレイヤーも同じクラスで表す。違いは意思決定を行う
「心（Mind）」だけで、寿命・就職・出世・結婚・死亡の仕組みは完全に共通である。
"""

from dataclasses import dataclass, field

from galaxy.content.traits import TRAITS, DISPOSITIONS

_DISP_CACHE = {}


def _disposition(traits, key):
    """特性の組み合わせごとに性向を計算してキャッシュする。"""
    k = (traits, key)
    v = _DISP_CACHE.get(k)
    if v is None:
        v = sum(TRAITS.get(tr, {}).get("mods", {}).get(key, 0.0) for tr in traits)
        _DISP_CACHE[k] = v
    return v


STATS = ("martial", "command", "intellect", "diplomacy", "learning", "resonance")
STAT_NAMES = {
    "martial": "武勇", "command": "統率", "intellect": "知略",
    "diplomacy": "弁舌", "learning": "学識", "resonance": "共鳴",
}


@dataclass
class Job:
    track: str            # careers.CAREERS のキー
    org_id: int | None    # 所属組織のID（国家・企業・律院・犯罪組織）
    rank: int
    since: int            # この階級になった月
    started: int          # この職に就いた月
    detail: str = ""      # 労働者などの具体的な職種名


@dataclass
class Person:
    id: int
    given: str
    family: str
    species: str
    sex: str
    birth_t: int
    birth_planet: int
    planet: int
    faction: int | None
    traits: list
    stats: dict
    ideology: str
    origin: str = ""
    wealth: float = 0.0
    health: float = 1.0
    job: Job | None = None
    retired: bool = False
    spouse: int | None = None
    former_spouses: list = field(default_factory=list)
    children: list = field(default_factory=list)
    parents: tuple = ()
    alive: bool = True
    death_t: int | None = None
    death_cause: str | None = None
    death_text: str | None = None
    fame: float = 0.0
    merit: float = 0.0
    bio: list = field(default_factory=list)       # [(t, 文)]
    quotes: list = field(default_factory=list)    # [(t, 台詞)]
    opinions: dict = field(default_factory=dict)  # {人物ID: 好感度}
    mentor: int | None = None
    apprentices: list = field(default_factory=list)
    rivals: set = field(default_factory=set)
    friends: set = field(default_factory=set)
    titles: list = field(default_factory=list)
    career_history: list = field(default_factory=list)  # [(track, org_id, 最高階級, 開始, 終了)]
    is_player: bool = False

    @property
    def name(self):
        return f"{self.given}・{self.family}"

    def age(self, t):
        end = self.death_t if self.death_t is not None else t
        return (end - self.birth_t) // 12

    def has(self, trait):
        return trait in self.traits

    def disposition(self, key):
        return _disposition(tuple(self.traits), key)

    def dispositions(self):
        return {k: self.disposition(k) for k in DISPOSITIONS}

    def stat(self, key):
        return self.stats.get(key, 0)

    def add_bio(self, t, text):
        self.bio.append((t, text))

    def add_quote(self, t, text):
        self.quotes.append((t, text))
        if len(self.quotes) > 40:
            del self.quotes[0]


@dataclass
class Planet:
    id: int
    name: str
    ptype: str
    region: str
    x: float
    y: float
    population: float               # 百万人単位
    development: float              # 0.1〜3.0
    minerals: float
    food: float
    energy: float
    species: str                    # 主要種族
    culture: str                    # 住民の主な理念
    owner: int | None = None
    features: list = field(default_factory=list)
    lanes: list = field(default_factory=list)
    desc: str = ""
    unrest: float = 0.0
    defense: float = 10.0
    conquered_t: int | None = None
    history: list = field(default_factory=list)  # [(t, 文)]


@dataclass
class Faction:
    id: int
    name: str
    base_name: str
    gov: str
    ideology: str
    capital: int
    founded_t: int
    planets: set = field(default_factory=set)
    leader: int | None = None
    dynasty: str | None = None
    treasury: float = 100.0
    fleet: float = 50.0
    tech: dict = field(default_factory=dict)
    research: dict = field(default_factory=dict)
    stability: float = 60.0
    exhaustion: float = 0.0
    relations: dict = field(default_factory=dict)   # {勢力ID: 好感度 -100〜100}
    grievances: dict = field(default_factory=dict)  # {勢力ID: 恨み}
    alive: bool = True
    fall_t: int | None = None
    motto: str = ""
    legend: str = ""
    main_species: str = "human"
    last_election_t: int = 0
    rulers: list = field(default_factory=list)      # [(人物ID, 開始, 終了)]
    history: list = field(default_factory=list)     # [(t, 文)]
    parent: int | None = None                       # 独立元の勢力


@dataclass
class Corporation:
    id: int
    name: str
    sector: str
    hq: int
    faction: int | None
    founded_t: int
    value: float = 100.0
    ceo: int | None = None
    founder: int | None = None
    branches: set = field(default_factory=set)
    motto: str = ""
    alive: bool = True
    closed_t: int | None = None
    history: list = field(default_factory=list)


@dataclass
class Organization:
    """律院・虚環派・犯罪組織などの国家横断的な組織。"""
    id: int
    kind: str          # 'order' | 'void' | 'syndicate'
    name: str
    seat: int          # 本拠地の惑星
    founded_t: int
    leader: int | None = None
    power: float = 50.0
    alive: bool = True
    desc: str = ""
    history: list = field(default_factory=list)


@dataclass
class War:
    id: int
    name: str
    attackers: set
    defenders: set
    att_leader: int    # 主戦国（攻撃側）
    def_leader: int    # 主戦国（防衛側）
    cause: str
    goal: int | None   # 目標惑星
    start_t: int
    end_t: int | None = None
    score: float = 0.0          # 正なら攻撃側優勢
    battles: list = field(default_factory=list)
    captured: list = field(default_factory=list)   # [(t, 惑星, 旧所有, 新所有)]
    fallen: list = field(default_factory=list)     # 戦死した名のある人物
    outcome: str = ""

    @property
    def active(self):
        return self.end_t is None

    def sides(self):
        return self.attackers | self.defenders

    def side_of(self, fid):
        if fid in self.attackers:
            return "att"
        if fid in self.defenders:
            return "def"
        return None

    def enemies_of(self, fid):
        if fid in self.attackers:
            return self.defenders
        if fid in self.defenders:
            return self.attackers
        return set()


@dataclass
class Entry:
    """年代記の一項目。"""
    t: int
    kind: str
    text: str
    importance: int = 1            # 1(些事)〜5(歴史的大事件)
    actors: tuple = ()
    planet: int | None = None
    factions: tuple = ()
    quote: str | None = None
    speaker: int | None = None
    reply: str | None = None
    replier: int | None = None
