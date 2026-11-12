"""
Data models for swimming results and qualifying standards calculations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class SwimmerResult:
    """Represents a single athlete's result in an event."""
    rank: int
    name: str
    year_group: Optional[str] = None
    school: Optional[str] = None
    time_str: str = ""
    time_seconds: float = 0.0
    is_tied: bool = False


@dataclass
class EventInfo:
    """Canonical metadata defining a swimming event."""
    event_number: int
    raw_title: str
    gender: str          # 'Girls' or 'Boys'
    school_year: str     # 'Y7', 'Y8', or 'Y7&8'
    age_group: str       # e.g. '12 & Over', '11 & Under'
    distance: int        # e.g. 25, 50, 100
    stroke: str          # 'Breaststroke', 'Butterfly', 'Backstroke', 'Freestyle', 'IM'
    is_relay: bool = False

    @property
    def canonical_name(self) -> str:
        """Standardized descriptor matching identical events across years."""
        return f"{self.school_year} {self.gender} {self.distance}m {self.stroke}"

    @property
    def event_order_key(self) -> tuple:
        """Sort key prioritizing standard event schedule."""
        stroke_order = {"Breaststroke": 1, "Backstroke": 2, "Butterfly": 3, "Freestyle": 4, "IM": 5}
        stroke_rank = stroke_order.get(self.stroke, 99)
        return (self.distance, stroke_rank, self.gender, self.school_year)


@dataclass
class EventResults:
    """Collection of results for a single event in a specific meet year."""
    event_info: EventInfo
    meet_year: int
    swimmers: List[SwimmerResult] = field(default_factory=list)

    @property
    def finisher_count(self) -> int:
        return len(self.swimmers)


@dataclass
class ExtrapolationResult:
    """Output of evaluating or extrapolating a target rank time for an event in one year."""
    event_info: EventInfo
    meet_year: int
    target_rank: int
    target_time_seconds: float
    target_time_str: str
    method_used: str     # 'direct', 'step-average', 'linear-trend', 'percent-increment'
    valid_count: int
    original_count: int
    is_extrapolated: bool
    pruned_ranks: List[int] = field(default_factory=list)
    audit_note: str = ""


@dataclass
class AggregatedStandard:
    """Final qualifying standard for an event synthesized across multiple years."""
    event_key: str
    event_info: EventInfo
    target_rank: int
    standard_seconds: float
    standard_time_str: str
    combination_method: str
    annual_results: Dict[int, ExtrapolationResult] = field(default_factory=dict)
    std_dev_seconds: Optional[float] = None
