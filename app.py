"""LogSeal console (projector-safe). Run: streamlit run app.py --server.port 8501
Options: LOGSEAL_CONFIG=config.local.json (env) | ?stage=1 hides the sidebar | ?mock=ok|edit|rewrite|offline tests without a backend"""
import html, json, os, time
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.environ.get("LOGSEAL_CONFIG", os.path.join(HERE, "config.json"))
GREEN, RED, AMBER, GREY = "#16a34a", "#dc2626", "#d97706", "#64748b"

try:
    import seal
    from verify import verify as _real_verify
except ImportError:
    _real_verify = None

def _mock(kind):
    h = lambda c: c * 64
    # edit: server differs, vaults hold the original. rewrite: server looks clean, both vaults reject.
    # offline: one vault is grey, the other two still agree.
    edit, rewrite, offline = kind == "edit", kind == "rewrite", kind == "offline"
    vh = h("b") if rewrite else h("a")
    nodes = [{"name": "Server", "role": "server", "reachable": True, "head_seq": 412, "head_hash": h("a"), "agrees": not edit},
             {"name": "Vault 1", "role": "vault", "reachable": True, "head_seq": 412, "head_hash": vh, "agrees": not rewrite},
             {"name": "Vault 2", "role": "vault", "reachable": not offline, "head_seq": None if offline else 412,
              "head_hash": None if offline else vh, "agrees": None if offline else not rewrite}]
    if edit:
        fnd = [{"class": "EDIT", "seq": 120, "expected": h("a"), "actual": h("b"),
                "detail": "Record 120 was changed after it was sealed.", "confirmed_by": ["Vault 1", "Vault 2"]}]
    elif rewrite:
        fnd = [{"class": "WITNESS_CONFLICT", "seq": 120, "expected": h("b"), "actual": h("a"),
                "detail": "The server's records were rewritten: the vaults remember record 120 differently.",
                "confirmed_by": ["Vault 1", "Vault 2"]}]
    else:
        fnd = []
    feed = [{"seq": i, "ts": f"2026-11-25T10:31:{i % 60:02d}", "event": "login_fail" if i % 7 == 0 else "file_read", "user": "alice",
             "src_ip": "10.0.0.7", "ok": not (fnd and i == 120)} for i in range(100, 130)]
    return {"status": "TAMPERED" if fnd else "OK", "checked_at": "mock", "log_lines": 412, "ledger_entries": 412,
            "findings": fnd, "nodes": nodes, "feed": feed}

def run_verify(mock):
    if mock:
        return _mock(mock)
    if _real_verify is None:
        raise RuntimeError("verify.py is not available")
    return _real_verify(seal.load_config(CFG))

def short(x, full=False):
    return "none" if not x else (x if full else x[:8])

def read_log_text():
    try:
        cfg = seal.load_config(CFG)
        with open(cfg["log_path"], "rb") as f:
            return f.read().decode("utf-8", "replace").split("\n")
    except Exception:
        return []

def seen_path():
    """Display-only cache lives next to the log, so parallel stacks cannot overwrite each other."""
    try:
        cfg = seal.load_config(CFG)
        return os.path.join(os.path.dirname(os.path.abspath(cfg["log_path"])), ".seen_lines.json")
    except Exception:
        return os.path.join(HERE, ".seen_lines.json")

def css():
    st.markdown("""<style>
    :root {--ink:#142238;--muted:#64748b;--line:#e2e8f0;--surface:#fff;--canvas:#f4f7fb;}
    html, body, [class*="css"] {font-size:16px;color:var(--ink);}
    .stApp {background:var(--canvas);}
    [data-testid="stHeader"] {background:rgba(244,247,251,.88);}
    [data-testid="stSidebar"] {background:#eef3f9;border-right:1px solid var(--line);}
    [data-testid="stMainBlockContainer"] {max-width:1500px;padding-top:2rem;padding-bottom:3rem;}
    h1,h2,h3 {color:var(--ink);letter-spacing:-.035em;}
    .topbar {display:flex;align-items:center;gap:14px;margin:0 0 24px;}
    .brand-mark {width:44px;height:44px;border-radius:14px;background:#163b67;color:#fff;display:flex;align-items:center;justify-content:center;font-size:21px;font-weight:800;box-shadow:0 5px 14px #163b6728;}
    .brand-title {font-size:26px;font-weight:800;line-height:1.15;letter-spacing:-.04em;color:var(--ink);}
    .brand-subtitle {font-size:14px;color:var(--muted);margin-top:4px;}
    .section-label {font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#64748b;font-weight:800;margin:4px 0 10px;}
    .steps {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:20px;}
    .step {display:flex;align-items:flex-start;gap:12px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:0 2px 8px #14223808;}
    .step-num {flex:0 0 30px;height:30px;border-radius:10px;background:#e8eff8;color:#1e4c7c;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;}
    .step b {font-size:14px;letter-spacing:.04em;color:#21364f;}
    .step-copy {font-size:13px;color:var(--muted);line-height:1.4;margin-top:3px;}
    .banner {display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:128px;color:#fff;text-align:center;border-radius:18px;padding:20px 24px;margin:8px 0 12px;box-shadow:0 8px 24px #14223818;}
    .banner-title {font-size:clamp(30px,3.5vw,46px);font-weight:850;line-height:1.1;letter-spacing:.01em;}
    .banner-meta {font-size:14px;opacity:.9;margin-top:8px;font-weight:550;}
    @keyframes pulse {0%,100%{box-shadow:0 8px 24px #dc262633}50%{box-shadow:0 8px 32px #dc262677}}
    .pulse {animation:pulse 1.5s ease-in-out infinite;}
    .tiles {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:14px 0 22px;}
    .tile {min-width:0;border:1px solid var(--line);border-top:4px solid;border-radius:15px;background:var(--surface);text-align:left;padding:17px 18px 15px;box-shadow:0 3px 12px #14223808;}
    .tile-head {display:flex;align-items:center;justify-content:space-between;gap:8px;}
    .tile .n {font-size:17px;font-weight:750;color:#1b2d43;}
    .role {font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#8290a2;font-weight:750;}
    .tile .rec {font-size:13px;color:var(--muted);margin-top:15px;}
    .tile .fp {font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:13px;color:#334b67;background:#f5f8fc;border:1px solid #e9eef5;border-radius:8px;padding:7px 9px;margin-top:6px;overflow-wrap:anywhere;}
    .tile-status {display:flex;align-items:center;gap:7px;margin-top:13px;font-size:13px;font-weight:700;}
    .dot {width:9px;height:9px;border-radius:50%;display:inline-block;}
    .alarm {background:#fff5f5;border:1px solid #fecaca;border-left:5px solid #dc2626;border-radius:13px;padding:16px 18px;margin:14px 0;color:#7f1d1d;box-shadow:0 3px 12px #7f1d1d0a;}
    .alarm code {color:#7f1d1d;background:#ffe4e6;padding:2px 5px;border-radius:4px;}
    table.feed {width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;font-size:14px;box-shadow:0 3px 12px #14223808;}
    table.feed td,table.feed th {padding:11px 14px;text-align:left;border-bottom:1px solid #edf1f6;}
    table.feed th {background:#f8fafc;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.09em;font-weight:800;}
    table.feed tr:last-child td {border-bottom:0;}
    table.feed td:first-child {width:35px;text-align:center;color:#56806b;}
    table.feed tr.bad {background:#fff1f2;color:#9f1239;font-weight:700;}
    @media(max-width:800px){.steps,.tiles{grid-template-columns:1fr}.banner-title{font-size:30px}.tile{padding:14px}}
    </style>""", unsafe_allow_html=True)

def steps():
    s = [("1", "RECORD", "Every action is written to a log"), ("2", "SEAL", "Each record fingerprint is sent to independent vaults"),
         ("3", "COMPARE", "Changes make the machines disagree")]
    st.markdown('<div class="steps">' + "".join(f'<div class="step"><div class="step-num">{n}</div><div><b>{a}</b><div class="step-copy">{b}</div></div></div>' for n, a, b in s) + "</div>", unsafe_allow_html=True)

def banner(r):
    txt, col, cls = {"OK": ("ALL RECORDS INTACT", GREEN, ""), "PENDING": ("SEALING...", AMBER, ""),
                     "TAMPERED": ("TAMPERING DETECTED", RED, "pulse")}.get(r.get("status"), ("CHECKING...", AMBER, ""))
    meta = f'{r["log_lines"]:,} records checked · {r["ledger_entries"]:,} sealed'
    st.markdown(f'<div class="banner {cls}" style="background:{col}"><div class="banner-title">{txt}</div><div class="banner-meta">{meta}</div></div>', unsafe_allow_html=True)

def tiles(r, raw):
    out = []
    for n in r["nodes"]:
        ag = n["agrees"]
        col, tick = (GREY, "") if ag is None else ((GREEN, "✔") if ag else (RED, "✘"))
        rec = "No connection" if ag is None else f"Latest record · #{n['head_seq']}"
        fp = "" if ag is None else short(n["head_hash"], raw)
        role = "INDEPENDENT VAULT" if n["role"] == "vault" else "LOCAL LEDGER"
        label = "OFFLINE" if ag is None else ("IN SYNC" if ag else "MISMATCH")
        out.append(f'<div class="tile" style="border-top-color:{col}"><div class="tile-head"><div class="n">{html.escape(n["name"])}</div><div class="role">{role}</div></div>'
                   f'<div class="rec">{rec}</div>'
                   f'<div class="fp">{html.escape(fp) if fp else "Fingerprint unavailable"}</div>'
                   f'<div class="tile-status" style="color:{col}"><span class="dot" style="background:{col}"></span>{tick if ag is None else ""} {label}</div></div>')
    st.markdown('<div class="tiles">' + "".join(out) + "</div>", unsafe_allow_html=True)

def alarm(r, raw):
    lines = read_log_text()
    try:
        with open(seen_path()) as f:
            seen = json.load(f)
    except Exception:
        seen = {}
    for f in r["findings"]:
        conf = ", ".join(f.get("confirmed_by") or []) or "no vault"
        st.markdown(f'<div class="alarm"><b>{html.escape(f["detail"])}</b><br>'
                    f'Server\'s file now fingerprints as <code>{short(f.get("actual"), raw)}</code>. '
                    f'Records say it should be <code>{short(f.get("expected"), raw)}</code>. Confirmed by: {html.escape(conf)}.</div>',
                    unsafe_allow_html=True)
        old, now = seen.get(str(f["seq"])), (lines[f["seq"] - 1] if 0 < f["seq"] <= len(lines) else None)
        if f["class"] == "EDIT" and old and now:
            st.markdown('<p class="beforeafter">Before / after (display only; the proof is the fingerprint mismatch)</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.code(old, language="json"); c2.code(now, language="json")

def feed(r):
    rows = []
    for x in reversed(r["feed"][-20:]):
        bad = not x.get("ok", True)
        ev = "UNREADABLE" if x["event"] == "UNPARSEABLE" else html.escape(str(x["event"]))
        rows.append(f'<tr class="{"bad" if bad else ""}"><td>{"⚠" if bad else "🔒"}</td><td>#{x["seq"]}</td><td>{html.escape(str(x.get("ts") or "")[11:19])}</td>'
                    f'<td>{html.escape(str(x.get("user") or ""))}</td><td>{ev}</td><td>{html.escape(str(x.get("src_ip") or ""))}</td></tr>')
    st.markdown('<div class="section-label">Recent activity</div><table class="feed"><tr><th></th><th>Record</th><th>Time</th><th>User</th><th>Event</th><th>IP address</th></tr>' + "".join(rows) + "</table>",
                unsafe_allow_html=True)

def activity():
    """Optional: events per 10 s window + suspicious windows from ml.py. Cut first if late."""
    import calendar, pandas as pd
    import ml
    evs = []
    for ln in read_log_text()[-400:]:
        try:
            evs.append(json.loads(ln))
        except Exception:
            pass
    if not evs:
        return
    cnt = {}
    for e in evs:
        s = calendar.timegm(time.strptime(e["ts"], "%Y-%m-%dT%H:%M:%S")) // 10 * 10
        cnt[s] = cnt.get(s, 0) + 1
    st.subheader("Activity (events per 10 seconds)")
    st.bar_chart(pd.Series({time.strftime("%H:%M:%S", time.gmtime(k)): v for k, v in sorted(cnt.items())}))
    try:
        bad = [w["window_start"][11:19] for w in ml.flag_windows(evs) if w["flagged"]]
    except FileNotFoundError:
        st.markdown('<div class="alarm" style="background:#fef3c7;border-color:#d97706;color:#78350f">Model not trained. Run <code>make dataset</code> then <code>make train</code>.</div>',
                    unsafe_allow_html=True)
        return
    if bad:
        st.markdown(f'<div class="alarm" style="background:#fef3c7;border-color:{AMBER};color:#78350f">Suspicious burst of failed logins around {", ".join(bad[-3:])}</div>',
                    unsafe_allow_html=True)

def dashboard(raw, mock, chart):
    try:
        r = run_verify(mock)
    except Exception as e:
        st.warning(f"Verifier is not available right now ({type(e).__name__}). Retrying...")
        return
    if r["status"] == "OK" and not mock:                       # remember what clean lines looked like (display only)
        try:
            lines = read_log_text()
            base = max(0, len(lines) - 201)
            with open(seen_path(), "w") as f:
                json.dump({str(i + 1): l for i, l in enumerate(lines[base:], base)}, f)
        except Exception:
            pass
    for section in (lambda: banner(r), lambda: tiles(r, raw), lambda: alarm(r, raw) if r["findings"] else None, lambda: feed(r)):
        try:
            section()
        except Exception as e:
            st.info(f"(section unavailable: {type(e).__name__})")
    if chart:
        try:
            activity()
        except Exception:
            pass

st.set_page_config(page_title="LogSeal", layout="wide")
css()
q = st.query_params
stage, mock = q.get("stage") == "1", q.get("mock")
raw, chart = False, True
if stage:
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='collapsedControl']{display:none}</style>", unsafe_allow_html=True)
else:
    with st.sidebar:
        st.title("LogSeal")
        if st.button("Verify now", use_container_width=True):
            st.rerun()
        raw = st.toggle("Show raw detail", False)
        chart = st.toggle("Activity chart", True)
        with st.expander("Benchmark numbers"):
            for f, label in (("bench.json", "Mutation test"), ("metrics.json", "Burst detector")):
                p = os.path.join(HERE, f)
                st.markdown(f"**{label}**")
                if os.path.exists(p):
                    with open(p) as fh:
                        st.json(json.load(fh))
                else:
                    st.write("not run yet")
st.markdown('<div class="topbar"><div class="brand-mark">L</div><div><div class="brand-title">LogSeal</div><div class="brand-subtitle">Tamper-evident security monitoring</div></div></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Integrity overview</div>', unsafe_allow_html=True)
steps()
if hasattr(st, "fragment"):
    dashboard = st.fragment(run_every=2)(dashboard)
dashboard(raw, mock, chart)
