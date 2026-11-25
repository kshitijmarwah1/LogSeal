# Contributing

Four people build in parallel. Each person owns files. The contract is the meeting point.

## File lanes

| Lane | Person | Files | May read | Must not edit |
|---|---|---|---|---|
| P1 | Core | `seal.py`, `verify.py` | all | `witness.py`, `app.py`, P4 files |
| P2 | Vault | `witness.py` | all | P1, P3, P4 files |
| P3 | Console | `app.py` | all | P1, P2, P4 files |
| P4 | Scenarios | `gen.py`, `attack.py`, `ml.py`, `bench.py` | all | P1, P2, P3 files |
| Lead | Shared | `config*.json`, `docs/03_CONTRACT.md`, `tests/`, `scripts/`, `Makefile` | all | — |

Need a change in a file you do not own? Ask the owner. Do not make the change yourself.

## Branch flow

```
main            protected, green, demo-ready
 └─ dev         integration branch
     ├─ p1/core
     ├─ p2/vault
     ├─ p3/console
     └─ p4/scenarios
```

1. Branch from `dev`: `git switch -c p1/core`.
2. Keep the branch short. Commit small changes.
3. Before each push run `make ci`.
4. Open a pull request into `dev`. One other person reviews.
5. The lead merges. Merge order is not fixed, because every lane works against the contract.
6. At code freeze the lead merges `dev` into `main`.

Do not push to `main`. Do not force-push a shared branch. Do not merge `dev` into your branch. Rebase instead.

## Commit messages

Use one line: `type(scope): message`.

```
feat(core): name the first changed record
fix(vault): skip reverse DNS on bind
test(console): cover the offline vault tile
docs(tasks): add the P3 done test
```

Types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`.

## Run your own stack

Every person uses a different stack name. The stack keeps ports, config, logs and data in `.run/<name>/`.

```
make demo NAME=p1        # two vaults + generator + console
make status NAME=p1
make down NAME=p1
make reset NAME=p1
```

Without `NAME`, the stack uses your OS user name. Do not start a second generator in the same stack.

Four people on one machine: use four names. Four people on four laptops: use one name each. The stack works in both cases.

## Test before you push

```
make check     # contract shape: config, signatures, stdlib-only
make test      # 51 core tests, 56 with the ML tests
make selftest  # the original 20-check core test
make lint      # ruff F rules
```

`make ci` runs all four. CI runs the same commands on every push.

## Change the contract

`docs/03_CONTRACT.md` is the law. Change it only when all four people agree.

1. Write the proposed change in the team chat.
2. Wait for an explicit yes from each owner.
3. One person changes the document and the code in the same pull request.
4. Run `make ci`.
5. Tell the team which tests changed.

A silent change to a file format, an endpoint or a return shape is a bug, not a refactor.

## Definition of done

A task is done when all of these are true:

1. The code runs from a clean checkout.
2. `make ci` passes.
3. The done test in `TASKS.md` passes on the demo laptop.
4. No runtime file is committed.
5. The owner can explain the change in one sentence.

## Windows notes

- Activate the venv with `.venv\Scripts\activate`.
- Set the key with `set LOGSEAL_KEY=demo-key-change-me`.
- Allow inbound TCP 8101 and 8102 in Windows Firewall on the vault laptops.
- Use `python` instead of `python3` if that is the only command.

## Runtime files

The tools write these files. Keep them out of git:

`app.log.jsonl`, `ledger.jsonl`, `witness_*.jsonl`, `*.bak`, `.verify_state.json`, `.seen_lines.json`, `model.joblib`, `dataset/`, `metrics.json`, `bench.json`, `.run/`.
