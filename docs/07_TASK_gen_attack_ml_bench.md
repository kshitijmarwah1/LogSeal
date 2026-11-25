# 07. Task: gen.py, attack.py, ml.py, bench.py (Person 4)

Order: **`gen.py` first (15 min), everyone needs it.** Then `attack.py` (needed for the demo), then `ml.py`, then `bench.py`. Stdlib only except `ml.py` (`scikit-learn numpy joblib`).

## gen.py
- `python gen.py --rate 2` appends about 2 benign events per second through `seal.append(evt, cfg)` until Ctrl+C. Seeded `random` for reproducibility (`--seed`).
- Benign mix (weights): `login_ok`, `logout`, `file_read` (most common), `file_write`, occasional `sudo`, rare `config_change`, rare isolated `login_fail`. Small set of users (5-8), internal IPs.
- `python gen.py --attack burst` injects about 40 `login_fail` events from one external IP against one user within about 10 seconds, then one `login_ok` (a successful brute force). Goes through `seal.append`, so it is sealed too.
- `python gen.py --dataset DIR` writes labeled data **without sealing**: `train.jsonl` (benign only, covering several simulated hours) and `test.jsonl` (benign + injected bursts), each event with a `"label"` field (0/1). Used only by `ml.py`.
- Events must match the contract fields.
- Launch only from the terminal, never from a UI button (avoids duplicate generators).

## attack.py (the smart-attacker act, about 15 min)
Reuses `seal.py` functions, so it is only a few dozen lines.
- `python attack.py rewrite --seq 120 --find alice --replace mallory`: edit the log line, then recompute `lhash`, `hash`, `mac` from that seq to the end using the real key, rewrite the ledger consistently, then try `witness.push` for the rewritten entries. The vaults must answer `409`; print what happened in a readable way ("Vault 1 REJECTED the rewrite").
- `python attack.py wipe --keep 100`: cut the log AND ledger back to the first 100 records consistently (log-wiping). The local verifier will say OK; the vaults are ahead.
- `python attack.py restore`: put back the saved copy of the files (the script saves `app.log.jsonl.bak` and `ledger.jsonl.bak` before attacking) so the demo can be repeated.
- The attacker has the HMAC key on purpose. The vaults are what stop it, not the key.

## ml.py (about 20 min)
1. Windows of 10 seconds. Features per window: event counts, `window_total`, distinct IPs and users, `fail_fraction`, per-IP failure count and share, failure gaps, entropy, and fail-then-success.
2. `python ml.py train` fits `IsolationForest(random_state=42)` on benign train windows only. The last 20% of training windows form a validation block. Threshold = **1st percentile of validation `score_samples`** (lower = more abnormal). Do not use the test set to choose it. Do not guess a `contamination` value. Save with joblib (`model.joblib`).
3. `python ml.py eval` scores the labeled test windows (a window is positive if it contains any attack event). It prints and writes `metrics.json` (contract shape). Extra window, burst, rule-baseline and interval values go to `metrics_detail.json`. **Report only what the script prints.**
4. Importable: `flag_windows(events) -> list[{"window_start","score","flagged"}]`, used by the console chart.
5. Honest wording: "trained and evaluated on synthetic data from our own generator and features, so the scores are optimistic by construction; a real deployment would need real logs".

## bench.py (SHOULD, about 15 min)
- Work on a **copy** of the files in a temp dir, never the live ones.
- Seal 200 events, apply 100 random mutations (edit, whitespace edit, delete, insert, truncate), run `verify(..., use_witnesses=False)` on each, record detected / class / time.
- Write `bench.json` (contract shape) and print a table. Say "N mutations, M detected, median X ms" and nothing grander. The vault-based cases are tested manually in rehearsal.

## Acceptance
- `gen.py` output parses as JSON, every line has the contract fields
- `attack.py rewrite` leaves `verify(use_witnesses=False)` reporting OK (that is the point) and with vaults running reports `WITNESS_CONFLICT`
- `metrics.json` and `bench.json` exist and contain only measured values
