"""
Outlier gap detection and n-th position extrapolation algorithms.
"""

from typing import List, Tuple, Optional
import numpy as np
from .models import SwimmerResult, EventResults, ExtrapolationResult
from .parser import seconds_to_time


def detect_outliers(
    swimmers: List[SwimmerResult],
    gap_threshold: float = 2.0,
    min_gap_floor: Optional[float] = None
) -> Tuple[List[SwimmerResult], List[int]]:
    """
    Identifies anomalous time blowouts between consecutive swimmers and prunes
    unrepresentative tail drop-offs.

    Returns:
        (valid_swimmers, pruned_ranks)
    """
    if len(swimmers) < 3:
        return list(swimmers), []

    # Ensure swimmers are strictly sorted by finishing time
    sorted_swimmers = sorted(swimmers, key=lambda s: s.time_seconds)
    times = [s.time_seconds for s in sorted_swimmers]
    k = len(times)
    diffs = [round(times[i] - times[i - 1], 2) for i in range(1, k)]

    # Check for outlier blowout starting at step i (between rank i and rank i+1)
    for i in range(1, len(diffs)):
        step = diffs[i]
        prev_steps = diffs[:i]

        # Median of preceding steps (filter zero steps from ties if possible)
        positive_prev = [d for d in prev_steps if d > 0]
        med_prev = float(np.median(positive_prev)) if positive_prev else 1.0

        # Dynamic floor buffer proportional to race duration (minimum 3.5s or 12% of time)
        if min_gap_floor is not None:
            floor = min_gap_floor
        else:
            floor = max(3.5, 0.12 * times[i - 1])

        cutoff = max(gap_threshold * med_prev, floor)

        if step > cutoff:
            # Distinguish an isolated tail blowout from a pack following breakaway leaders
            remaining_count = k - (i + 1)
            if remaining_count >= 2:
                # Check if the subsequent swimmers form a tight pack
                rem_steps = diffs[i + 1:]
                positive_rem = [d for d in rem_steps if d > 0]
                med_rem = float(np.median(positive_rem)) if positive_rem else 0.5
                if med_rem < step * 0.4:
                    # Swimmers after this jump are bunched together (breakaway leader pack)
                    continue

            # This is an unrepresentative tail blowout; prune everything from i+1 onwards
            valid_swimmers = sorted_swimmers[: i + 1]
            pruned_ranks = [s.rank for s in sorted_swimmers[i + 1:]]
            return valid_swimmers, pruned_ranks

    return list(sorted_swimmers), []


def extrapolate_time(
    valid_swimmers: List[SwimmerResult],
    target_rank: int,
    method: str = "step-average",
    percent_margin: float = 0.03
) -> float:
    """
    Extrapolates the qualifying time for target_rank from valid_swimmers.

    Methods:
        - 'step-average': T_n = T_m + (n - m) * mean_step
        - 'linear-trend': Ordinary least-squares regression line
        - 'percent-increment': T_n = T_m * (1 + p)^(n - m)
    """
    if not valid_swimmers:
        raise ValueError("Cannot extrapolate from empty swimmers list")

    sorted_swimmers = sorted(valid_swimmers, key=lambda s: s.time_seconds)
    m = len(sorted_swimmers)
    t_m = sorted_swimmers[-1].time_seconds
    t_1 = sorted_swimmers[0].time_seconds

    if m >= target_rank:
        return sorted_swimmers[target_rank - 1].time_seconds

    steps_to_target = target_rank - m

    if method == "step-average":
        if m > 1:
            mean_step = (t_m - t_1) / (m - 1)
        else:
            mean_step = max(0.05 * t_m, 1.5)
        # Apply safety sanity bound (cannot exceed 15% of last time per step)
        mean_step = min(mean_step, 0.15 * t_m)
        mean_step = max(mean_step, 0.10)
        projected = t_m + steps_to_target * mean_step

    elif method == "linear-trend":
        if m >= 2:
            ranks = np.array([i + 1 for i in range(m)], dtype=float)
            times = np.array([s.time_seconds for s in sorted_swimmers], dtype=float)
            # Ordinary least squares
            poly = np.polyfit(ranks, times, deg=1)
            slope, intercept = poly[0], poly[1]
            # Ensure monotonicity: slope must be non-negative
            if slope <= 0:
                slope = max(0.03 * t_m, 1.0)
            slope = min(slope, 0.15 * t_m)
            projected = slope * target_rank + intercept
            # Monotonicity guard: projected cannot be faster than t_m
            projected = max(projected, t_m + steps_to_target * 0.1)
        else:
            projected = t_m * (1.0 + percent_margin) ** steps_to_target

    elif method == "percent-increment":
        p = percent_margin
        # If possible, derive empirical percentage margin from observed field
        if m > 1 and t_m > 0:
            empirical_p = (t_m - t_1) / ((m - 1) * t_m)
            p = min(max(empirical_p, 0.01), 0.10)
        projected = t_m * ((1.0 + p) ** steps_to_target)

    else:
        raise ValueError(f"Unknown extrapolation method: {method}")

    return round(projected, 2)


def evaluate_event(
    event_results: EventResults,
    target_rank: int = 8,
    method: str = "step-average",
    gap_threshold: float = 2.0,
    min_gap_floor: Optional[float] = None,
    percent_margin: float = 0.03
) -> ExtrapolationResult:
    """
    Evaluates an EventResults object for a given meet year, detects outliers,
    and calculates or extrapolates the qualifying time for target_rank.
    """
    swimmers = event_results.swimmers
    original_count = len(swimmers)

    if original_count == 0:
        return ExtrapolationResult(
            event_info=event_results.event_info,
            meet_year=event_results.meet_year,
            target_rank=target_rank,
            target_time_seconds=0.0,
            target_time_str="0.00",
            method_used="none",
            valid_count=0,
            original_count=0,
            is_extrapolated=True,
            pruned_ranks=[],
            audit_note="No competitors"
        )

    valid_swimmers, pruned_ranks = detect_outliers(
        swimmers,
        gap_threshold=gap_threshold,
        min_gap_floor=min_gap_floor
    )
    valid_count = len(valid_swimmers)

    if valid_count >= target_rank:
        # Direct lookup of target_rank
        target_time_sec = valid_swimmers[target_rank - 1].time_seconds
        method_used = "direct"
        is_extrapolated = False
        if pruned_ranks:
            audit_note = f"Direct (Ranks {pruned_ranks} pruned)"
        else:
            audit_note = "Direct"
    else:
        # Needs extrapolation
        target_time_sec = extrapolate_time(
            valid_swimmers,
            target_rank=target_rank,
            method=method,
            percent_margin=percent_margin
        )
        method_used = method
        is_extrapolated = True

        if pruned_ranks:
            audit_note = f"Pruned Outlier at Rank {pruned_ranks[0]} -> Extrapolated ({method})"
        else:
            audit_note = f"Sparse ({valid_count} swimmers) -> Extrapolated ({method})"

    return ExtrapolationResult(
        event_info=event_results.event_info,
        meet_year=event_results.meet_year,
        target_rank=target_rank,
        target_time_seconds=target_time_sec,
        target_time_str=seconds_to_time(target_time_sec),
        method_used=method_used,
        valid_count=valid_count,
        original_count=original_count,
        is_extrapolated=is_extrapolated,
        pruned_ranks=pruned_ranks,
        audit_note=audit_note
    )
