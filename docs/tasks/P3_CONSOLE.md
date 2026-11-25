# P3: console lane

You own `app.py`. You own the screen that judges understand in 5 seconds.

Detailed reference: `docs/06_TASK_console_frontend.md` and the contract `docs/03_CONTRACT.md`.

## Start now

```
./scripts/bootstrap.sh
make demo NAME=p3
```

Open the console URL that the stack prints. `app.py` already has four mock states, so you do not wait for P1:

```
http://127.0.0.1:<port>/?mock=ok
http://127.0.0.1:<port>/?mock=edit
http://127.0.0.1:<port>/?mock=rewrite
http://127.0.0.1:<port>/?mock=offline
```

## Do these in order

1. **Check the three states.** The banner must be green, red and red. The server tile must stay green in the rewrite state. The vault tiles must go red. An offline vault must be grey, not an error.
2. **Wire the real verifier.** Start the stack without `--with-console`, then run the console with the stack config:
   `LOGSEAL_CONFIG=.run/p3/config.json streamlit run app.py --server.port 8501`.
   Edit a line in `.run/p3/app.log.jsonl`. The banner must turn red within 3 seconds and name the record.
3. **Keep the three tiles.** They are the explanation. Never cut them.
4. **Check the alarm box.** It must show the plain-English `detail`, the two short fingerprints and `confirmed_by`.
5. **Projector test.** Stand at the back of the room. Body text at least 20 px, banner at least 48 px. No dark theme. No thin grey text.
6. **Optional:** activity chart and benchmark panel. Cut these first if time is short.

## Done when

- `make ci` passes.
- The mock states switch correctly.
- A real edit turns the banner red in 3 seconds and names the record.
- A dead vault shows a grey `OFFLINE` tile and the console keeps running.
- A person at the back of the room can read the banner and the three tiles.

## Do not touch

`seal.py`, `verify.py`, `witness.py`, P4 files, the contract. If `verify()` lacks a field you need, ask P1. Do not recompute hashes in the console.
