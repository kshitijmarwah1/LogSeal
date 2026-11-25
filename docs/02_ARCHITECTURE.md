# 02. Architecture

## Machines (demo day)
```
 [Attacker laptop]        [Victim server]  --push (seq,hash)-->  [Vault 1: witness.py]
  attack.py  ----edits---> app.log.jsonl   --push (seq,hash)-->  [Vault 2: witness.py]
                           ledger.jsonl
                           gen.py + seal.py
                                 ^
                                 | reads files, queries vaults over HTTP
                      [Control room: app.py + verify.py]  (projector)
```
All of this also runs on ONE machine with the vaults on localhost ports 8101 and 8102 (fallback config).

## Components
| Component | Job |
|---|---|
| `gen.py` | Produces synthetic security events and calls `seal.append()` |
| `seal.py` | Canonical line, hash chain, HMAC, writes log then ledger, pushes to vaults |
| `witness.py` | Independent append-only vault: stores `(seq, prev, hash)`, rejects conflicts, has a live status page |
| `verify.py` | Re-hashes the raw log, compares with ledger and vaults, returns findings |
| `app.py` | Streamlit console for non-technical viewers |
| `attack.py` | Plays the smart attacker (rewrites log and ledger, tries to push to vaults) |
| `ml.py` | IsolationForest burst detector, writes `metrics.json` |
| `bench.py` | Mutation tests on a COPY of the files, writes `bench.json` |

## Seal algorithm (per event)
```
line  = json.dumps(event, sort_keys=True, separators=(",", ":"))   # written once, never re-dumped
lhash = sha256(line)                                               # fingerprint of this line alone
hash  = sha256(prev + line)                                        # chain: binds content AND position
mac   = HMAC(KEY, f"{seq}:{prev}:{hash}:{lhash}")                  # authenticates ledger entries
```
Order of writes: (1) append line to log + fsync, (2) append entry to ledger + fsync, (3) push `(seq, prev, hash)` to every vault, best effort. The verifier hashes **raw line bytes**, never parsed JSON, so a whitespace-only edit still alarms.

## Threat model
| Attack | Caught by |
|---|---|
| Edit a line | line hash differs from ledger `lhash` |
| Delete a line | log line list is ledger list minus one |
| Insert a line | log line list is ledger list plus one |
| Truncate tail of log | log shorter than ledger |
| Edit the ledger without the key | MAC fails (`LEDGER_FORGED`) |
| Edit log AND ledger WITH the key (root attacker) | **vault conflict**: vault has a different hash for the same seq |
| Truncate log AND ledger consistently | **vault is ahead** of the server (`WITNESS_AHEAD`) |
| Destroy everything and all vaults | Out of scope. Needs an honest vault. Say so. |

Trust assumptions to state out loud: at least one vault is honest, vaults and their storage are not controlled by the attacker, tampering before sealing is out of scope, timestamps are not compared across machines (use seq and hashes only).

## ML (secondary, tiny)
10-second windows, 18 features: event counts, window total, distinct IPs and users, fail fraction, per-IP failure count and share, failure gaps, entropy, and fail-then-success. IsolationForest fits benign windows only. The last 20% of training windows form a validation block; the alarm threshold is the 1st percentile of validation scores, never the test set. Evaluated on a synthetic labeled holdout from our own generator. Numbers are labelled "synthetic data, measured by our scripts today".

## Production path (slide only, not built)
Merkle batching and inclusion proofs, signed checkpoints, quorum across organisations, anchoring to a public transparency log (Rekor) or immudb, S3 Object Lock for raw archive.
