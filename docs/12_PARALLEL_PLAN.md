# 12. Parallel build plan

This document explains the base that is ready now. Read `TASKS.md` first, then your brief in `docs/tasks/`.

## What the base gives you

| Piece | File | Purpose |
|---|---|---|
| Contract gate | `scripts/check_contract.py` | Fails fast when config, signatures or stdlib-only rules break |
| Test suite | `tests/` | 51 core tests, 56 with ML: mutations, vault API, restart, two-vault end-to-end |
| Private stack | `scripts/local_stack.py` | Two vaults, generator and console on your own ports |
| Demo check | `scripts/demo_check.py` | Runs all five demo acts on real vaults and asserts the result |
| One-command setup | `scripts/bootstrap.sh` | Venv, dependencies, contract check, tests |
| CI | `.github/workflows/ci.yml`, `.forgejo/workflows/ci.yml` | Contract, tests, selftest, lint, demo acts, scenario and ML smoke |
| Ownership | `CODEOWNERS` | Reminds reviewers which lane owns each file |
| Task board | `TASKS.md` | Ordered tasks with a done test for each |

The original task files `04` to `07` remain the detailed reference. Your brief in `docs/tasks/` tells you where to start today.

## Why four people do not block each other

Every lane depends on the contract, not on another person.

| Consumer | Needs | Ready now |
|---|---|---|
| P4 generator | `seal.append()` | Yes |
| P2 vault | HTTP shape from `03_CONTRACT.md` | Yes, client helpers included |
| P1 verifier | `witness.head()` and `witness.entry()` | Yes |
| P3 console | `verify()` return shape | Yes, plus built-in `?mock=` states |

P3 starts with the mock. P4 starts with the generator. P2 starts with the server. P1 starts with the tests. No lane waits.

## Ports and data

`scripts/local_stack.py` builds this layout for a stack name:

```
.run/<name>/
  config.json          paths resolve inside this folder
  app.log.jsonl        the sealed log
  ledger.jsonl         the hash chain
  witness_vault_1.jsonl
  witness_vault_2.jsonl
  pids.json
  *.log
```

Ports come from a hash of the name, in the range 18000 to 19200. The script checks that the three ports are free before it starts. Two people with different names cannot collide.

The demo `config.json` still points at real vault laptops. The private stack never edits it.

## Sequence for the day

| Time | What happens |
|---|---|
| 09:00 | Network, Python, firewall. Run `bootstrap.sh` on every laptop. |
| 09:20 | Read `03_CONTRACT.md` together. Agree the vault IPs. P2 writes `config.json`. |
| 09:30 | Each person runs `make check`, `make test` and `make demo NAME=<lane>`. |
| 09:40 | Parallel work starts. Each lane follows its brief. |
| 10:50 | Integration check `I-1`: two real vaults and one console. |
| 11:10 | Tamper scene, reset drill (`I-2`, `I-3`). |
| 11:40 | P4 produces `metrics.json` and `bench.json`. P3 polishes. |
| 12:15 | Code freeze. Two rehearsals (`I-4`). |

## Merge map

| Merge | Files touched | Risk | Check after merge |
|---|---|---|---|
| P1 into `dev` | `seal.py`, `verify.py` | Core shape changes | `make test` |
| P2 into `dev` | `witness.py` | HTTP or storage change | `make test`, one real vault |
| P3 into `dev` | `app.py` | Display only | `?mock=edit`, then real edit |
| P4 into `dev` | `gen.py`, `attack.py`, `ml.py`, `bench.py` | Event fields | `make check`, rewrite scene |

If two lanes need the same new field, stop and change the contract together first.

## Fallback

If the venue network fails, run everything on one laptop:

```
make demo NAME=fallback
```

The stack already uses localhost vaults. The demo fallback `config.local.json` stays as a second option for the manual run order in `10_SETUP_NETWORK_RESET.md`.

## What is not built

Do not add Merkle trees, quorum, Docker, a database or a public chain. The cut list in `09_TIMELINE_CUTS_FAILURES.md` is still in force.

## First integration rule

Before the first merge, each owner runs `make ci` on a clean checkout. The lead merges only a green branch. A red `dev` stops all four lanes, so report a red test at once.
