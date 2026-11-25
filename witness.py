"""LogSeal vault (witness): independent append-only store of (seq, prev, hash).
Server : python witness.py --name "Vault 1" --port 8101 [--allow-reset] [--dir DIR]
Client : push(entry, cfg), head(url, timeout), entry(url, seq, timeout), reset(cfg)  (stdlib only)"""
import argparse, html, json, os, re, socket, socketserver, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ZERO = "0" * 64

# ------------------------------------------------------------------ client helpers
def _req(url, body=None, timeout=1.0):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                               method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
        finally:
            e.close()

def _push_one(w, entry, timeout):
    body = {k: entry[k] for k in ("seq", "prev", "hash")}
    try:
        status, j = _req(w["url"].rstrip("/") + "/append", body, timeout)
        return {"name": w["name"], "ok": bool(j.get("ok")), "status": status,
                "error": j.get("error"), "count": j.get("count")}
    except Exception as e:
        return {"name": w["name"], "ok": False, "status": None, "error": str(e)[:80], "count": None}

def _parallel(fn, items):
    out, threads = [None] * len(items), []
    def run(i, it):
        out[i] = fn(it)
    for i, it in enumerate(items):
        t = threading.Thread(target=run, args=(i, it), daemon=True)
        t.start(); threads.append(t)
    for t in threads:
        t.join()
    return out

def push(entry, cfg):
    """Send one ledger entry to every vault in parallel. Never raises."""
    t = cfg.get("witness_timeout_s", 1.0)
    return _parallel(lambda w: _push_one(w, entry, t), cfg.get("witnesses", []))

def head(url, timeout=1.0):
    try:
        status, j = _req(url.rstrip("/") + "/head", None, timeout)
        return j if status == 200 else None
    except Exception:
        return None

def entry(url, seq, timeout=1.0):
    try:
        status, j = _req(f"{url.rstrip('/')}/entry/{int(seq)}", None, timeout)
        return j if status == 200 else None
    except Exception:
        return None

def reset(cfg):
    """Ask every vault to clear itself (works only if started with --allow-reset)."""
    t = cfg.get("witness_timeout_s", 1.0)
    def one(w):
        try:
            return {"name": w["name"], "status": _req(w["url"].rstrip("/") + "/reset", {}, t)[0]}
        except Exception as e:
            return {"name": w["name"], "status": None, "error": str(e)[:80]}
    return _parallel(one, cfg.get("witnesses", []))

# ------------------------------------------------------------------ server
class Vault:
    def __init__(self, name, folder, allow_reset):
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "vault"
        self.name, self.allow_reset, self.lock = name, allow_reset, threading.Lock()
        self.path = os.path.join(folder, f"witness_{slug}.jsonl")
        self.cpath = os.path.join(folder, f"witness_{slug}.conflicts.jsonl")
        self.entries, self.conflicts = self._load(self.path), self._load(self.cpath)

    @staticmethod
    def _load(path):
        out = []
        if os.path.exists(path):
            with open(path, "rb") as f:
                raw = f.read()
            for ln in raw.split(b"\n"):
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
        return out

    @staticmethod
    def _persist(path, obj):
        with open(path, "ab") as f:
            f.write((json.dumps(obj, separators=(",", ":")) + "\n").encode())
            f.flush(); os.fsync(f.fileno())

    def append(self, b):
        try:
            seq, prev, h = int(b["seq"]), str(b["prev"]), str(b["hash"])
        except Exception:
            return 400, {"ok": False, "error": "BAD_REQUEST"}
        with self.lock:
            n = len(self.entries)
            if 1 <= seq <= n:
                stored = self.entries[seq - 1]["hash"]
                if stored == h:
                    return 200, {"ok": True, "duplicate": True}
                c = {"time": time.strftime("%H:%M:%S"), "seq": seq, "stored": stored, "offered": h}
                self.conflicts.append(c); self._persist(self.cpath, c)
                return 409, {"ok": False, "error": "CONFLICT", "seq": seq, "stored": stored, "offered": h}
            head_hash = self.entries[-1]["hash"] if self.entries else ZERO
            if seq != n + 1 or prev != head_hash:
                return 422, {"ok": False, "error": "GAP", "count": n}
            e = {"seq": seq, "prev": prev, "hash": h}
            self.entries.append(e); self._persist(self.path, e)
            return 200, {"ok": True, "count": n + 1}

    def head(self):
        with self.lock:
            n = len(self.entries)
            return {"name": self.name, "count": n, "seq": n, "hash": self.entries[-1]["hash"] if n else ZERO}

    def get(self, seq):
        with self.lock:
            return self.entries[seq - 1] if 1 <= seq <= len(self.entries) else None

    def reset(self):
        with self.lock:
            self.entries, self.conflicts = [], []
            for p in (self.path, self.cpath):
                open(p, "wb").close()

    def page(self):
        with self.lock:
            n = len(self.entries)
            fp = self.entries[-1]["hash"][:8] if n else "--------"
            cs = list(reversed(self.conflicts))[:4]
        if cs:
            rows = "".join(f"<div>Record #{c['seq']}: I hold <b>{c['stored'][:8]}</b>, offered <b>{c['offered'][:8]}</b> "
                           f"({c['time']})</div>" for c in cs)
            strip = f"<div class='s red'>REWRITE ATTEMPT REJECTED<div class='d'>{rows}</div></div>"
        else:
            strip = "<div class='s green'>ALL RECORDS CONSISTENT</div>"
        safe_name = html.escape(self.name)
        return f"""<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<title>{safe_name}</title><style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f8fafc;color:#0f172a;margin:0;padding:3vh 4vw}}
h1{{font-size:clamp(44px,7vw,120px);margin:0}} .k{{font-size:clamp(28px,3.8vw,64px);margin:1.5vh 0}} code{{background:#e2e8f0;padding:0 .4em;border-radius:6px}}
.s{{font-size:clamp(32px,4.5vw,80px);font-weight:800;color:#fff;padding:2vh 2vw;border-radius:16px;margin-top:3vh}}
.green{{background:#16a34a}} .red{{background:#dc2626}} .d{{font-size:clamp(20px,2.4vw,38px);font-weight:500;margin-top:1vh}}
</style></head><body><h1>{safe_name}</h1>
<div class="k">Records held: <b>{n}</b></div>
<div class="k">Latest fingerprint: <code>{fp}</code></div>{strip}</body></html>"""

def make_handler(vault):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj=None, html=None):
            body = html.encode() if html is not None else json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html is not None else "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body)

        def _body(self):
            try:
                return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except Exception:
                return None

        def do_GET(self):
            if self.path == "/head":
                return self._send(200, vault.head())
            m = re.fullmatch(r"/entry/(\d+)", self.path)
            if m:
                e = vault.get(int(m.group(1)))
                return self._send(200, e) if e else self._send(404, {"ok": False, "error": "NOT_FOUND"})
            if self.path in ("/", "/index.html"):
                return self._send(200, html=vault.page())
            self._send(404, {"ok": False})

        def do_POST(self):
            if self.path == "/append":
                b = self._body()
                return self._send(*(vault.append(b) if isinstance(b, dict) else (400, {"ok": False, "error": "BAD_REQUEST"})))
            if self.path == "/reset":
                if not vault.allow_reset:
                    return self._send(403, {"ok": False, "error": "RESET_DISABLED"})
                vault.reset(); return self._send(200, {"ok": True})
            self._send(404, {"ok": False})
    return H

def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "127.0.0.1"

class VaultServer(ThreadingHTTPServer):
    """HTTPServer.server_bind() calls socket.getfqdn(), a reverse DNS lookup that can
    block for many seconds on a venue network. Bind first, never resolve names."""
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name = self.server_address[0]
        self.server_port = self.server_address[1]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="Vault 1"); ap.add_argument("--port", type=int, default=8101)
    ap.add_argument("--allow-reset", action="store_true")
    ap.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    v = Vault(a.name, a.dir, a.allow_reset)
    srv = VaultServer(("0.0.0.0", a.port), make_handler(v))
    print(f"{a.name} listening: http://{_lan_ip()}:{a.port}/  (holds {len(v.entries)} records)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
