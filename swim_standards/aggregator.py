"""
Multi-year event alignment and statistical combinations engine.
"""

from typing import List, Dict, Optional
import numpy as np
from .models import EventResults, ExtrapolationResult, AggregatedStandard, EventInfo
from .extrapolator import evaluate_event
from .parser import seconds_to_time


class MultiYearAggregator:
    """
    Synthesizes qualifying standards across multiple annual meet workbooks.
    """

    def __init__(
        self,
        target_rank: int = 8,
        combine_method: str = "average",
        extrapolate_method: str = "step-average",
        gap_threshold: float = 2.0,
        percent_margin: float = 0.03
    ):
        if combine_method not in ["average", "median", "fastest"]:
            raise ValueError(f"Unknown combine method: {combine_method}. Choose from 'average', 'median', 'fastest'.")
        if extrapolate_method not in ["step-average", "linear-trend", "percent-increment"]:
            raise ValueError(f"Unknown extrapolate method: {extrapolate_method}.")

        self.target_rank = target_rank
        self.combine_method = combine_method
        self.extrapolate_method = extrapolate_method
        self.gap_threshold = gap_threshold
        self.percent_margin = percent_margin

    def aggregate_meets(self, meet_datasets: List[List[EventResults]]) -> List[AggregatedStandard]:
        """
        Takes datasets from multiple years, aligns corresponding events,
        evaluates annual target times, and aggregates them into multi-year standards.
        """
        # Map canonical_name -> dict of meet_year -> EventResults
        event_groups: Dict[str, Dict[int, EventResults]] = {}
        canonical_info_map: Dict[str, EventInfo] = {}

        for dataset in meet_datasets:
            for event in dataset:
                c_name = event.event_info.canonical_name
                canonical_info_map[c_name] = event.event_info
                if c_name not in event_groups:
                    event_groups[c_name] = {}
                event_groups[c_name][event.meet_year] = event

        aggregated_standards: List[AggregatedStandard] = []

        for c_name, year_dict in event_groups.items():
            ev_info = canonical_info_map[c_name]
            annual_evaluations: Dict[int, ExtrapolationResult] = {}
            target_times_sec: List[float] = []

            for yr in sorted(year_dict.keys()):
                ev_res = year_dict[yr]
                extrap_res = evaluate_event(
                    ev_res,
                    target_rank=self.target_rank,
                    method=self.extrapolate_method,
                    gap_threshold=self.gap_threshold,
                    percent_margin=self.percent_margin
                )
                annual_evaluations[yr] = extrap_res
                if extrap_res.target_time_seconds > 0:
                    target_times_sec.append(extrap_res.target_time_seconds)

            if not target_times_sec:
                standard_sec = 0.0
                std_dev = 0.0
            else:
                if self.combine_method == "average":
                    standard_sec = float(np.mean(target_times_sec))
                elif self.combine_method == "median":
                    standard_sec = float(np.median(target_times_sec))
                elif self.combine_method == "fastest":
                    standard_sec = float(np.min(target_times_sec))
                else:
                    standard_sec = float(np.mean(target_times_sec))

                if len(target_times_sec) > 1:
                    std_dev = float(np.std(target_times_sec, ddof=1))
                else:
                    std_dev = 0.0

            standard_sec = round(standard_sec, 2)
            std_dev = round(std_dev, 2)

            agg = AggregatedStandard(
                event_key=c_name,
                event_info=ev_info,
                target_rank=self.target_rank,
                standard_seconds=standard_sec,
                standard_time_str=seconds_to_time(standard_sec),
                combination_method=self.combine_method,
                annual_results=annual_evaluations,
                std_dev_seconds=std_dev
            )
            aggregated_standards.append(agg)

        # Sort events by standard event order
        aggregated_standards.sort(key=lambda s: s.event_info.event_order_key)
        return aggregated_standards
