#!/usr/bin/env python3
"""Run the burst detector on several generated datasets and report the range.

One seed can flatter a model. This script trains and evaluates five seeds in
temporary folders, then prints mean and range for the main scores. It also
reports the simple per-IP rule baseline. It writes metrics_sweep.json.
"""
import json
import os
import statistics
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gen  # noqa: E402
import ml   # noqa: E402

SEEDS = [41, 42, 43, 44, 45]
FIELDS = ["precision", "recall", "f1"]


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="logseal_sweep_") as tmp:
        for seed in SEEDS:
            dataset = os.path.join(tmp, f"dataset_{seed}")
            model = os.path.join(tmp, f"model_{seed}.joblib")
            gen.write_dataset(dataset, seed)
            ml.train(dataset, model, quiet=True)
            result = ml.evaluate(dataset, model)
            d = result["detail"]
            rows.append({"seed": seed, "precision": result["precision"], "recall": result["recall"],
                         "f1": result["f1"], "pr_auc": d["window"]["pr_auc"],
                         "bursts_detected": d["bursts"]["detected"], "bursts_total": d["bursts"]["total"],
                         "false_alarm_groups": d["bursts"]["false_alarm_groups"],
                         "rule_f1": d["rule_baseline"]["f1"]})
            print(f"seed {seed}: precision {result['precision']}, recall {result['recall']}, "
                  f"f1 {result['f1']}, rule f1 {d['rule_baseline']['f1']}")
    summary = {"seeds": SEEDS,
               "mean": {f: round(statistics.fmean(r[f] for r in rows), 4) for f in FIELDS + ["pr_auc", "rule_f1"]},
               "min": {f: min(r[f] for r in rows) for f in FIELDS + ["pr_auc", "rule_f1"]},
               "max": {f: max(r[f] for r in rows) for f in FIELDS + ["pr_auc", "rule_f1"]},
               "bursts_detected": sum(r["bursts_detected"] for r in rows),
               "bursts_total": sum(r["bursts_total"] for r in rows),
               "false_alarm_groups": sum(r["false_alarm_groups"] for r in rows),
               "data": "synthetic, own generator, five seeds",
               "rows": rows}
    with open(os.path.join(ROOT, "metrics_sweep.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
