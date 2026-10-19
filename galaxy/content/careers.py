"""職業（キャリアトラック）の定義。

org     : 所属先の種類。faction=国家, corp=企業, order=律院/虚環派, syndicate=犯罪組織, none=個人
ranks   : 階級名（下から順）
caps    : 上位階級の定員（最上位から順）。定員がない階級は無制限。
weights : 昇進判定に使う能力値の重み
notable : この階級以上への昇進は年代記に記録される
"""

CAREERS = {
    "military": {
        "name": "軍人",
        "org": "faction",
        "ranks": ["新兵", "伍長", "少尉", "中尉", "大尉", "少佐", "中佐", "大佐", "准将", "提督", "大提督", "元帥"],
        "caps": [1, 2, 4, 7],
        "weights": {"martial": 0.5, "command": 1.0, "intellect": 0.3},
        "notable": 8,
        "desc": "国家の艦隊と地上軍に仕える。",
    },
    "government": {
        "name": "官僚・政治家",
        "org": "faction",
        # 最上位（元首）は継承でのみ就く。表示名は政体ごとに変わる。
        "ranks": ["下級官吏", "書記官", "課長", "局長", "次官", "大臣", "宰相", "元首"],
        "caps": [1, 1, 5, 8],
        "weights": {"diplomacy": 1.0, "intellect": 0.6, "command": 0.2},
        "notable": 5,
        "desc": "国家の行政と政治を担う。",
    },
    "academic": {
        "name": "学者",
        "org": "faction",
        "ranks": ["助手", "研究員", "主任研究員", "教授", "学部長", "学院長"],
        "caps": [1, 3],
        "weights": {"learning": 1.0, "intellect": 0.7},
        "notable": 4,
        "desc": "国立学院で研究と教育に従事する。",
    },
    "corporate": {
        "name": "企業人",
        "org": "corp",
        "ranks": ["社員", "主任", "課長", "部長", "執行役員", "取締役", "社長"],
        "caps": [1, 4, 8],
        "weights": {"intellect": 0.8, "diplomacy": 0.6, "learning": 0.2},
        "notable": 6,
        "desc": "星間企業で働く。",
    },
    "order": {
        "name": "律士",
        "org": "order",
        "ranks": ["修練生", "律士", "上級律士", "導師", "大導師"],
        "caps": [1, 6],
        "weights": {"resonance": 1.2, "martial": 0.4, "learning": 0.4},
        "notable": 3,
        "desc": "共鳴の力を持つ者が、律院または虚環派に属して修行する。",
    },
    "merchant": {
        "name": "交易商",
        "org": "none",
        "ranks": ["行商人", "交易商", "豪商", "商会主"],
        "caps": [],
        "weights": {"diplomacy": 0.8, "intellect": 0.6},
        "notable": 3,
        "desc": "独立した商人として航路を渡る。",
    },
    "underworld": {
        "name": "裏社会",
        "org": "syndicate",
        "ranks": ["チンピラ", "密輸人", "用心棒", "幹部", "若頭", "首領"],
        "caps": [1, 2, 5],
        "weights": {"martial": 0.6, "intellect": 0.5, "diplomacy": 0.4},
        "notable": 4,
        "desc": "密輸と闇取引の世界に生きる。",
    },
    "arts": {
        "name": "芸術家",
        "org": "none",
        "ranks": ["見習い", "芸人", "人気芸術家", "巨匠"],
        "caps": [],
        "weights": {"diplomacy": 0.6, "learning": 0.4, "intellect": 0.3},
        "notable": 3,
        "desc": "ホロドラマ、詩、音楽、彫刻で名を立てる。",
    },
    "explorer": {
        "name": "探検家",
        "org": "none",
        "ranks": ["航路測量士", "探検家", "名探検家", "伝説の探検家"],
        "caps": [],
        "weights": {"command": 0.5, "learning": 0.5, "martial": 0.3},
        "notable": 2,
        "desc": "星図の空白を埋めるために未踏宙域へ向かう。",
    },
    "laborer": {
        "name": "労働者",
        "org": "none",
        "ranks": ["労働者", "熟練工", "現場監督"],
        "caps": [],
        "weights": {"martial": 0.3, "learning": 0.3},
        "notable": 99,
        "desc": "鉱山、農場、造船所、港湾で銀河を支える。",
    },
}

CAREER_KEYS = list(CAREERS.keys())

# 職業ごとの月収（階級ごとに増える）
BASE_INCOME = {
    "military": 3, "government": 3, "academic": 2.5, "corporate": 4, "order": 0.5,
    "merchant": 4, "underworld": 3.5, "arts": 2, "explorer": 2, "laborer": 1.2,
}

LABOR_JOBS = [
    "鉱山労働者", "水耕農場の作業員", "造船所の溶接工", "港湾の荷役", "貨物船の機関士",
    "大気精製所の技師", "酒場の店主", "ドロイド整備士", "開拓地の農夫", "軌道エレベーターの保守員",
    "ホロ放送局の技術者", "医療ステーションの看護師", "教師", "料理人", "警備員",
]


def cap_for(track, rank):
    """その階級の定員を返す（None なら無制限）。"""
    c = CAREERS[track]
    top = len(c["ranks"]) - 1
    idx = top - rank
    if 0 <= idx < len(c["caps"]):
        return c["caps"][idx]
    return None

# 虚環派に属する者の階級名（律院の階級と対応する）
VOID_RANKS = ["囁かれし者", "虚徒", "虚環の剣", "影の導師", "虚主"]
