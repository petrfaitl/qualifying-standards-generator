"""
Unit tests for multi-year event matching and statistical combinations.
"""

import unittest
from swim_standards.models import SwimmerResult, EventInfo, EventResults
from swim_standards.aggregator import MultiYearAggregator


class TestAggregator(unittest.TestCase):

    def setUp(self):
        self.ev_info_2024 = EventInfo(
            event_number=13,
            raw_title="Event 13 Girls 12 & Over 50 SC Meter Freestyle Y8 Girls",
            gender="Girls",
            school_year="Y8",
            age_group="12 & Over",
            distance=50,
            stroke="Freestyle"
        )
        self.ev_info_2026 = EventInfo(
            event_number=13,
            raw_title="Event 13 Girls 12 & Over 50 SC Meter Freestyle Y8 Girls",
            gender="Girls",
            school_year="Y8",
            age_group="12 & Over",
            distance=50,
            stroke="Freestyle"
        )

    def _make_swimmers(self, base_time: float, eighth_time: float) -> list:
        step = (eighth_time - base_time) / 7.0
        return [
            SwimmerResult(rank=i, name=f"S{i}", time_seconds=round(base_time + (i - 1) * step, 2))
            for i in range(1, 9)
        ]

    def test_multi_year_combinations(self):
        # 2024 8th place: 36.00s
        # 2025 8th place: 34.00s
        # 2026 8th place: 38.00s
        swimmers_2024 = self._make_swimmers(30.0, 36.00)
        swimmers_2025 = self._make_swimmers(29.0, 34.00)
        swimmers_2026 = self._make_swimmers(31.0, 38.00)

        d2024 = [EventResults(event_info=self.ev_info_2024, meet_year=2024, swimmers=swimmers_2024)]
        d2025 = [EventResults(event_info=self.ev_info_2024, meet_year=2025, swimmers=swimmers_2025)]
        d2026 = [EventResults(event_info=self.ev_info_2026, meet_year=2026, swimmers=swimmers_2026)]

        datasets = [d2024, d2025, d2026]

        # Test Average: (36 + 34 + 38) / 3 = 36.00
        agg_avg = MultiYearAggregator(combine_method="average")
        results_avg = agg_avg.aggregate_meets(datasets)
        self.assertEqual(len(results_avg), 1)
        self.assertEqual(results_avg[0].standard_seconds, 36.00)
        self.assertEqual(results_avg[0].standard_time_str, "36.00")
        self.assertAlmostEqual(results_avg[0].std_dev_seconds, 2.00, places=2)

        # Test Median: median([34, 36, 38]) = 36.00
        agg_med = MultiYearAggregator(combine_method="median")
        results_med = agg_med.aggregate_meets(datasets)
        self.assertEqual(results_med[0].standard_seconds, 36.00)

        # Test Fastest: min([34, 36, 38]) = 34.00
        agg_fast = MultiYearAggregator(combine_method="fastest")
        results_fast = agg_fast.aggregate_meets(datasets)
        self.assertEqual(results_fast[0].standard_seconds, 34.00)

    def test_custom_target_rank_10(self):
        # 8 swimmers per meet, target rank 10
        swimmers_2024 = self._make_swimmers(30.0, 37.00)
        d2024 = [EventResults(event_info=self.ev_info_2024, meet_year=2024, swimmers=swimmers_2024)]

        agg = MultiYearAggregator(target_rank=10, combine_method="average")
        results = agg.aggregate_meets([d2024])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].annual_results[2024].is_extrapolated)
        self.assertGreater(results[0].standard_seconds, 37.00)


if __name__ == '__main__':
    unittest.main()
