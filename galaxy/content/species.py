"""銀河に住む種族の定義。

lifespan   : 平均寿命（年）。死亡率曲線の基準になる。
adult      : 成人年齢（年）。就職・結婚が可能になる。
fertility  : 出生しやすさの倍率（1.0 = 人間基準）。0 なら自然出生しない。
can_marry  : 婚姻制度を持つか。
stat_bias  : 能力値の傾向。
trait_bias : 生まれやすい性格。
"""

SPECIES = {
    "human": {
        "name": "人間",
        "desc": "旧帝政を築いた種族。銀河のどこにでもいて、どこでも揉め事を起こす。",
        "lifespan": 82,
        "adult": 18,
        "fertility": 1.0,
        "can_marry": True,
        "sexes": ("男", "女"),
        "stat_bias": {},
        "trait_bias": {"野心的": 1.2, "好奇心旺盛": 1.2},
        "names": "human",
        "homeworld_types": ["temperate", "ecumenopolis", "ocean", "desert"],
    },
    "varr": {
        "name": "ヴァール族",
        "desc": "鱗に覆われた長命の種族。三百年先を見据えて契約を結び、決して忘れない。",
        "lifespan": 210,
        "adult": 40,
        "fertility": 0.35,
        "can_marry": True,
        "sexes": ("雄", "雌"),
        "stat_bias": {"intellect": 2, "diplomacy": 1, "martial": 1},
        "trait_bias": {"冷静": 2.0, "狡猾": 1.5, "忍耐強い": 2.0},
        "names": "varr",
        "homeworld_types": ["desert", "volcanic", "jungle"],
    },
    "ketari": {
        "name": "ケタリ",
        "desc": "群体意識を持つ甲殻種族。個体は短命だが、群れの記憶は数千年続く。",
        "lifespan": 42,
        "adult": 5,
        "fertility": 2.2,
        "can_marry": True,
        "sexes": ("働体", "繁体"),
        "stat_bias": {"learning": 1, "command": 1},
        "trait_bias": {"勤勉": 3.0, "忠実": 2.5, "内向的": 1.5},
        "names": "ketari",
        "homeworld_types": ["jungle", "toxic", "barren"],
    },
    "orm": {
        "name": "オルム族",
        "desc": "岩石質の皮膚を持つ巨躯の種族。歩みは遅いが、一度決めたことは山のように動かない。",
        "lifespan": 290,
        "adult": 60,
        "fertility": 0.2,
        "can_marry": True,
        "sexes": ("男", "女"),
        "stat_bias": {"martial": 3, "learning": 1, "diplomacy": -1},
        "trait_bias": {"頑健": 3.0, "忍耐強い": 2.0, "保守的": 1.5},
        "names": "orm",
        "homeworld_types": ["volcanic", "barren", "ice"],
    },
    "silen": {
        "name": "シレン",
        "desc": "海洋惑星に住む両生種族。歌で会話し、その歌声は共鳴とよく響き合う。",
        "lifespan": 120,
        "adult": 22,
        "fertility": 0.8,
        "can_marry": True,
        "sexes": ("男", "女"),
        "stat_bias": {"diplomacy": 2, "resonance": 2, "martial": -1},
        "trait_bias": {"詩人気質": 3.0, "慈悲深い": 1.5, "社交的": 1.5},
        "names": "silen",
        "homeworld_types": ["ocean", "ice"],
    },
    "zaeru": {
        "name": "ザエル",
        "desc": "小柄で多産、そして短命な種族。三十年で一生を駆け抜けるため、誰よりも生き急ぐ。",
        "lifespan": 36,
        "adult": 9,
        "fertility": 2.6,
        "can_marry": True,
        "sexes": ("男", "女"),
        "stat_bias": {"intellect": 1, "diplomacy": 1, "martial": -1},
        "trait_bias": {"陽気": 2.5, "激情家": 1.5, "好奇心旺盛": 2.0},
        "names": "zaeru",
        "homeworld_types": ["temperate", "jungle", "desert"],
    },
    "tiryn": {
        "name": "ティリン族",
        "desc": "羽毛に覆われた遊牧の種族。母星を持たず、船団で星々を渡り歩く。",
        "lifespan": 95,
        "adult": 16,
        "fertility": 0.9,
        "can_marry": True,
        "sexes": ("男", "女"),
        "stat_bias": {"command": 1, "diplomacy": 1},
        "trait_bias": {"好奇心旺盛": 2.0, "勇敢": 1.5, "寛容": 1.5},
        "names": "tiryn",
        "homeworld_types": ["gas_moon", "temperate", "barren"],
    },
    "mekan": {
        "name": "機知体",
        "desc": "旧帝政が生んだ自律人工知性の末裔。工廠で生まれ、記憶の劣化によって死ぬ。",
        "lifespan": 160,
        "adult": 1,
        "fertility": 0.0,
        "can_marry": False,
        "sexes": ("—",),
        "stat_bias": {"intellect": 3, "learning": 3, "diplomacy": -2, "resonance": -20},
        "trait_bias": {"冷静": 3.0, "勤勉": 2.0, "好奇心旺盛": 1.5},
        "names": "mekan",
        "homeworld_types": ["ecumenopolis", "barren", "asteroid"],
    },
}

SPECIES_KEYS = list(SPECIES.keys())

# 世界生成時の母星分布の重み
SPECIES_WEIGHTS = {
    "human": 5.0,
    "varr": 1.4,
    "ketari": 1.2,
    "orm": 0.8,
    "silen": 1.0,
    "zaeru": 1.2,
    "tiryn": 0.9,
    "mekan": 0.6,
}
