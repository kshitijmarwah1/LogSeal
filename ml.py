"""Tiny burst detector (secondary feature). Needs: pip install scikit-learn numpy joblib
  python gen.py --dataset dataset && python ml.py train && python ml.py eval
Trained and evaluated on synthetic data from our own generator and features, so scores are optimistic by construction.

The threshold comes from an unseen benign validation block, not from the test set.
The console chart calls flag_windows(). Heavy imports stay inside functions so core tools remain stdlib-only.
"""
import calendar
import json
import math
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "model.joblib")
WIN = 10
TYPES = ["login_ok", "login_fail", "logout", "file_read", "file_write", "sudo", "config_change"]
EXTRA = ["window_total", "unique_src_ip", "unique_user", "fail_fraction", "max_ip_fail",
         "top_ip_fail_share", "fail_gap_mean", "fail_gap_std", "user_entropy", "ip_entropy",
         "fail_then_success"]
FEATURES = [f"count_{t}" for t in TYPES] + EXTRA
I_MAX_IP_FAIL = FEATURES.index("max_ip_fail")
VALIDATION_FRACTION = 0.2
ALARM_PERCENTILE = 1.0


def _t(ts):
    return calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))


def _entropy(values):
    n = len(values)
    if n < 2:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in Counter(values).values())


def _git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=HERE, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def featurize(events):
    """Return (window starts, feature matrix, window events). One row per 10 s window."""
    import numpy as np
    wins = {}
    for e in events:
        try:
            wins.setdefault(_t(e["ts"]) // WIN * WIN, []).append(e)
        except Exception:
            continue                                            # skip rows without a usable timestamp
    starts = sorted(wins)
    X = []
    for s in starts:
        ev = wins[s]
        n = len(ev)
        counts, ips, users = {}, [], []
        fail_by_ip, success_by_ip = {}, {}
        for e in ev:
            kind = e.get("event")
            counts[kind] = counts.get(kind, 0) + 1
            ip = e.get("src_ip") or "unknown"
            ips.append(ip)
            users.append(e.get("user") or "unknown")
            if kind == "login_fail":
                fail_by_ip.setdefault(ip, []).append(_t(e["ts"]))
            elif kind == "login_ok":
                success_by_ip.setdefault(ip, []).append(_t(e["ts"]))
        fails = [t for times in fail_by_ip.values() for t in times]
        fails.sort()
        gaps = [fails[i] - fails[i - 1] for i in range(1, len(fails))]
        max_ip_fail = max((len(times) for times in fail_by_ip.values()), default=0)
        nfail = len(fails)
        top_share = max_ip_fail / nfail if nfail else 0.0
        fail_then_success = 0
        for ip, fail_times in fail_by_ip.items():
            first_fail = min(fail_times)
            if any(t >= first_fail for t in success_by_ip.get(ip, [])):
                fail_then_success = 1
                break
        X.append([counts.get(t, 0) for t in TYPES]
                 + [n, len(set(ips)), len(set(users)), nfail / n if n else 0.0,
                    max_ip_fail, top_share,
                    statistics.fmean(gaps) if gaps else float(WIN),
                    statistics.pstdev(gaps) if len(gaps) > 1 else 0.0,
                    _entropy(users), _entropy(ips), fail_then_success])
    return starts, np.array(X, dtype=float), wins


def _load(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _wilson(k, n, z=1.96):
    """95% Wilson interval for a proportion. Small samples get a wide interval."""
    if not n:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, centre - radius), 4), round(min(1.0, centre + radius), 4)]


def _groups(starts, flags):
    """Group consecutive flagged window indexes. Adjacent windows share a 10 s edge."""
    groups, current = [], []
    for i, (s, flag) in enumerate(zip(starts, flags)):
        if not flag:
            if current:
                groups.append(current)
                current = []
            continue
        if current and s - starts[current[-1]] <= WIN:
            current.append(i)
        else:
            if current:
                groups.append(current)
            current = [i]
    if current:
        groups.append(current)
    return groups


def train(dataset="dataset", model_path=MODEL, quiet=False):
    import joblib
    import numpy as np
    import sklearn
    from sklearn.ensemble import IsolationForest

    starts, X, _ = featurize(_load(os.path.join(dataset, "train.jsonl")))
    cut = max(1, int(len(starts) * (1 - VALIDATION_FRACTION)))
    fit, val = X[:cut], X[cut:]
    model = IsolationForest(random_state=42).fit(fit)
    val_scores = model.score_samples(val)
    thr = float(np.percentile(val_scores, ALARM_PERCENTILE))  # unseen benign windows, not the test set
    rule_min_fails = max(3, int(val[:, I_MAX_IP_FAIL].max()) + 1)
    bundle = {"model": model, "threshold": thr, "feature_names": FEATURES,
              "train_windows": len(X), "fit_windows": len(fit), "validation_windows": len(val),
              "validation_flagged": int(sum(val_scores < thr)), "validation_max_ip_fail": int(val[:, I_MAX_IP_FAIL].max()),
              "rule_min_fails": rule_min_fails, "alarm_percentile": ALARM_PERCENTILE,
              "seed": 42, "sklearn_version": sklearn.__version__, "git_hash": _git_hash()}
    joblib.dump(bundle, model_path)
    if not quiet:
        print(f"trained on {len(X)} benign windows, fit {len(fit)}, validation {len(val)}, threshold {thr:.4f}")
    return bundle


def evaluate(dataset="dataset", model_path=MODEL):
    import joblib
    from sklearn.metrics import average_precision_score

    m = joblib.load(model_path)
    starts, X, wins = featurize(_load(os.path.join(dataset, "test.jsonl")))
    scores = m["model"].score_samples(X)
    flag = scores < m["threshold"]
    y = [any(e.get("label") for e in wins[s]) for s in starts]
    tp = int(sum(bool(f) and bool(t) for f, t in zip(flag, y)))
    fp = int(sum(bool(f) and not bool(t) for f, t in zip(flag, y)))
    fn = int(sum((not bool(f)) and bool(t) for f, t in zip(flag, y)))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    pr_auc = float(average_precision_score(y, -scores)) if 0 < sum(y) < len(y) else 0.0

    positive = _groups(starts, y)
    alarms = _groups(starts, flag)
    bursts_detected = int(sum(any(bool(flag[i]) for i in group) for group in positive))
    false_alarm_groups = int(sum(not any(y[i] for i in group) for group in alarms))

    rule_flag = X[:, I_MAX_IP_FAIL] >= m["rule_min_fails"]
    rule_tp = int(sum(bool(f) and bool(t) for f, t in zip(rule_flag, y)))
    rule_fp = int(sum(bool(f) and not bool(t) for f, t in zip(rule_flag, y)))
    rule_fn = int(sum((not bool(f)) and bool(t) for f, t in zip(rule_flag, y)))
    rp = rule_tp / (rule_tp + rule_fp) if rule_tp + rule_fp else 0.0
    rr = rule_tp / (rule_tp + rule_fn) if rule_tp + rule_fn else 0.0
    rule_bursts = int(sum(any(bool(rule_flag[i]) for i in group) for group in positive))
    rule_false_groups = int(sum(not any(y[i] for i in group) for group in _groups(starts, rule_flag)))

    out = {"data": "synthetic, own generator", "train_windows": int(m["train_windows"]),
           "test_windows": len(starts), "precision": round(p, 3), "recall": round(r, 3),
           "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
           "threshold": round(m["threshold"], 4),
           "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
    out["detail"] = {
        "features": FEATURES,
        "feature_count": len(FEATURES),
        "window": {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 4), "recall": round(r, 4),
                   "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "pr_auc": round(pr_auc, 4),
                   "precision_ci95": _wilson(tp, tp + fp), "recall_ci95": _wilson(tp, tp + fn)},
        "bursts": {"total": len(positive), "detected": bursts_detected,
                   "alarm_groups": len(alarms), "false_alarm_groups": false_alarm_groups},
        "rule_baseline": {"min_fails_per_ip": int(m["rule_min_fails"]),
                          "precision": round(rp, 4), "recall": round(rr, 4),
                          "f1": round(2 * rp * rr / (rp + rr), 4) if rp + rr else 0.0,
                          "bursts_detected": rule_bursts, "false_alarm_groups": rule_false_groups},
        "validation": {"fit_windows": int(m["fit_windows"]), "validation_windows": int(m["validation_windows"]),
                       "validation_flagged": int(m["validation_flagged"]), "alarm_percentile": ALARM_PERCENTILE},
        "model": {"seed": int(m["seed"]), "sklearn_version": m["sklearn_version"], "git_hash": m["git_hash"]},
        "sources": ["scikit-learn outlier detection: score_samples, contamination, average_precision_score",
                    "MITRE ATT&CK T1110.003: authentication failures from the same IP in a time window"],
    }
    return out


def flag_windows(events, model_path=MODEL):
    """-> [{"window_start","score","flagged"}] for the console chart."""
    import joblib
    with open(model_path, "rb") as f:
        m = joblib.load(f)
    starts, X, _ = featurize(events)
    if not len(starts):
        return []
    sc = m["model"].score_samples(X)
    return [{"window_start": datetime.fromtimestamp(s, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
             "score": float(v), "flagged": bool(v < m["threshold"])} for s, v in zip(starts, sc)]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eval"
    ds = sys.argv[2] if len(sys.argv) > 2 else "dataset"
    if cmd == "train":
        train(ds)
    else:
        result = evaluate(ds)
        detail = result.pop("detail")
        with open(os.path.join(HERE, "metrics.json"), "w") as f:
            json.dump(result, f, indent=2)
        with open(os.path.join(HERE, "metrics_detail.json"), "w") as f:
            json.dump(detail, f, indent=2)
        print(json.dumps(result, indent=2))
        print(json.dumps(detail["window"], indent=2))
        print(json.dumps(detail["bursts"], indent=2))
        print(json.dumps(detail["rule_baseline"], indent=2))
