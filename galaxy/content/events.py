"""年代記に記録されるイベント文のテンプレート集。

同じ種類のイベントでも毎回違う語り口になるよう、複数の言い回しを用意している。
"""

TEMPLATES = {
    # ------------------------------------------------------------ 人生
    "birth_notable": [
        "{parents}のもとに、{person}が生まれた。",
        "{planet}で、{parents}の子{person}が産声を上げた。",
    ],
    "coming_of_age": [
        "{planet}の{origin}だった{person}が、頭角を現しはじめた。",
        "{planet}で、{person}という名が人々の口にのぼるようになった。",
    ],
    "marriage": [
        "{person}と{target}が{planet}で結婚した。",
        "{planet}の空の下、{person}と{target}が永遠の誓いを交わした。",
        "{person}と{target}の婚礼が{planet}で執り行われた。招待客は{guests}人を数えた。",
    ],
    "marriage_political": [
        "{faction}の{person}と{target_faction}の{target}が政略結婚を結んだ。両国の絆は強まるだろう。",
    ],
    "death_natural": [
        "{person}が{planet}で息を引き取った。享年{age}。",
        "{person}、{planet}にて永眠。{age}歳であった。",
        "{age}年の生涯を終え、{person}が静かに旅立った。",
    ],
    "death_illness": [
        "{person}が病に倒れ、帰らぬ人となった。享年{age}。",
        "長い闘病の末、{person}が{planet}で亡くなった。{age}歳だった。",
    ],
    "death_accident": [
        "{person}が{accident}により命を落とした。享年{age}。",
    ],
    "death_battle": [
        "{person}が{battle}で戦死した。享年{age}。",
        "{battle}において、{person}の乗艦が撃沈された。{age}歳であった。",
    ],
    "death_assassinated": [
        "{person}が暗殺された。{method}。享年{age}。",
        "{planet}で{person}が何者かに殺害された。{method}。",
    ],
    "death_executed": [
        "{person}が{killer}の命により処刑された。享年{age}。",
    ],
    "death_plague": [
        "{plague}が{person}の命を奪った。享年{age}。",
    ],
    "promotion": [
        "{person}が{org}の{rank}に昇進した。",
        "{org}は{person}を{rank}に任じた。",
    ],
    "promotion_top": [
        "{person}が{org}の{rank}に就任した。",
        "{org}の頂点に、{person}が立った。新たな{rank}の誕生である。",
    ],
    "renown": [
        "{person}は、今や「{rank}」と呼ばれる存在になった。",
        "{planet}の人々は、{person}を{rank}と讃えた。",
        "{person}の名は銀河に広まり、{rank}の名をほしいままにしている。",
    ],
    "retire": [
        "{person}が{org}の{rank}を退き、引退した。",
    ],
    "fired": [
        "{person}が{reason}のため{org}を追われた。",
    ],
    "career_change": [
        "{person}は{old}の道を捨て、{new}として新たな人生を歩み始めた。",
    ],
    "mentor": [
        "{org}の{target}が、{person}を弟子として迎えた。",
    ],
    "fall_to_void": [
        "律院の{person}が姿を消した。虚環派に走ったという噂が囁かれている。",
        "{person}が律院を去り、虚ろな環の徒となった。",
    ],
    "rivalry": [
        "{person}と{target}の確執が深まっている。",
    ],
    # ------------------------------------------------------------ 政治
    "succession_hereditary": [
        "{prev}の崩御により、{person}が{faction}の{title}に即位した。",
        "{faction}の新たな{title}として、{person}が戴冠した。",
    ],
    "succession_elective": [
        "{faction}で選挙が行われ、{person}が{title}に選出された。",
        "{faction}の民は{person}を新たな{title}に選んだ。得票率は{share}%。",
    ],
    "succession_other": [
        "{person}が{faction}の{title}の座に就いた。",
        "{prev}の後を継ぎ、{person}が{faction}を率いることになった。",
    ],
    "election_reelected": [
        "{faction}の選挙で、現職の{person}が再選された。",
    ],
    "coup": [
        "{faction}でクーデターが発生。{person}が{target}を打倒し、権力を掌握した。",
        "軍の反乱により{target}が失脚。{faction}の実権は{person}の手に渡った。",
    ],
    "coup_failed": [
        "{faction}で{person}によるクーデター未遂事件が発生した。首謀者は捕らえられた。",
    ],
    "revolution": [
        "{planet}で蜂起が発生し、{faction}からの独立を宣言した。新国家「{new_faction}」が誕生した。",
        "{planet}の民が{faction}の支配に反旗を翻した。指導者{person}のもと、「{new_faction}」が樹立された。",
    ],
    "ideology_shift": [
        "{faction}の国是が{old}から{new}へと転換した。",
        "{person}の指導のもと、{faction}は{new}を掲げる国へと生まれ変わった。",
    ],
    "gov_change": [
        "{faction}の政体が{old}から{new}へと移行した。国名は「{new_name}」と改められた。",
    ],
    "faction_fall": [
        "{faction}が滅亡した。建国から{years}年、その旗は二度と翻ることはない。",
        "{faction}は歴史の幕を下ろした。最後の星{planet}が陥落したのである。",
    ],
    "exile": [
        "{person}は故国を追われ、{planet}へと亡命した。",
    ],
    "stability_crisis": [
        "{faction}で政情不安が広がっている。各地で抗議活動が起きている。",
        "{faction}の首都{planet}で大規模な暴動が発生した。",
    ],
    "colonize": [
        "{faction}が{planet}への植民を開始した。最初の入植船が軌道に到着した。",
        "{planet}に{faction}の旗が立てられた。新たな開拓地の誕生である。",
    ],
    # ------------------------------------------------------------ 外交・戦争
    "war_declared": [
        "{faction}が{enemy}に宣戦布告した。{war}の始まりである。",
        "{cause}を理由に、{faction}は{enemy}との戦端を開いた。",
        "{faction}の艦隊が国境を越えた。{enemy}との{war}が勃発した。",
    ],
    "war_joined": [
        "{faction}が同盟国{ally}の求めに応じ、{war}に参戦した。",
    ],
    "battle": [
        "{battle}で{winner}軍が{loser}軍を破った。",
        "{battle}は{winner}の勝利に終わった。{loser}は{losses}隻を失った。",
        "{planet}の空で両軍が激突した。{battle}と呼ばれるこの戦いは、{winner}の勝利に終わった。",
    ],
    "battle_decisive": [
        "{battle}で{winner}が歴史的大勝利を収めた。{commander}の名は銀河中に轟いた。",
        "{battle}――後世の教科書に必ず載るであろうこの会戦で、{commander}率いる{winner}艦隊が{loser}を壊滅させた。",
    ],
    "planet_captured": [
        "{planet}が{winner}軍の手に落ちた。",
        "{planet}を巡る攻防は{winner}の勝利に終わり、{loser}の旗が降ろされた。",
    ],
    "peace_white": [
        "{war}が終結した。どちらも勝者とは言えない、痛み分けの和平である。",
        "{faction}と{enemy}の間で停戦が成立し、{war}は幕を閉じた。",
    ],
    "peace_victory": [
        "{war}は{winner}の勝利に終わった。{loser}は{terms}。",
        "{loser}が降伏し、{war}は終結した。講和条約により{loser}は{terms}。",
    ],
    "peace_annihilation": [
        "{war}は、{loser}の滅亡をもって終結した。",
        "{loser}の旗が全て降ろされ、{war}は{winner}の完全勝利に終わった。",
    ],
    "alliance": [
        "{faction}と{target_faction}が同盟を締結した。",
        "{planet}で{faction}と{target_faction}の首脳が会談し、同盟条約に調印した。",
    ],
    "alliance_broken": [
        "{faction}と{target_faction}の同盟が破棄された。",
    ],
    "trade_pact": [
        "{faction}と{target_faction}が通商協定を結んだ。航路に商船が溢れるだろう。",
    ],
    "trade_broken": [
        "{faction}と{target_faction}の通商協定が失効した。",
    ],
    "border_incident": [
        "{planet}近傍で{faction}と{target_faction}の哨戒艦が交戦した。両国の関係は悪化している。",
        "{faction}の商船が{target_faction}の巡視艇に拿捕された。外交問題に発展している。",
        "{target_faction}の外交官が{faction}の晩餐会で侮辱的な発言をしたと報じられた。",
    ],
    # ------------------------------------------------------------ 経済・技術
    "tech": [
        "{faction}の{person}が「{tech}」を完成させた。",
        "{faction}の学院で「{tech}」の開発に成功した。主導したのは{person}である。",
        "{person}の研究チームが「{tech}」を実現した。{faction}の{field}は新たな段階に入った。",
    ],
    "tech_nobody": [
        "{faction}が「{tech}」を実用化した。",
    ],
    "corp_founded": [
        "{person}が{planet}で{org}を創業した。",
        "{planet}に新たな企業{org}が誕生した。創業者は{person}。",
    ],
    "corp_bankrupt": [
        "{org}が経営破綻した。創業から{years}年の歴史に幕が下りた。",
        "{org}の株価が暴落し、事実上の倒産に追い込まれた。",
    ],
    "corp_acquired": [
        "{org}が{target_org}に買収された。",
    ],
    "corp_boom": [
        "{org}の業績が急伸している。{reason}",
    ],
    "trade_boom": [
        "{planet}の宇宙港が空前の活況に沸いている。",
    ],
    "recession": [
        "{faction}で不況が深刻化している。失業者が街にあふれている。",
    ],
    # ------------------------------------------------------------ 事件
    "plague": [
        "{planet}で{plague}が流行している。",
        "{plague}が{planet}を襲った。医療ステーションは患者であふれている。",
    ],
    "disaster": [
        "{planet}を{disaster}が襲った。",
        "{disaster}により、{planet}の主要都市が甚大な被害を受けた。",
    ],
    "pirate_raid": [
        "海賊が{planet}を襲撃した。{loot}が奪われた。",
        "{org}の海賊船団が{planet}の商船航路を荒らしている。",
    ],
    "relic_found": [
        "{person}が{planet}で{relic}を発見した。",
        "{planet}の遺跡調査で{relic}が見つかった。発見者は{person}。",
    ],
    "exploration": [
        "探検家{person}が未踏宙域の調査から帰還した。持ち帰った星図は{faction}の宝となった。",
        "{person}が{planet}の先にある新たな航路を発見した。",
    ],
    "exploration_lost": [
        "探検家{person}の船が未踏宙域で消息を絶った。",
    ],
    "festival": [
        "{planet}で{festival}が盛大に催された。",
        "{festival}の夜、{planet}の空は花火と光の帯で埋め尽くされた。",
    ],
    "artwork": [
        "{person}の{work}『{title}』が発表され、銀河中で話題を呼んでいる。",
        "{person}が{work}『{title}』を完成させた。批評家たちは絶賛している。",
    ],
    "scandal": [
        "{person}の{scandal}が発覚した。",
        "ホロネットが{person}の{scandal}を報じ、大騒動となっている。",
    ],
    "prophecy": [
        "律院の{person}が預言を告げた。",
        "{planet}の聖地で、{person}が共鳴の夢を見たという。",
    ],
    "resonance_awakening": [
        "{planet}で、{person}に共鳴の才が目覚めた。律院の使者が訪れるだろう。",
    ],
    "refugees": [
        "{war}を逃れた難民の船団が{planet}に到着した。",
    ],
    "anomaly": [
        "{planet}周辺で{anomaly}が観測された。",
    ],
    "crime_boss": [
        "{org}の{person}が{planet}の裏社会を掌握した。",
    ],
    "smuggling_bust": [
        "{faction}の当局が{org}の密輸ルートを摘発した。",
    ],
    "duel": [
        "{person}と{target}が{planet}で決闘を行った。勝ったのは{winner}だった。",
    ],
    "assassination_failed": [
        "{target}を狙った暗殺未遂事件が{planet}で発生した。",
    ],
    "year_summary": [
        "{year}年。",
    ],
}

PLAGUES = [
    "灰咳病", "赤斑熱", "星間インフルエンザ", "結晶化症", "眠り病", "虚脱熱", "胞子肺",
    "記憶喪失熱", "鱗剥がれ病", "翅腐れ病", "回路錆病",
]

DISASTERS = [
    "巨大地震", "恒星フレア", "隕石群の落下", "大津波", "火山の大噴火", "大気循環の崩壊",
    "軌道エレベーターの崩落", "原因不明の重力震", "百年に一度の大砂嵐", "氷河の崩壊",
]

ACCIDENTS = [
    "貨物船の事故", "超空間航行中の座標誤差", "採掘基地の崩落", "エアロック事故",
    "スピーダーの衝突事故", "高層都市からの転落", "狩猟中の事故", "実験炉の暴走",
]

ASSASSINATION_METHODS = [
    "毒が盛られた葡萄酒が原因だった",
    "犯人は狙撃手と見られている",
    "爆弾が乗用艇に仕掛けられていた",
    "寝室に忍び込んだ刺客の仕業だった",
    "暗殺ドロイドによる犯行だった",
    "共鳴の力による犯行と囁かれている",
    "犯人は身内だったという噂がある",
]

FESTIVALS = [
    "残光祭", "大寂滅慰霊の日", "星渡りの祭り", "収穫祭", "建国記念祭", "潮歌の夜",
    "灯籠流しの夜", "千隻観艦式", "群の目覚めの儀", "長き夜の宴",
]

WORK_TYPES = ["ホロドラマ", "交響詩", "叙事詩", "彫刻", "長編小説", "歌劇", "壁画", "舞踊劇"]

WORK_TITLE_A = [
    "残光の", "最後の", "星を喰む", "名もなき", "沈黙の", "燃える", "千年の", "凍てつく",
    "帰らざる", "遠き", "青ざめた", "美しき", "裏切りの", "砕けた",
]
WORK_TITLE_B = [
    "玉座", "艦隊", "恋人たち", "旋律", "皇帝", "航路", "海", "子守唄", "冠", "星図",
    "庭園", "王女", "傭兵", "鐘",
]

SCANDALS = [
    "巨額の横領", "敵国との密通", "隠し子の存在", "学歴詐称", "賄賂の受け取り",
    "違法な共鳴結晶の取引", "選挙資金の不正", "愛人との密会", "密輸組織との癒着",
]

ANOMALIES = [
    "周期的な共鳴波", "帝政時代の救難信号", "光速を超えて移動する光点", "時間の流れが歪む領域",
    "巨大な未確認構造物", "恒星の不自然な減光", "超空間航路のひずみ",
]

LOOTS = ["食料備蓄", "共鳴結晶の積荷", "徴税官の金庫", "医薬品", "数百人の住民", "造船所の設計図"]

WAR_CAUSES = {
    "territory": "領土問題",
    "ideology": "理念の対立",
    "revenge": "過去の戦争への報復",
    "resources": "資源の奪い合い",
    "independence": "独立の阻止",
    "holy": "聖戦の大義",
    "conquest": "覇権の拡大",
}

ORIGINS = [
    "貧しい鉱夫の子", "没落貴族の末裔", "孤児院育ち", "商家の三男坊", "港町の荒くれ者",
    "名門家の出", "難民船で生まれた子", "辺境の農夫の娘", "元奴隷", "学者一家の出",
    "酒場の看板娘", "退役軍人の子", "放浪者",
]
