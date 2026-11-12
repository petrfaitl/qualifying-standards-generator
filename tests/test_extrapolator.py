"""
Unit tests for outlier gap detection and extrapolation algorithms.
"""

import unittest
from swim_standards.models import SwimmerResult, EventInfo, EventResults
from swim_standards.extrapolator import (
    detect_outliers,
    extrapolate_time,
    evaluate_event
)


class TestExtrapolator(unittest.TestCase):

    def setUp(self):
        self.sample_info = EventInfo(
            event_number=1,
            raw_title="Event 1 Girls 12 & Over 100 SC Meter Breaststroke Y8 Girls",
            gender="Girls",
            school_year="Y8",
            age_group="12 & Over",
            distance=100,
            stroke="Breaststroke"
        )

    def test_complete_top8_field(self):
        # 8 uniformly distributed finishers
        swimmers = [
            SwimmerResult(rank=1, name="S1", time_seconds=90.0),
            SwimmerResult(rank=2, name="S2", time_seconds=92.0),
            SwimmerResult(rank=3, name="S3", time_seconds=93.5),
            SwimmerResult(rank=4, name="S4", time_seconds=95.0),
            SwimmerResult(rank=5, name="S5", time_seconds=97.0),
            SwimmerResult(rank=6, name="S6", time_seconds=98.5),
            SwimmerResult(rank=7, name="S7", time_seconds=100.0),
            SwimmerResult(rank=8, name="S8", time_seconds=102.0),
        ]
        ev_results = EventResults(event_info=self.sample_info, meet_year=2024, swimmers=swimmers)
        res = evaluate_event(ev_results, target_rank=8, method="step-average")

        self.assertFalse(res.is_extrapolated)
        self.assertEqual(res.target_time_seconds, 102.0)
        self.assertEqual(res.method_used, "direct")
        self.assertEqual(res.valid_count, 8)
        self.assertEqual(len(res.pruned_ranks), 0)

    def test_tied_eighth_place(self):
        # Tied 8th place
        swimmers = [
            SwimmerResult(rank=i, name=f"S{i}", time_seconds=30.0 + i) for i in range(1, 8)
        ] + [
            SwimmerResult(rank=8, name="S8a", time_seconds=38.0, is_tied=True),
            SwimmerResult(rank=8, name="S8b", time_seconds=38.0, is_tied=True),
        ]
        ev_results = EventResults(event_info=self.sample_info, meet_year=2024, swimmers=swimmers)
        res = evaluate_event(ev_results, target_rank=8)

        self.assertFalse(res.is_extrapolated)
        self.assertEqual(res.target_time_seconds, 38.0)
        self.assertEqual(res.method_used, "direct")

    def test_extreme_tail_outlier_blowout_2024_ev11(self):
        # Actual 2024 Event 11 numbers: 5th is 100.35, 6th is 134.19 (+33.84s blowout)
        swimmers = [
            SwimmerResult(rank=1, name="Jury, Rylee", time_seconds=81.10),
            SwimmerResult(rank=2, name="Applegate, Isabella", time_seconds=88.11),
            SwimmerResult(rank=3, name="Ellis, Anna", time_seconds=95.09),
            SwimmerResult(rank=4, name="Scott, Nizzy", time_seconds=97.03),
            SwimmerResult(rank=5, name="McHardy, Tamsin", time_seconds=100.35),
            SwimmerResult(rank=6, name="Jones, Kyla", time_seconds=134.19),
        ]
        ev_results = EventResults(event_info=self.sample_info, meet_year=2024, swimmers=swimmers)
        res = evaluate_event(ev_results, target_rank=8, method="step-average", gap_threshold=2.0)

        self.assertTrue(res.is_extrapolated)
        self.assertEqual(res.valid_count, 5)
        self.assertEqual(res.pruned_ranks, [6])
        self.assertIn("Pruned Outlier at Rank 6", res.audit_note)

        # Expected calculation:
        # m = 5, T_1 = 81.10, T_5 = 100.35
        # mean_step = (100.35 - 81.10) / 4 = 4.8125
        # T_8 = 100.35 + 3 * 4.8125 = 114.7875 -> 114.79
        self.assertAlmostEqual(res.target_time_seconds, 114.79, places=2)

    def test_sparse_field_2024_ev4(self):
        # 2 swimmers (Collins 107.48, Latimer 113.77)
        swimmers = [
            SwimmerResult(rank=1, name="Collins, Jack", time_seconds=107.48),
            SwimmerResult(rank=2, name="Latimer, Isaia", time_seconds=113.77),
        ]
        ev_results = EventResults(event_info=self.sample_info, meet_year=2024, swimmers=swimmers)

        # Test step-average
        res_step = evaluate_event(ev_results, target_rank=8, method="step-average")
        self.assertTrue(res_step.is_extrapolated)
        self.assertEqual(res_step.valid_count, 2)
        # mean_step = 113.77 - 107.48 = 6.29
        # T_8 = 113.77 + 6 * 6.29 = 151.51
        self.assertAlmostEqual(res_step.target_time_seconds, 151.51, places=2)

        # Test linear-trend
        res_linear = evaluate_event(ev_results, target_rank=8, method="linear-trend")
        self.assertTrue(res_linear.is_extrapolated)
        self.assertAlmostEqual(res_linear.target_time_seconds, 151.51, places=2)

        # Test percent-increment
        res_pct = evaluate_event(ev_results, target_rank=8, method="percent-increment", percent_margin=0.03)
        self.assertTrue(res_pct.is_extrapolated)
        self.assertGreater(res_pct.target_time_seconds, 113.77)

    def test_target_rank_10(self):
        # 8 swimmers evaluated for 10th rank standard
        swimmers = [
            SwimmerResult(rank=i, name=f"S{i}", time_seconds=50.0 + i * 2.0) for i in range(1, 9)
        ]
        ev_results = EventResults(event_info=self.sample_info, meet_year=2024, swimmers=swimmers)
        res = evaluate_event(ev_results, target_rank=10, method="step-average")

        self.assertTrue(res.is_extrapolated)
        # T_8 = 66.0, T_1 = 52.0. mean_step = (66 - 52) / 7 = 2.0.
        # T_10 = 66.0 + 2 * 2.0 = 70.0
        self.assertAlmostEqual(res.target_time_seconds, 70.0, places=2)

    def test_extrapolation_monotonicity(self):
        # Projected time must always be greater than valid finisher times
        swimmers = [
            SwimmerResult(rank=1, name="S1", time_seconds=20.0),
            SwimmerResult(rank=2, name="S2", time_seconds=21.0),
            SwimmerResult(rank=3, name="S3", time_seconds=21.5),
        ]
        for m in ["step-average", "linear-trend", "percent-increment"]:
            t_proj = extrapolate_time(swimmers, target_rank=8, method=m)
            self.assertGreater(t_proj, 21.5)


if __name__ == '__main__':
    unittest.main()
