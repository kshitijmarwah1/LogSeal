#!/usr/bin/env python3
"""Run the three demo acts against real vaults and assert the result.

This is the automated version of the rehearsal:
  1. live green
  2. a judge edits one line          -> local alarm, vaults confirm
  3. a root attacker rewrites both   -> server green, vaults red
  4. a root attacker wipes both      -> server green, vaults ahead
  5. reset                           -> green again

Run: python scripts/demo_check.py
Exit 0 only when every act behaves as docs/08_DEMO_AND_PITCH.md says.
"""
import os
import random
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import attack    # noqa: E402
import gen       # noqa: E402
import seal      # noqa: E402
import verify    # noqa: E402
import witness   # noqa: E402

failures = []


def check(name, condition, detail=""):
    print(("PASS  " if condition else "FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not condition:
        failures.append(name)


def free_port():
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_vault(name, folder):
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "witness.py"),
                             "--name", name, "--port", str(port), "--allow-reset", "--dir", folder],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        if witness.head(url, 0.2) is not None:
            return proc, url
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    proc.terminate()
    raise RuntimeError(f"{name} did not start")


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def write_bytes(path, data):
    with open(path, "wb") as f:
        f.write(data)


def main():
    tmp = tempfile.TemporaryDirectory(prefix="logseal_demo_")
    folder = tmp.name
    v1 = v2 = None
    try:
        v1, u1 = start_vault("Vault 1", folder)
        v2, u2 = start_vault("Vault 2", folder)
        cfg = {
            "log_path": os.path.join(folder, "app.log.jsonl"),
            "ledger_path": os.path.join(folder, "ledger.jsonl"),
            "hmac_key_env": "LOGSEAL_KEY",
            "hmac_key_default": "demo-check-key",
            "witnesses": [{"name": "Vault 1", "url": u1}, {"name": "Vault 2", "url": u2}],
            "witness_timeout_s": 0.6,
            "pending_grace_s": 2,
        }
        os.environ[cfg["hmac_key_env"]] = cfg["hmac_key_default"]

        print("\nAct 1: live events, all machines agree")
        rng = random.Random(11)
        for _ in range(60):
            seal.append(gen.make_event(rng), cfg)
        result = verify.verify(cfg)
        check("status is OK", result["status"] == "OK", result["status"])
        check("three machines are present", len(result["nodes"]) == 3, str(len(result["nodes"])))
        check("all three agree", all(n["agrees"] is True for n in result["nodes"]))
        check("server and vaults hold 60 records",
              all(n["head_seq"] == 60 for n in result["nodes"]), str([n["head_seq"] for n in result["nodes"]]))

        print("\nAct 2: a judge edits one line")
        clean_log, clean_ledger = read_bytes(cfg["log_path"]), read_bytes(cfg["ledger_path"])
        lines = clean_log.rstrip(b"\n").split(b"\n")
        lines[23] = lines[23].replace(b"srv-01", b"srv-02", 1)
        write_bytes(cfg["log_path"], b"\n".join(lines) + b"\n")
        result = verify.verify(cfg)
        check("status is TAMPERED", result["status"] == "TAMPERED", result["status"])
        finding = result["findings"][0] if result["findings"] else {}
        check("class is EDIT", finding.get("class") == "EDIT", str(finding.get("class")))
        check("record 24 is named", finding.get("seq") == 24, str(finding.get("seq")))
        check("both vaults confirm the original",
              set(finding.get("confirmed_by") or []) == {"Vault 1", "Vault 2"}, str(finding.get("confirmed_by")))
        check("server tile is red, vault tiles green",
              result["nodes"][0]["agrees"] is False and all(n["agrees"] for n in result["nodes"][1:]))
        write_bytes(cfg["log_path"], clean_log)
        write_bytes(cfg["ledger_path"], clean_ledger)
        check("restore returns to green", verify.verify(cfg)["status"] == "OK")

        print("\nAct 3: a root attacker rewrites the log and the ledger with the key")
        attack.rewrite(cfg, 20, "srv-01", "mallory")
        check("server alone says OK", verify.verify(cfg, use_witnesses=False)["status"] == "OK")
        result = verify.verify(cfg)
        conflict = next((f for f in result["findings"] if f["class"] == "WITNESS_CONFLICT"), {})
        check("status is TAMPERED", result["status"] == "TAMPERED", result["status"])
        check("WITNESS_CONFLICT at record 20", conflict.get("seq") == 20, str(conflict.get("seq")))
        check("server tile stays green", result["nodes"][0]["agrees"] is True)
        check("both vault tiles are red", all(n["agrees"] is False for n in result["nodes"][1:]))
        attack.restore(cfg)
        check("restore returns to green", verify.verify(cfg)["status"] == "OK")

        print("\nAct 4: a root attacker wipes the tail of both files")
        attack.wipe(cfg, 30)
        check("server alone says OK", verify.verify(cfg, use_witnesses=False)["status"] == "OK")
        result = verify.verify(cfg)
        ahead = next((f for f in result["findings"] if f["class"] == "WITNESS_AHEAD"), {})
        check("status is TAMPERED", result["status"] == "TAMPERED", result["status"])
        check("WITNESS_AHEAD at record 31", ahead.get("seq") == 31, str(ahead.get("seq")))
        attack.restore(cfg)
        check("restore returns to green", verify.verify(cfg)["status"] == "OK")

        print("\nAct 5: reset for the next run")
        started = time.perf_counter()
        seal.reset(cfg)
        elapsed = time.perf_counter() - started
        result = verify.verify(cfg)
        check("status is OK after reset", result["status"] == "OK", result["status"])
        check("vaults are empty", all(witness.head(w["url"], 0.5)["count"] == 0 for w in cfg["witnesses"]))
        check("reset is under 30 seconds", elapsed < 30, f"{elapsed:.2f} s")
    finally:
        if v1:
            stop(v1)
        if v2:
            stop(v2)
        tmp.cleanup()

    print()
    if failures:
        print(f"{len(failures)} FAILED: " + ", ".join(failures))
        return 1
    print("ALL DEMO ACTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
