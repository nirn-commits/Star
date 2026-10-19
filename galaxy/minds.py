"""人物の意思決定を担う「心」。

シミュレーションの各システムは、人物に選択を迫るとき必ず `mind_of(world, person)` を
通して判断を仰ぐ。NPCは AIMind が性格・理念・状況から判断し、将来プレイヤーが
追加されたときは PlayerMind に差し替えるだけで、同じ人生の仕組みに乗ることができる。
"""

import math

from galaxy.content.ideologies import IDEOLOGIES, compatibility


class Mind:
    """意思決定のインターフェース。全ての判断はここを通る。"""

    def choose_career(self, world, person, options):
        """options: [(track, org_id, 重み)] から1つ選ぶ。"""
        raise NotImplementedError

    def accept_marriage(self, world, person, partner):
        raise NotImplementedError

    def want_retire(self, world, person):
        raise NotImplementedError

    def want_found_corp(self, world, person):
        raise NotImplementedError

    def plot_coup(self, world, person, faction):
        raise NotImplementedError

    def heed_void(self, world, person):
        raise NotImplementedError

    def want_career_change(self, world, person):
        raise NotImplementedError

    # 以下は国家元首としての判断
    def consider_war(self, world, leader, faction, target, odds):
        raise NotImplementedError

    def honor_alliance(self, world, leader, faction, ally, war):
        raise NotImplementedError

    def accept_peace(self, world, leader, faction, war, terms_favorable):
        raise NotImplementedError

    def consider_alliance(self, world, leader, faction, other):
        raise NotImplementedError


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


class AIMind(Mind):
    def choose_career(self, world, person, options):
        total = sum(max(w, 0.01) for _, _, w in options)
        r = world.rng.random() * total
        for opt in options:
            r -= max(opt[2], 0.01)
            if r <= 0:
                return opt
        return options[-1]

    def accept_marriage(self, world, person, partner):
        op = person.opinions.get(partner.id, 0)
        base = 0.55 + op / 200 + person.disposition("sociability") * 0.08
        if partner.species != person.species:
            base -= 0.35 if person.disposition("zeal") <= 0 else 0.6
            if person.ideology == "purity":
                base -= 0.5
        return world.rng.random() < base

    def want_retire(self, world, person):
        ambition = person.disposition("ambition")
        return world.rng.random() < 0.35 - ambition * 0.08

    def want_found_corp(self, world, person):
        d = person.disposition("ambition") + person.disposition("greed") + person.disposition("boldness") * 0.5
        return world.rng.random() < 0.02 + max(d, 0) * 0.02

    def plot_coup(self, world, person, faction):
        leader = world.person(faction.leader)
        op = person.opinions.get(faction.leader, 0) if leader else -50
        drive = (person.disposition("ambition") * 0.6 - person.disposition("loyalty") * 0.7
                 + person.disposition("boldness") * 0.3 - op / 40)
        if leader is not None and leader.ideology != person.ideology:
            drive += 0.8 - compatibility(leader.ideology, person.ideology)
        drive += (40 - faction.stability) / 15
        return world.rng.random() < _sigmoid(drive - 4.0)

    def heed_void(self, world, person):
        d = (person.disposition("ambition") - person.disposition("compassion")
             + person.disposition("zeal") * 0.5)
        return world.rng.random() < _sigmoid(d - 3.5)

    def want_career_change(self, world, person):
        d = person.disposition("ambition") + person.disposition("curiosity") * 0.5
        return world.rng.random() < 0.05 + max(d, 0) * 0.03

    def consider_war(self, world, leader, faction, target, odds):
        ideo = IDEOLOGIES[faction.ideology]
        bold = leader.disposition("boldness") if leader else 0
        compassion = leader.disposition("compassion") if leader else 0
        drive = (ideo["aggression"] * 3.0 + bold * 0.4 - compassion * 0.3
                 + (odds - 1.0) * 2.5 - faction.exhaustion / 20
                 - faction.relations.get(target.id, 0) / 30)
        return world.rng.random() < _sigmoid(drive - 4.5)

    def honor_alliance(self, world, leader, faction, ally, war):
        loyalty = leader.disposition("loyalty") + leader.disposition("honesty") if leader else 0
        op = faction.relations.get(ally.id, 0)
        return world.rng.random() < 0.55 + loyalty * 0.1 + op / 300 - faction.exhaustion / 150

    def accept_peace(self, world, leader, faction, war, terms_favorable):
        if terms_favorable:
            return True
        stubborn = (leader.disposition("zeal") + leader.disposition("boldness")) if leader else 0
        return world.rng.random() < 0.3 + faction.exhaustion / 120 - stubborn * 0.06

    def consider_alliance(self, world, leader, faction, other):
        return world.rng.random() < 0.6 + (leader.disposition("sociability") * 0.05 if leader else 0)


class PlayerMind(Mind):
    """プレイヤー用の心（将来の拡張用）。

    現時点では AIMind に判断を委ねるが、各メソッドを UI からの入力待ちに置き換える
    ことでプレイヤーキャラクターとして振る舞えるようになる。
    """

    def __init__(self, fallback=None):
        self.fallback = fallback or AIMind()

    def __getattribute__(self, name):
        if name in ("fallback", "__init__", "__class__", "__dict__"):
            return object.__getattribute__(self, name)
        return getattr(object.__getattribute__(self, "fallback"), name)


_AI = AIMind()
_overrides = {}


def set_mind(person_id, mind):
    _overrides[person_id] = mind


def mind_of(world, person):
    if person is None:
        return _AI
    return _overrides.get(person.id, _AI)
