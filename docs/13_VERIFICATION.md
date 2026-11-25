# 13. Verification record

This file records what the base proved on one Linux machine. It is evidence, not a target list.

Environment: Linux, Python 3.14.10, localhost vaults. Date: 2026-11-25.

## Commands and results

| Command | Result |
|---|---|
| `python scripts/check_contract.py` | 38 checks pass, `CONTRACT OK` |
| `python -m unittest discover -s tests -t .` | 51 core tests pass in about 5 s, one ML test skipped without sklearn |
| `.venv/bin/python -m unittest discover -s tests -t .` | 56 tests pass in about 7 s |
| `python seal.py --selftest` | All 20 checks pass. `verify()` on 1,000 events: 9 ms |
| `python scripts/demo_check.py` | All five acts pass |
| `python gen.py --dataset dataset` | 29,055 train events, 7,448 test events |
| `python ml.py train` | 1,440 benign windows, fit 1,152, validation 288, threshold -0.5824 |
| `python ml.py eval` | precision 0.632, recall 1.0, F1 0.774 on 360 test windows |
| `python scripts/model_sweep.py` | Five seeds, mean F1 0.7288, range 0.5 to 0.88 |
| `python bench.py` | 100 mutations, 100 detected, median 1.72 ms, p95 1.77 ms |
| Browser: `?mock=ok` | Green banner, three green tiles |
| Browser: `?mock=edit` | Red banner, server ✘, both vaults ✔, record 120 named |
| Browser: `?mock=rewrite` | Red banner, server ✔, both vaults ✘ |
| Browser: `?mock=offline` | Green banner, Vault 2 OFFLINE, other tiles ✔ |
| Browser: `?stage=1&mock=edit` | Sidebar and title hidden, red banner visible |
| Browser: real edit in `.run/verify/app.log.jsonl` | Banner flipped to red 2.33 s after the edit |

These numbers were measured by the lead on the development laptop. Every person must repeat them on the demo laptop before the pitch. `dataset/`, `model.joblib`, `metrics.json`, `metrics_detail.json`, `metrics_sweep.json` and `bench.json` are generated files and are not committed.

## Demo acts proved by `make demo-check`

| Act | Check | Result |
|---|---|---|
| 1 | 60 sealed events, three machines agree | PASS |
| 2 | Edit record 24, both vaults confirm the original | PASS |
| 3 | Rewrite with the key: server green, two vaults red at record 20 | PASS |
| 4 | Wipe to 30 records: server green, vaults ahead at record 31 | PASS |
| 5 | Reset clears log, ledger and both vaults | PASS |

The rewrite act also printed:

```
Vault 1 REJECTED the rewrite (conflict at record 20)
Vault 2 REJECTED the rewrite (conflict at record 20)
```

A real-browser pass used Streamlit 1.67.0 on Python 3.12 with `LOGSEAL_CONFIG=.run/verify/config.json` and two live vaults. The console refresh fragment runs every 2 s; a one-line edit flipped the banner in 2.33 s. The console title line was fixed: a conditional expression rendered a Streamlit `DeltaGenerator` object as a large internal-methods table on every page load. It is now a plain `if` statement.

P3 branch `8db9046` merged into `dev` as `48b3f48`. It adds the offline mock, the projector theme in `.streamlit/config.toml`, and larger alarm text. The merge conflict in `app.py` was resolved by keeping the P3 mock and theme work and the lead fixes for the title, file handles, per-stack cache and model fail-safe message. All four mock states and the stage mode render as listed above.

P1 pull request #2 from @kshitijmarwah1 merged into `dev` as `592eba5`. It adds `test_empty_log_is_ok` to `tests/test_verify_mutations.py`. The test checks that an empty log gives `OK`, zero log lines, zero ledger entries and empty findings and feed. Pull request #1 carried the same change against `main`; it was closed as a duplicate. After the merge, 51 core tests pass and 56 tests pass with scikit-learn installed.

P2 pull request #3 from @akash77007 merged into `dev` as `07fdbbc`. It escapes the vault name in the vault page, removes a trailing slash before vault URLs, and changes the page font sizes to `clamp()` values. All checks pass after the merge. A manual check with the name `<b>Vault</b>` rendered `<h1>&lt;b&gt;Vault&lt;/b&gt;</h1>`. A call to `witness.head("http://127.0.0.1:18999/")` returned the vault name and count.

## Benchmark detail

```
100 mutations, 100 detected, median 1.72 ms (p95 1.77 ms)
  INSERT     18/18
  TRUNCATE   21/21
  EDIT       40/40
  DELETE     21/21
```

These are local checks on a copy of the log. Vaults are not part of this number. `bench.json` holds the same values.

## Model detail

```
trained on 1440 benign windows, fit 1152, validation 288, threshold -0.5824
metrics.json: precision 0.632, recall 1.0, f1 0.774, test_windows 360
window: tp 12, fp 7, fn 0, pr_auc 1.0, precision_ci95 [0.4104, 0.8085], recall_ci95 [0.7575, 1.0]
bursts: 6 total, 6 detected, 13 alarm groups, 7 false alarm groups
rule: 3 failures from one IP in 10 s, precision 1.0, recall 1.0, f1 1.0, 6 bursts detected
```

The threshold comes from unseen benign validation windows. The test set does not set it. The data is synthetic: our generator, our features, measured today. `metrics_detail.json` holds the extra values. See `docs/14_MODEL_REPORT.md` for the five-seed range.

## Still open

| Item | Owner | Status |
|---|---|---|
| Projector readability from 3 m | P3 | Pending |
| P3 review of the model fail-safe message in `app.py` | P3 / lead | Pending |
| Two physical vault laptops over the hotspot | P2 / lead | Pending |
| Two full rehearsals | Lead | Pending |

Do not move an item to done until the exact command output is in this file.
