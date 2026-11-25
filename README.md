# LogSeal

Tamper-evident security log. Every event is sealed into a hash chain, and a fingerprint of each record is copied to independent vault machines. Edit or delete the log and the console goes red.

The full spec is in `docs/`. Start with `docs/00_README_START_HERE.md`. The law is `docs/03_CONTRACT.md`.

## Team start

Four people work in parallel. Each person has a lane, a private stack and a done test.

1. `./scripts/bootstrap.sh`
2. `make check` and `make test`
3. `make demo NAME=p1` (use your lane name: `p1`, `p2`, `p3` or `p4`)
4. Read `TASKS.md`, then your brief in `docs/tasks/`.

The private stack gives you two vaults, a generator and a console on your own ports. Its data stays in `.run/<name>/`, so four stacks can run at the same time.

| Command | Use |
|---|---|
| `make demo NAME=p1` | Vaults + generator + console |
| `make stack NAME=p1` | Vaults only |
| `make status NAME=p1` | Show process and vault state |
| `make down NAME=p1` | Stop the stack |
| `make reset NAME=p1` | Clear log, ledger and vaults |
| `make demo-check` | All five demo acts on real vaults |
| `make ci` | Contract, tests, selftest, lint, demo acts |

## Status

| File | State |
|---|---|
| `seal.py`, `verify.py`, `witness.py` | Done. Covered by `tests/` and `seal.py --selftest` |
| `gen.py`, `attack.py`, `bench.py`, `ml.py` | Done, tested |
| `app.py` | Checked in a real browser: four mock states, stage mode and a live edit at 2.33 s. Projector test is still open |
| `metrics.json`, `bench.json` | Measured by the lead on the dev laptop. P4 must repeat them on the demo laptop |
| `scripts/`, `tests/`, CI | Base ready for four parallel lanes |

## Manual setup

```
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python seal.py --selftest
```

Put the vault IPs in `config.json`. Use `--config config.local.json` on every tool for the one-laptop fallback.

## Manual run

```
python witness.py --name "Vault 1" --port 8101 --allow-reset    # each vault
export LOGSEAL_KEY=anything-same-everywhere                     # Windows: set LOGSEAL_KEY=...
python gen.py --rate 2                                          # victim server
streamlit run app.py --server.port 8501                         # control room (?stage=1 for projector)
python verify.py --watch                                        # terminal fallback console
```

Demo: stop `gen.py`, wait 3 s, edit a line of `app.log.jsonl` -> red. Then `python attack.py rewrite --seq 120` -> server tile green, vault tiles red. `python gen.py --attack burst` for the ML act.

Before the pitch: `python gen.py --dataset dataset && python ml.py train && python ml.py eval && python bench.py`

Reset: stop `gen.py`, then `python attack.py restore` (after an attack) or `python seal.py --reset`.

## Docs

| File | Content |
|---|---|
| `TASKS.md` | Board, owners, done tests, checkpoints |
| `CONTRIBUTING.md` | Lanes, branches, review, definition of done |
| `docs/12_PARALLEL_PLAN.md` | How the four-lane base works |
| `docs/13_VERIFICATION.md` | What the base proved, and what is still open |
| `docs/14_MODEL_REPORT.md` | Burst-detector design, exact numbers and improvement plan |
| `docs/tasks/` | One brief per person |
| `docs/08_DEMO_AND_PITCH.md` | Demo script and pitch |
| `docs/09_TIMELINE_CUTS_FAILURES.md` | Timeboxes and cut order |
| `docs/11_CLAIMS_AND_HONESTY.md` | What may be said to judges |

## Notes

- `?mock=ok|edit|rewrite` on the console URL previews the three states with no backend.
- `?stage=1` hides the sidebar for the projector.
- `LOGSEAL_CONFIG=config.local.json` makes the console use the fallback config.
- Never call this a blockchain. Say: authenticated append-only ledger with independent witnesses.
- Never invent a number. Any metric shown to judges must come from our own script output that day.
