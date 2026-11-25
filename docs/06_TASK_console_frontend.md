# 06. Task: app.py, the Streamlit console (Person 3)

Audience: judges and non-technical visitors, viewing a projector from a few metres. Goal: they understand what is happening **without hearing the word "hash"**. Build against a **mocked `verify()`** returning the contract shape until Person 1's real one lands. Put the mock behind `try: from verify import verify except ImportError: from mock_verify import ...` inside `app.py` itself (no extra file).

Install: `pip install streamlit` (plus `scikit-learn numpy joblib` for the ML chart). Run: `streamlit run app.py --server.port 8501`.

## Screen layout, top to bottom
1. **3-step strip** (always visible): `1 RECORD  ->  2 SEAL  ->  3 COMPARE`, with one short sentence under each ("Every action is written to a log", "A fingerprint of each record is sent to independent vaults", "If anything changes, the machines disagree"). This is the permanent explanation.
2. **Status banner**, full width, very large:
   - `OK` -> green "ALL RECORDS INTACT"
   - `PENDING` -> amber "SEALING..."
   - `TAMPERED` -> red "TAMPERING DETECTED" (add CSS pulse)
3. **Three machine tiles side by side** from `nodes`: Server, Vault 1, Vault 2. Each shows name, "Record #head_seq", short fingerprint (first 8 hex), and a big tick (agrees true) or cross (false). Unreachable (`agrees` null) -> grey "OFFLINE" tile, nothing crashes. **These tiles are the explanation. Never cut them.**
4. **Alarm box** (only when findings exist), plain English from `finding["detail"]`, plus: "Server's file now fingerprints as `actual[:8]`. Records say it should be `expected[:8]`. Confirmed by: Vault 1, Vault 2." Also show a before/after text diff using a **display-only cache** of lines the console has already seen while status was OK (stored in a file such as `.seen_lines.json`). Label it "display only; the proof is the fingerprint mismatch".
5. **Live feed**: last 20 rows, columns lock icon, seq, time, user, event, IP. Rows whose seq appears in `findings` are red; unparseable rows are red with "UNREADABLE".
6. **Activity chart** (SHOULD): events per 10 s window, with amber markers where `ml.py` flags a window ("suspicious burst of failed logins"). Cut this first if late.
7. Sidebar: "Verify now" button, "Show raw detail" toggle (hashes in full, for technical questions), link to the benchmark numbers panel (reads `metrics.json` and `bench.json` if present, otherwise shows "not run yet").

## Behaviour rules
- Refresh with `@st.fragment(run_every=2)` for the banner, tiles, alarm and feed. If the fragment API misbehaves on the installed version, fall back to the "Verify now" button plus `streamlit-autorefresh`-free manual refresh. Keep state in files, never rely on `st.session_state` surviving.
- Never let a bad line, a missing file or an unreachable vault raise: wrap each section in try/except and show a calm message.
- Never call `verify()` more than once per refresh.
- **Projector-safe styling:** light or mid-tone background, minimum 20 px body text, 48 px+ banner, saturated green `#16a34a`, red `#dc2626`, amber `#d97706`. No dark theme. No thin grey text.
- A "demo mode" query param `?stage=1` hides the sidebar and the raw-detail toggle.

## Order of work
1. Mock `verify()` with three states (OK, TAMPERED edit, TAMPERED rewrite), banner + tiles (20 min)
2. Alarm box + feed (15 min)
3. Wire to the real `verify()` (5 min)
4. Styling polish (10 min)
5. Chart and benchmark panel only if everything above works

## Acceptance
- flip between the four mock states: banner and tiles change correctly
- real `verify()`: edit a line in the log -> red within 3 seconds, record number shown
- kill a vault -> its tile greys out, console keeps running
- readable from the back of a classroom on a projector (test it)
