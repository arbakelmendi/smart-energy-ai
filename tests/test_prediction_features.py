"""Pure deterministic feature math and latest-window readiness; fixture values only."""
from datetime import datetime, timedelta, timezone
import json, math, random
import unittest
from unittest.mock import patch
import numpy as np
from backend.db_models import RAW_MEASUREMENT_COLUMNS
from backend.prediction_features import (assess_history,build_latest_feature_row,HistoryNotReady,
    REQUIRED_OBSERVATIONS,REQUIRED_HISTORY_INTERVALS,ordered_feature_names,FeatureContractUnavailable)
from ml.src.feature_engineering import engineer_origin_features


def history(count=1009, start=datetime(2024,1,1)):
    return [{"timestamp":start+timedelta(minutes=10*i),
        **{name:float(i % 53 + i*.5) if name=='Appliances' else 1.5 for name in RAW_MEASUREMENT_COLUMNS}}
        for i in range(count)]

class PureFeatureTests(unittest.TestCase):
    def test_exact_minimum_and_ordered_contract(self):
        self.assertEqual(REQUIRED_HISTORY_INTERVALS,1008);self.assertEqual(REQUIRED_OBSERVATIONS,1009)
        row=build_latest_feature_row(history())
        self.assertEqual(row.feature_names,ordered_feature_names());self.assertEqual(len(row.values),42)
        self.assertEqual(row.as_frame().columns.tolist(),list(row.feature_names))
        self.assertEqual(tuple(row.ordered_mapping()),row.feature_names)
        # Existing production validator accepts directly; no model load or predict.
        from ml.src.model_inference import validate_feature_frame
        frame=row.as_frame();self.assertIs(validate_feature_frame(frame),frame)

    def test_current_appliances_and_all_lags_origin_relative(self):
        raw=history();values=build_latest_feature_row(raw).ordered_mapping()
        self.assertEqual(values['Appliances'],raw[-1]['Appliances'])
        for lag in [1,6,144,1008]:self.assertEqual(values[f'appliances_lag_{lag}'],raw[-1-lag]['Appliances'])

    def test_rolling_full_current_included_sample_std(self):
        raw=history();values=build_latest_feature_row(raw).ordered_mapping()
        for label,n in [('1h',6),('24h',144)]:
            energy=np.array([r['Appliances'] for r in raw[-n:]])
            self.assertAlmostEqual(values[f'appliances_roll_mean_{label}'],energy.mean(),places=10)
            self.assertAlmostEqual(values[f'appliances_roll_std_{label}'],energy.std(ddof=1),places=10)
            self.assertNotAlmostEqual(values[f'appliances_roll_std_{label}'],energy.std(ddof=0),places=6)

    def test_temporal_and_cycles_use_integer_hour_and_weekday(self):
        raw=history(start=datetime(2024,1,6,12,35));v=build_latest_feature_row(raw).ordered_mapping()
        self.assertEqual([v[k] for k in ['hour','day_of_week','month','is_weekend']],[12,5,1,1])
        for key,expected in [('hour_sin',math.sin(2*math.pi*12/24)),('hour_cos',math.cos(2*math.pi*12/24)),('dow_sin',math.sin(2*math.pi*5/7)),('dow_cos',math.cos(2*math.pi*5/7))]:self.assertAlmostEqual(v[key],expected,places=15)

    def test_no_history_one_and_nearly_enough(self):
        for count,code in [(0,'NO_MEASUREMENTS'),(1,'INSUFFICIENT_HISTORY'),(1008,'INSUFFICIENT_HISTORY')]:
            result=assess_history(history(count));self.assertFalse(result.readiness.ready)
            self.assertEqual(result.readiness.reason_code,code);self.assertIsNone(result.feature_row)
            self.assertEqual(result.readiness.continuous_intervals_available,max(0,count-1))

    def test_first_valid_and_extra_history(self):
        for count in [1009,1010,1500]:
            result=assess_history(history(count));self.assertTrue(result.readiness.ready)
            self.assertEqual(result.readiness.continuous_intervals_available,1008)
            self.assertEqual(result.feature_row.feature_timestamp,history(count)[-1]['timestamp'])

    def test_gap_early_and_near_latest_and_no_fill(self):
        for index in [1,1007]:
            raw=history();del raw[index];r=assess_history(raw)
            self.assertEqual(r.readiness.reason_code,'LATEST_WINDOW_HAS_GAPS');self.assertIsNone(r.feature_row)
            self.assertEqual(r.readiness.first_gap.actual_interval_seconds,1200)

    def test_large_count_but_required_window_gap(self):
        raw=history(1500);del raw[1000];r=assess_history(raw)
        self.assertEqual(r.readiness.measurement_count,1499);self.assertFalse(r.readiness.ready)
        self.assertEqual(r.readiness.reason_code,'LATEST_WINDOW_HAS_GAPS')

    def test_old_gaps_and_invalid_old_raw_do_not_block(self):
        raw=history(1500);raw[0]['T1']=float('nan');del raw[1]
        self.assertTrue(assess_history(raw).readiness.ready)

    def test_out_of_order_and_descending_input(self):
        raw=history(1100);expected=build_latest_feature_row(raw)
        self.assertEqual(build_latest_feature_row(list(reversed(raw))),expected)
        random.Random(42).shuffle(raw);self.assertEqual(build_latest_feature_row(raw),expected)

    def test_missing_invalid_nonfinite_raw(self):
        for value in [None,'1',True,float('nan'),float('inf'),-float('inf')]:
            raw=history();raw[500]['T1']=value
            self.assertEqual(assess_history(raw).readiness.reason_code,'INVALID_RAW_DATA')
        raw=history();del raw[-1]['RH_9'];self.assertFalse(assess_history(raw).readiness.ready)

    def test_duplicate_timestamps_including_boundary(self):
        for index in [0,500,1008]:
            raw=history();raw.append(raw[index].copy())
            self.assertEqual(assess_history(raw).readiness.reason_code,'INVALID_RAW_DATA')

    def test_corrupt_or_aware_timestamp(self):
        for value in [None,'bad',datetime(2024,1,1,tzinfo=timezone.utc)]:
            raw=history();raw[-1]['timestamp']=value
            self.assertEqual(assess_history(raw).readiness.reason_code,'INVALID_RAW_DATA')

    def test_new_latest_gap_no_fallback_and_restoration(self):
        raw=history();latest=raw[-1]['timestamp'];extra={**raw[-1],'timestamp':latest+timedelta(minutes=20)}
        r=assess_history([*raw,extra]);self.assertFalse(r.readiness.ready)
        self.assertEqual(r.readiness.latest_measurement_timestamp,extra['timestamp'])
        self.assertEqual(r.readiness.continuous_intervals_available,0)
        restored=[*raw,{**raw[-1],'timestamp':latest+timedelta(minutes=10)},extra]
        self.assertTrue(assess_history(restored).readiness.ready)

    def test_no_target_required_or_exposed(self):
        raw=history();first=build_latest_feature_row(raw)
        for row in raw:row['target_appliances_next']=float('inf')
        self.assertEqual(build_latest_feature_row(raw),first)
        self.assertNotIn('target_appliances_next',first.feature_names)

    def test_no_future_in_shared_origin_calculations(self):
        import pandas as pd
        raw=history(1010);source=pd.DataFrame(raw).rename(columns={'timestamp':'date'})
        before=engineer_origin_features(source).iloc[1008]
        source.loc[1009,'Appliances']=1e9
        after=engineer_origin_features(source).iloc[1008]
        np.testing.assert_array_equal(before[list(ordered_feature_names())].to_numpy(),after[list(ordered_feature_names())].to_numpy())

    def test_raises_structured_not_ready(self):
        with self.assertRaises(HistoryNotReady) as error:build_latest_feature_row(history(1008))
        self.assertEqual(error.exception.readiness.reason_code,'INSUFFICIENT_HISTORY')

    def test_contract_missing_or_mismatch_fails_closed(self):
        with patch('backend.prediction_features.SCHEMA_PATH') as path:
            path.read_bytes.side_effect=OSError('test-only')
            with self.assertRaises(FeatureContractUnavailable):assess_history(history())

    def test_extreme_finite_values_cannot_produce_invalid_features(self):
        raw=history()
        for index,row in enumerate(raw):row['Appliances']=1e308 if index%2 else -1e308
        result=assess_history(raw)
        self.assertFalse(result.readiness.ready);self.assertIsNone(result.feature_row)

    def test_real_uci_db_parity_and_unchanged_research_export(self):
        from verify_feature_parity import verify
        evidence=verify()
        self.assertTrue(evidence['passed']);self.assertTrue(evidence['research_export_byte_identical'])
        self.assertEqual(len(evidence['parity_points']),3)
