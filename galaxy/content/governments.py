"""政体の定義。

succession（継承方式）:
  hereditary : 世襲。子→配偶者→兄弟→最高位官僚の順に継ぐ
  elective   : 選挙。任期ごとに上位官僚から選ばれる
  order      : 律院・神官団の最高位者が継ぐ
  military   : 軍の最高位者が継ぐ
  corporate  : 国内企業のCEOの中で最も富める者が継ぐ
  strongest  : 最も武勇と名声に優れる者が奪い取る
  hive       : 群体の最も古い個体が継ぐ
"""

GOVERNMENTS = {
    "empire": {
        "name": "帝国", "title": "皇帝", "title_f": "女帝", "succession": "hereditary",
        "stability": 60, "term": None,
        "suffixes": ["帝国", "星間帝国", "神聖帝国"],
    },
    "kingdom": {
        "name": "王国", "title": "国王", "title_f": "女王", "succession": "hereditary",
        "stability": 58, "term": None,
        "suffixes": ["王国", "星王国", "連合王国"],
    },
    "republic": {
        "name": "共和国", "title": "大統領", "succession": "elective",
        "stability": 55, "term": 6,
        "suffixes": ["星間共和国", "共和国", "民主共和国"],
    },
    "federation": {
        "name": "連邦", "title": "連邦首相", "succession": "elective",
        "stability": 52, "term": 5,
        "suffixes": ["連邦", "星系連邦", "自由連邦"],
    },
    "council": {
        "name": "評議会", "title": "評議会議長", "succession": "elective",
        "stability": 50, "term": 4,
        "suffixes": ["評議会同盟", "長老評議会", "盟約評議会"],
    },
    "corporate": {
        "name": "企業国家", "title": "最高経営責任者", "succession": "corporate",
        "stability": 50, "term": None,
        "suffixes": ["通商機構", "企業連合", "開発公社"],
    },
    "theocracy": {
        "name": "神権国", "title": "大司律", "succession": "order",
        "stability": 62, "term": None,
        "suffixes": ["神聖律国", "聖域", "教導国"],
    },
    "junta": {
        "name": "軍事政権", "title": "総統", "succession": "military",
        "stability": 42, "term": None,
        "suffixes": ["軍政府", "防衛機構", "鉄血同盟"],
    },
    "tribal": {
        "name": "氏族連合", "title": "大族長", "succession": "strongest",
        "stability": 45, "term": None,
        "suffixes": ["氏族連合", "部族同盟", "大氏族"],
    },
    "pirate": {
        "name": "海賊同盟", "title": "大頭目", "succession": "strongest",
        "stability": 35, "term": None,
        "suffixes": ["自由同盟", "海賊連合", "略奪者組合"],
    },
    "hive": {
        "name": "大群体", "title": "群母", "succession": "hive",
        "stability": 75, "term": None,
        "suffixes": ["大群体", "巣群", "群体圏"],
    },
}

GOV_KEYS = list(GOVERNMENTS.keys())


def leader_title(gov_key, sex=None):
    g = GOVERNMENTS[gov_key]
    if sex in ("女", "雌", "繁体") and "title_f" in g:
        return g["title_f"]
    return g["title"]
