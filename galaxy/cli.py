"""コマンドラインから銀河を動かし、年代記を読むための入口。"""

import argparse
import pickle
import sys

from galaxy.worldgen import generate
from galaxy.sim import engine
from galaxy.narrative import chronicle as ch

HELP = """\
コマンド一覧:
  run <年数>        時を進める（年代記を表示）
  step <月数>       月単位で進める
  overview          銀河の現状
  famous [件数]     著名人の一覧（dead を付けると故人も含む）
  person <ID>       人物伝
  faction <ID>      国家史
  planet <ID>       惑星の情報
  war <ID>          戦史
  wars              全ての戦争の一覧
  year <西暦>       その年の年代記（詳細）
  search <名前>     人物を名前で検索
  tech              技術の最前線
  level <1-5>       年代記に表示する重要度の下限
  save <ファイル>   世界を保存
  quit              終了
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="残光暦銀河シミュレーター")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--planets", type=int, default=120)
    ap.add_argument("--years", type=int, default=30, help="最初に進める年数")
    ap.add_argument("--min", type=int, default=3, help="年代記に載せる重要度の下限 (1-5)")
    ap.add_argument("--no-quotes", action="store_true")
    ap.add_argument("--no-prologue", action="store_true")
    ap.add_argument("-i", "--interactive", action="store_true", help="シミュレーション後に対話モードへ")
    ap.add_argument("--load", help="保存した世界を読み込む")
    ap.add_argument("--save", help="終了時に世界を保存する")
    args = ap.parse_args(argv)

    if args.load:
        with open(args.load, "rb") as fh:
            world = pickle.load(fh)
    else:
        world = generate(seed=args.seed, n_planets=args.planets)
        if not args.no_prologue:
            print(ch.prologue(world))

    state = {"min": args.min, "quotes": not args.no_quotes}
    advance(world, args.years * 12, state)
    print(ch.overview(world))

    if args.interactive:
        repl(world, state)
    if args.save:
        save(world, args.save)


def advance(world, months, state):
    def on_year(w, year):
        print(ch.year_chronicle(w, year, state["min"], state["quotes"]))
        print(ch.year_stats(w, year))
    engine.run(world, months, on_year)


def save(world, path):
    with open(path, "wb") as fh:
        pickle.dump(world, fh)
    print(f"{path} に保存しました。")


def repl(world, state):
    print(HELP)
    while True:
        try:
            line = input(f"[{world.date()}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        cmd, *rest = line.split()
        arg = rest[0] if rest else None
        try:
            if cmd in ("quit", "exit", "q"):
                return
            elif cmd == "help":
                print(HELP)
            elif cmd == "run":
                advance(world, int(arg or 1) * 12, state)
            elif cmd == "step":
                before = len(world.log)
                engine.run(world, int(arg or 1))
                for e in world.log[before:]:
                    if e.importance >= state["min"]:
                        print(f"{world.year_of(e.t)}年 " + ch.format_entry(world, e, state["quotes"]))
            elif cmd == "overview":
                print(ch.overview(world))
            elif cmd == "famous":
                n = int(arg) if arg and arg.isdigit() else 20
                print(ch.famous(world, n, alive_only="dead" not in rest))
            elif cmd == "person":
                print(ch.biography(world, int(arg)))
            elif cmd == "faction":
                print(ch.faction_report(world, int(arg)))
            elif cmd == "planet":
                print(ch.planet_report(world, int(arg)))
            elif cmd == "war":
                print(ch.war_report(world, int(arg)))
            elif cmd == "wars":
                for w in world.wars.values():
                    status = "継続中" if w.active else w.outcome
                    print(f"  [{w.id}] {w.name}（{world.year_of(w.start_t)}年〜）{status}")
            elif cmd == "year":
                print(ch.year_chronicle(world, int(arg), 1, True))
            elif cmd == "search":
                hits = [p for p in world.persons.values() if arg and arg in p.name]
                for p in hits[:30]:
                    mark = "" if p.alive else "†"
                    print(f"  [{p.id}] {p.name}{mark}")
                if not hits:
                    print("  見つかりません。")
            elif cmd == "tech":
                print(ch.tech_report(world))
            elif cmd == "level":
                state["min"] = max(1, min(5, int(arg)))
            elif cmd == "save":
                save(world, arg or "galaxy.sav")
            else:
                print("不明なコマンドです。help で一覧を表示します。")
        except (ValueError, TypeError):
            print("引数が正しくありません。")


if __name__ == "__main__":
    sys.exit(main())
