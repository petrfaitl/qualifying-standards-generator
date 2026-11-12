"""
swim_standards package.
Generates regional swimming qualifying standards from multi-year meet data.
"""

from .models import SwimmerResult, EventInfo, EventResults, ExtrapolationResult, AggregatedStandard
from .parser import WorkbookReader, parse_event_header, time_to_seconds, seconds_to_time

__all__ = [
    "SwimmerResult",
    "EventInfo",
    "EventResults",
    "ExtrapolationResult",
    "AggregatedStandard",
    "WorkbookReader",
    "parse_event_header",
    "time_to_seconds",
    "seconds_to_time",
]
