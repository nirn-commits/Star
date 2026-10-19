# 残光暦銀河シミュレーター

かつて銀河を統べた「アウラ帝政」が崩壊してから三千年。
百を超える星々で国家・企業・信仰・犯罪組織がせめぎ合い、
そこに生きる人々が年を取り、働き、出世し、恋をし、死んでいく――
その歴史を自動で紡ぎ出す、ナラティブ重視のSF世界シミュレーターです。

外部ライブラリは不要です（Python 3.10 以上）。

```bash
# 30年分の年代記を表示する
python -m galaxy

# シードや規模、年数を指定し、終了後に対話モードで世界を覗く
python -m galaxy --seed 42 --planets 200 --years 50 -i

# 細かな出来事まで読む（重要度1〜5、既定は3）
python -m galaxy --years 10 --min 1

# 世界を保存して、あとで続きから
python -m galaxy --years 100 --save galaxy.sav
python -m galaxy --load galaxy.sav --years 20 -i

# テスト
python -m unittest discover -s tests
```

出力例は [`docs/sample_chronicle.txt`](docs/sample_chronicle.txt) にあります。

## 対話モードのコマンド

| コマンド | 内容 |
|---|---|
| `run <年数>` / `step <月数>` | 時間を進める |
| `overview` | 銀河の現状（列強・戦争） |
| `famous [件数] [dead]` | 著名人ランキング |
| `person <ID>` | 人物伝（経歴・家族・師弟・宿敵・生涯・語録・最期） |
| `faction <ID>` | 国家史（歴代元首・外交・技術・歩み） |
| `planet <ID>` | 惑星の情報と歴史、住人 |
| `war <ID>` / `wars` | 戦史（会戦・領土の変化・戦死者） |
| `year <年>` | その年の詳細な年代記 |
| `search <名前>` | 人物検索 |
| `tech` | 技術の最前線 |
| `level <1-5>` | 年代記の表示粒度 |

## 世界で起きること

- **人生**：全ての人物は誕生 → 成人 → 就職 → 昇進 → 結婚 → 出産 → 引退 → 死亡を辿る。
  寿命は種族と医療技術で決まり、性格・能力・理念は親から一部受け継がれる。
- **職業**：軍人・官僚・学者・企業人・律士・交易商・裏社会・芸術家・探検家・労働者。
  上位の階級には定員があり、席が空かなければ昇進できない。燻った者同士は宿敵になる。
- **政治**：世襲・選挙・軍政・神権・企業・群体など政体ごとの継承。選挙、クーデター、
  暗殺、理念の転換、政体の変化、王朝交代。
- **外交**：理念の相性・国境の摩擦・恨み・脅威から感情が動き、通商協定・同盟・
  宣戦布告・同盟の裏切りが起きる。
- **戦争**：提督の能力と技術で決まる会戦、惑星の攻略、首都移転、講和（割譲・賠償・
  痛み分け）、国家の滅亡。大国は統治が行き届かず、辺境で独立戦争が起き、
  宿敵国が独立派を支援する。小国は理念の近い大国へ平和的に合流することもある。
- **経済・技術**：惑星の生産、艦隊建造、企業の創業・急成長・倒産・買収、
  6分野48段階の技術革新と、その開発者の栄誉。
- **事件**：疫病、天災、海賊、帝政遺跡の発見、祭典、芸術作品、醜聞、預言、
  共鳴の目覚め、決闘、難民、未踏宙域の探検と遭難。
- **共鳴**：ごく稀に生まれる共鳴者は「ハルモニア律院」で師に導かれて修行するが、
  野心ある者は「虚環派」へ堕ちることもある。

## 構成

```
galaxy/
  content/        世界観データ（ここを書き足すほど物語が豊かになる）
    lore.py         銀河の歴史・地域・共鳴の設定
    species.py      8種族（寿命・成人年齢・出生率・気質）
    traits.py       性格特性と性向
    ideologies.py   11の理念（4軸座標で相性を計算）
    governments.py  11の政体と継承方式
    careers.py      10の職業と階級・定員
    technologies.py 6分野の技術ツリー
    planets.py      惑星タイプ・特徴・名前素材
    corporations.py 企業の業種と名前素材
    names.py        種族別の人名
    dialogue.py     場面別の台詞（性格・理念・職業・種族で出し分け）と二人の掛け合い
    events.py       年代記の文章テンプレートと事件の素材
  model/          データ構造（Person / Planet / Faction / Corporation / War など）と World
  sim/            毎月の処理（engine が順に呼び出す）
    demography.py 老化・死亡・結婚・出産・人物の補充
    careers.py    就職・昇進・引退・起業・律士の修行
    politics.py   継承・選挙・政変・独立運動・併合・領土移動
    diplomacy.py  国家感情・条約・宣戦布告
    warfare.py    会戦・惑星攻略・講和
    economy.py    生産・財政・艦隊・企業
    technology.py 研究とブレイクスルー
    incidents.py  突発的な事件
    life.py       人物の生成・死亡処理など共通操作
  narrative/      台詞・文章の生成（voice）と読み物の組み立て（chronicle）
  minds.py        意思決定（AIMind / PlayerMind）
  worldgen.py     銀河の生成
  cli.py          コマンドライン
```

## プレイヤーキャラクターの追加に向けて

NPCとプレイヤーは同じ `Person` クラスで表され、寿命・就職・出世・結婚・死亡の
仕組みは完全に共通です。違うのは判断を下す「心（Mind）」だけで、
シミュレーションは人物に選択を迫るとき必ず `minds.mind_of(world, person)` を通します。

```python
from galaxy.minds import PlayerMind, set_mind
set_mind(person.id, PlayerMind())  # この人物の判断をプレイヤー側に切り替える
```

現在の `PlayerMind` は AI に判断を委ねる雛形です。`choose_career`・`accept_marriage`・
`want_retire`・`plot_coup`・`consider_war` などのメソッドを UI からの入力に置き換えれば、
プレイヤーは NPC と同じ銀河の中で一人の人物として生きることになります。

## 物語を増やすには

`galaxy/content/dialogue.py` と `galaxy/content/events.py` に行を足すだけで、
次の実行から反映されます。台詞には `("台詞", {"trait": "残忍"})` のように条件を付けられ、
条件に合う人物が優先して口にします。
