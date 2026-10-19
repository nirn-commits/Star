"""イデオロギー（理念）の定義。

各理念は4つの軸上の座標を持ち、理念同士の相性は座標の距離から計算される。
  authority : 権威主義(+1) ⇔ 自由主義(-1)
  market    : 市場・私益(+1) ⇔ 共同体・公益(-1)
  mystic    : 神秘・信仰(+1) ⇔ 世俗・合理(-1)
  xeno      : 排他(+1) ⇔ 融和(-1)

aggression : 戦争への傾き (0〜1)
trade      : 交易への熱意 (0〜1)
research   : 研究への熱意 (0〜1)
"""

import math

IDEOLOGIES = {
    "imperial": {
        "name": "帝政復古主義",
        "desc": "アウラ帝政の栄光をふたたび。銀河はひとつの玉座のもとでのみ平和たりうる。",
        "axes": (0.9, 0.0, 0.3, 0.4),
        "aggression": 0.7, "trade": 0.4, "research": 0.5,
        "govs": ["empire", "kingdom"],
        "slogans": ["玉座なき銀河に秩序なし", "千の星をひとつの冠に", "残光を、再び恒星に"],
    },
    "republic": {
        "name": "共和主義",
        "desc": "権力は市民から委ねられるもの。いかなる王も、二度と星々を所有してはならない。",
        "axes": (-0.6, 0.1, -0.4, -0.3),
        "aggression": 0.35, "trade": 0.6, "research": 0.7,
        "govs": ["republic", "federation", "council"],
        "slogans": ["一票は一隻の戦艦に勝る", "星々は誰のものでもない", "議場こそ我らの戦場"],
    },
    "corporatism": {
        "name": "企業至上主義",
        "desc": "効率こそ美徳。国家は株主に奉仕する一企業にすぎない。",
        "axes": (0.4, 0.95, -0.6, 0.0),
        "aggression": 0.45, "trade": 0.95, "research": 0.7,
        "govs": ["corporate"],
        "slogans": ["利益は嘘をつかない", "全ての星に値札を", "契約は神よりも重い"],
    },
    "harmonist": {
        "name": "律院正統派",
        "desc": "共鳴の旋律に耳を澄ませ、銀河の調和を守ること。それが知性ある者の務めである。",
        "axes": (0.2, -0.4, 0.95, -0.4),
        "aggression": 0.2, "trade": 0.4, "research": 0.5,
        "govs": ["theocracy", "council"],
        "slogans": ["旋律に従え、さすれば迷わず", "調和は剣より強し", "星々は歌っている"],
    },
    "voidism": {
        "name": "虚環主義",
        "desc": "旋律の裂け目にこそ真の力が宿る。調和とは弱者の言い訳にすぎない。",
        "axes": (0.8, -0.1, 0.95, 0.6),
        "aggression": 0.85, "trade": 0.2, "research": 0.6,
        "govs": ["theocracy", "empire"],
        "slogans": ["沈黙の向こうに真理あり", "弱き旋律は断ち切られるべし", "虚ろこそ満ちる"],
    },
    "purity": {
        "name": "種族純血主義",
        "desc": "我らの血こそ星々を継ぐにふさわしい。異種族との混交は滅びへの道である。",
        "axes": (0.7, -0.2, 0.1, 1.0),
        "aggression": 0.8, "trade": 0.2, "research": 0.4,
        "govs": ["empire", "kingdom", "junta"],
        "slogans": ["血は記憶し、血は裁く", "母星の名にかけて", "純粋なるものだけが残る"],
    },
    "freetrade": {
        "name": "自由交易主義",
        "desc": "航路を開け、関税を壊せ。交易船が通う限り、戦艦は眠っていられる。",
        "axes": (-0.5, 0.8, -0.3, -0.7),
        "aggression": 0.25, "trade": 1.0, "research": 0.6,
        "govs": ["republic", "corporate", "council"],
        "slogans": ["開かれた航路に栄えあれ", "商人は国境を知らない", "取引のあるところに戦争なし"],
    },
    "pacifism": {
        "name": "調和平和主義",
        "desc": "大寂滅を繰り返してはならない。いかなる大義も、星を焼く理由にはならない。",
        "axes": (-0.4, -0.5, 0.3, -0.8),
        "aggression": 0.05, "trade": 0.6, "research": 0.6,
        "govs": ["republic", "council", "federation"],
        "slogans": ["剣を鋤に、戦艦を貨物船に", "最後の戦争は既に終わった", "誰の子も星屑にさせない"],
    },
    "militarism": {
        "name": "鋼鉄軍国主義",
        "desc": "力なき理念は戯言である。艦隊の大きさこそが国家の正しさを証明する。",
        "axes": (0.85, -0.3, -0.5, 0.5),
        "aggression": 0.95, "trade": 0.3, "research": 0.6,
        "govs": ["junta", "empire"],
        "slogans": ["鋼は嘘をつかない", "平和とは次の戦争の準備期間である", "砲声こそ国歌"],
    },
    "liberation": {
        "name": "辺境解放主義",
        "desc": "国家も企業も律院も要らない。星々は、そこで生きる者の手に。",
        "axes": (-0.95, -0.6, -0.2, -0.2),
        "aggression": 0.5, "trade": 0.5, "research": 0.4,
        "govs": ["tribal", "pirate", "council"],
        "slogans": ["鎖を断て、航路を奪え", "旗なき船に自由あり", "支配者の星図は燃やせ"],
    },
    "collectivism": {
        "name": "群体合一主義",
        "desc": "個は群のために、群は個のために。孤独な意志こそ銀河の病である。",
        "axes": (0.6, -0.95, 0.2, 0.3),
        "aggression": 0.5, "trade": 0.3, "research": 0.8,
        "govs": ["hive", "council"],
        "slogans": ["我らは一つ、一つは我ら", "群の記憶は滅びない", "孤独を捨てよ"],
    },
}

IDEOLOGY_KEYS = list(IDEOLOGIES.keys())


def compatibility(a, b):
    """理念同士の相性を -1〜+1 で返す。"""
    if a == b:
        return 1.0
    pa, pb = IDEOLOGIES[a]["axes"], IDEOLOGIES[b]["axes"]
    dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)))
    # 最大距離はおよそ 4.0
    return max(-1.0, 1.0 - dist)


# 種族ごとの理念の生まれやすさ
SPECIES_IDEOLOGY_BIAS = {
    "ketari": {"collectivism": 6.0},
    "mekan": {"corporatism": 1.5, "liberation": 2.0, "republic": 1.5},
    "silen": {"harmonist": 2.5, "pacifism": 2.0},
    "varr": {"imperial": 1.8, "corporatism": 1.5},
    "orm": {"militarism": 1.5, "purity": 1.5},
    "zaeru": {"freetrade": 2.0, "liberation": 1.5},
    "tiryn": {"freetrade": 1.8, "liberation": 1.8},
}
