"""Burst detector checks. Skipped when scikit-learn is not installed."""
import os
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gen  # noqa: E402
import ml   # noqa: E402

CONTRACT_KEYS = {"data", "train_windows", "test_windows", "precision", "recall", "f1", "threshold", "generated_at"}


class MLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import joblib  # noqa: F401
            import sklearn  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("scikit-learn is not installed")
        cls.tmp = tempfile.TemporaryDirectory(prefix="logseal_ml_")
        cls.dataset = os.path.join(cls.tmp.name, "dataset")
        cls.model = os.path.join(cls.tmp.name, "model.joblib")
        gen.write_dataset(cls.dataset, 7)
        ml.train(cls.dataset, cls.model, quiet=True)
        cls.result = ml.evaluate(cls.dataset, cls.model)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_feature_names_are_unique(self):
        self.assertEqual(len(ml.FEATURES), 18)
        self.assertEqual(len(set(ml.FEATURES)), 18)

    def test_wilson_interval_bounds_the_point_estimate(self):
        low, high = ml._wilson(12, 16)
        self.assertLess(low, 0.75)
        self.assertGreater(high, 0.75)
        self.assertLessEqual(high, 1.0)

    def test_adjacent_windows_merge_into_one_alarm_group(self):
        starts = [0, 10, 20, 40]
        self.assertEqual(ml._groups(starts, [True, True, False, True]), [[0, 1], [3]])

    def test_evaluate_keeps_the_contract_keys(self):
        self.assertTrue(CONTRACT_KEYS.issubset(self.result))
        detail = self.result["detail"]
        self.assertEqual(detail["feature_count"], 18)
        self.assertEqual(detail["bursts"]["total"], 6)
        self.assertGreaterEqual(detail["rule_baseline"]["min_fails_per_ip"], 3)
        self.assertEqual(detail["model"]["seed"], 42)

    def test_flag_windows_marks_a_seeded_burst(self):
        import random
        events = [dict(e) for _, e in gen.burst_events(random.Random(7), datetime(2026, 11, 25))]
        flagged = [w for w in ml.flag_windows(events, self.model) if w["flagged"]]
        self.assertTrue(flagged)


if __name__ == "__main__":
    unittest.main()
