# Task board

Status: **dev integrated**. P1, P2 and P3 lanes are merged. Open items are listed in `docs/13_VERIFICATION.md`.

## Everyone: first 10 minutes

1. Run `./scripts/bootstrap.sh`. On Windows use `python -m venv .venv` then `pip install -r requirements.txt -r requirements-dev.txt`.
2. Run `make check` and `make test`. Both must pass before you change code.
3. Run `make demo NAME=<yourname>`. Open the console URL that the command prints.
4. Read your brief in `docs/tasks/`. It lists your files, your first task and your done test.

Your `NAME` is your lane: `p1`, `p2`, `p3`, `p4`. Each name gets its own ports, config, log files and vault data in `.run/<name>/`. A stack never touches another stack.

## Board

| ID | Owner | Task | Done when |
|---|---|---|---|
| P1-1 | P1 core @kshitijmarwah1 | Run the full mutation table | All rows pass in `make test` and `make selftest` |
| P1-2 | P1 core @kshitijmarwah1 | Check verify speed | 1,000 events verify in under 1 s on the demo laptop |
| P1-3 | P1 core @kshitijmarwah1 | Check `confirmed_by` and `detail` text for the console | An edit names record N and both vaults |
| P1-4 | P1 core @kshitijmarwah1 | Read `seal.py` write order | Log is written and fsynced before the ledger |
| P2-1 | P2 vault @akash77007 | Check every HTTP row in `03_CONTRACT.md` | `tests/test_witness_api.py` passes |
| P2-2 | P2 vault @akash77007 | Read the vault page from 3 m | Large name, count, fingerprint, red conflict strip |
| P2-3 | P2 vault @akash77007 | Start two vaults and `curl` both | `/head`, `/entry/1`, `/append`, `/reset` answer |
| P2-4 | P2 vault @akash77007 | Restart a vault after a conflict | Entries and conflict history survive |
| P3-1 | P3 console | Open `?mock=ok`, `?mock=edit`, `?mock=rewrite` | Banner and all three tiles change correctly |
| P3-2 | P3 console | Wire the real verifier | An edit turns the banner red in 3 s and shows the record |
| P3-3 | P3 console | Kill one vault | That tile goes grey, the console keeps running |
| P3-4 | P3 console | Projector test | Readable from the back of the room |
| P4-1 | P4 scenarios @Vic-41148 | Run the generator and the burst | Events parse and carry contract fields |
| P4-2 | P4 scenarios @Vic-41148 | Run rewrite, wipe, restore | Server green locally, vaults red, restore is clean |
| P4-3 | P4 scenarios @Vic-41148 | Make the measured numbers | `metrics.json` exists and contains only script output |
| P4-4 | P4 scenarios @Vic-41148 | Run the benchmark | `bench.json` exists and prints mutation count and median |
| I-1 | All | End-to-end with two vaults | `make demo-check` passes all five acts |
| I-2 | All | Judge-edit rehearsal | Stop the generator, edit a line, see red in 3 s |
| I-3 | All | Reset drill | `make down`, `make reset`, `make demo` in under 30 s |
| I-4 | All | Code freeze and two rehearsals | Two clean runs, back to back |

## Lead lane (not P1 to P4)

The lead owns integration. The lead does not take a code lane.

| ID | Task | Command |
|---|---|---|
| I-1 | Prove the five demo acts on real vaults | `make demo-check` |
| I-2 | Judge-edit rehearsal on the demo laptop | manual, 3 s alarm |
| I-3 | Reset drill under 30 s | `make down`, `make reset`, `make demo` |
| I-4 | Code freeze and two rehearsals | manual |

`make ci` now runs `demo-check`, so a broken demo act fails CI before the pitch.

## Integration checkpoints

| Clock | Checkpoint | Owner |
|---|---|---|
| T+00 | Contract read, config agreed, `NAME` chosen | All |
| T+10 | `make check` and `make test` pass on every laptop | All |
| T+50 | Every lane passes its own done tests | All |
| T+70 | First end-to-end with real vaults (`I-1`) | All |
| T+100 | Tamper scene and reset drill (`I-2`, `I-3`) | All |
| T+120 | Numbers produced (`P4-3`, `P4-4`) | P4 |
| T+135 | Code freeze, rehearsal one | All |
| T+145 | Rehearsal two | All |

## Rules

- Edit only your files. The lane table is in `CONTRIBUTING.md` and `CODEOWNERS`.
- `config.json`, `config.local.json` and `docs/03_CONTRACT.md` change only when all four agree.
- Do not commit files that the tools write at run time. `.gitignore` already covers them.
- Pull from `dev` before you push. Rebase your short branch. Do not merge `dev` into your branch.
- A red test is a blocker for the whole team. Tell the team at once.

## Known gaps

- `app.py` is smoke-tested, not yet checked on the projector.
- `metrics.json` and `bench.json` were measured by the lead on the development laptop. P4 must repeat them on the demo laptop. Exact output is in `docs/13_VERIFICATION.md`.
- The real vault IPs are not in `config.json` yet. P2 owns that after the network check.
- The P3 handle in `CODEOWNERS` is still a placeholder. P1, P2, P4 and lead handles are set.
