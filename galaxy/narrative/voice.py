"""台詞とイベント文の生成。"""

import string

from galaxy.content.dialogue import LINES, EXCHANGES
from galaxy.content.events import TEMPLATES
from galaxy.content.ideologies import IDEOLOGIES


# 埋められなかったプレースホルダの記録（テストで検出するため）
MISSING = set()


class _Safe(dict):
    def __missing__(self, key):
        MISSING.add(key)
        return "某"


_formatter = string.Formatter()


def fmt(template, **ctx):
    return _formatter.vformat(template, (), _Safe(ctx))


def narrate(world, kind, **ctx):
    """イベント種別に応じたテンプレートを1つ選び、文章にする。"""
    options = TEMPLATES.get(kind)
    if not options:
        return fmt(kind, **ctx)
    return fmt(world.rng.choice(options), **ctx)


def _matches(person, cond):
    for key, val in cond.items():
        if key == "trait" and val not in person.traits:
            return False
        if key == "ideology" and person.ideology != val:
            return False
        if key == "track" and (person.job is None or person.job.track != val):
            return False
        if key == "species" and person.species != val:
            return False
    return True


def say(world, person, situation, **ctx):
    """人物の性格・理念・職業・種族に合った台詞を選ぶ。"""
    lines = LINES.get(situation)
    if not lines or person is None:
        return None
    weighted = []
    for entry in lines:
        if isinstance(entry, tuple):
            text, cond = entry
            if _matches(person, cond):
                weighted.append((text, 4.0))
        else:
            weighted.append((entry, 1.0))
    if not weighted:
        return None
    total = sum(w for _, w in weighted)
    r = world.rng.random() * total
    for text, w in weighted:
        r -= w
        if r <= 0:
            break
    ctx.setdefault("self", person.name)
    ctx.setdefault("slogan", world.rng.choice(IDEOLOGIES[person.ideology]["slogans"]))
    return fmt(text, **ctx)


def exchange(world, kind, **ctx):
    pairs = EXCHANGES.get(kind)
    if not pairs:
        return None, None
    a, b = world.rng.choice(pairs)
    return fmt(a, **ctx), fmt(b, **ctx)
