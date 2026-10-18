"""Focused post-hoc safeguards; no real test-set evaluation."""
import unittest
from unittest.mock import Mock, patch
import numpy as np
from ml.src import explain_final_model as explain


class ExplainabilitySafeguards(unittest.TestCase):
    def test_metric_mismatch_stops_before_importance(self):
        with patch.object(explain, "reconstruct_final_model", side_effect=ValueError("STOP: mismatch")), patch.object(explain, "gain_values") as gain, patch.object(explain, "permutation_importance") as permutation:
            with self.assertRaisesRegex(ValueError, "STOP"):
                explain.calculate_importance()
            gain.assert_not_called()
            permutation.assert_not_called()

    def test_metric_equivalence_gate_rejects_discrepancy(self):
        reference = {"test_mae": 0.0, "test_rmse": 0.0, "test_r2": 1.0}
        with self.assertRaisesRegex(ValueError, "does not reproduce"):
            explain.verify_metrics(np.array([1., 2., 3.]), np.array([2., 3., 4.]), reference)
        result = explain.verify_metrics(np.array([1., 2., 3.]), np.array([1., 2., 3.]), reference)
        self.assertTrue(result["passed"])

    def test_gain_mapping_and_zero_fill(self):
        named = Mock(feature_names=["Appliances", "lights", "T1"])
        named.get_score.return_value = {"lights": 3.0, "Appliances": 6.0}
        np.testing.assert_array_equal(explain.gain_values(named, named.feature_names), [6., 3., 0.])
        named.get_score.assert_called_once_with(importance_type="gain")
        positional = Mock(feature_names=None)
        positional.get_score.return_value = {"f1": 2.0}
        np.testing.assert_array_equal(explain.gain_values(positional, ["Appliances", "lights"]), [0., 2.])
        positional.get_score.return_value = {"f2": 2.0}
        with self.assertRaisesRegex(ValueError, "Unknown booster"):
            explain.gain_values(positional, ["Appliances", "lights"])

    def test_documented_groups_cover_schema(self):
        features = explain.read_json(explain.RESULTS / "feature_schema.json")["model_feature_columns"]
        groups = explain.feature_groups(features)
        self.assertEqual(len(groups), 42)
        self.assertEqual(groups["T6"], "Outdoor/weather")
        self.assertEqual(groups["RH_6"], "Outdoor/weather")
        self.assertEqual(groups["T7"], "Indoor temperature")
        self.assertEqual(groups["lights"], "Lighting")
        with self.assertRaisesRegex(ValueError, "no documented group"):
            explain.feature_groups(["unknown"])

    def test_existing_result_blocks_recomputation(self):
        with patch.object(explain, "RESULT_PATH") as path, patch.object(explain, "calculate_importance") as calculate:
            path.exists.return_value = True
            with self.assertRaises(FileExistsError):
                explain.run_phase12()
            calculate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
