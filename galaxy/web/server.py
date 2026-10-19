"""ブラウザ画面用の小さな Web サーバー（Python 標準ライブラリのみ）。

python -m galaxy.web          # http://localhost:8000 を開く
"""

import argparse
import json
import pickle
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from galaxy.worldgen import generate
from galaxy.sim import engine
from galaxy.web import api

STATIC = Path(__file__).parent / "static"
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}
MAX_STEP = 12 * 50


class Game:
    """サーバーが保持する一つの銀河。全ての操作はロックの内側で行う。"""

    def __init__(self, world):
        self.world = world
        self.lock = threading.Lock()

    def new(self, seed, planets):
        with self.lock:
            self.world = generate(seed=seed, n_planets=planets)


def make_handler(game):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _static(self, path):
            name = "index.html" if path in ("", "/") else path.lstrip("/")
            file = (STATIC / name).resolve()
            if STATIC.resolve() not in file.parents or not file.is_file():
                return self._send(404, {"error": "not found"})
            self._send(200, file.read_bytes(), CONTENT_TYPES.get(file.suffix, "application/octet-stream"))

        def do_GET(self):
            url = urlparse(self.path)
            if not url.path.startswith("/api/"):
                return self._static(url.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            parts = url.path.split("/")[2:]
            try:
                with game.lock:
                    body = self._route(parts, q)
            except (ValueError, KeyError, IndexError):
                return self._send(400, {"error": "bad request"})
            if body is None:
                return self._send(404, {"error": "not found"})
            self._send(200, body)

        def _route(self, parts, q):
            w = game.world
            kind = parts[0] if parts else ""
            arg = int(parts[1]) if len(parts) > 1 and parts[1] else None
            if kind == "state":
                return api.state(w)
            if kind == "map":
                return api.galaxy_map(w)
            if kind == "prologue":
                return api.prologue(w)
            if kind == "chronicle":
                return api.chronicle(w, int(q.get("since", 0)), int(q.get("min", 3)), int(q.get("limit", 400)))
            if kind == "person":
                return api.person(w, arg)
            if kind == "faction":
                return api.faction(w, arg)
            if kind == "planet":
                return api.planet(w, arg)
            if kind == "war":
                return api.war(w, arg)
            if kind == "famous":
                return api.famous(w, int(q.get("n", 40)), q.get("dead") != "1")
            if kind == "search":
                return api.search(w, q.get("q", ""))
            if kind == "wars":
                return api.wars_list(w)
            return None

        def do_POST(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/api/step":
                    months = max(1, min(MAX_STEP, int(q.get("months", 1))))
                    with game.lock:
                        engine.run(game.world, months)
                        return self._send(200, {"date": game.world.date(), "t": game.world.t})
                if url.path == "/api/new":
                    seed = int(q.get("seed", 7))
                    planets = max(30, min(300, int(q.get("planets", 120))))
                    game.new(seed, planets)
                    return self._send(200, {"ok": True})
            except ValueError:
                return self._send(400, {"error": "bad request"})
            self._send(404, {"error": "not found"})

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description="残光暦銀河シミュレーター（ブラウザ版）")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--planets", type=int, default=120)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--load", help="CLI で保存した世界を読み込む")
    ap.add_argument("--no-browser", action="store_true", help="ブラウザを自動で開かない")
    args = ap.parse_args(argv)

    if args.load:
        with open(args.load, "rb") as fh:
            world = pickle.load(fh)
    else:
        print("銀河を生成しています……")
        world = generate(seed=args.seed, n_planets=args.planets)
    game = Game(world)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(game))
    url = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{args.port}/"
    print(f"{url} で銀河が待っています。終了するには Ctrl+C を押してください。")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n銀河の観測を終了しました。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
