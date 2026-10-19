"""人物の性格特性。

各特性は「性向（disposition）」への補正を持つ。性向は意思決定の重みとして使われる。

性向の軸:
  ambition    野心   … 出世・権力を求める
  boldness    大胆さ … 危険を恐れない
  honesty     誠実さ … 約束を守る、嘘をつかない
  compassion  慈悲   … 他者を思いやる
  sociability 社交性 … 人と関わる、結婚しやすい
  diligence   勤勉さ … 仕事の成果が出やすい
  curiosity   好奇心 … 研究・探検を好む
  loyalty     忠誠   … 主君や組織を裏切らない
  zeal        狂信   … 理念のために極端な行動をとる
  greed       強欲   … 富を求める
"""

DISPOSITIONS = (
    "ambition", "boldness", "honesty", "compassion", "sociability",
    "diligence", "curiosity", "loyalty", "zeal", "greed",
)

TRAITS = {
    "野心的": {"desc": "より高い場所を見ずにはいられない。", "mods": {"ambition": 2, "loyalty": -0.5}},
    "無欲": {"desc": "地位にも富にも興味がない。", "mods": {"ambition": -2, "greed": -1.5}},
    "勇敢": {"desc": "恐怖を知らぬわけではない。ただ、それに従わない。", "mods": {"boldness": 2}, "stats": {"martial": 1}},
    "臆病": {"desc": "最悪の事態を常に想像している。", "mods": {"boldness": -2}},
    "誠実": {"desc": "口にした言葉を必ず守る。", "mods": {"honesty": 2, "loyalty": 1}},
    "狡猾": {"desc": "真実は使い方次第だと知っている。", "mods": {"honesty": -2, "ambition": 0.5}, "stats": {"intellect": 1}},
    "慈悲深い": {"desc": "敵の痛みにさえ心を寄せる。", "mods": {"compassion": 2, "zeal": -0.5}},
    "残忍": {"desc": "苦痛を道具として扱う。", "mods": {"compassion": -2.5, "boldness": 0.5}},
    "社交的": {"desc": "どの酒場でも知り合いがいる。", "mods": {"sociability": 2}, "stats": {"diplomacy": 1}},
    "内向的": {"desc": "人混みより書庫を好む。", "mods": {"sociability": -2, "curiosity": 0.5}},
    "勤勉": {"desc": "誰よりも早く来て、誰よりも遅く帰る。", "mods": {"diligence": 2}},
    "怠惰": {"desc": "明日できることは明後日やる。", "mods": {"diligence": -2}},
    "好奇心旺盛": {"desc": "星図の空白を見ると眠れなくなる。", "mods": {"curiosity": 2}, "stats": {"learning": 1}},
    "保守的": {"desc": "古いやり方には古いだけの理由がある、と考える。", "mods": {"curiosity": -1.5, "loyalty": 0.5}},
    "忠実": {"desc": "一度誓った相手を見捨てない。", "mods": {"loyalty": 2.5}},
    "気まぐれ": {"desc": "昨日の主君は今日の他人。", "mods": {"loyalty": -2, "boldness": 0.5}},
    "寛容": {"desc": "異なる神、異なる種族、異なる理念を受け入れる。", "mods": {"zeal": -2, "compassion": 0.5}},
    "狂信的": {"desc": "信じるもののためなら星ひとつ燃やせる。", "mods": {"zeal": 2.5, "compassion": -0.5}},
    "陽気": {"desc": "絶望の中でも冗談を言う。", "mods": {"sociability": 1, "boldness": 0.5}},
    "陰鬱": {"desc": "宇宙の冷たさを誰よりも感じている。", "mods": {"sociability": -1, "curiosity": 0.5}},
    "激情家": {"desc": "怒りも愛も、火のように燃え上がる。", "mods": {"boldness": 1, "honesty": 0.5, "zeal": 0.5}},
    "冷静": {"desc": "艦橋が炎に包まれても声色を変えない。", "mods": {"boldness": 0.5}, "stats": {"command": 1}},
    "強欲": {"desc": "金庫の重さで自分の価値を量る。", "mods": {"greed": 2.5, "honesty": -0.5}},
    "寛大": {"desc": "持っているものを惜しげもなく分け与える。", "mods": {"greed": -2, "compassion": 1}},
    "忍耐強い": {"desc": "百年待つことを苦にしない。", "mods": {"diligence": 1, "boldness": -0.5}},
    "詩人気質": {"desc": "戦場でさえ韻を踏む。", "mods": {"curiosity": 1, "sociability": 0.5}, "stats": {"diplomacy": 1}},
    "天才": {"desc": "百年に一人の頭脳。", "mods": {"curiosity": 1}, "stats": {"intellect": 4, "learning": 4}, "rare": True},
    "頑健": {"desc": "病も毒も彼を避けて通る。", "mods": {}, "stats": {"martial": 2}, "health": 0.35},
    "病弱": {"desc": "季節の変わり目ごとに寝込む。", "mods": {"boldness": -0.5}, "health": -0.5},
    "美貌": {"desc": "その顔は星間ホロ誌の表紙を飾るほどだ。", "mods": {"sociability": 0.5}, "stats": {"diplomacy": 2}},
    # 人生の中で獲得する特性
    "英雄": {"desc": "その名は酒場の歌になっている。", "mods": {"boldness": 1}, "acquired": True},
    "傷痕": {"desc": "戦場の記憶が肌に刻まれている。", "mods": {"boldness": 0.5}, "acquired": True},
    "復讐者": {"desc": "奪われたものを決して忘れない。", "mods": {"zeal": 1.5, "compassion": -1}, "acquired": True},
    "隻眼": {"desc": "片目を失い、残る片目で多くを見るようになった。", "mods": {}, "stats": {"command": 1}, "acquired": True},
    "未亡人": {"desc": "伴侶に先立たれた。", "mods": {"sociability": -0.5}, "acquired": True},
    "亡命者": {"desc": "故国を追われた。", "mods": {"zeal": 0.5, "loyalty": -0.5}, "acquired": True},
    "預言者": {"desc": "共鳴の夢に未来を見る。", "mods": {"zeal": 1}, "stats": {"resonance": 3}, "acquired": True},
    "堕ちた者": {"desc": "虚ろな環の囁きに身を委ねた。", "mods": {"compassion": -2, "ambition": 1.5}, "acquired": True},
}

OPPOSITES = [
    ("野心的", "無欲"), ("勇敢", "臆病"), ("誠実", "狡猾"), ("慈悲深い", "残忍"),
    ("社交的", "内向的"), ("勤勉", "怠惰"), ("好奇心旺盛", "保守的"), ("忠実", "気まぐれ"),
    ("寛容", "狂信的"), ("陽気", "陰鬱"), ("激情家", "冷静"), ("強欲", "寛大"),
    ("頑健", "病弱"), ("激情家", "忍耐強い"),
]

INNATE_TRAITS = [k for k, v in TRAITS.items() if not v.get("acquired")]


def conflicts(a, b):
    return (a, b) in OPPOSITES or (b, a) in OPPOSITES
